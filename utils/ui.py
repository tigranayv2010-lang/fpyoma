import discord
from datetime import datetime
import os

EMBED_THEMES = {
    "youtube":  {"color": 0xFF0000, "emoji": "<:youtube:1530644091707068440>", "name": "YouTube"},
    "tiktok":   {"color": 0x00F2EA, "emoji": "<:tiktok:1530643835301003304>", "name": "TikTok"},
    "pixabay":  {"color": 0x2EC866, "emoji": "<:pixabay:1530644282883571854>", "name": "Pixabay"},
    "nekos":    {"color": 0xFF69B4, "emoji": "<:18:1530644654758826155>", "name": "Nekos 18+"},
    "anime":    {"color": 0xE91E63, "emoji": "<:anime:1530644484524736522>", "name": "Anime Art"},
    "settings": {"color": 0x3498DB, "emoji": "⚙️", "name": "Настройки"},
    "success":  {"color": 0x2ECC71, "emoji": "✅", "name": "Успех"},
    "error":    {"color": 0xE74C3C, "emoji": "❌", "name": "Ошибка"},
    "info":     {"color": 0xFFFFFF, "emoji": "💎", "name": "Russia Games"},
}

def create_embed(description: str = None, title: str = None, theme: str = "info") -> discord.Embed:
    t = EMBED_THEMES.get(theme, EMBED_THEMES["info"])
    embed = discord.Embed(color=t["color"], timestamp=datetime.utcnow(), description=description)
    if title: embed.title = f"{t['emoji']}  {title}"
    return embed
