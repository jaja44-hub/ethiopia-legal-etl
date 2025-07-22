import requests
from bs4 import BeautifulSoup
import json

page_url = "https://www.fsc.gov.et/Digital-Law-Library/Publications/Federal-Cassation-Decision-Series/category/cassation-volumes-1"

resp = requests.get(page_url)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "lxml")

links = []
for a in soup.select("a[href$='.pdf']"):
    href = a["href"]
    full = href if isinstance(href, str) and href.startswith("http") else f"https://www.fsc.gov.et{href}"
    links.append(full)

with open("pdf_links.json", "w", encoding="utf-8") as f:
    json.dump(links, f, indent=2)

print(f"Extracted {len(links)} PDF URLs to pdf_links.json")
