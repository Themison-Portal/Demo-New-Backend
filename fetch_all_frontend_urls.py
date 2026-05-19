import urllib.request
import re
import time
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

def fetch_js_urls(base_url):
    try:
        req = urllib.request.Request(f"{base_url}?cb={int(time.time())}", headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        response = urllib.request.urlopen(req)
        html = response.read().decode('utf-8')
        
        parser = ScriptExtractor()
        parser.feed(html)
        
        found_urls = set()
        for src in parser.script_srcs:
            if not src.startswith('http'):
                src = base_url.rstrip('/') + '/' + src.lstrip('/')
            
            js_req = urllib.request.Request(src, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            js_response = urllib.request.urlopen(js_req)
            js_content = js_response.read().decode('utf-8')
            
            urls = set(re.findall(r'https?://[^\s"\'<>`{}|]+', js_content))
            for u in urls:
                if 'run.app' in u or 'onrender' in u or 'core-backend' in u:
                    found_urls.add(u)
                    
        return found_urls
    except Exception as e:
        return str(e)

print("Found backend URLs:")
print(fetch_js_urls('https://themison-frontend-eu-768873408671.europe-west1.run.app'))
