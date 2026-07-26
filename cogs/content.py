import discord
from discord.ext import commands, tasks
import random
import asyncio
import aiohttp
import io
from utils.ui import create_embed, EMBED_THEMES
from utils.config import load_config, load_topics, save_topics
from utils.api import get_random_anime_image, get_random_tiktok, get_random_pixabay, get_random_nekos_nsfw

PLATFORM_HANDLERS = {
    "TikTok": get_random_tiktok,
    "Pixabay": get_random_pixabay,
    "Nekos": get_random_nekos_nsfw,
    "Anime": get_random_anime_image
}

async def send_media(channel: discord.TextChannel, data: dict):
    if not data or not data.get("url"): return
    
    url = data.get("download_url") or data.get("url")
    file_attachment = None
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    media_bytes = await resp.read()
                    if len(media_bytes) < 25 * 1024 * 1024:
                        ext = data.get("ext")
                        if not ext:
                            ext = url.split('?')[0].split('.')[-1]
                            if len(ext) > 4 or not ext.isalnum(): ext = "jpg"
                        file_attachment = discord.File(fp=io.BytesIO(media_bytes), filename=f"media.{ext}")
    except Exception:
        pass
        
    await channel.send(file=file_attachment) if file_attachment else await channel.send(content=data.get("url"))

class TopicModal(discord.ui.Modal):
    def __init__(self, platform: str):
        super().__init__(title=f"Темы для {platform}")
        self.platform = platform
        self.topics_input = discord.ui.TextInput(
            label="Темы (через запятую)", style=discord.TextStyle.paragraph,
            default=", ".join(load_topics(platform)), required=True
        )
        self.add_item(self.topics_input)

    async def on_submit(self, interaction: discord.Interaction):
        topics = [t.strip() for t in self.topics_input.value.split(',') if t.strip()]
        save_topics(self.platform, topics)
        embed = create_embed(f"**{self.platform}**\n{', '.join(f'`{t}`' for t in topics)}", "Темы обновлены", "success")
        await interaction.response.send_message(embed=embed, ephemeral=False)

class TopicView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    async def _handle(self, interaction: discord.Interaction, p: str):
        await interaction.response.send_modal(TopicModal(p))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="btn_tt", emoji=EMBED_THEMES["tiktok"]["emoji"])
    async def btn_tt(self, i: discord.Interaction, b: discord.ui.Button): await self._handle(i, "TikTok")
        
    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.primary, custom_id="btn_px", emoji=EMBED_THEMES["pixabay"]["emoji"])
    async def btn_px(self, i: discord.Interaction, b: discord.ui.Button): await self._handle(i, "Pixabay")
        
    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="btn_nk", emoji=EMBED_THEMES["nekos"]["emoji"])
    async def btn_nk(self, i: discord.Interaction, b: discord.ui.Button): await self._handle(i, "Nekos")

@discord.app_commands.command(name="topics", description="Настройка тем")
async def topics_command(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_embed("Выбери платформу для настройки авто-тем", "Настройка", "settings"), view=TopicView(), ephemeral=True)

