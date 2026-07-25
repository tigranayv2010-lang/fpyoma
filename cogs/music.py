import discord
from discord.ext import commands
import asyncio
import yt_dlp
from utils.ui import create_embed
from utils.api import get_random_youtube

# YTDL Settings
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
ffmpeg_options = {'options': '-vn'}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.is_playing = False
        self.current_requester = None

    def get_vc(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        return interaction.guild.voice_client

    async def ensure_voice(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice:
            await interaction.response.send_message(embed=create_embed(description="Вы не в голосовом канале!", theme="error"), ephemeral=True)
            return False
            
        vc = self.get_vc(interaction)
        if not vc:
            await interaction.user.voice.channel.connect()
        return True

    def play_next_song(self):
        vc = discord.utils.get(self.bot.voice_clients)
        if not vc or not vc.is_connected():
            self.is_playing = False
            return
            
        if self.queue:
            song = self.queue.pop(0)
            url, self.current_requester = song['url'], song['requester']
            print(f"Играем заказ из очереди: {url}")
        else:
            url, topic = get_random_youtube()
            self.current_requester = self.bot.user.id
            print(f"Очередь пуста. Включаем фоновую музыку: {url} (Тема: {topic})")
            if not url:
                self.bot.loop.call_later(5, self.play_next_song)
                return

        def after_playing(e):
            if e:
                print(f"Player error: {e}")
            self.bot.loop.call_later(2, self.play_next_song)

        async def play():
            try:
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                vc.play(player, after=after_playing)
            except Exception as e:
                print(f"Ошибка воспроизведения: {e}")
                self.bot.loop.call_later(2, self.play_next_song)
                
        asyncio.run_coroutine_threadsafe(play(), self.bot.loop)

    @discord.app_commands.command(name="play", description="Воспроизвести музыку с YouTube")
    async def play(self, interaction: discord.Interaction, search: str):
        if not await self.ensure_voice(interaction):
            return
            
        await interaction.response.defer()
        
        # Check permissions for /play
        from utils.config import check_user_allowed, get_roles_str
        if not check_user_allowed(interaction.user, interaction.guild.owner_id):
            embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        self.queue.append({'url': search, 'requester': interaction.user.id})
        
        vc = self.get_vc(interaction)
        if not vc.is_playing() and not self.is_playing:
            self.is_playing = True
            self.play_next_song()
            embed = create_embed(description=f"🎵 Начинаем воспроизведение: **{search}**", theme="youtube")
        else:
            embed = create_embed(description=f"➕ Добавлено в очередь: **{search}**", theme="info")
            
        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(name="skip", description="Пропустить текущий трек")
    async def skip(self, interaction: discord.Interaction):
        vc = self.get_vc(interaction)
        if not vc or not vc.is_playing():
            await interaction.response.send_message(embed=create_embed(description="Сейчас ничего не играет!", theme="error"), ephemeral=True)
            return
            
        from utils.config import check_user_allowed, get_roles_str
        if self.current_requester == interaction.user.id or check_user_allowed(interaction.user, interaction.guild.owner_id):
            vc.stop()
            await interaction.response.send_message(embed=create_embed(description="⏭️ Трек пропущен!", theme="success"))
        else:
            embed = create_embed(description=f"Вы не можете пропустить этот трек!\nНужны роли: `{get_roles_str()}`", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="stop", description="Остановить музыку и очистить очередь")
    async def stop(self, interaction: discord.Interaction):
        from utils.config import check_user_allowed, get_roles_str
        if not check_user_allowed(interaction.user, interaction.guild.owner_id):
            embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        vc = self.get_vc(interaction)
        if vc:
            self.queue.clear()
            self.is_playing = False
            vc.stop()
            await vc.disconnect()
            await interaction.response.send_message(embed=create_embed(description="🛑 Музыка остановлена, бот покинул канал.", theme="success"))
        else:
            await interaction.response.send_message(embed=create_embed(description="Бот не в голосовом канале!", theme="error"), ephemeral=True)

    @discord.app_commands.command(name="join", description="Присоединиться к голосовому каналу")
    async def join(self, interaction: discord.Interaction):
        if await self.ensure_voice(interaction):
            await interaction.response.send_message(embed=create_embed(description="✅ Подключился к вашему голосовому каналу!", theme="success"))

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
