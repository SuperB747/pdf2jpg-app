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
    pdf_file = request.files['pdf']
    images = convert_from_bytes(pdf_file.read(), dpi=300)

    # 여백 제거 없이 원본 그대로 저장
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for idx, img in enumerate(images):
            img_byte = io.BytesIO()
            img.save(img_byte, format='JPEG')
            zip_file.writestr(f'page_{idx+1}.jpg', img_byte.getvalue())

    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name='converted_images.zip', mimetype='application/zip')

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
