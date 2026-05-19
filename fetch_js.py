import urllib.request
import re

url = "https://core-frontend-v3.vercel.app/assets/index-DeI7l8Uo.js"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
response = urllib.request.urlopen(req)
js_content = response.read().decode('utf-8')

# Search for potential backend URLs
urls = re.findall(r'https?://[a-zA-Z0-9.-]+\.run\.app', js_content)
urls += re.findall(r'https?://core-backend[a-zA-Z0-9.-]*', js_content)
urls += re.findall(r'https?://[a-zA-Z0-9.-]*backend[a-zA-Z0-9.-]*', js_content)

print("Found backend URLs in JS bundle:")
for u in set(urls):
    print(u)
