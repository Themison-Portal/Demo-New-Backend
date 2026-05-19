import urllib.request
import re

url = "https://core-frontend-v3.vercel.app/assets/index-DeI7l8Uo.js"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
response = urllib.request.urlopen(req)
js_content = response.read().decode('utf-8')

urls = set(re.findall(r'https?://[^\s"\'<>`{}|]+', js_content))
for u in urls:
    if "vercel" not in u and "react" not in u and "auth0" not in u and "w3.org" not in u and "fonts" not in u and "github" not in u:
        print(u)
