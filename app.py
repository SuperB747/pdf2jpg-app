from flask import Flask, render_template, request, send_file, abort
from pdf2image import convert_from_bytes
from fpdf import FPDF
from PIL import Image
import io
import zipfile
import uuid
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB 제한

# 에러 처리: 파일 크기 초과
@app.errorhandler(413)
def request_entity_too_large(error):
    return "File is too large. Maximum upload size is 10MB.", 413


# 홈 페이지
@app.route('/')
def index():
    return render_template('index.html')


# PDF → JPG 또는 PNG 변환
@app.route('/convert', methods=['POST'])
def convert():
    if 'pdf' not in request.files:
        return "No file part in the request.", 400

    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return "No selected file.", 400

    if not pdf_file.filename.lower().endswith('.pdf'):
        return "Invalid file type. Only PDF files are allowed.", 400

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
        pillow_format = 'JPEG' if output_format == 'jpg' else 'PNG'
        ext = 'jpg' if output_format == 'jpg' else 'png'

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for idx, img in enumerate(images):
                img_byte = io.BytesIO()
                img.save(img_byte, format=pillow_format)
                zip_file.writestr(f'page_{idx+1}.{ext}', img_byte.getvalue())

        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name='converted_images.zip', mimetype='application/zip')

    except Exception as e:
        return f"An error occurred during conversion: {str(e)}", 500


# JPG → PDF 변환
@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf():
    if request.method == 'POST':
        images = []
        i = 0
        while f'images[{i}]' in request.files:
            images.append(request.files[f'images[{i}]'])
            i += 1

        if not images:
            return "No images uploaded", 400

        try:
            pdf = None
            page_width, page_height = 612, 792  # Letter size

            for image in images:
                if not pdf:
                    pdf = FPDF(unit='pt', format=(page_width, page_height))
                pdf.add_page()

                img = Image.open(image.stream).convert('RGB')
                img_width, img_height = img.size

                scale = min(page_width / img_width, page_height / img_height)
                new_width = img_width * scale
                new_height = img_height * scale
                x = (page_width - new_width) / 2
                y = (page_height - new_height) / 2

                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG')
                img_buffer.seek(0)

                temp_path = f"/tmp/{uuid.uuid4().hex}.jpeg"
                with open(temp_path, 'wb') as f:
                    f.write(img_buffer.read())

                pdf.image(temp_path, x, y, w=new_width, h=new_height)
                os.remove(temp_path)

            output = io.BytesIO()
            pdf.output(output, 'F')
            output.seek(0)

            return send_file(output, as_attachment=True, download_name='merged_output.pdf', mimetype='application/pdf')

        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    return render_template('jpg_to_pdf.html')


# 기타 정적 파일 라우트
@app.route('/ads.txt')
def ads_txt():
    return send_file('static/ads.txt')


@app.route('/sitemap.xml')
def sitemap():
    return send_file('static/sitemap.xml')


@app.route('/robots.txt')
def robots():
    return send_file('static/robots.txt')


if __name__ == '__main__':
    app.run(debug=True)
