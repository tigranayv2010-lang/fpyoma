import requests, json, bs4, re

url = 'https://ru.pinterest.com/search/pins/?q=cats'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
res = requests.get(url, headers=headers)
soup = bs4.BeautifulSoup(res.text, 'html.parser')
script = soup.find('script', id='__PWS_DATA__')
if script:
    try:
        data = json.loads(script.string)
        def find_images(obj, urls):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    find_images(v, urls)
            elif isinstance(obj, list):
                for v in obj:
                    find_images(v, urls)
            elif isinstance(obj, str):
                if obj.startswith('https://i.pinimg.com/') and (obj.endswith('.jpg') or obj.endswith('.png')):
                    urls.add(obj)
        
        urls = set()
        find_images(data, urls)
        print(list(urls)[:5])
    except Exception as e:
        print(e)
else:
    print('No script found')
