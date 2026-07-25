import discord
from discord.ext import commands, tasks
import random
from utils.ui import create_embed
from utils.config import load_config, load_topics, save_topics
from utils.api import get_random_anime_image, get_random_tiktok, get_random_youtube, get_random_pixabay, get_random_nekos_nsfw
import asyncio

PLATFORM_HANDLERS = {
    "YouTube": {"func": get_random_youtube, "title": "Смотри, что нашел", "theme": "youtube", "type": "video"},
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

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="btn_yt", emoji=discord.PartialEmoji.from_str("<:youtube:1530525984942588027>"))
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button(interaction, "YouTube")

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="btn_tt", emoji=discord.PartialEmoji.from_str("<:tiktok:1530525976797380638>"))
    async def btn_tt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button(interaction, "TikTok")
        
    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.primary, custom_id="btn_px", emoji=discord.PartialEmoji.from_str("<:pinterest:1530525972540166244>"))
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button(interaction, "Pixabay")
        
    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="btn_nk", emoji=discord.PartialEmoji.from_str("<:18:1530525967297020035>"))
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
        
        # Load topics dynamically
        topics = load_topics(platform)

        options = [discord.SelectOption(label="Случайная тема", value="random", emoji="🎲")]
        if topics:
            # We filter out "random" just in case it's in the topics list to avoid duplicate values
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
            
        url, topic, title, thumb = data.get("url"), data.get("topic"), data.get("title"), data.get("thumbnail")
        cfg = load_config()
        target_id = cfg.get("nsfw_channel_id") if self.platform == "Nekos" else cfg.get("main_channel_id")
        channel = interaction.client.get_channel(target_id) if target_id else None
        
        if not channel:
            error_embed = create_embed(description=f"Канал для {'NSFW' if self.platform == 'Nekos' else 'основного'} контента не настроен! Используйте `/setup`", theme="error")
            await interaction.edit_original_response(content=None, embed=error_embed, view=None)
            return

        desc = f"**Тема:** {topic}\n\n[▶ Открыть контент]({url})\n\n{url}" if platform_info["type"] == "video" else f"**Тема:** {topic}"
        embed_title = title if title else platform_info["title"]
        embed = create_embed(title=embed_title, description=desc, theme=platform_info["theme"])
        
        if platform_info["type"] == "image":
            embed.set_image(url=url)
        if thumb:
            embed.set_thumbnail(url=thumb)
            
        download_url = data.get("download_url")
        file_attachment = None
        
        if download_url:
            import aiohttp
            import io
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as resp:
                        if resp.status == 200:
                            video_bytes = await resp.read()
                            if len(video_bytes) < 25 * 1024 * 1024:  # 25 MB limit
                                file_attachment = discord.File(fp=io.BytesIO(video_bytes), filename="video.mp4")
                                # If we successfully downloaded the video, we can remove the video link from the description to make it cleaner
                                embed.description = f"**Тема:** {topic}"
            except Exception as e:
                print(f"Ошибка загрузки видеофайла: {e}")
                
        if platform_info["type"] == "video":
            if file_attachment:
                await channel.send(file=file_attachment)
            else:
                await channel.send(content=url)
        else:
            await channel.send(embed=embed)
            
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

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="send_yt", emoji=discord.PartialEmoji.from_str("<:youtube:1530525984942588027>"))
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_platform(interaction, "YouTube")

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="send_tt", emoji=discord.PartialEmoji.from_str("<:tiktok:1530525976797380638>"))
    async def btn_tt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_platform(interaction, "TikTok")

    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.success, custom_id="send_px", emoji=discord.PartialEmoji.from_str("<:pinterest:1530525972540166244>"))
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_platform(interaction, "Pixabay")

    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="send_nk", emoji=discord.PartialEmoji.from_str("<:18:1530525967297020035>"))
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_platform(interaction, "Nekos")
        
    @discord.ui.button(label="Anime", style=discord.ButtonStyle.secondary, custom_id="send_an", emoji=discord.PartialEmoji.from_str("<:animejpg:1530526067939479654>"))
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
        url, topic = data.get("url"), data.get("topic")
        if url:
            embed = create_embed(title="Аниме Арт", description=f"**Тема:** {topic}", image_url=url, theme="anime")
            await channel.send(embed=embed)
            await interaction.followup.send(embed=create_embed(description=f"✅ Отправлено в <#{target_id}>", theme="success"), ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed(description="Ошибка при получении Аниме.", theme="error"), ephemeral=True)

