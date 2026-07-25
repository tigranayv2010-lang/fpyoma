import discord
from discord.ext import commands, tasks
import requests
import random
import asyncio
import yt_dlp as youtube_dl
import imageio_ffmpeg
import os
import json
from dotenv import load_dotenv

load_dotenv()

# === НАСТРОЙКИ ===
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
PIXABAY_API_KEY = os.getenv('PIXABAY_API_KEY')
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID', 1530259440459321565))
ALLOWED_ROLE_NAME = "Content" 

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

from datetime import datetime

# === ДИЗАЙН EMBED ===
EMBED_THEMES = {
    "youtube":  {"color": 0xFF0000, "emoji": "<:youtube:1530525984942588027>", "name": "YouTube"},
    "tiktok":   {"color": 0x00F2EA, "emoji": "<:tiktok:1530525976797380638>", "name": "TikTok"},
    "pixabay":  {"color": 0x2EC866, "emoji": "<:pinterest:1530525972540166244>", "name": "Pixabay"},
    "nekos":    {"color": 0xFF69B4, "emoji": "<:18:1530525967297020035>", "name": "Nekos 18+"},
    "anime":    {"color": 0xE91E63, "emoji": "<:animejpg:1530526067939479654>", "name": "Anime Art"},
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

# === НАСТРОЙКИ МУЗЫКИ ===
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

music_queue = []
current_requester = None
voice_client = None

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

# Старые функции (оставляем для работы текстовых рассылок)
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
            return response.json().get("url")
    except Exception as e:
        print(f"Ошибка при получении картинки: {e}")
    return None

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
                    return f"https://www.tiktok.com/@{author_id}/video/{video_id}"
                elif video.get('play'):
                    return video.get('play')
    except Exception as e:
        print(f"Ошибка при получении TikTok: {e}")
    return None

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
                return photo.get('largeImageURL', photo.get('webformatURL'))
    except Exception as e:
        print(f"Ошибка при получении фото с Pixabay: {e}")
    return None

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
                return data[0].get('url')
    except Exception:
        pass
        
    # Фоллбэк без тегов (просто случайная explicit картинка)
    try:
        url2 = "https://api.nekosapi.com/v4/images/random?rating=explicit&limit=1"
        response2 = requests.get(url2, timeout=10)
        if response2.status_code == 200:
            data2 = response2.json()
            if data2 and len(data2) > 0:
                return data2[0].get('url')
    except Exception as e:
        print(f"Ошибка при получении Nekos: {e}")
    return None

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
                    return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print(f"Ошибка при получении YouTube видео: {e}")
    return None

def search_youtube_interactive(query):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=5&q={query}&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get('items', [])
    except Exception as e:
        print(f"Ошибка при поиске YouTube: {e}")
    return []

# === ЛОГИКА МУЗЫКИ ===
def play_next_song(error=None):
    global current_requester
    if error:
        print(f"Ошибка проигрывания: {error}")
    
    if not voice_client or not voice_client.is_connected():
        return
        
    if len(music_queue) > 0:
        # Играем заказанную музыку
        song = music_queue.pop(0)
        url = song['url']
        current_requester = song['requester']
        print(f"Играем заказ из очереди: {url}")
    else:
        # Автопилот (Фоновая музыка)
        url = get_random_youtube()
        current_requester = bot.user.id # Бот сам заказал
        print(f"Очередь пуста. Включаем фоновую музыку: {url}")
        if not url:
            # Ждем немного и пробуем снова (лимиты ютуба)
            bot.loop.call_later(5, play_next_song)
            return

    try:
        data = ytdl.extract_info(url, download=False)
        audio_url = data['url']
        
        def after_playing(e):
            bot.loop.call_soon_threadsafe(play_next_song, e)
            
        voice_client.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=audio_url, **ffmpeg_options), after=after_playing)
    except Exception as e:
        print(f"Error playing video: {e}")
        bot.loop.call_later(5, play_next_song)

def has_allowed_role():
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id:
            return True
        for role in ctx.author.roles:
            if role.name.lower() == ALLOWED_ROLE_NAME.lower():
                return True
        embed = create_embed(description=f"У вас нет прав для этой команды!\nНужна роль: `{ALLOWED_ROLE_NAME}`", theme="error")
        await ctx.send(embed=embed)
        return False
    return commands.check(predicate)

