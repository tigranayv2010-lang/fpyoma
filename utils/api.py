import requests
import random
import os
from dotenv import load_dotenv
from utils.config import get_saved_topics, get_saved_tiktok_topics, get_saved_pixabay_topics, get_saved_nekos_topics

load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
PIXABAY_API_KEY = os.getenv('PIXABAY_API_KEY')

def check_youtube_api():
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q=test&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def check_tiktok_api():
    try:
        response = requests.get("https://www.tikwm.com/api/feed/list?region=RU&count=1", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def get_random_anime_image():
    try:
        response = requests.get("https://nekos.life/api/v2/img/neko", timeout=5)
        if response.status_code == 200:
            return response.json().get("url"), "Аниме Арт"
    except Exception as e:
        print(f"Ошибка при получении картинки: {e}")
    return None, None

def get_random_tiktok(custom_query=None):
    if custom_query:
        url = f"https://www.tikwm.com/api/feed/search?keywords={custom_query}&count=10"
    else:
        topics = get_saved_tiktok_topics()
        if topics:
            query = random.choice(topics)
            url = f"https://www.tikwm.com/api/feed/search?keywords={query}&count=10"
        else:
            url = "https://www.tikwm.com/api/feed/list?region=RU&count=10"
        
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json().get('data', [])
            if isinstance(data, dict):
                data = data.get('videos', [])
            if data:
                video = random.choice(data)
                author_id = video.get('author', {}).get('unique_id', '')
                video_id = video.get('video_id', video.get('id', ''))
                if author_id and video_id:
                    return f"https://www.tiktok.com/@{author_id}/video/{video_id}", custom_query or query
                elif video.get('play'):
                    return video.get('play'), custom_query or query
    except Exception as e:
        print(f"Ошибка при получении TikTok: {e}")
    return None, None

def get_random_pixabay(custom_query=None):
    if custom_query:
        query = custom_query
    else:
        topics = get_saved_pixabay_topics()
        if not topics:
            topics = ["nature", "city", "cyberpunk", "animals", "cars"]
        query = random.choice(topics)
        
    if not PIXABAY_API_KEY:
        print("PIXABAY_API_KEY не установлен!")
        return None
        
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&per_page=20"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            hits = response.json().get('hits', [])
            if hits:
                photo = random.choice(hits)
                return photo.get('largeImageURL', photo.get('webformatURL')), query
    except Exception as e:
        print(f"Ошибка при получении фото с Pixabay: {e}")
    return None, None

def get_random_nekos_nsfw(custom_query=None):
    if custom_query:
        tag = custom_query.strip().lower()
    else:
        topics = get_saved_nekos_topics()
        if not topics:
            topics = ["girl", "pussy", "large_breasts", "kemonomimi", "exposed_girl_breasts"]
        tag = random.choice(topics).strip().lower()
        
    url = f"https://api.nekosapi.com/v4/images/random?rating=explicit&tag={tag}&limit=1"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get('url'), tag
    except Exception:
        pass
        
    # Фоллбэк без тегов (просто случайная explicit картинка)
    try:
        url2 = "https://api.nekosapi.com/v4/images/random?rating=explicit&limit=1"
        response2 = requests.get(url2, timeout=10)
        if response2.status_code == 200:
            data2 = response2.json()
            if data2 and len(data2) > 0:
                return data2[0].get('url'), tag
    except Exception as e:
        print(f"Ошибка при получении Nekos: {e}")
    return None, None

def get_random_youtube(custom_query=None):
    if custom_query:
        query = custom_query
    else:
        # Темы для YouTube
        queries = get_saved_topics()
        if not queries:
            queries = ["lofi hip hop radio", "chill background music", "gaming mix", "synthwave mix"]
        query = random.choice(queries)
    
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=10&q={query}&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            items = response.json().get('items', [])
            if items:
                video = random.choice(items)
                video_id = video.get('id', {}).get('videoId')
                if video_id:
                    return f"https://www.youtube.com/watch?v={video_id}", query
    except Exception as e:
        print(f"Ошибка при получении YouTube видео: {e}")
    return None, None

def search_youtube_interactive(query):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=5&q={query}&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get('items', [])
    except Exception as e:
        print(f"Ошибка при поиске YouTube: {e}")
    return []

