import discord
from discord.ext import commands, tasks
import random
from utils.ui import create_embed
from utils.config import load_config, save_config, check_user_allowed, get_roles_str
from utils.config import get_saved_topics, save_topics, get_saved_tiktok_topics, save_tiktok_topics, get_saved_nekos_topics, save_nekos_topics, get_saved_pixabay_topics, save_pixabay_topics
from utils.api import get_random_anime_image, get_random_tiktok, get_random_youtube, get_random_pixabay, get_random_nekos_nsfw
import asyncio

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
        if not check_user_allowed(interaction.user, interaction.guild.owner_id):
            embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="btn_yt", emoji=discord.PartialEmoji.from_str("<:youtube:1530525984942588027>"))
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("YouTube"))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.success, custom_id="btn_tk", emoji=discord.PartialEmoji.from_str("<:tiktok:1530525976797380638>"))
    async def btn_tk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("TikTok"))

    @discord.ui.button(label="Фото (Pixabay)", style=discord.ButtonStyle.secondary, custom_id="btn_px", emoji=discord.PartialEmoji.from_str("<:pinterest:1530525972540166244>"))
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("Pixabay"))

    @discord.ui.button(label="Nekos (18+)", style=discord.ButtonStyle.danger, custom_id="btn_nk", emoji=discord.PartialEmoji.from_str("<:18:1530525967297020035>"))
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopicModal("Nekos"))

