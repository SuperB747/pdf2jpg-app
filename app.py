from flask import Flask, render_template, request, send_file, abort, make_response, send_from_directory, Response
from pdf2image import convert_from_bytes
from fpdf import FPDF
from PIL import Image
import io
import zipfile
import uuid
import os
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15MB


@app.errorhandler(413)
def request_entity_too_large(error):
    return "File size exceeds the limit (15MB). Please try a smaller file.", 413



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


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
    if file_size > 15 * 1024 * 1024:
        return "File is too large. Maximum upload size is 15MB.", 400

    output_format = request.form.get('format', 'jpg').lower()
    if output_format not in ['jpg', 'png']:
        return "Invalid format type. Only JPG or PNG is allowed.", 400

    try:

        pdf_bytes = pdf_file.read()
        images = convert_from_bytes(pdf_bytes, dpi=150, timeout=60)

        pillow_format = 'JPEG' if output_format == 'jpg' else 'PNG'
        ext = 'jpg' if output_format == 'jpg' else 'png'

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for idx, img in enumerate(images):
                img_byte = io.BytesIO()
                img.save(img_byte, format=pillow_format)
                zip_file.writestr(f'page_{idx + 1}.{ext}', img_byte.getvalue())

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
    if request.method == 'POST':
        images = []
        i = 0
        while f'images[{i}]' in request.files:
            images.append(request.files[f'images[{i}]'])
            i += 1

        if not images:
            return "No images uploaded", 400

        try:



            pdf = FPDF(unit='pt', format=(612, 792))
            for image in images:


                pdf.add_page()

                img = Image.open(image.stream).convert('RGB')
                img_width, img_height = img.size


                scale = min(612 / img_width, 792 / img_height)
                new_width = img_width * scale
                new_height = img_height * scale


                x = (612 - new_width) / 2
                y = (792 - new_height) / 2

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



@app.route('/ads.txt')
def ads_txt():
    return send_file('static/ads.txt', mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap():
    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
    <url>
        <loc>https://freepdf2jpg.ca/</loc>
        <lastmod>2025-05-26</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
        <xhtml:link rel="alternate" hreflang="en" href="https://freepdf2jpg.ca/"/>
        <xhtml:link rel="alternate" hreflang="fr" href="https://freepdf2jpg.ca/fr/"/>
        <xhtml:link rel="alternate" hreflang="es" href="https://freepdf2jpg.ca/es/"/>
        <xhtml:link rel="alternate" hreflang="ko" href="https://freepdf2jpg.ca/ko/"/>
        <xhtml:link rel="alternate" hreflang="ja" href="https://freepdf2jpg.ca/ja/"/>
        <xhtml:link rel="alternate" hreflang="zh" href="https://freepdf2jpg.ca/zh/"/>
    </url>
    <url>
        <loc>https://freepdf2jpg.ca/jpg-to-pdf</loc>
        <lastmod>2025-05-26</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>https://freepdf2jpg.ca/about</loc>
        <lastmod>2025-05-26</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
</urlset>'''

    response = Response(sitemap_xml, content_type='application/xml; charset=utf-8')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.route('/robots.txt')
def robots():
    return send_file('static/robots.txt', mimetype='text/plain')


if __name__ == '__main__':
    app.run(debug=True)