class TopicModal(discord.ui.Modal):
    def __init__(self, platform: str):
        super().__init__(title=f"Темы для {platform}")
        self.platform = platform
        
        if platform == "YouTube":
            current_topics = get_saved_topics()
        elif platform == "TikTok":
            current_topics = get_saved_tiktok_topics()
        elif platform == "Pixabay":
            current_topics = get_saved_pixabay_topics()
        else:
            current_topics = get_saved_nekos_topics()
            
        default_val = ", ".join(current_topics)
        
        self.topics_input = discord.ui.TextInput(
            label="Темы (через запятую)",
            style=discord.TextStyle.paragraph,
            placeholder="Например: cats, funny, phonk",
            default=default_val,
            required=True
        )
        self.add_item(self.topics_input)

    async def on_submit(self, interaction: discord.Interaction):
        topics_str = self.topics_input.value
        topics_list = [t.strip() for t in topics_str.split(',') if t.strip()]
        
        if self.platform == "YouTube":
            save_topics(topics_list)
        elif self.platform == "TikTok":
            save_tiktok_topics(topics_list)
        elif self.platform == "Pixabay":
            save_pixabay_topics(topics_list)
        else:
            save_nekos_topics(topics_list)
            
        topics_formatted = ', '.join([f'`{t}`' for t in topics_list])
        embed = create_embed(title="Темы обновлены", description=f"**Платформа:** {self.platform}\n\n{topics_formatted}", theme="success")
        await interaction.response.send_message(embed=embed, ephemeral=False)

class TopicView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        is_allowed = False
        if interaction.user.id == interaction.guild.owner_id:
            is_allowed = True
        else:
            for role in getattr(interaction.user, 'roles', []):
                if role.name.lower() == ALLOWED_ROLE_NAME.lower():
                    is_allowed = True
                    break
        if not is_allowed:
            embed = create_embed(description=f"У вас нет прав!\nНужна роль: `{ALLOWED_ROLE_NAME}`", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="btn_yt")
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("YouTube"))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.success, custom_id="btn_tk")
    async def btn_tk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("TikTok"))

    @discord.ui.button(label="Фото (Pixabay)", style=discord.ButtonStyle.secondary, custom_id="btn_px")
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("Pixabay"))

    @discord.ui.button(label="Nekos (18+)", style=discord.ButtonStyle.danger, custom_id="btn_nk")
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("Nekos"))

@bot.tree.command(name="topics", description="Настройка тем для контента")
async def topics_command(interaction: discord.Interaction):
    yt_topics = get_saved_topics()
    tk_topics = get_saved_tiktok_topics()
    px_topics = get_saved_pixabay_topics()
    nk_topics = get_saved_nekos_topics()
    
    yt_text = ", ".join(yt_topics) if yt_topics else "По умолчанию"
    tk_text = ", ".join(tk_topics) if tk_topics else "По умолчанию"
    px_text = ", ".join(px_topics) if px_topics else "По умолчанию"
    nk_text = ", ".join(nk_topics) if nk_topics else "По умолчанию (girl, pussy, large_breasts...)"
    
    desc = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"<:youtube:1530525984942588027>  **YouTube:**  {yt_text}\n"
        f"<:tiktok:1530525976797380638>  **TikTok:**  {tk_text}\n"
        f"<:pinterest:1530525972540166244>  **Pixabay:**  {px_text}\n"
        f"<:18:1530525967297020035>  **Nekos 18+:**  {nk_text}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Нажмите на кнопку ниже, чтобы изменить темы:"
    )
    embed = create_embed(title="Настройки тем контента", description=desc, theme="settings")
    await interaction.response.send_message(embed=embed, view=TopicView())

@bot.command(name='join')
@has_allowed_role()
async def join_command(ctx):
    """Подключает бота к голосовому каналу и запускает фоновую музыку."""
    global voice_client
    if not ctx.author.voice:
        embed = create_embed(description="Сначала зайди в голосовой канал!", theme="error")
        await ctx.send(embed=embed)
        return
        
    channel = ctx.author.voice.channel
    if voice_client and voice_client.is_connected():
        await voice_client.move_to(channel)
    else:
        voice_client = await channel.connect()
        # Запускаем бесконечный цикл музыки
        play_next_song()
    embed = create_embed(title="Подключился!", description=f"Канал: **{channel.name}**\nФоновая музыка запущена!\n\nЗаказывай музыку через `!play <название>`", theme="music")
    await ctx.send(embed=embed)

