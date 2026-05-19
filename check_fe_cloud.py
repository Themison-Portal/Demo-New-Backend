import urllib.request
import re
from html.parser import HTMLParser

class ScriptExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_srcs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            for attr in attrs:
                if attr[0] == 'src' and attr[1]:
                    self.script_srcs.append(attr[1])

def check_url(url):
    print(f"Checking {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        h = urllib.request.urlopen(req).read().decode('utf-8')
        p = ScriptExtractor()
        p.feed(h)
        print(f"Found scripts: {p.script_srcs}")
        for src in p.script_srcs:
            if not src.startswith('http'):
                from urllib.parse import urljoin
                src = urljoin(url, src)
            print(f"Reading JS: {src}")
            js = urllib.request.urlopen(src).read().decode('utf-8')
            # Look for API URLs
            backends = re.findall(r'https?://[a-zA-Z0-9.-]+\.run\.app', js)
            backends += re.findall(r'https?://[a-zA-Z0-9.-]+\.onrender\.com', js)
            if backends:
                print(f"  Found backends: {set(backends)}")
    except Exception as e:
        print(f"  Error: {e}")

check_url('https://themison-frontend-eu-768873408671.europe-west1.run.app/signin')
