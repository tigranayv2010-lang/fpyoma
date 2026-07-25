import json, re

with open('pws_data.json', 'r', encoding='utf-8') as f:
    text = f.read()

urls = re.findall(r'https://[^\"\'\s]+\.jpg', text)
print(list(set(urls))[:10])
