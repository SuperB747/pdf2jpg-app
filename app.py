from flask import Flask, render_template, request, send_file, abort
from pdf2image import convert_from_bytes
import io
import zipfile

app = Flask(__name__)

# Set maximum upload size to 10MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

@app.errorhandler(413)
def request_entity_too_large(error):
    return "File is too large. Maximum upload size is 10MB.", 413

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

    # 추가적인 파일 크기 체크 (혹시 모를 예외 상황 대비)
    pdf_file.seek(0, io.SEEK_END)
    file_size = pdf_file.tell()
    pdf_file.seek(0)
    if file_size > 10 * 1024 * 1024:
        return "File is too large. Maximum upload size is 10MB.", 400

    output_format = request.form.get('format', 'jpg').lower()
    if output_format not in ['jpg', 'png']:
        return "Invalid format type. Only JPG or PNG is allowed.", 400

    try:
        images = convert_from_bytes(pdf_file.read(), dpi=300)

        # 여백 제거 없이 원본 그대로 저장
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for idx, img in enumerate(images):
                img_byte = io.BytesIO()
                img.save(img_byte, format='JPEG' if output_format == 'jpg' else 'PNG')
                ext = 'jpg' if output_format == 'jpg' else 'png'
                zip_file.writestr(f'page_{idx+1}.{ext}', img_byte.getvalue())

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='converted_images.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        return f"An error occurred during conversion: {str(e)}", 500

@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf():
    return render_template('jpg_to_pdf.html')

@app.route('/ads.txt')
def ads_txt():
    return send_file('static/ads.txt')

@app.route('/sitemap.xml')
def sitemap():
    return send_file('static/sitemap.xml')

if __name__ == '__main__':
    app.run(debug=True)
