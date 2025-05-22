@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf():
    if request.method == 'POST':
        from fpdf import FPDF
        from PIL import Image
        import uuid
        import os

        images = []
        i = 0
        while f'images[{i}]' in request.files:
            images.append(request.files[f'images[{i}]'])
            i += 1

        if not images:
            return "No images uploaded", 400

        pdf = None
        page_width, page_height = 612, 792  # Letter size

        try:
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
