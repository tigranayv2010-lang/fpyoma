import requests

YOUTUBE_API_KEY = 'AIzaSyC6_tBSI-vbH8BsNALxEqPcSS1fQzYZLk4'
url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q=test&key={YOUTUBE_API_KEY}"

response = requests.get(url)
print(f"Status Code: {response.status_code}")
print(f"Response Body: {response.text}")
