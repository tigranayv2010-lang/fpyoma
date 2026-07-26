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
    if not data or not data.get("url"):
        return
    
    url = data.get("download_url") or data.get("url")
    file_attachment = None
    
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    media_bytes = await resp.read()
                    if len(media_bytes) < 25 * 1024 * 1024:
                        ext = data.get("ext")
                        if not ext:
                            ext = url.split('?')[0].split('.')[-1]
                            if len(ext) > 4 or not ext.isalnum():
                                ext = "jpg"
                        file_attachment = discord.File(fp=io.BytesIO(media_bytes), filename=f"media.{ext}")
    except Exception as e:
        print(f"send_media error: {e}")
        
    if file_attachment:
        await channel.send(file=file_attachment)
    else:
        await channel.send(content=data.get("url"))

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
    def __init__(self):
        super().__init__(timeout=None)
    
    async def _handle(self, interaction: discord.Interaction, p: str):
        await interaction.response.send_modal(TopicModal(p))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="btn_tt", emoji=EMBED_THEMES["tiktok"]["emoji"])
    async def btn_tt(self, i: discord.Interaction, b: discord.ui.Button):
        await self._handle(i, "TikTok")
        
    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.primary, custom_id="btn_px", emoji=EMBED_THEMES["pixabay"]["emoji"])
    async def btn_px(self, i: discord.Interaction, b: discord.ui.Button):
        await self._handle(i, "Pixabay")
        
    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="btn_nk", emoji=EMBED_THEMES["nekos"]["emoji"])
    async def btn_nk(self, i: discord.Interaction, b: discord.ui.Button):
        await self._handle(i, "Nekos")

@discord.app_commands.command(name="topics", description="Настройка тем")
async def topics_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=create_embed("Выбери платформу для настройки авто-тем", "Настройка", "settings"),
        view=TopicView(), ephemeral=True
    )

class TopicSelect(discord.ui.Select):
    def __init__(self, platform: str):
        self.platform = platform
        opts = [discord.SelectOption(label="Случайная тема", value="random", emoji="🎲")]
        for t in load_topics(platform)[:24]:
            if t.lower() != "random":
                opts.append(discord.SelectOption(label=t, value=t))
        super().__init__(placeholder=f"Выбери тему ({platform})", options=opts, custom_id=f"select_{platform}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        query = self.values[0] if self.values[0] != "random" else None
        
        cfg = load_config()
        tid = cfg.get("nsfw_channel_id") if self.platform == "Nekos" else cfg.get("main_channel_id")
        channel = interaction.client.get_channel(tid) if tid else None
        
        if not channel:
            return await interaction.edit_original_response(
                embed=create_embed("Канал не настроен!", theme="error"), view=None
            )
            
        data = await asyncio.to_thread(PLATFORM_HANDLERS[self.platform], query)
        if not data:
            return await interaction.edit_original_response(
                embed=create_embed("Ошибка API", theme="error"), view=None
            )
            
        await send_media(channel, data)
        try:
            await interaction.delete_original_response()
        except Exception:
            pass

class SendPlatformView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _handle_platform(self, interaction: discord.Interaction, platform: str):
        view = discord.ui.View(timeout=None)
        view.add_item(TopicSelect(platform))
        await interaction.response.send_message(f"Тема для **{platform}**:", view=view, ephemeral=True)

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.primary, custom_id="send_tt", emoji=EMBED_THEMES["tiktok"]["emoji"])
    async def btn_tt(self, i: discord.Interaction, b: discord.ui.Button):
        await self._handle_platform(i, "TikTok")

    @discord.ui.button(label="Pixabay", style=discord.ButtonStyle.success, custom_id="send_px", emoji=EMBED_THEMES["pixabay"]["emoji"])
    async def btn_px(self, i: discord.Interaction, b: discord.ui.Button):
        await self._handle_platform(i, "Pixabay")

    @discord.ui.button(label="Nekos", style=discord.ButtonStyle.danger, custom_id="send_nk", emoji=EMBED_THEMES["nekos"]["emoji"])
    async def btn_nk(self, i: discord.Interaction, b: discord.ui.Button):
        await self._handle_platform(i, "Nekos")
        
    @discord.ui.button(label="Anime", style=discord.ButtonStyle.secondary, custom_id="send_an", emoji=EMBED_THEMES["anime"]["emoji"])
    async def btn_an(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        tid = load_config().get("main_channel_id")
        channel = interaction.client.get_channel(tid) if tid else None
        
        if not channel:
            return await interaction.followup.send("Канал не настроен!", ephemeral=True)
            
        data = await asyncio.to_thread(get_random_anime_image)
        if data:
            await send_media(channel, data)
        else:
            await interaction.followup.send("Ошибка API", ephemeral=True)

@discord.app_commands.command(name="panel", description="Панель контента")
async def panel_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=create_embed("Выбери платформу для мгновенной отправки медиа в чат.", "Контент-панель", "info"),
        view=SendPlatformView()
    )

