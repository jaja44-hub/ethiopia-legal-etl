import requests
import pdfplumber
import json
import datetime
import os
from urllib.parse import urlparse

# Create output directories if they don't exist
os.makedirs("downloaded_pdfs", exist_ok=True)
os.makedirs("output_json", exist_ok=True)

# 1. Load the links from the scraper's output
try:
    with open("pdf_links.json", "r", encoding="utf-8") as f:
        links = json.load(f)
except FileNotFoundError:
    print("❌ Error: pdf_links.json not found. Please run scrape_pdf_links.py first.")
    exit(1)

for url in links:
    try:
        # Generate safe filenames from the URL
        pdf_filename = os.path.basename(urlparse(url).path)
        base_name = os.path.splitext(pdf_filename)[0].replace('%20', '_')
        pdf_filepath = os.path.join("downloaded_pdfs", pdf_filename)
        json_filepath = os.path.join("output_json", f"{base_name}.json")

        print(f"--- Processing {url} ---")

        # 2. Download PDF
        print(f"Downloading to {pdf_filepath}...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()

        if 'application/pdf' not in r.headers.get('Content-Type', ''):
            print(f"⚠️ Warning: Content-Type is not PDF for {url}. Skipping.")
            continue

        with open(pdf_filepath, "wb") as f:
            f.write(r.content)

        # 3. Extract text
        print(f"Extracting text from {pdf_filepath}...")
        text = ""
        with pdfplumber.open(pdf_filepath) as pdf:
            pages_text = [p.extract_text() for p in pdf.pages if p.extract_text()]
            text = "\n".join(pages_text)

        if not text.strip():
            print(f"⚠️ Warning: No text could be extracted from {pdf_filepath}. Skipping.")
            continue

        # 4. Build JSON document
        doc = {
            "title": base_name.replace('_', ' '),
            "year": "", # This could be inferred from the text later
            "sourceURL": url,
            "dateIngested": datetime.date.today().isoformat(),
            "category": "CassationDecision",
            "tags": ["CassationDecision"],
            "content": text,
            "caseFields": {"issue": "", "holding": "", "ratio": ""},
            "legisFields": {"scope": "", "keyArticles": [], "effectiveDate": ""},
            "templateFields": {"placeholders": []}
        }

        # 5. Write JSON to file
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        print(f"✅ Generated {json_filepath}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error for {url}: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred while processing {url}: {e}")
