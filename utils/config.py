import json
import os
from dotenv import load_dotenv
import discord

load_dotenv()

CONFIG_FILE = "config.json"
TOPICS_FILE = "topics.json"

DEFAULT_CONFIG = {
    "main_channel_id": int(os.getenv("TARGET_CHANNEL_ID")) if os.getenv("TARGET_CHANNEL_ID") else None,
    "nsfw_channel_id": None,
    "auto_post_interval_hours": 2,
    "allowed_roles": ["Content"]
}

DEFAULT_TOPICS = {
    "YouTube": ["lofi hip hop radio", "chill background music", "gaming mix", "synthwave mix"],
    "TikTok": [],
    "Pixabay": ["nature", "city", "cyberpunk", "animals", "cars"],
    "Nekos": ["girl", "pussy", "large_breasts", "kemonomimi", "exposed_girl_breasts"]
}

def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

def save_config(config_data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def check_user_allowed(user: discord.Member | discord.User, guild_owner_id: int) -> bool:
    if user.id == guild_owner_id:
        return True
    
    allowed = {r.lower() for r in load_config().get("allowed_roles", ["Content"])}
    return any(role.name.lower() in allowed for role in getattr(user, "roles", []))

def get_roles_str() -> str:
    return ", ".join(load_config().get("allowed_roles", ["Content"]))

def load_topics(platform: str) -> list[str]:
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get(platform, DEFAULT_TOPICS.get(platform, []))
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_TOPICS.get(platform, [])

def save_topics(platform: str, topics_list: list[str]):
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = DEFAULT_TOPICS.copy()
    
    data[platform] = topics_list
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