@discord.app_commands.command(name="topics", description="Настройка тем для контента")
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
            url, topic = get_random_youtube(custom_query=query)
            title = "Смотри, что нашел"
        elif self.platform == "TikTok":
            url, topic = get_random_tiktok(custom_query=query)
            title = "Лови TikTok"
        elif self.platform == "Pixabay":
            url, topic = get_random_pixabay(custom_query=query)
            title = "Красивое фото"
        elif self.platform == "Nekos":
            url, topic = get_random_nekos_nsfw(custom_query=query)
            title = "18+ Контент"
        
        if url:
            cfg = load_config()
            target_id = cfg.get("nsfw_channel_id") if self.platform == "Nekos" else cfg.get("main_channel_id")
            channel = interaction.client.get_channel(target_id) if target_id else None
            
            if channel:
                if self.platform in ["YouTube", "TikTok"]:
                    desc = f"**Тема:** {topic}\n\n[▶ Открыть видео]({url})\n\n{url}"
                    embed = create_embed(title=title, description=desc, theme=theme)
                    await channel.send(embed=embed)
                else:
                    desc = f"**Тема:** {topic}"
                    embed = create_embed(title=title, description=desc, image_url=url, theme=theme)
                    await channel.send(embed=embed)
                    
                success_embed = create_embed(description=f"✅ Успешно отправлено в <#{target_id}>", theme="success")
                await interaction.followup.send(embed=success_embed, ephemeral=True)
            else:
                embed = create_embed(description=f"Канал для {'NSFW' if self.platform == 'Nekos' else 'основного'} контента не настроен! Используйте `/setup`", theme="error")
                await interaction.followup.send(embed=embed, ephemeral=True)
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
        if not check_user_allowed(interaction.user, interaction.guild.owner_id):
            embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="send_yt", emoji=discord.PartialEmoji.from_str("<:youtube:1530525984942588027>"))
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_topics()
        if not topics: topics = ["lofi hip hop", "gaming mix", "synthwave"]
        embed = create_embed(description="<:youtube:1530525984942588027>  **YouTube** — Выбери тему:", theme="youtube")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("YouTube", topics))

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.success, custom_id="send_tk", emoji=discord.PartialEmoji.from_str("<:tiktok:1530525976797380638>"))
    async def btn_tk(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_tiktok_topics()
        if not topics: topics = ["phonk", "cats", "funny"]
        embed = create_embed(description="<:tiktok:1530525976797380638>  **TikTok** — Выбери тему:", theme="tiktok")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("TikTok", topics))

    @discord.ui.button(label="Фото (Pixabay)", style=discord.ButtonStyle.secondary, custom_id="send_px", emoji=discord.PartialEmoji.from_str("<:pinterest:1530525972540166244>"))
    async def btn_px(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_pixabay_topics()
        if not topics: topics = ["nature", "city", "cyberpunk"]
        embed = create_embed(description="<:pinterest:1530525972540166244>  **Pixabay** — Выбери тему:", theme="pixabay")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("Pixabay", topics))

    @discord.ui.button(label="Nekos (18+)", style=discord.ButtonStyle.danger, custom_id="send_nk", emoji=discord.PartialEmoji.from_str("<:18:1530525967297020035>"))
    async def btn_nk(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_saved_nekos_topics()
        if not topics: topics = ["girl", "pussy", "large_breasts", "kemonomimi", "exposed_girl_breasts"]
        embed = create_embed(description="<:18:1530525967297020035>  **Nekos 18+** — Выбери тему:", theme="nekos")
        await interaction.response.edit_message(embed=embed, content=None, view=TopicSelectView("Nekos", topics))

    @discord.ui.button(label="Аниме (Случайно)", style=discord.ButtonStyle.primary, custom_id="send_an", emoji=discord.PartialEmoji.from_str("<:animejpg:1530526067939479654>"))
    async def btn_an(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        url = get_random_anime_image()
        if url:
            embed = create_embed(title="Аниме арт", image_url=url, theme="anime")
            await interaction.followup.send(embed=embed)
        else:
            embed = create_embed(description="Ошибка при получении аниме.", theme="error")
            await interaction.followup.send(embed=embed)


@discord.app_commands.command(name="send", description="Отправить контент в чат с выбором темы")
async def send_command(interaction: discord.Interaction):
    if not check_user_allowed(interaction.user, interaction.guild.owner_id):
        embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
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
async def auto_post_loop(bot_instance):
    await bot_instance.wait_until_ready()
    cfg = load_config()
    main_channel = bot_instance.get_channel(cfg.get("main_channel_id", 0))
    nsfw_channel = bot_instance.get_channel(cfg.get("nsfw_channel_id", 0))
    
    content_funcs = [get_random_anime_image, get_random_tiktok, get_random_youtube, get_random_pixabay, get_random_nekos_nsfw]
    chosen_func = random.choice(content_funcs)
    content_url, topic = chosen_func()
    
    if content_url:
        if chosen_func == get_random_nekos_nsfw:
            if nsfw_channel:
                embed = create_embed(title="18+ Контент!", description=f"**Тема:** {topic}", image_url=content_url, theme="nekos")
                await nsfw_channel.send(embed=embed)
        else:
            if main_channel:
                if chosen_func == get_random_anime_image:
                    embed = create_embed(title="Время контента!", description=f"**Тема:** {topic}", image_url=content_url, theme="anime")
                    await main_channel.send(embed=embed)
                elif chosen_func == get_random_pixabay:
                    embed = create_embed(title="Красивое фото!", description=f"**Тема:** {topic}", image_url=content_url, theme="pixabay")
                    await main_channel.send(embed=embed)
                elif chosen_func == get_random_tiktok:
                    desc = f"**Тема:** {topic}\n\n[▶ Открыть TikTok]({content_url})\n\n{content_url}"
                    embed = create_embed(title="Свежий TikTok!", description=desc, theme="tiktok")
                    await main_channel.send(embed=embed)
                else:
                    desc = f"**Тема:** {topic}\n\n[▶ Открыть YouTube]({content_url})\n\n{content_url}"
                    embed = create_embed(title="Зацени видео!", description=desc, theme="youtube")
                    await main_channel.send(embed=embed)

@auto_post_loop.before_loop
async def before_auto_post():
    pass

    pass


async def setup(bot):
    class ContentCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.bot.tree.add_command(topics_command)
            self.bot.tree.add_command(send_command)
            
        @commands.Cog.listener()
        async def on_ready(self):
            if not auto_post_loop.is_running():
                cfg = load_config()
                auto_post_loop.change_interval(hours=cfg.get("auto_post_interval_hours", 2))
                auto_post_loop.start(self.bot)

    await bot.add_cog(ContentCog(bot))
