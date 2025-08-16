import os
import re
import json
import datetime
import logging
import requests
import pdfplumber

from urllib.parse    import urlparse
from bs4             import BeautifulSoup
from fastapi         import FastAPI
from fastapi.staticfiles import StaticFiles

# --- Configuration ---
BASE_URL        = "https://www.fsc.gov.et"
START_PAGE_URL  = f"{BASE_URL}/Digital-Law-Library/Publications/Federal-Cassation-Decision-Series/category/cassation-volumes-1"
PDF_DIR         = "downloaded_pdfs"
JSON_DIR        = "output_json"

# --- Logging Setup ---
logging.basicConfig(
    level   = logging.INFO,
    format  = '%(asctime)s - %(levelname)s - %(message)s'
)

# --- FastAPI App ---
app = FastAPI(
    title       = "Ethiopia Legal ETL",
    description = "ETL service for Federal Cassation Decisions + static manifest"
)

# Serve mcp.json & openapi.json at /manifest/{filename}
app.mount(
    "/manifest",
    StaticFiles(directory=".", html=False),
    name="manifest"
)

def scrape_pdf_links(page_url: str) -> list[str]:
    logging.info(f"Scraping {page_url} for PDF links…")
    try:
        resp = requests.get(page_url, timeout=30)
        resp.raise_for_status()
        soup  = BeautifulSoup(resp.text, "lxml")

        links = []
        for a in soup.select("a[href$='.pdf']"):
            href = a["href"]
            full = href if href.startswith("http") else f"{BASE_URL}{href}"
            if full not in links:
                links.append(full)

        logging.info(f"Found {len(links)} PDF links.")
        return links

    except requests.RequestException as e:
        logging.error(f"Error scraping {page_url}: {e}")
        return []

def extract_year_from_text(text: str) -> str:
    match = re.search(r'\b(19[5-9]\d|20\d{2})\b', text[:1000])
    return match.group(1) if match else ""

def process_pdf_url(url: str) -> None:
    try:
        fname      = os.path.basename(urlparse(url).path)
        base       = os.path.splitext(fname)[0].replace("%20", "_")
        pdf_path   = os.path.join(PDF_DIR,  fname)
        json_path  = os.path.join(JSON_DIR, f"{base}.json")

        if os.path.exists(json_path):
            logging.info(f"Skipping {base}, JSON already exists.")
            return

        logging.info(f"Downloading PDF {url} → {pdf_path}")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        if "application/pdf" not in r.headers.get("Content-Type", ""):
            logging.warning(f"Not a PDF ({url}). Skipping.")
            return

        with open(pdf_path, "wb") as f:
            f.write(r.content)

        logging.info(f"Extracting text from {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            pages = [p.extract_text() for p in pdf.pages if p.extract_text()]
        text = "\n".join(pages).strip()
        if not text:
            logging.warning(f"No extractable text in {pdf_path}. Removing.")
            os.remove(pdf_path)
            return

        doc = {
            "title"        : base.replace("_", " "),
            "year"         : extract_year_from_text(text),
            "sourceURL"    : url,
            "dateIngested" : datetime.date.today().isoformat(),
            "category"     : "CassationDecision",
            "tags"         : ["CassationDecision"],
            "content"      : text,
            "caseFields"   : {"issue": "", "holding": "", "ratio": ""},
            "legisFields"  : {"scope": "", "keyArticles": [], "effectiveDate": ""},
            "templateFields": {"placeholders": []}
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        logging.info(f"Generated JSON → {json_path}")

    except requests.RequestException as e:
        logging.error(f"Network error for {url}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error for {url}: {e}")

@app.get("/ingest")
async def ingest():
    """
    Trigger full ETL run:
    1. Scrape PDF links
    2. Download & parse into JSON
    """
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)

    links = scrape_pdf_links(START_PAGE_URL)
    for link in links:
        process_pdf_url(link)

    return {"status": "complete", "count": len(links)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host    = "0.0.0.0",
        port    = 8000,
        reload  = True
    )