class TopicSelect(discord.ui.Select):
    def __init__(self, platform: str):
        self.platform = platform
        opts = [discord.SelectOption(label="Случайная тема", value="random", emoji="🎲")]
        opts.extend([discord.SelectOption(label=t, value=t) for t in load_topics(platform) if t.lower() != "random"][:24])
        super().__init__(placeholder=f"Выбери тему ({platform})", options=opts, custom_id=f"select_{platform}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        query = self.values[0] if self.values[0] != "random" else None
        
        cfg = load_config()
        tid = cfg.get("nsfw_channel_id") if self.platform == "Nekos" else cfg.get("main_channel_id")
        channel = interaction.client.get_channel(tid) if tid else None
        
        if not channel:
            return await interaction.edit_original_response(embed=create_embed("Канал не настроен!", theme="error"), view=None)
            
        data = await asyncio.to_thread(PLATFORM_HANDLERS[self.platform], query)
        if not data:
            return await interaction.edit_original_response(embed=create_embed("Ошибка API", theme="error"), view=None)
            
        await send_media(channel, data)
        try: await interaction.delete_original_response()
        except: pass

class SendPlatformView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    async def _handle_platform(self, interaction: discord.Interaction, platform: str):
        view = discord.ui.View(timeout=None)
        view.add_item(TopicSelect(platform))
        await interaction.response.send_message(f"Тема для **{platform}**:", view=view, ephemeral=True)

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="send_tt", emoji=EMBED_THEMES["tiktok"]["emoji"])
    async def btn_tt(self, i: discord.Interaction, b: discord.ui.Button): await self._handle_platform(i, "TikTok")

    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.success, custom_id="send_px", emoji=EMBED_THEMES["pixabay"]["emoji"])
    async def btn_px(self, i: discord.Interaction, b: discord.ui.Button): await self._handle_platform(i, "Pixabay")

    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="send_nk", emoji=EMBED_THEMES["nekos"]["emoji"])
    async def btn_nk(self, i: discord.Interaction, b: discord.ui.Button): await self._handle_platform(i, "Nekos")
        
    @discord.ui.button(label="Anime", style=discord.ButtonStyle.secondary, custom_id="send_an", emoji=EMBED_THEMES["anime"]["emoji"])
    async def btn_an(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        tid = load_config().get("main_channel_id")
        channel = interaction.client.get_channel(tid) if tid else None
        
        if not channel: return await interaction.followup.send("Канал не настроен!", ephemeral=True)
            
        data = await asyncio.to_thread(get_random_anime_image)
        if data:
            await send_media(channel, data)
        else:
            await interaction.followup.send("Ошибка API", ephemeral=True)

@discord.app_commands.command(name="panel", description="Панель контента")
async def panel_command(interaction: discord.Interaction):
    desc = "Выбери платформу для мгновенной отправки медиа в чат."
    await interaction.response.send_message(embed=create_embed(desc, "Контент-панель", "info"), view=SendPlatformView())

@discord.app_commands.command(name="send", description="Отправить контент")
@discord.app_commands.choices(platform=[discord.app_commands.Choice(name=p, value=p) for p in PLATFORM_HANDLERS.keys()])
async def send_command(interaction: discord.Interaction, platform: str, topic: str):
    if platform == "Nekos" and not getattr(interaction.channel, "is_nsfw", lambda: False)():
        return await interaction.response.send_message(embed=create_embed("Только NSFW каналы!", theme="error"), ephemeral=True)
        
    await interaction.response.defer()
    
    data = await asyncio.to_thread(PLATFORM_HANDLERS[platform], topic if platform != "Anime" else None)
    if not data:
        return await interaction.followup.send("Ошибка API", ephemeral=True)
        
    await send_media(interaction.channel, data)
    try: await interaction.delete_original_response()
    except: pass

@tasks.loop(minutes=120)
async def auto_post_loop(bot_instance):
    await bot_instance.wait_until_ready()
    cfg = load_config()
    main_ch = bot_instance.get_channel(cfg.get("main_channel_id", 0))
    nsfw_ch = bot_instance.get_channel(cfg.get("nsfw_channel_id", 0))
    
    funcs = [("Nekos", nsfw_ch), ("Anime", main_ch), ("TikTok", main_ch), ("Pixabay", main_ch)]
    platform, target_channel = random.choice(funcs)
    
    if target_channel:
        data = await asyncio.to_thread(PLATFORM_HANDLERS[platform])
        if data: await send_media(target_channel, data)

@auto_post_loop.before_loop
async def before_auto_post(): pass

async def setup(bot):
    class ContentCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            for cmd in [topics_command, panel_command, send_command]:
                self.bot.tree.add_command(cmd)
            
        @commands.Cog.listener()
        async def on_ready(self):
            self.bot.add_view(SendPlatformView())
            if not auto_post_loop.is_running():
                auto_post_loop.change_interval(minutes=load_config().get("auto_post_interval_minutes", 120))
                auto_post_loop.start(self.bot)
                
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if getattr(interaction.command, "name", "") == "send": return True
            from utils.config import check_user_allowed
            if not check_user_allowed(interaction.user, interaction.guild.owner_id):
                await interaction.response.send_message(embed=create_embed("Нет прав!", theme="error"), ephemeral=True)
                return False
            return True

    await bot.add_cog(ContentCog(bot))
