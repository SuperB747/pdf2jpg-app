from flask import Flask, render_template, request, send_file
from pdf2image import convert_from_bytes
import io
import zipfile

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'pdf' not in request.files:
        return "No file part in the request.", 400

    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return "No selected file.", 400

    if not pdf_file.filename.lower().endswith('.pdf'):
        return "Invalid file type. Only PDF files are allowed.", 400

    output_format = request.form.get('format', 'jpg').lower()
    if output_format not in ['jpg', 'png']:
        return "Invalid format type. Only JPG or PNG is allowed.", 400

    try:
        images = convert_from_bytes(pdf_file.read(), dpi=300)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for idx, img in enumerate(images):
                img_byte = io.BytesIO()
                img.save(img_byte, format=output_format.upper())
                zip_file.writestr(f'page_{idx+1}.{output_format}', img_byte.getvalue())

        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name='converted_images.zip', mimetype='application/zip')
    except Exception as e:
        return f"An error occurred during conversion: {str(e)}", 500

# ✅ ads.txt 라우트
@app.route('/ads.txt')
def ads_txt():
    return send_file('static/ads.txt')

# ✅ sitemap.xml 라우트
@app.route('/sitemap.xml')
def sitemap():
    return send_file('static/sitemap.xml')

if __name__ == '__main__':
    app.run(debug=True)
