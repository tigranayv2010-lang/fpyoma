import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import imageio_ffmpeg
from utils.ui import create_embed
from utils.api import get_random_youtube, search_youtube_interactive
import asyncio
from utils.config import check_user_allowed, get_roles_str

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

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queue = []
        self.current_requester = None
        self.voice_client = None

    def play_next_song(self, error=None):
        if error:
            print(f"Ошибка проигрывания: {error}")
        
        if not self.voice_client or not self.voice_client.is_connected():
            return
            
        if len(self.music_queue) > 0:
            song = self.music_queue.pop(0)
            url = song['url']
            self.current_requester = song['requester']
            print(f"Играем заказ из очереди: {url}")
        else:
            url, topic = get_random_youtube()
            self.current_requester = self.bot.user.id
            print(f"Очередь пуста. Включаем фоновую музыку: {url} (Тема: {topic})")
            if not url:
                self.bot.loop.call_later(5, self.play_next_song)
                return

        try:
            data = ytdl.extract_info(url, download=False)
            audio_url = data['url']
            
            def after_playing(e):
                self.bot.loop.call_soon_threadsafe(self.play_next_song, e)
                
            self.voice_client.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=audio_url, **ffmpeg_options), after=after_playing)
        except Exception as e:
            print(f"Error playing video: {e}")
            self.bot.loop.call_later(5, self.play_next_song)

    @commands.command(name='join')
    async def join_command(self, ctx):
        """Подключает бота к голосовому каналу и запускает фоновую музыку."""
        if not check_user_allowed(ctx.author, ctx.guild.owner_id):
            embed = create_embed(description=f"У вас нет прав для этой команды!\nНужны роли: `{get_roles_str()}`", theme="error")
            await ctx.send(embed=embed)
            return

        if not ctx.author.voice:
            embed = create_embed(description="Сначала зайди в голосовой канал!", theme="error")
            await ctx.send(embed=embed)
            return

        channel = ctx.author.voice.channel
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.move_to(channel)
        else:
            self.voice_client = await channel.connect()
            self.play_next_song()
            
        embed = create_embed(title="Подключился!", description=f"Канал: **{channel.name}**\nФоновая музыка запущена!\n\nЗаказывай музыку через `!play <название>`", theme="music")
        await ctx.send(embed=embed)

    @commands.command(name='play')
    async def play_command(self, ctx, *, query: str):
        """Ищет песню на YouTube и предлагает выбор (1-5)."""
        if not self.voice_client or not self.voice_client.is_connected():
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

        msg = "**Выбери трек (напиши цифру от 1 до 5):**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, item in enumerate(results, 1):
            title = item.get('snippet', {}).get('title', 'Без названия')
            msg += f"**`{i}`**  ▸  {title}\n"

        embed = create_embed(title="Результаты поиска", description=msg, theme="music")
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        try:
            msg_reply = await self.bot.wait_for('message', check=check, timeout=30.0)
            choice = int(msg_reply.content)
            if 1 <= choice <= len(results):
                selected_video = results[choice - 1]
                video_id = selected_video.get('id', {}).get('videoId')
                video_title = selected_video.get('snippet', {}).get('title')
                url = f"https://www.youtube.com/watch?v={video_id}"

                self.music_queue.append({'url': url, 'requester': ctx.author.id, 'title': video_title})
                embed = create_embed(title="Добавлено в очередь", description=f"**{video_title}**", theme="success")
                await ctx.send(embed=embed)

                if self.current_requester == self.bot.user.id and self.voice_client.is_playing():
                    self.voice_client.stop()
            else:
                embed = create_embed(description="Неверный номер. Попробуй заново через `!play`.", theme="error")
                await ctx.send(embed=embed)
        except asyncio.TimeoutError:
            embed = create_embed(description="Время вышло! Ты не выбрал трек.\nНапиши `!play` снова.", theme="error")
            await ctx.send(embed=embed)

    @commands.command(name='skip')
    async def skip_command(self, ctx):
        """Пропускает текущую песню. Только для заказчика или админа."""
        if not check_user_allowed(ctx.author, ctx.guild.owner_id):
            embed = create_embed(description=f"У вас нет прав для этой команды!\nНужны роли: `{get_roles_str()}`", theme="error")
            await ctx.send(embed=embed)
            return
            
        if not self.voice_client or not self.voice_client.is_playing():
            embed = create_embed(description="Сейчас ничего не играет!", theme="error")
            await ctx.send(embed=embed)
            return

        if self.current_requester == self.bot.user.id or self.current_requester == ctx.author.id or ctx.author.id == ctx.guild.owner_id:
            self.voice_client.stop()
            embed = create_embed(title="Трек пропущен", description="Включаю следующий...", theme="music")
            await ctx.send(embed=embed)
        else:
            embed = create_embed(description="Ты не можешь пропустить чужой заказ!", theme="error")
            await ctx.send(embed=embed)

    @commands.command(name='stop')
    async def stop_command(self, ctx):
        """Останавливает бота и очищает очередь."""
        if not check_user_allowed(ctx.author, ctx.guild.owner_id):
            embed = create_embed(description=f"У вас нет прав для этой команды!\nНужны роли: `{get_roles_str()}`", theme="error")
            await ctx.send(embed=embed)
            return
            
        self.music_queue.clear()
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
            self.voice_client = None
            embed = create_embed(title="Отключился", description="Очередь очищена!", theme="music")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
