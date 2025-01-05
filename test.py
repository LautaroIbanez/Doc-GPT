from flask import Flask, request, render_template, session, send_from_directory
from openai import OpenAI
import PyPDF2
import os
import uuid  # Para generar nombres únicos de archivo
from API_KEY import OpenAI_API_KEY


# Configuración de Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Clave secreta para usar sesiones

# Carpeta temporal para almacenar los archivos PDF
UPLOAD_FOLDER = 'uploaded_files'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de OpenAI
client = OpenAI(api_key=OpenAI_API_KEY)


def extract_text_from_pdf(file_path):
    """Extrae texto de un archivo PDF."""
    text = ""
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error procesando el PDF: {e}")
    return text

def query_chatgpt(text, question, model="gpt-4"):
    """Envía el texto y la pregunta a ChatGPT para obtener una respuesta."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de documentos técnicos."},
                {"role": "user", "content": f"Texto del documento: {text}\nPregunta: {question}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error al consultar ChatGPT: {e}"

@app.route('/', methods=['GET', 'POST'])
def upload_and_process():
    response = None
    uploaded_files = session.get('uploaded_files', [])

    if request.method == 'POST':
        # Procesar nuevos archivos solo si se seleccionaron
        files = request.files.getlist('files')
        if files and files[0].filename != '':
            for file in files:
                # Generar un nombre único para cada archivo
                filename = f"{uuid.uuid4().hex}_{file.filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                # Verificar si el archivo ya está en la lista antes de agregarlo
                if file_path not in uploaded_files:
                    uploaded_files.append(file_path)
            session['uploaded_files'] = uploaded_files

        # Realizar consulta
        question = request.form.get('question', '')
        all_text = ""

        for file_path in uploaded_files:
            all_text += extract_text_from_pdf(file_path)

        if not all_text:
            return render_template('upload.html', response="Error: No se pudo extraer texto de los archivos.", uploaded_files=uploaded_files)

        # Consulta a ChatGPT
        response = query_chatgpt(all_text, question)

    return render_template('upload.html', response=response, uploaded_files=uploaded_files)

@app.route('/download/<filename>')
def download_file(filename):
    """Permite descargar un archivo previamente subido."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
