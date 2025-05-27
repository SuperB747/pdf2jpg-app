import json
import os
from flask import Flask, Response
from flask import render_template
from flask import redirect, request

app = Flask(__name__)

@app.before_request
def redirect_to_canonical_domain():
    preferred_domain = "freepdf2jpg.ca"
    if request.host.startswith("www."):
        return redirect(f"https://{preferred_domain}{request.path}", code=301)

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

from flask import request, send_file, jsonify
from pdf2image import convert_from_bytes
from PIL import Image
import io
import zipfile

@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf():
    if request.method == 'POST':
        if 'images' not in request.files:
            return jsonify(error="No file part"), 400

        files = request.files.getlist('images')
        if not files:
            return jsonify(error="No files uploaded"), 400

        # US Letter size at 150dpi: 1275 x 1650 pixels (8.5 x 11 inches)
        base_width, base_height = 1275, 1650  # US Letter at 150dpi (8.5 x 11 inches)
        images = []
        for file in files:
            original = Image.open(file.stream).convert('RGB')
            base_width, base_height = 1275, 1650  # US Letter at 150dpi
            canvas = Image.new('RGB', (base_width, base_height), 'white')

            ratio = min(base_width / original.width, base_height / original.height)
            new_size = (int(original.width * ratio), int(original.height * ratio))
            resized = original.resize(new_size, Image.LANCZOS)

            offset = ((base_width - new_size[0]) // 2, (base_height - new_size[1]) // 2)
            canvas.paste(resized, offset)
            images.append(canvas)

        if not images:
            return jsonify(error="No valid images"), 400

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


@app.route('/rate', methods=['GET', 'POST'])
def rate():
    from datetime import datetime
    ratings_file = 'ratings.json'
    vote_log_file = 'vote_log.json'

    if not os.path.exists(ratings_file):
        with open(ratings_file, 'w') as f:
            json.dump({"summary": {"total_votes": 0, "total_score": 0}}, f)

    if not os.path.exists(vote_log_file):
        with open(vote_log_file, 'w') as f:
            json.dump({}, f)

    with open(ratings_file, 'r') as f:
        data = json.load(f)
        summary = data.get("summary", {"total_votes": 0, "total_score": 0})

    with open(vote_log_file, 'r') as f:
        vote_log = json.load(f)

    client_ip = request.remote_addr
    today = datetime.utcnow().strftime('%Y-%m-%d')

    if request.method == 'POST':
        lang = request.cookies.get("pdf2jpg_lang") or request.args.get("lang", "en")
        messages = {
            "en": "You have already voted today.",
            "fr": "Vous avez déjà voté aujourd'hui.",
            "es": "Ya has votado hoy.",
            "ko": "오늘은 이미 투표하셨습니다.",
            "ja": "今日はすでに投票済みです。",
            "zh": "您今天已经投过票了。"
        }
        if vote_log.get(client_ip) == today:
            app.logger.info("Duplicate vote attempt detected (IP suppressed).")
            return jsonify(error=messages.get(lang, messages["en"])), 403

        req = request.get_json()
        rating = int(req.get('rating', 0))
        if not (1 <= rating <= 5):
            return jsonify(error="Invalid rating"), 400

        summary["total_votes"] += 1
        summary["total_score"] += rating
        vote_log[client_ip] = today

        with open(ratings_file, 'w') as f:
            json.dump({"summary": summary}, f)
        with open(vote_log_file, 'w') as f:
            json.dump(vote_log, f)

    average = summary["total_score"] / summary["total_votes"] if summary["total_votes"] else 0
    return jsonify(average=average, count=summary["total_votes"])


# Error handlers
@app.errorhandler(403)
def handle_403(e):
    return jsonify(error="Forbidden"), 403

@app.errorhandler(400)
def handle_400(e):
    return jsonify(error="Bad Request"), 400

from flask import send_from_directory

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory('static', 'robots.txt')

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory('static', 'ads.txt')

# Run the app
if __name__ == '__main__':
    import os
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
