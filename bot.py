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
        await ctx.send(f"У вас нет прав для этой команды! Нужна роль: `{ALLOWED_ROLE_NAME}`")
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
            
        await interaction.response.send_message(f"Темы для {self.platform} обновлены!\nНовые темы: **{', '.join(topics_list)}**", ephemeral=False)

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
            await interaction.response.send_message(f"У вас нет прав! Нужна роль: `{ALLOWED_ROLE_NAME}`", ephemeral=True)
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
    
    await interaction.response.send_message(
        f"**Текущие темы контента:**\n\n📺 **YouTube:** {yt_text}\n📱 **TikTok:** {tk_text}\n🖼️ **Фото:** {px_text}\n🔞 **Nekos (18+):** {nk_text}\n\nНажмите на кнопку ниже, чтобы изменить темы:",
        view=TopicView()
    )

@bot.command(name='join')
@has_allowed_role()
async def join_command(ctx):
    """Подключает бота к голосовому каналу и запускает фоновую музыку."""
    global voice_client
    if not ctx.author.voice:
        await ctx.send("Сначала зайди в голосовой канал!")
        return
        
    channel = ctx.author.voice.channel
    if voice_client and voice_client.is_connected():
        await voice_client.move_to(channel)
    else:
        voice_client = await channel.connect()
        # Запускаем бесконечный цикл музыки
        play_next_song()
    await ctx.send(f"Подключился к `{channel.name}`. Фоновая музыка запущена! Заказывай музыку через `!play <название>`")

@bot.command(name='play')
async def play_command(ctx, *, query: str):
    """Ищет песню на YouTube и предлагает выбор (1-5)."""
    if not voice_client or not voice_client.is_connected():
        await ctx.send("Я еще не в канале! Пусть админ напишет `!join`")
        return
        
    await ctx.send(f"Ищу **{query}**...")
    results = search_youtube_interactive(query)
    
    if not results:
        await ctx.send("Ничего не найдено.")
        return
        
    # Формируем список
    msg = "**Выбери трек (напиши цифру от 1 до 5):**\n"
    for i, item in enumerate(results, 1):
        title = item.get('snippet', {}).get('title', 'Без названия')
        msg += f"{i}. {title}\n"
        
    await ctx.send(msg)
    
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
            await ctx.send(f"Добавлено в очередь: **{video_title}**")
            
            # Если сейчас играет фоновая музыка, скипаем
            if current_requester == bot.user.id and voice_client.is_playing():
                voice_client.stop()
        else:
            await ctx.send("Неверный номер. Попробуй заново через `!play`.")
    except asyncio.TimeoutError:
        await ctx.send("Время вышло! Ты не выбрал трек. Напиши `!play` снова.")

@bot.command(name='skip')
async def skip_command(ctx):
    """Пропускает текущую песню. Только для заказчика или админа."""
    if not voice_client or not voice_client.is_playing():
        await ctx.send("Сейчас ничего не играет!")
        return
        
    # Если заказал сам бот (фоновая музыка), пропустить может любой. 
    # Если заказал человек, пропустить может только он или создатель сервера.
    if current_requester == bot.user.id or current_requester == ctx.author.id or ctx.author.id == ctx.guild.owner_id:
        voice_client.stop() # Это триггерит play_next_song() автоматически
        await ctx.send("Трек пропущен!")
    else:
        await ctx.send("Ты не можешь пропустить чужой заказ!")

@bot.command(name='stop')
@has_allowed_role()
async def stop_command(ctx):
    """Останавливает бота и очищает очередь."""
    global music_queue
    music_queue.clear()
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send("Отключился, очередь очищена!")

# Старые текстовые команды
@bot.command(name='test')
async def test_api(ctx):
    yt_status = "" if check_youtube_api() else ""
    tt_status = "" if check_tiktok_api() else ""
    await ctx.send(f"youtube - {yt_status}\ntiktok - {tt_status}")

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
        
        if self.platform == "YouTube":
            url = get_random_youtube(custom_query=query)
            msg = f"Смотри, что нашел {f'на тему **{query}**' if query else ''}:\n"
        elif self.platform == "TikTok":
            url = get_random_tiktok(custom_query=query)
            msg = f"Лови TikTok {f'на тему **{query}**' if query else ''}:\n"
        elif self.platform == "Pixabay":
            url = get_random_pixabay(custom_query=query)
            msg = f"Красивое фото {f'на тему **{query}**' if query else ''}:\n"
        elif self.platform == "Nekos":
            url = get_random_nekos_nsfw(custom_query=query)
            msg = f"🔞 18+ Контент {f'на тему **{query}**' if query else ''}:\n|| "
        
        if url:
            if self.platform == "Nekos":
                await interaction.followup.send(f"{msg}{url} ||")
            else:
                await interaction.followup.send(f"{msg}{url}")
        else:
            await interaction.followup.send(f"Ошибка при получении контента для {self.platform}.")

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
            await interaction.response.send_message(f"У вас нет прав! Нужна роль: `{ALLOWED_ROLE_NAME}`", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="send_yt")
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_topics()
        if not topics: topics = ["lofi hip hop", "gaming mix", "synthwave"]
        await interaction.response.edit_message(content="**YouTube:** Выбери тему:", view=TopicSelectView("YouTube", topics))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.success, custom_id="send_tk")
    async def btn_tk(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_tiktok_topics()
        if not topics: topics = ["phonk", "cats", "funny"]
        await interaction.response.edit_message(content="**TikTok:** Выбери тему:", view=TopicSelectView("TikTok", topics))

    @discord.ui.button(label="Фото (Pixabay)", style=discord.ButtonStyle.secondary, custom_id="send_px")
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_pixabay_topics()
        if not topics: topics = ["nature", "city", "cyberpunk"]
        await interaction.response.edit_message(content="**Pixabay:** Выбери тему:", view=TopicSelectView("Pixabay", topics))

    @discord.ui.button(label="Nekos (18+)", style=discord.ButtonStyle.danger, custom_id="send_nk")
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_nekos_topics()
        if not topics: topics = ["girl", "pussy", "large_breasts", "kemonomimi", "exposed_girl_breasts"]
        await interaction.response.edit_message(content="**Nekos (18+):** Выбери тему:", view=TopicSelectView("Nekos", topics))

    @discord.ui.button(label="Аниме (Случайно)", style=discord.ButtonStyle.primary, custom_id="send_an")
    async def btn_an(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        url = get_random_anime_image()
        if url:
            await interaction.followup.send(f"Аниме арт:\n{url}")
        else:
            await interaction.followup.send("Ошибка при получении аниме.")

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
        await interaction.response.send_message(f"У вас нет прав! Нужна роль: `{ALLOWED_ROLE_NAME}`", ephemeral=True)
        return
        
    await interaction.response.send_message(
        "**Выбери платформу для отправки контента:**",
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
        if chosen_func == get_random_anime_image:
            msg = "Время контента!\n"
        elif chosen_func == get_random_tiktok:
            msg = "Свежий TikTok!\n"
        elif chosen_func == get_random_pixabay:
            msg = "Красивое фото!\n"
        elif chosen_func == get_random_nekos_nsfw:
            msg = "🔞 18+ Контент!\n|| "
            content_url += " ||"
        else:
            msg = "Зацени видео с YouTube!\n"
        await channel.send(f"{msg}{content_url}")

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
