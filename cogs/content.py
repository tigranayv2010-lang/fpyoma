import discord
from discord.ext import commands, tasks
import random
from utils.ui import create_embed, EMBED_THEMES
from utils.config import load_config, load_topics, save_topics
from utils.api import get_random_anime_image, get_random_tiktok, get_random_pixabay, get_random_nekos_nsfw
import asyncio

PLATFORM_HANDLERS = {
    "TikTok": {"func": get_random_tiktok, "title": "Лови TikTok", "theme": "tiktok", "type": "video"},
    "Pixabay": {"func": get_random_pixabay, "title": "Красивое фото", "theme": "pixabay", "type": "image"},
    "Nekos": {"func": get_random_nekos_nsfw, "title": "18+ Контент", "theme": "nekos", "type": "image"}
}

class TopicModal(discord.ui.Modal):
    def __init__(self, platform: str):
        super().__init__(title=f"Темы для {platform}")
        self.platform = platform
        
        self.topics_input = discord.ui.TextInput(
            label="Темы (через запятую)",
            style=discord.TextStyle.paragraph,
            placeholder="Например: cats, funny, phonk",
            default=", ".join(load_topics(platform)),
            required=True
        )
        self.add_item(self.topics_input)

    async def on_submit(self, interaction: discord.Interaction):
        topics_list = [t.strip() for t in self.topics_input.value.split(',') if t.strip()]
        save_topics(self.platform, topics_list)
            
        topics_formatted = ', '.join([f'`{t}`' for t in topics_list])
        embed = create_embed(title="Темы обновлены", description=f"**Платформа:** {self.platform}\n\n{topics_formatted}", theme="success")
        await interaction.response.send_message(embed=embed, ephemeral=False)

class TopicView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_button(self, interaction: discord.Interaction, platform: str):
        await interaction.response.send_modal(TopicModal(platform))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="btn_tt", emoji=EMBED_THEMES["tiktok"]["emoji"])
    async def btn_tt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button(interaction, "TikTok")
        
    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.primary, custom_id="btn_px", emoji=EMBED_THEMES["pixabay"]["emoji"])
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button(interaction, "Pixabay")
        
    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="btn_nk", emoji=EMBED_THEMES["nekos"]["emoji"])
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button(interaction, "Nekos")

@discord.app_commands.command(name="topics", description="Настройка тем для контента")
async def topics_command(interaction: discord.Interaction):
    embed = create_embed(
        title="Настройка тем", 
        description="Выбери платформу, чтобы задать список тем для авто-отправки и случайного поиска.\n\nТемы будут выбираться рандомно из твоего списка.",
        theme="settings"
    )
    await interaction.response.send_message(embed=embed, view=TopicView(), ephemeral=True)

class TopicSelect(discord.ui.Select):
    def __init__(self, platform: str):
        self.platform = platform
        
        topics = load_topics(platform)
        options = [discord.SelectOption(label="Случайная тема", value="random", emoji="🎲")]
        if topics:
            filtered_topics = [t for t in topics if t.lower() != "random"]
            options.extend([discord.SelectOption(label=t, value=t) for t in filtered_topics[:24]])
            
        super().__init__(placeholder=f"Выбери тему для {platform}", options=options, custom_id=f"select_topic_{platform}")

    async def callback(self, interaction: discord.Interaction):
        import asyncio
        await interaction.response.defer()
        
        query = self.values[0] if self.values[0] != "random" else None
        platform_info = PLATFORM_HANDLERS.get(self.platform)
        
        if not platform_info:
            return
            
        data = await asyncio.to_thread(platform_info["func"], query)
        if not data or not data.get("url"):
            error_embed = create_embed(description=f"Ошибка при получении контента для {self.platform}.", theme="error")
            await interaction.edit_original_response(content=None, embed=error_embed, view=None)
            return
            
        url, topic = data.get("url"), data.get("topic")
        cfg = load_config()
        target_id = cfg.get("nsfw_channel_id") if self.platform == "Nekos" else cfg.get("main_channel_id")
        channel = interaction.client.get_channel(target_id) if target_id else None
        
        if not channel:
            error_embed = create_embed(description=f"Канал для {'NSFW' if self.platform == 'Nekos' else 'основного'} контента не настроен! Используйте `/setup`", theme="error")
            await interaction.edit_original_response(content=None, embed=error_embed, view=None)
            return
            
        download_url = data.get("download_url") or data.get("url")
        file_attachment = None
        
        if download_url:
            import aiohttp
            import io
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as resp:
                        if resp.status == 200:
                            media_bytes = await resp.read()
                            if len(media_bytes) < 25 * 1024 * 1024:
                                ext = download_url.split('?')[0].split('.')[-1]
                                if len(ext) > 4 or not ext.isalnum(): ext = "jpg"
                                file_attachment = discord.File(fp=io.BytesIO(media_bytes), filename=f"media.{ext}")
            except Exception as e:
                print(f"Ошибка загрузки файла: {e}")
                
        if file_attachment:
            await channel.send(file=file_attachment)
        else:
            await channel.send(content=url)
            
        try:
            await interaction.delete_original_response()
        except discord.errors.HTTPException:
            pass

