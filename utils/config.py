import json
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "main_channel_id": int(os.getenv('TARGET_CHANNEL_ID', 1530259440459321565)) if os.getenv('TARGET_CHANNEL_ID') else None,
    "nsfw_channel_id": None,
    "auto_post_interval_hours": 2,
    "allowed_roles": ["Content"]
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data: data[k] = v
            return data
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def check_user_allowed(user, guild_owner_id):
    if user.id == guild_owner_id:
        return True
    cfg = load_config()
    allowed = [r.lower() for r in cfg.get("allowed_roles", ["Content"])]
    for role in getattr(user, 'roles', []):
        if role.name.lower() in allowed:
            return True
    return False

def get_roles_str():
    return ", ".join(load_config().get("allowed_roles", ["Content"]))

def get_saved_topics():
    try:
        with open('topics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('topics', [])
    except FileNotFoundError:
        return []

def save_topics(topics_list):
    with open('topics.json', 'w', encoding='utf-8') as f:
        json.dump({'topics': topics_list}, f, ensure_ascii=False, indent=4)

def get_saved_tiktok_topics():
    try:
        with open('tiktok_topics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('topics', [])
    except FileNotFoundError:
        return []

def save_tiktok_topics(topics_list):
    with open('tiktok_topics.json', 'w', encoding='utf-8') as f:
        json.dump({'topics': topics_list}, f, ensure_ascii=False, indent=4)

def get_saved_nekos_topics():
    try:
        with open('nekos_topics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('topics', [])
    except FileNotFoundError:
        return []

def save_nekos_topics(topics_list):
    with open('nekos_topics.json', 'w', encoding='utf-8') as f:
        json.dump({'topics': topics_list}, f, ensure_ascii=False, indent=4)

def get_saved_pixabay_topics():
    try:
        with open('pixabay_topics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('topics', [])
    except FileNotFoundError:
        return []

def save_pixabay_topics(topics_list):
    with open('pixabay_topics.json', 'w', encoding='utf-8') as f:
        json.dump({'topics': topics_list}, f, ensure_ascii=False, indent=4)
