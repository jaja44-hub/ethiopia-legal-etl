import requests
from bs4 import BeautifulSoup
import pdfplumber
import json
import datetime
import os
from urllib.parse import urlparse
import re
import logging

# --- Configuration ---
BASE_URL = "https://www.fsc.gov.et"
START_PAGE_URL = f"{BASE_URL}/Digital-Law-Library/Publications/Federal-Cassation-Decision-Series/category/cassation-volumes-1"
PDF_DIR = "downloaded_pdfs"
JSON_DIR = "output_json"

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_pdf_links(page_url):
    """Scrapes a webpage to find all links ending in .pdf."""
    logging.info(f"Scraping {page_url} for PDF links...")
    try:
        resp = requests.get(page_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        
        links = []
        for a in soup.select("a[href$='.pdf']"):
            href = a["href"]
            full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if full_url not in links:
                links.append(full_url)
            
        logging.info(f"Found {len(links)} unique PDF links.")
        return links
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to scrape {page_url}: {e}")
        return []

def extract_year_from_text(text):
    """Searches for a 4-digit year in the first 1000 characters of text."""
    match = re.search(r'\b(19[5-9]\d|20\d{2})\b', text[:1000])
    return match.group(1) if match else ""

def process_pdf_url(url):
    """Downloads a PDF from a URL, extracts text, and saves it as a structured JSON file."""
    try:
        # Generate safe filenames from the URL
        pdf_filename = os.path.basename(urlparse(url).path)
        base_name = os.path.splitext(pdf_filename)[0].replace('%20', '_')
        pdf_filepath = os.path.join(PDF_DIR, pdf_filename)
        json_filepath = os.path.join(JSON_DIR, f"{base_name}.json")

        if os.path.exists(json_filepath):
            logging.info(f"Skipping {url}, output file already exists.")
            return

        logging.info(f"--- Processing {url} ---")

        # Download PDF
        logging.info(f"Downloading to {pdf_filepath}...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()

        if 'application/pdf' not in r.headers.get('Content-Type', ''):
            logging.warning(f"Content-Type is not PDF for {url}. Skipping.")
            return

        with open(pdf_filepath, "wb") as f:
            f.write(r.content)

        # Extract text
        logging.info(f"Extracting text from {pdf_filepath}...")
        text = ""
        with pdfplumber.open(pdf_filepath) as pdf:
            pages_text = [p.extract_text() for p in pdf.pages if p.extract_text()]
            text = "\n".join(pages_text)

        if not text.strip():
            logging.warning(f"No text could be extracted from {pdf_filepath}. Skipping.")
            os.remove(pdf_filepath) # Clean up empty PDF
            return

        # Build JSON document
        doc = {
            "title": base_name.replace('_', ' '),
            "year": extract_year_from_text(text),
            "sourceURL": url,
            "dateIngested": datetime.date.today().isoformat(),
            "category": "CassationDecision",
            "tags": ["CassationDecision"],
            "content": text,
            "caseFields": {"issue": "", "holding": "", "ratio": ""},
            "legisFields": {"scope": "", "keyArticles": [], "effectiveDate": ""},
            "templateFields": {"placeholders": []}
        }

        # Write JSON to file
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        logging.info(f"Successfully generated {json_filepath}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error for {url}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing {url}: {e}")

if __name__ == "__main__":
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)
    
    pdf_urls = scrape_pdf_links(START_PAGE_URL)
    for url in pdf_urls:
        process_pdf_url(url)
    
    logging.info("--- ETL process complete. ---")