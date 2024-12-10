import re
import os
import requests
import io
from flask import Flask, render_template, request, send_file, jsonify
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY
import urllib.parse
from zipfile import ZipFile

app = Flask(__name__)

# Ensure generated PDFs directory exists
os.makedirs('generated_pdfs', exist_ok=True)


def sanitize_filename(url):
    """
    Create a filename from the URL, extracting meaningful parts
    """
    try:
        # Parse the URL
        parsed_url = urllib.parse.urlparse(url)

        # Extract path and remove leading/trailing slashes
        path = parsed_url.path.strip('/')

        # Split path and get meaningful parts
        path_parts = path.split('/')

        # Try to find a meaningful identifier (last part or a specific segment)
        filename = path_parts[-1] if path_parts else 'article'

        # Remove any non-alphanumeric characters except hyphens
        filename = re.sub(r'[^\w\-]', '', filename)

        # Truncate to reasonable length
        filename = filename[:100]

        return filename
    except Exception as e:
        print(f"Error creating filename from URL: {e}")
        return 'article_' + str(hash(url))

def download_image(image_url, base_url):
    """
    Download and process an image, handling relative URLs
    """
    try:
        # Handle relative URLs
        if not image_url.startswith(('http://', 'https://')):
            image_url = urllib.parse.urljoin(base_url, image_url)

        # Download image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=10)

        # Check if image download was successful
        if response.status_code == 200:
            # Check image size and type
            img_data = response.content
            img = Image(io.BytesIO(img_data))

            # Resize if image is too large
            if img.drawWidth > 1*inch or img.drawHeight > 1*inch:
                img.drawWidth = min(img.drawWidth, 1*inch)
                img.drawHeight = min(img.drawHeight, 1*inch)

            return img
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
    return None

def extract_article_content(url):
    """
    Extract main article content, including images
    """
    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement', 'ads']):
            script.decompose()

        # Try to find the main article content
        article_content = soup.find(['article', 'main', 'div.content', 'div.article-body', 'div.post-content'])

        if not article_content:
            # Fallback to body if no specific article tag found
            article_content = soup.body

        return article_content, url

    except requests.RequestException as e:
        print(f"Request Error extracting content from {url}: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected Error extracting content from {url}: {e}")
        return None, None

def create_printer_friendly_pdf(content, base_url, filename):
    """
    Create a comprehensive, printer-friendly PDF
    """
    try:
        pdf_path = os.path.join('generated_pdfs', filename + '.pdf')
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)

        # Define styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            'Justify',
            parent=styles['Normal'],
            alignment=TA_JUSTIFY
        ))

        # Story elements to be added to PDF
        story = []

        # Process text and images
        for element in content.find_all(['p', 'img', 'h1', 'h2', 'h3']):
            if element.name == 'p':
                # Add text paragraphs
                text = element.get_text(strip=True)
                if text:
                    story.append(Paragraph(text, styles['Justify']))
                    story.append(Spacer(1, 0.25*inch))

            elif element.name == 'img':
                # Try to download and add images
                img_url = element.get('src')
                if img_url:
                    img = download_image(img_url, base_url)
                    if img:
                        story.append(img)
                        story.append(Spacer(1, 0.25*inch))

        # Build PDF
        doc.build(story)
        return pdf_path

    except Exception as e:
        print(f"Error creating PDF: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get URLs from form
        urls = [request.form.get(f'url{i}') for i in range(1, 6) if request.form.get(f'url{i}')]

        generated_pdfs = []
        conversion_errors = []
        for i, url in enumerate(urls, 1):
            if url:
                # Extract content
                content, base_url = extract_article_content(url)
                if content:
                    # Create PDF filename using URL details
                    pdf_filename = sanitize_filename(url)

                    # Generate printer-friendly PDF
                    pdf_path = create_printer_friendly_pdf(content, base_url, pdf_filename)

                    if pdf_path:
                        generated_pdfs.append(os.path.basename(pdf_path))
                else:
                    # Track URLs that failed conversion
                    conversion_errors.append(f"Unable to convert URL: {url}")

        return render_template('index.html', pdfs=generated_pdfs, errors=conversion_errors)

    return render_template('index.html')
@app.route('/zip_pdfs', methods=['POST'])
def zip_pdfs():
    try:
        pdf_urls = request.json['pdf_urls']

        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            for url in pdf_urls:
                filename = os.path.basename(url)
                pdf_path = os.path.join('generated_pdfs', filename)
                zip_file.write(pdf_path, filename)

        zip_buffer.seek(0)

        return send_file(zip_buffer, as_attachment=True, download_name='downloaded_pdfs.zip', mimetype='application/zip')

    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/download/<filename>')
def download_pdf(filename):
    try:
        return send_file(os.path.join('generated_pdfs', filename),
                         as_attachment=True,
                         download_name=filename)
    except Exception as e:
        return str(e), 404

if __name__ == '__main__':
    app.run(debug=True)