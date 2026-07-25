import discord
from discord.ext import commands
from utils.ui import create_embed
from utils.config import load_config, save_config, check_user_allowed, get_roles_str
import asyncio

class SetupChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, channel_type: str):
        super().__init__(placeholder=f"Выбери {channel_type} канал", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        self.target_type = channel_type

    async def callback(self, interaction: discord.Interaction):
        cfg = load_config()
        if self.target_type == "SFW":
            cfg["main_channel_id"] = self.values[0].id
        else:
            cfg["nsfw_channel_id"] = self.values[0].id
        save_config(cfg)
        embed = create_embed(description=f"✅ {self.target_type} канал успешно установлен на <#{self.values[0].id}>!", theme="success")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SetupChannelView(discord.ui.View):
    def __init__(self, channel_type: str):
        super().__init__(timeout=180)
        self.add_item(SetupChannelSelect(channel_type))

class SetupIntervalModal(discord.ui.Modal, title='Интервал авто-отправки'):
    interval = discord.ui.TextInput(
        label='Часы (например, 2 или 5)',
        style=discord.TextStyle.short,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = float(self.interval.value.replace(',', '.'))
            if val <= 0: raise ValueError
            cfg = load_config()
            cfg["auto_post_interval_hours"] = val
            save_config(cfg)
            auto_post_loop.change_interval(hours=val)
            embed = create_embed(description=f"✅ Интервал авто-поста установлен на {val} часов.", theme="success")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            embed = create_embed(description="❌ Пожалуйста, введите корректное положительное число.", theme="error")
            await interaction.response.send_message(embed=embed, ephemeral=True)

class SetupRolesModal(discord.ui.Modal, title='Роли управления (через запятую)'):
    roles_input = discord.ui.TextInput(
        label='Названия ролей',
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        roles_list = [r.strip() for r in self.roles_input.value.split(',') if r.strip()]
        if not roles_list: roles_list = ["Content"]
        cfg = load_config()
        cfg["allowed_roles"] = roles_list
        save_config(cfg)
        embed = create_embed(description=f"✅ Роли управления обновлены: `{', '.join(roles_list)}`", theme="success")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Основной канал", style=discord.ButtonStyle.primary, emoji="📺")
    async def btn_main_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Выбери канал для обычного контента:", view=SetupChannelView("SFW"), ephemeral=True)

    @discord.ui.button(label="NSFW канал", style=discord.ButtonStyle.danger, emoji="🔞")
    async def btn_nsfw_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Выбери канал для 18+ контента (Nekos):", view=SetupChannelView("NSFW"), ephemeral=True)

    @discord.ui.button(label="Интервал рассылки", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def btn_interval(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetupIntervalModal())
        
    @discord.ui.button(label="Роли", style=discord.ButtonStyle.success, emoji="👥")
    async def btn_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetupRolesModal()
        modal.roles_input.default = ", ".join(load_config().get("allowed_roles", ["Content"]))
        await interaction.response.send_modal(modal)

@discord.app_commands.command(name="setup", description="Настройка каналов, интервалов и ролей")
async def setup_command(interaction: discord.Interaction):
    if not check_user_allowed(interaction.user, interaction.guild.owner_id):
        embed = create_embed(description=f"У вас нет прав!\nНужны роли: `{get_roles_str()}`", theme="error")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    cfg = load_config()
    m_ch = f"<#{cfg['main_channel_id']}>" if cfg.get('main_channel_id') else "Не установлен"
    n_ch = f"<#{cfg['nsfw_channel_id']}>" if cfg.get('nsfw_channel_id') else "Не установлен"
    
    desc = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 **Основной канал:** {m_ch}\n"
        f"🔞 **NSFW канал:** {n_ch}\n"
        f"⏱️ **Интервал:** {cfg.get('auto_post_interval_hours', 2)} ч.\n"
        f"👥 **Роли:** `{', '.join(cfg.get('allowed_roles', ['Content']))}`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Используйте кнопки ниже для настройки:"
    )
    embed = create_embed(title="Настройки бота", description=desc, theme="settings")
    await interaction.response.send_message(embed=embed, view=SetupView(), ephemeral=True)



async def setup(bot):
    # Register views
    class SetupCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.bot.tree.add_command(setup_command)
    await bot.add_cog(SetupCog(bot))