class TopicSelectView(discord.ui.View):
    def __init__(self, platform: str):
        super().__init__(timeout=None)
        self.add_item(TopicSelect(platform))

class SendPlatformView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_platform(self, interaction: discord.Interaction, platform: str):
        await interaction.response.send_message(f"Выбери тему для **{platform}**:", view=TopicSelectView(platform), ephemeral=True)

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="send_tt", emoji=EMBED_THEMES["tiktok"]["emoji"])
    async def btn_tt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_platform(interaction, "TikTok")

    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.success, custom_id="send_px", emoji=EMBED_THEMES["pixabay"]["emoji"])
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_platform(interaction, "Pixabay")

    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="send_nk", emoji=EMBED_THEMES["nekos"]["emoji"])
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_platform(interaction, "Nekos")
        
    @discord.ui.button(label="Anime", style=discord.ButtonStyle.secondary, custom_id="send_an", emoji=EMBED_THEMES["anime"]["emoji"])
    async def btn_an(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        cfg = load_config()
        target_id = cfg.get("main_channel_id")
        channel = interaction.client.get_channel(target_id) if target_id else None
        
        if not channel:
            await interaction.followup.send(embed=create_embed(description="Основной канал не настроен!", theme="error"), ephemeral=True)
            return
            
        import asyncio
        data = await asyncio.to_thread(get_random_anime_image)
        url = data.get("url")
        if url:
            import aiohttp
            import io
            file_attachment = None
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            media_bytes = await resp.read()
                            if len(media_bytes) < 25 * 1024 * 1024:
                                ext = url.split('?')[0].split('.')[-1]
                                if len(ext) > 4 or not ext.isalnum(): ext = "jpg"
                                file_attachment = discord.File(fp=io.BytesIO(media_bytes), filename=f"media.{ext}")
            except Exception:
                pass
            
            if file_attachment:
                await channel.send(file=file_attachment)
            else:
                await channel.send(content=url)
            await interaction.followup.send(embed=create_embed(description=f"✅ Отправлено в <#{target_id}>", theme="success"), ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed(description="Ошибка при получении Аниме.", theme="error"), ephemeral=True)

@discord.app_commands.command(name="panel", description="Панель администратора для отправки контента")
async def panel_command(interaction: discord.Interaction):
    desc = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"{EMBED_THEMES['tiktok']['emoji']}  **TikTok**  │  {EMBED_THEMES['pixabay']['emoji']}  **Pixabay**\n"
        f"{EMBED_THEMES['nekos']['emoji']}  **Nekos 18+**  │  {EMBED_THEMES['anime']['emoji']}  **Anime**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выбери платформу ниже и отправь контент в чат:"
    )
    await interaction.response.send_message(embed=create_embed(title="Панель контента", description=desc), view=SendPlatformView(), ephemeral=False)