@discord.app_commands.command(name="send", description="Отправить контент")
@discord.app_commands.choices(platform=[
    discord.app_commands.Choice(name=p, value=p) for p in PLATFORM_HANDLERS.keys()
])
async def send_command(interaction: discord.Interaction, platform: str, topic: str):
    if platform == "Nekos" and not getattr(interaction.channel, "is_nsfw", lambda: False)():
        return await interaction.response.send_message(
            embed=create_embed("Только NSFW каналы!", theme="error"), ephemeral=True
        )
        
    await interaction.response.defer()
    
    data = await asyncio.to_thread(PLATFORM_HANDLERS[platform], topic if platform != "Anime" else None)
    if not data:
        return await interaction.followup.send("Ошибка API", ephemeral=True)
        
    await send_media(interaction.channel, data)
    try:
        await interaction.delete_original_response()
    except Exception:
        pass

async def setup(bot):
    class ContentCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            for cmd in [topics_command, panel_command, send_command]:
                self.bot.tree.add_command(cmd)

        @tasks.loop(minutes=120)
        async def auto_post(self):
            cfg = load_config()
            main_ch = self.bot.get_channel(cfg.get("main_channel_id", 0))
            nsfw_ch = self.bot.get_channel(cfg.get("nsfw_channel_id", 0))

            choices = []
            if main_ch:
                choices += [("TikTok", main_ch), ("Pixabay", main_ch), ("Anime", main_ch)]
            if nsfw_ch:
                choices.append(("Nekos", nsfw_ch))

            if not choices:
                print("auto_post: нет настроенных каналов, пропуск")
                return

            platform, channel = random.choice(choices)
            print(f"auto_post: отправляю {platform}")

            try:
                data = await asyncio.to_thread(PLATFORM_HANDLERS[platform])
                if data:
                    await send_media(channel, data)
                    print(f"auto_post: {platform} отправлен успешно")
                else:
                    print(f"auto_post: {platform} — API вернул пустой результат")
            except Exception as e:
                print(f"auto_post error: {e}")

        @auto_post.before_loop
        async def before_auto_post(self):
            await self.bot.wait_until_ready()

        @commands.Cog.listener()
        async def on_ready(self):
            self.bot.add_view(SendPlatformView())
            if not self.auto_post.is_running():
                interval = load_config().get("auto_post_interval_minutes", 120)
                self.auto_post.change_interval(minutes=interval)
                self.auto_post.start()
                print(f"auto_post запущен с интервалом {interval} мин.")

        async def cog_unload(self):
            self.auto_post.cancel()

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if getattr(interaction.command, "name", "") == "send":
                return True
            from utils.config import check_user_allowed
            if not check_user_allowed(interaction.user, interaction.guild.owner_id):
                await interaction.response.send_message(
                    embed=create_embed("Нет прав!", theme="error"), ephemeral=True
                )
                return False
            return True

    await bot.add_cog(ContentCog(bot))