@bot.command(name='play')
async def play_command(ctx, *, query: str):
    """Ищет песню на YouTube и предлагает выбор (1-5)."""
    if not voice_client or not voice_client.is_connected():
        embed = create_embed(description="Я еще не в канале!\nПусть админ напишет `!join`", theme="error")
        await ctx.send(embed=embed)
        return
        
    embed = create_embed(description=f"Ищу **{query}**...", theme="music")
    await ctx.send(embed=embed)
    results = search_youtube_interactive(query)
    
    if not results:
        embed = create_embed(description="Ничего не найдено.", theme="error")
        await ctx.send(embed=embed)
        return
        
    # Формируем список
    msg = "**Выбери трек (напиши цифру от 1 до 5):**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, item in enumerate(results, 1):
        title = item.get('snippet', {}).get('title', 'Без названия')
        msg += f"**`{i}`**  ▸  {title}\n"
        
    embed = create_embed(title="Результаты поиска", description=msg, theme="music")
    await ctx.send(embed=embed)
    
    # Ждем ответ от того же пользователя
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
    try:
        # Ждем 30 секунд
        msg_reply = await bot.wait_for('message', check=check, timeout=30.0)
        choice = int(msg_reply.content)
        if 1 <= choice <= len(results):
            selected_video = results[choice - 1]
            video_id = selected_video.get('id', {}).get('videoId')
            video_title = selected_video.get('snippet', {}).get('title')
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            music_queue.append({'url': url, 'requester': ctx.author.id, 'title': video_title})
            embed = create_embed(title="Добавлено в очередь", description=f"**{video_title}**", theme="success")
            await ctx.send(embed=embed)
            
            # Если сейчас играет фоновая музыка, скипаем
            if current_requester == bot.user.id and voice_client.is_playing():
                voice_client.stop()
        else:
            embed = create_embed(description="Неверный номер. Попробуй заново через `!play`.", theme="error")
            await ctx.send(embed=embed)
    except asyncio.TimeoutError:
        embed = create_embed(description="Время вышло! Ты не выбрал трек.\nНапиши `!play` снова.", theme="error")
        await ctx.send(embed=embed)

@bot.command(name='skip')
async def skip_command(ctx):
    """Пропускает текущую песню. Только для заказчика или админа."""
    if not voice_client or not voice_client.is_playing():
        embed = create_embed(description="Сейчас ничего не играет!", theme="error")
        await ctx.send(embed=embed)
        return
        
    # Если заказал сам бот (фоновая музыка), пропустить может любой. 
    # Если заказал человек, пропустить может только он или создатель сервера.
    if current_requester == bot.user.id or current_requester == ctx.author.id or ctx.author.id == ctx.guild.owner_id:
        voice_client.stop() # Это триггерит play_next_song() автоматически
        embed = create_embed(title="Трек пропущен", description="Включаю следующий...", theme="music")
        await ctx.send(embed=embed)
    else:
        embed = create_embed(description="Ты не можешь пропустить чужой заказ!", theme="error")
        await ctx.send(embed=embed)

@bot.command(name='stop')
@has_allowed_role()
async def stop_command(ctx):
    """Останавливает бота и очищает очередь."""
    global music_queue
    music_queue.clear()
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        embed = create_embed(title="Отключился", description="Очередь очищена!", theme="music")
        await ctx.send(embed=embed)

# Старые текстовые команды
@bot.command(name='test')
async def test_api(ctx):
    yt_status = "" if check_youtube_api() else ""
    tt_status = "" if check_tiktok_api() else ""
    embed = create_embed(title="Статус API", description=f"━━━━━━━━━━━━━━━━━━━━━\n<:youtube:1530525984942588027>  **YouTube:**  {yt_status}\n<:tiktok:1530525976797380638>  **TikTok:**  {tt_status}\n━━━━━━━━━━━━━━━━━━━━━", theme="settings")
    await ctx.send(embed=embed)

