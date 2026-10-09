from curl_cffi import requests
from html.parser import HTMLParser
from urllib.parse import urlparse

URLS = [
    ("Known Surakarta article", "https://rri.co.id/surakarta/regional/2796447/icp-starlight-travel-in-space-bahasa-inggris-jadi-pengalaman-nyata?nocache=true"),
    ("RRI homepage", "https://rri.co.id/"),
    ("Surakarta latest list", "https://rri.co.id/surakarta/terbaru/list/"),
]

class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.parts.append(data.strip())

for label, url in URLS:
    print("=" * 72)
    print(f"CHECK: {label}")
    print(f"REQUESTED_URL: {url}")
    try:
        response = requests.get(
            url,
            impersonate="chrome",
            timeout=25,
            allow_redirects=True,
            headers={"Accept-Language": "id-ID,id;q=0.9,en-US;q=0.7,en;q=0.6"},
        )
        parser = TitleParser()
        parser.feed(response.text[:300000])
        title = " ".join(part for part in parser.parts if part)
        print(f"STATUS: {response.status_code}")
        print(f"FINAL_URL: {response.url}")
        print(f"CONTENT_TYPE: {response.headers.get('content-type', '')}")
        print(f"TITLE: {title[:240] or '(no title found)'}")
        print(f"BODY_SNIPPET: {' '.join(response.text[:500].split())}")
        if response.status_code == 200 and ("Just a moment..." not in title):
            print("RESULT: HTTP 200 without the standard Cloudflare challenge title; inspect body to confirm it is the actual page.")
        elif response.status_code == 403 or "Just a moment..." in title:
            print("RESULT: Access still appears blocked by the site's protection.")
        else:
            print("RESULT: Review status/title/body above.")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
print("=" * 72)
print("Diagnostic finished. This script is read-only and does not write repository data.")
