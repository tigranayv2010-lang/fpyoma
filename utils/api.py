import requests
import random
import os
from dotenv import load_dotenv
from utils.config import load_topics

load_dotenv()
PIXABAY_API_KEY = os.getenv('PIXABAY_API_KEY')

def _fetch(url: str, timeout: int = 5) -> dict | None:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"API Error ({url}): {e}")
    return None

def get_random_anime_image(query: str = None) -> dict:
    data = _fetch("https://nekos.life/api/v2/img/neko")
    return {"url": data.get("url"), "topic": "Аниме Арт"} if data else {}

def get_random_tiktok(query: str = None) -> dict:
    topics = load_topics("TikTok")
    topic = query or (random.choice(topics) if topics else None)
    url = f"https://www.tikwm.com/api/feed/search?keywords={topic}&count=10" if topic else "https://www.tikwm.com/api/feed/list?region=RU&count=10"
    
    data = _fetch(url)
    if not data: return {}
    
    videos = data.get('data', {}).get('videos', []) if isinstance(data.get('data'), dict) else data.get('data', [])
    if not videos: return {}
    
    video = random.choice(videos)
    author, vid_id = video.get('author', {}).get('unique_id'), video.get('video_id', video.get('id'))
    play_url = video.get('play')
    
    return {
        "url": f"https://www.tiktok.com/@{author}/video/{vid_id}" if author and vid_id else play_url,
        "topic": topic,
        "download_url": play_url
    }

def get_random_pixabay(query: str = None) -> dict:
    if not PIXABAY_API_KEY: return {}
    topic = query or random.choice(load_topics("Pixabay"))
    data = _fetch(f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={topic}&image_type=photo&per_page=20")
    
    hits = data.get('hits', []) if data else []
    if hits:
        photo = random.choice(hits)
        return {"url": photo.get('largeImageURL', photo.get('webformatURL')), "topic": topic}
    return {}

def get_random_nekos_nsfw(query: str = None) -> dict:
    topic = query or random.choice(load_topics("Nekos"))
    tag = topic.strip().lower()
    
    data = _fetch(f"https://api.nekosapi.com/v4/images/random?rating=explicit&tag={tag}&limit=1", timeout=10)
    if not data or not data.get(0):
        data = _fetch("https://api.nekosapi.com/v4/images/random?rating=explicit&limit=1", timeout=10)
        
    return {"url": data[0].get('url'), "topic": tag} if data and data.get(0) else {}
