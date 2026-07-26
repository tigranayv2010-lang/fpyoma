import discord
from datetime import datetime
import os

EMBED_THEMES = {
    "youtube":  {"color": 0xFF0000, "emoji": os.getenv("EMOJI_YOUTUBE", "📺"), "name": "YouTube"},
    "tiktok":   {"color": 0x00F2EA, "emoji": os.getenv("EMOJI_TIKTOK", "📱"), "name": "TikTok"},
    "pixabay":  {"color": 0x2EC866, "emoji": os.getenv("EMOJI_PIXABAY", "🖼️"), "name": "Pixabay"},
    "nekos":    {"color": 0xFF69B4, "emoji": os.getenv("EMOJI_NEKOS", "🔞"), "name": "Nekos 18+"},
    "anime":    {"color": 0xE91E63, "emoji": os.getenv("EMOJI_ANIME", "🌸"), "name": "Anime Art"},
    "music":    {"color": 0x9B59B6, "emoji": "🎵", "name": "Music Player"},
    "settings": {"color": 0x3498DB, "emoji": "⚙️", "name": "Настройки"},
    "success":  {"color": 0x2ECC71, "emoji": "✅", "name": "Успех"},
    "error":    {"color": 0xE74C3C, "emoji": "❌", "name": "Ошибка"},
    "info":     {"color": 0xFFFFFF, "emoji": "💎", "name": "Russia Games"},
}
ANBU_ICON = "https://cdn.discordapp.com/embed/avatars/0.png"

def create_embed(description=None, title=None, image_url=None, theme="info"):
    t = EMBED_THEMES.get(theme, EMBED_THEMES["info"])
    embed = discord.Embed(color=t["color"], timestamp=datetime.utcnow())
    
    if title:
        embed.title = f"{t['emoji']}  {title}"
    if description:
        embed.description = description
    if image_url:
        embed.set_image(url=image_url)
    
    embed.set_footer(text=f"Разработано ANBU Coding  •  {t['name']}", icon_url=ANBU_ICON)
    return embed
