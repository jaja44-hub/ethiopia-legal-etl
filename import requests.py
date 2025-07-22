import requests
from bs4 import BeautifulSoup
import pdfplumber # type: ignore
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

def scrape_pdf_links(session: requests.Session, page_url: str) -> list[str]:
    """Scrapes a webpage to find all links ending in .pdf."""
    logging.info(f"Scraping for PDF links at: {page_url}")
    links = []
    try:
        resp = session.get(page_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for a in soup.select("a[href$='.pdf']"):
            href = a.get("href")
            if href:
                # Ensure the URL is absolute
                full_url = href if isinstance(href, str) and href.startswith("http") else f"{BASE_URL}{href}"
                links.append(full_url)
        logging.info(f"Found {len(links)} PDF links.")
        return links
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch page {page_url}: {e}")
    return links

def extract_year_from_text(text: str) -> str:
    """Searches for the first 4-digit number that looks like a year."""
    # Regex for a 4-digit number between 1950 and 2099
    match = re.search(r'\b(19[5-9]\d|20\d{2})\b', text[:1000])
    return match.group(1) if match else ""

def process_pdf_url(session: requests.Session, url: str):
    """Downloads a PDF, extracts its text, and saves it as a structured JSON file."""
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
        r = session.get(url, timeout=60)
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
            # Clean up the empty or corrupted PDF file
            os.remove(pdf_filepath)
            return

        year = extract_year_from_text(text)

        # Build JSON document
        doc = {
            "title": base_name.replace('_', ' '),
            "year": year,
            "sourceURL": url,
            "dateIngested": datetime.date.today().isoformat(),
            "category": "CassationDecision",
            "tags": ["CassationDecision"],
            "content": text,
            "caseFields": {"issue": "", "holding": "", "ratio": ""},
            "legisFields": {"scope": "", "keyArticles": [], "effectiveDate": ""},
            "templateFields": {"placeholders": []}
        }

        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        logging.info(f"Successfully generated {json_filepath}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error for {url}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing {url}: {e}")

def main():
    """Main function to run the ETL process."""
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)

    with requests.Session() as session:
        pdf_links = scrape_pdf_links(session, START_PAGE_URL)
        for link in pdf_links:
            process_pdf_url(session, link)
    
    logging.info("--- ETL process has completed. ---")

if __name__ == "__main__":
    main()