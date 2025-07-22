# Filename: mcp_server.py

from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
import datetime
import pdfplumber
import requests

app = FastAPI(title="Ethiopia Legal ETL MCP Tool")

class DocumentRequest(BaseModel):
    volume: str
    pdf_url: str
    source: Optional[str] = "FSC Cassation Volume"

@app.post("/ingest")
def ingest_document(req: DocumentRequest):
    try:
        r = requests.get(req.pdf_url)
        pdf_filename = f"{req.volume}.pdf"
        open(pdf_filename, "wb").write(r.content)
    except Exception as e:
        return {"error": f"Download failed: {e}"}

    try:
        with pdfplumber.open(pdf_filename) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        return {"error": f"PDF parse failed: {e}"}

    doc = {
        "title": req.volume,
        "sourceURL": req.pdf_url,
        "category": "CassationDecision",
        "dateIngested": datetime.date.today().isoformat(),
        "content": text,
        "caseFields": {"issue": "", "holding": "", "ratio": ""},
        "legisFields": {"scope": "", "keyArticles": [], "effectiveDate": ""},
        "templateFields": {"placeholders": []}
    }

    return doc
