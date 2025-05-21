from flask import Flask, render_template, request, send_file
from pdf2image import convert_from_bytes
import io
import zipfile
from PIL import Image, ImageChops

app = Flask(__name__)

def trim(im):
    """이미지의 공백을 제거합니다."""
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
    pdf_file = request.files['pdf']
    images = convert_from_bytes(pdf_file.read(), dpi=300)

    # 공백 제거
    trimmed_images = [trim(img) for img in images]

    # 이미지들을 zip으로 압축
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for idx, img in enumerate(trimmed_images):
            img_byte = io.BytesIO()
            img.save(img_byte, format='JPEG')
            zip_file.writestr(f'page_{idx+1}.jpg', img_byte.getvalue())

    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name='converted_images.zip', mimetype='application/zip')

# ✅ ads.txt 요청 처리 라우트
@app.route('/ads.txt')
def ads_txt():
    return send_file('static/ads.txt')

if __name__ == '__main__':
    app.run(debug=True)
