from flask import Flask, render_template, request, send_file
from pdf2image import convert_from_bytes
import io
import zipfile
from PIL import Image, ImageChops

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 최대 10MB 업로드 허용

def trim(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    try:
        pdf_file = request.files['pdf']

        # 파일 확장자 체크
        if not pdf_file.filename.lower().endswith('.pdf'):
            return "Only PDF files are supported", 400

        # 이미지 변환 및 트리밍
        images = convert_from_bytes(pdf_file.read(), dpi=300)
        images = [trim(img) for img in images]

        # ZIP 파일 생성
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for i, img in enumerate(images):
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG')
                img_bytes.seek(0)
                zip_file.writestr(f'page_{i+1}.jpg', img_bytes.read())
        zip_buffer.seek(0)

        return send_file(zip_buffer, mimetype='application/zip',
                         download_name='converted_images.zip', as_attachment=True)
    except Exception as e:
        return f"Error: {str(e)}", 500
