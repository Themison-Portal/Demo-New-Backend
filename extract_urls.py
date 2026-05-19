import re

content = open(r'C:\Users\JONAATH\.gemini\antigravity\brain\2d62309e-0a68-4e59-98f5-9b5d9a98e188\.system_generated\steps\33\content.md', encoding='utf-8').read()
urls = re.findall(r'https?://[^\s"\'<>]+', content)
print("\n".join(set(urls)))
