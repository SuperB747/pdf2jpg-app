from flask import Flask, Response
from flask import render_template
app = Flask(__name__)

@app.route('/sitemap.xml')
def sitemap():
    from datetime import date
    from xml.etree.ElementTree import Element, SubElement, tostring
    import xml.dom.minidom

    urlset = Element('urlset')
    urlset.set('xmlns', "http://www.sitemaps.org/schemas/sitemap/0.9")
    urlset.set('xmlns:xhtml', "http://www.w3.org/1999/xhtml")

    urls = [
        {
            "loc": "https://freepdf2jpg.ca/",
            "lastmod": date.today().isoformat(),
            "changefreq": "weekly",
            "priority": "1.0",
            "hreflangs": {
                "en": "https://freepdf2jpg.ca/",
                "fr": "https://freepdf2jpg.ca/fr/",
                "es": "https://freepdf2jpg.ca/es/",
                "ko": "https://freepdf2jpg.ca/ko/",
                "ja": "https://freepdf2jpg.ca/ja/",
                "zh": "https://freepdf2jpg.ca/zh/"
            }
        },
        {
            "loc": "https://freepdf2jpg.ca/jpg-to-pdf",
            "lastmod": date.today().isoformat(),
            "changefreq": "weekly",
            "priority": "0.9"
        },
        {
            "loc": "https://freepdf2jpg.ca/about",
            "lastmod": date.today().isoformat(),
            "changefreq": "monthly",
            "priority": "0.8",
            "hreflangs": {
                "en": "https://freepdf2jpg.ca/about",
                "fr": "https://freepdf2jpg.ca/fr/about",
                "es": "https://freepdf2jpg.ca/es/about",
                "ko": "https://freepdf2jpg.ca/ko/about",
                "ja": "https://freepdf2jpg.ca/ja/about",
                "zh": "https://freepdf2jpg.ca/zh/about"
            }
        }
    ]

    for url in urls:
        url_el = SubElement(urlset, 'url')
        SubElement(url_el, 'loc').text = url["loc"]
        SubElement(url_el, 'lastmod').text = url["lastmod"]
        SubElement(url_el, 'changefreq').text = url["changefreq"]
        SubElement(url_el, 'priority').text = url["priority"]
        if 'hreflangs' in url:
            for lang, href in url["hreflangs"].items():
                hreflang_el = SubElement(url_el, '{http://www.w3.org/1999/xhtml}link')
                hreflang_el.set('rel', 'alternate')
                hreflang_el.set('hreflang', lang)
                hreflang_el.set('href', href)

    rough_string = tostring(urlset, 'utf-8')
    reparsed = xml.dom.minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    response = Response(pretty_xml, mimetype='application/xml')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

from flask import request, send_file
from pdf2image import convert_from_bytes
from PIL import Image
import io
import zipfile

@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf():
    if request.method == 'POST':
        if 'images' not in request.files:
            return "No file part", 400

        files = request.files.getlist('images')
        if not files:
            return "No files uploaded", 400

        images = []
        for file in files:
            img = Image.open(file.stream).convert('RGB')
            images.append(img)

        if not images:
            return "No valid images", 400

        output_pdf = io.BytesIO()
        images[0].save(output_pdf, format='PDF', save_all=True, append_images=images[1:])
        output_pdf.seek(0)

        return send_file(output_pdf, mimetype='application/pdf', as_attachment=True, download_name='merged.pdf')

    return render_template('jpg_to_pdf.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'pdf' not in request.files:
        return "No file part in the request.", 400

    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return "No selected file.", 400

    images = convert_from_bytes(pdf_file.read(), dpi=150)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for i, img in enumerate(images):
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)
            zipf.writestr(f"page_{i+1}.jpg", img_io.read())
    zip_buffer.seek(0)

    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='converted_images.zip')

if __name__ == '__main__':
    app.run(debug=True)