@discord.app_commands.command(name="send", description="Отправить контент на выбранную тему")
@discord.app_commands.choices(platform=[
    discord.app_commands.Choice(name="TikTok", value="TikTok"),
    discord.app_commands.Choice(name="Pixabay", value="Pixabay"),
    discord.app_commands.Choice(name="Nekos (18+)", value="Nekos"),
    discord.app_commands.Choice(name="Anime", value="Anime")
])
async def send_command(interaction: discord.Interaction, platform: str, topic: str):
    if platform == "Nekos" and not getattr(interaction.channel, "is_nsfw", lambda: False)():
        embed = create_embed(description="🔞 Этот контент можно запрашивать только в NSFW каналах (18+)!", theme="error")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    await interaction.response.defer()
    
    platform_info = PLATFORM_HANDLERS.get(platform)
    if not platform_info and platform != "Anime":
        await interaction.followup.send("Платформа не найдена.", ephemeral=True)
        return
        
    import asyncio
    
    if platform == "Anime":
        data = await asyncio.to_thread(get_random_anime_image)
    else:
        data = await asyncio.to_thread(platform_info["func"], topic)
    
    if not data or not data.get("url"):
        error_embed = create_embed(description=f"Ошибка при получении контента для {platform}.", theme="error")
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        return
        
    url, actual_topic = data.get("url"), data.get("topic")
    
    download_url = data.get("download_url") or data.get("url")
    file_attachment = None
    
    if download_url:
        import aiohttp
        import io
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as resp:
                    if resp.status == 200:
                        media_bytes = await resp.read()
                        if len(media_bytes) < 25 * 1024 * 1024:
                            ext = download_url.split('?')[0].split('.')[-1]
                            if len(ext) > 4 or not ext.isalnum(): ext = "jpg"
                            file_attachment = discord.File(fp=io.BytesIO(media_bytes), filename=f"media.{ext}")
        except Exception as e:
            print(f"Ошибка загрузки файла (user /send): {e}")
            
    if file_attachment:
        await interaction.followup.send(file=file_attachment)
    else:
        await interaction.followup.send(content=url)

@tasks.loop(minutes=120)
async def auto_post_loop(bot_instance):
    await bot_instance.wait_until_ready()
    cfg = load_config()
    main_channel = bot_instance.get_channel(cfg.get("main_channel_id", 0))
    nsfw_channel = bot_instance.get_channel(cfg.get("nsfw_channel_id", 0))
    
    content_funcs = [
        ("Nekos", get_random_nekos_nsfw, nsfw_channel),
        ("Anime", get_random_anime_image, main_channel),
        ("TikTok", get_random_tiktok, main_channel),
        ("Pixabay", get_random_pixabay, main_channel)
    ]
    
    platform, func, target_channel = random.choice(content_funcs)
    if not target_channel:
        return
        
    import asyncio
    data = await asyncio.to_thread(func)
    url, topic = data.get("url"), data.get("topic")
    if not url:
        return
        
    download_url = data.get("download_url") or data.get("url")
    file_attachment = None
    if download_url:
        import aiohttp
        import io
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as resp:
                    if resp.status == 200:
                        media_bytes = await resp.read()
                        if len(media_bytes) < 25 * 1024 * 1024:
                            ext = download_url.split('?')[0].split('.')[-1]
                            if len(ext) > 4 or not ext.isalnum(): ext = "jpg"
                            file_attachment = discord.File(fp=io.BytesIO(media_bytes), filename=f"media.{ext}")
        except Exception as e:
            print(f"Ошибка загрузки файла в авто-посте: {e}")
            
    if file_attachment:
        await target_channel.send(file=file_attachment)
    else:
        await target_channel.send(content=url)

@auto_post_loop.before_loop
async def before_auto_post():
    pass

async def setup(bot):
    class ContentCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.bot.tree.add_command(topics_command)
            self.bot.tree.add_command(panel_command)
            self.bot.tree.add_command(send_command)
            
        @commands.Cog.listener()
        async def on_ready(self):
            self.bot.add_view(SendPlatformView())
            for plat in ["TikTok", "Pixabay", "Nekos"]:
                self.bot.add_view(TopicSelectView(plat))
                
            if not auto_post_loop.is_running():
                cfg = load_config()
                auto_post_loop.change_interval(minutes=cfg.get("auto_post_interval_minutes", 120))
                auto_post_loop.start(self.bot)
                
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.type == discord.InteractionType.application_command and getattr(interaction.command, "name", "") == "send":
                return True
                
            from utils.config import check_user_allowed, get_roles_str
            if not check_user_allowed(interaction.user, interaction.guild.owner_id):
                embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
            return True

    await bot.add_cog(ContentCog(bot))
