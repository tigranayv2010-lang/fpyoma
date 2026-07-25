import requests
import random
import os
from dotenv import load_dotenv
from utils.config import load_topics

load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
PIXABAY_API_KEY = os.getenv('PIXABAY_API_KEY')

def get_random_anime_image() -> tuple[str | None, str]:
    try:
        response = requests.get("https://nekos.life/api/v2/img/neko", timeout=5)
        response.raise_for_status()
        return response.json().get("url"), "Аниме Арт"
    except Exception as e:
        print(f"Ошибка получения Anime: {e}")
        return None, None

def get_random_tiktok(query: str = None) -> tuple[str | None, str | None]:
    topics = load_topics("TikTok")
    topic = query or (random.choice(topics) if topics else None)
    url = f"https://www.tikwm.com/api/feed/search?keywords={topic}&count=10" if topic else "https://www.tikwm.com/api/feed/list?region=RU&count=10"
        
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json().get('data', [])
        videos = data.get('videos', []) if isinstance(data, dict) else data
        
        if videos:
            video = random.choice(videos)
            author, vid_id = video.get('author', {}).get('unique_id'), video.get('video_id', video.get('id'))
            if author and vid_id:
                return f"https://www.tiktok.com/@{author}/video/{vid_id}", topic
            elif video.get('play'):
                return video.get('play'), topic
    except Exception as e:
        print(f"Ошибка получения TikTok: {e}")
    return None, None

def get_random_pixabay(query: str = None) -> tuple[str | None, str | None]:
    if not PIXABAY_API_KEY:
        return None, None
        
    topic = query or random.choice(load_topics("Pixabay"))
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={topic}&image_type=photo&per_page=20"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        hits = response.json().get('hits', [])
        if hits:
            photo = random.choice(hits)
            return photo.get('largeImageURL', photo.get('webformatURL')), topic
    except Exception as e:
        print(f"Ошибка получения Pixabay: {e}")
    return None, None

def get_random_nekos_nsfw(query: str = None) -> tuple[str | None, str | None]:
    topic = query or random.choice(load_topics("Nekos"))
    tag = topic.strip().lower()
    
    url = f"https://api.nekosapi.com/v4/images/random?rating=explicit&tag={tag}&limit=1"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and (data := response.json()):
            return data[0].get('url'), tag
    except Exception:
        pass
        
    # Fallback to random explicit
    try:
        response = requests.get("https://api.nekosapi.com/v4/images/random?rating=explicit&limit=1", timeout=10)
        if response.status_code == 200 and (data := response.json()):
            return data[0].get('url'), tag
    except Exception as e:
        print(f"Ошибка получения Nekos: {e}")
    return None, None

def get_random_youtube(query: str = None) -> tuple[str | None, str | None]:
    topic = query or random.choice(load_topics("YouTube"))
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=10&q={topic}&key={YOUTUBE_API_KEY}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        items = response.json().get('items', [])
        if items:
            video_id = random.choice(items).get('id', {}).get('videoId')
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}", topic
    except Exception as e:
        print(f"Ошибка получения YouTube: {e}")
    return None, None

def search_youtube_interactive(query: str) -> list:
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=5&q={query}&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get('items', [])
    except Exception as e:
        print(f"Ошибка поиска YouTube: {e}")
    return []
