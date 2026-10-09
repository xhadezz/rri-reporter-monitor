from curl_cffi import requests
from bs4 import BeautifulSoup

URLS = [
    ("RRI homepage", "https://rri.co.id/"),
    ("Global latest list", "https://rri.co.id/terbaru/list"),
    ("Surakarta latest list", "https://rri.co.id/surakarta/terbaru/list/"),
]
HEADERS = {
    "User-Agent": "RRI-Reporter-Monitor-Connectivity-Test/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

for label, url in URLS:
    print("=" * 70)
    print(f"CHECK: {label}")
    print(f"REQUESTED_URL: {url}")
    try:
        # Probe transport compatibility only; does not impersonate a browser
        # or attempt to solve/bypass Cloudflare challenges.
        response = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        soup = BeautifulSoup(response.text or "", "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        print(f"STATUS: {response.status_code}")
        print(f"FINAL_URL: {response.url}")
        print(f"CONTENT_TYPE: {response.headers.get('content-type', '')}")
        print(f"TITLE: {title[:200]}")
        print(f"BODY_SNIPPET: {(response.text or '')[:220].replace(chr(10), ' ')}")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
print("Diagnostic finished. No repository data files were changed.")