@discord.app_commands.command(name="send", description="Отправить контент в чат с выбором темы")
async def send_command(interaction: discord.Interaction):
    desc = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "<:youtube:1530525984942588027>  **YouTube**  │  <:tiktok:1530525976797380638>  **TikTok**\n"
        "<:pinterest:1530525972540166244>  **Pixabay**  │  <:18:1530525967297020035>  **Nekos 18+**\n"
        "<:animejpg:1530526067939479654>  **Anime**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выбери платформу ниже и отправь контент в чат:"
    )
    await interaction.response.send_message(embed=create_embed(title="Отправить контент", description=desc), view=SendPlatformView(), ephemeral=False)

@tasks.loop(hours=2)
async def auto_post_loop(bot_instance):
    await bot_instance.wait_until_ready()
    cfg = load_config()
    main_channel = bot_instance.get_channel(cfg.get("main_channel_id", 0))
    nsfw_channel = bot_instance.get_channel(cfg.get("nsfw_channel_id", 0))
    
    content_funcs = [
        ("Nekos", get_random_nekos_nsfw, nsfw_channel),
        ("Anime", get_random_anime_image, main_channel),
        ("TikTok", get_random_tiktok, main_channel),
        ("YouTube", get_random_youtube, main_channel),
        ("Pixabay", get_random_pixabay, main_channel)
    ]
    
    platform, func, target_channel = random.choice(content_funcs)
    if not target_channel:
        return
        
    import asyncio
    data = await asyncio.to_thread(func)
    url, topic, title, thumb = data.get("url"), data.get("topic"), data.get("title"), data.get("thumbnail")
    if not url:
        return
        
    if platform == "Anime":
        embed = create_embed(title="Время контента!", description=f"**Тема:** {topic}", image_url=url, theme="anime")
    elif platform == "Pixabay":
        embed = create_embed(title="Красивое фото!", description=f"**Тема:** {topic}", image_url=url, theme="pixabay")
    elif platform == "Nekos":
        embed = create_embed(title="18+ Контент!", description=f"**Тема:** {topic}", image_url=url, theme="nekos")
    elif platform == "TikTok":
        embed_title = title if title else "Свежий TikTok!"
        embed = create_embed(title=embed_title, description=f"**Тема:** {topic}\n\n[▶ Открыть TikTok]({url})\n\n{url}", theme="tiktok")
        if thumb: embed.set_thumbnail(url=thumb)
    else:
        embed_title = title if title else "Зацени видео!"
        embed = create_embed(title=embed_title, description=f"**Тема:** {topic}\n\n[▶ Открыть YouTube]({url})\n\n{url}", theme="youtube")
        if thumb: embed.set_thumbnail(url=thumb)
        
    download_url = data.get("download_url")
    file_attachment = None
    if download_url:
        import aiohttp
        import io
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as resp:
                    if resp.status == 200:
                        video_bytes = await resp.read()
                        if len(video_bytes) < 25 * 1024 * 1024:
                            file_attachment = discord.File(fp=io.BytesIO(video_bytes), filename="video.mp4")
                            embed.description = f"**Тема:** {topic}"
        except Exception as e:
            print(f"Ошибка загрузки видеофайла в авто-посте: {e}")
            
    if platform in ["TikTok", "YouTube"]:
        if file_attachment:
            await target_channel.send(file=file_attachment)
        else:
            await target_channel.send(content=url)
    else:
        await target_channel.send(embed=embed)

@auto_post_loop.before_loop
async def before_auto_post():
    pass

async def setup(bot):
    class ContentCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.bot.tree.add_command(topics_command)
            self.bot.tree.add_command(send_command)
            
        @commands.Cog.listener()
        async def on_ready(self):
            # Register persistent views
            self.bot.add_view(SendPlatformView())
            for plat in ["YouTube", "TikTok", "Pixabay", "Nekos"]:
                self.bot.add_view(TopicSelectView(plat))
                
            if not auto_post_loop.is_running():
                cfg = load_config()
                auto_post_loop.change_interval(hours=cfg.get("auto_post_interval_hours", 2))
                auto_post_loop.start(self.bot)
                
        # This acts globally for the cog's app_commands
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            from utils.config import check_user_allowed, get_roles_str
            if not check_user_allowed(interaction.user, interaction.guild.owner_id):
                embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
            return True

    await bot.add_cog(ContentCog(bot))
