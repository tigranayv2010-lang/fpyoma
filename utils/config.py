import json
import os
import discord
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"
TOPICS_FILE = "topics.json"

DEFAULT_CONFIG = {
    "main_channel_id": int(os.getenv("TARGET_CHANNEL_ID")) if os.getenv("TARGET_CHANNEL_ID") else None,
    "nsfw_channel_id": None,
    "auto_post_interval_minutes": 120,
    "allowed_roles": ["Content"]
}

DEFAULT_TOPICS = {
    "TikTok": [],
    "Pixabay": ["nature", "city", "cyberpunk", "animals", "cars"],
    "Nekos": ["girl", "pussy", "large_breasts", "kemonomimi", "exposed_girl_breasts"]
}

def _load_json(file_path: str, default: dict) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return {**default, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return default.copy()

def _save_json(file_path: str, data: dict):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_config() -> dict:
    return _load_json(CONFIG_FILE, DEFAULT_CONFIG)

def save_config(config_data: dict):
    _save_json(CONFIG_FILE, config_data)

def load_topics(platform: str) -> list[str]:
    data = _load_json(TOPICS_FILE, DEFAULT_TOPICS)
    return data.get(platform, DEFAULT_TOPICS.get(platform, []))

def save_topics(platform: str, topics_list: list[str]):
    data = _load_json(TOPICS_FILE, DEFAULT_TOPICS)
    data[platform] = topics_list
    _save_json(TOPICS_FILE, data)

def check_user_allowed(user: discord.Member | discord.User, guild_owner_id: int) -> bool:
    if user.id == guild_owner_id: return True
    allowed = {r.lower() for r in load_config().get("allowed_roles", ["Content"])}
    return any(role.name.lower() in allowed for role in getattr(user, "roles", []))

def get_roles_str() -> str:
    return ", ".join(load_config().get("allowed_roles", ["Content"]))