class TopicSelect(discord.ui.Select):
    def __init__(self, platform: str, topics: list):
        self.platform = platform
        options = [discord.SelectOption(label="Случайная тема", value="random")]
        for t in topics:
            options.append(discord.SelectOption(label=t, value=t))
        super().__init__(placeholder="Выбери тему...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer() # Ждем загрузки контента
        selected = self.values[0]
        query = selected if selected != "random" else None
        
        url = None
        msg = ""
        
        platform_themes = {"YouTube": "youtube", "TikTok": "tiktok", "Pixabay": "pixabay", "Nekos": "nekos"}
        theme = platform_themes.get(self.platform, "info")
        
        if self.platform == "YouTube":
            url = get_random_youtube(custom_query=query)
            title = f"Смотри, что нашел{f' на тему **{query}**' if query else ''}"
        elif self.platform == "TikTok":
            url = get_random_tiktok(custom_query=query)
            title = f"Лови TikTok{f' на тему **{query}**' if query else ''}"
        elif self.platform == "Pixabay":
            url = get_random_pixabay(custom_query=query)
            title = f"Красивое фото{f' на тему **{query}**' if query else ''}"
        elif self.platform == "Nekos":
            url = get_random_nekos_nsfw(custom_query=query)
            title = f"18+ Контент{f' на тему **{query}**' if query else ''}"
        
        if url:
            if self.platform in ["YouTube", "TikTok"]:
                embed = create_embed(title=title, theme=theme)
                await interaction.followup.send(content=url, embed=embed)
            else:
                embed = create_embed(title=title, image_url=url, theme=theme)
                await interaction.followup.send(embed=embed)
        else:
            embed = create_embed(description=f"Ошибка при получении контента для {self.platform}.", theme="error")
            await interaction.followup.send(embed=embed)

class TopicSelectView(discord.ui.View):
    def __init__(self, platform: str, topics: list):
        super().__init__(timeout=180)
        self.add_item(TopicSelect(platform, topics))

class SendPlatformView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        is_allowed = False
        if interaction.user.id == interaction.guild.owner_id:
            is_allowed = True
        else:
            for role in getattr(interaction.user, 'roles', []):
                if role.name.lower() == ALLOWED_ROLE_NAME.lower():
                    is_allowed = True
                    break
        if not is_allowed:
            embed = create_embed(description=f"У вас нет прав!\nНужна роль: `{ALLOWED_ROLE_NAME}`", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="send_yt")
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_topics()
        if not topics: topics = ["lofi hip hop", "gaming mix", "synthwave"]
        embed = create_embed(description="<:youtube:1530525984942588027>  **YouTube** — Выбери тему:", theme="youtube")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("YouTube", topics))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.success, custom_id="send_tk")
    async def btn_tk(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_tiktok_topics()
        if not topics: topics = ["phonk", "cats", "funny"]
        embed = create_embed(description="<:tiktok:1530525976797380638>  **TikTok** — Выбери тему:", theme="tiktok")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("TikTok", topics))

    @discord.ui.button(label="Фото (Pixabay)", style=discord.ButtonStyle.secondary, custom_id="send_px")
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_pixabay_topics()
        if not topics: topics = ["nature", "city", "cyberpunk"]
        embed = create_embed(description="<:pinterest:1530525972540166244>  **Pixabay** — Выбери тему:", theme="pixabay")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("Pixabay", topics))

    @discord.ui.button(label="Nekos (18+)", style=discord.ButtonStyle.danger, custom_id="send_nk")
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_nekos_topics()
        if not topics: topics = ["girl", "pussy", "large_breasts", "kemonomimi", "exposed_girl_breasts"]
        embed = create_embed(description="<:18:1530525967297020035>  **Nekos 18+** — Выбери тему:", theme="nekos")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("Nekos", topics))

    @discord.ui.button(label="Аниме (Случайно)", style=discord.ButtonStyle.primary, custom_id="send_an")
    async def btn_an(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        url = get_random_anime_image()
        if url:
            embed = create_embed(title="Аниме арт", image_url=url, theme="anime")
            await interaction.followup.send(embed=embed)
        else:
            embed = create_embed(description="Ошибка при получении аниме.", theme="error")
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="send", description="Отправить контент в чат с выбором темы")
async def send_command(interaction: discord.Interaction):
    is_allowed = False
    if interaction.user.id == interaction.guild.owner_id:
        is_allowed = True
    else:
        for role in getattr(interaction.user, 'roles', []):
            if role.name.lower() == ALLOWED_ROLE_NAME.lower():
                is_allowed = True
                break
    if not is_allowed:
        embed = create_embed(description=f"У вас нет прав!\nНужна роль: `{ALLOWED_ROLE_NAME}`", theme="error")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    desc = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "<:youtube:1530525984942588027>  **YouTube**  │  <:tiktok:1530525976797380638>  **TikTok**\n"
        "<:pinterest:1530525972540166244>  **Pixabay**  │  <:18:1530525967297020035>  **Nekos 18+**\n"
        "<:animejpg:1530526067939479654>  **Anime**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выбери платформу ниже и отправь контент в чат:"
    )
    embed = create_embed(title="Отправить контент", description=desc)
    await interaction.response.send_message(
        embed=embed,
        view=SendPlatformView(),
        ephemeral=False
    )

@tasks.loop(hours=2)
async def auto_post_loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel: return
    content_funcs = [get_random_anime_image, get_random_tiktok, get_random_youtube, get_random_pixabay, get_random_nekos_nsfw]
    chosen_func = random.choice(content_funcs)
    content_url = chosen_func()
    if content_url:
        if chosen_func in [get_random_anime_image, get_random_pixabay, get_random_nekos_nsfw]:
            if chosen_func == get_random_anime_image:
                embed = create_embed(title="Время контента!", image_url=content_url, theme="anime")
            elif chosen_func == get_random_pixabay:
                embed = create_embed(title="Красивое фото!", image_url=content_url, theme="pixabay")
            else:
                embed = create_embed(title="18+ Контент!", image_url=content_url, theme="nekos")
            await channel.send(embed=embed)
        else:
            if chosen_func == get_random_tiktok:
                embed = create_embed(title="Свежий TikTok!", theme="tiktok")
            else:
                embed = create_embed(title="Зацени видео!", theme="youtube")
            await channel.send(content=content_url, embed=embed)

@auto_post_loop.before_loop
async def before_auto_post():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f'Бот {bot.user} успешно запущен!')
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} слеш-команд")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")
    if not auto_post_loop.is_running():
        auto_post_loop.start()

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
