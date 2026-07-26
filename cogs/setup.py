import discord
from discord.ext import commands
from utils.ui import create_embed
from utils.config import load_config, save_config

class SetupChannelModal(discord.ui.Modal, title='Настройка каналов'):
    main_ch = discord.ui.TextInput(label='ID основного канала', required=False)
    nsfw_ch = discord.ui.TextInput(label='ID NSFW канала', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = load_config()
        if self.main_ch.value.isdigit(): cfg["main_channel_id"] = int(self.main_ch.value)
        if self.nsfw_ch.value.isdigit(): cfg["nsfw_channel_id"] = int(self.nsfw_ch.value)
        save_config(cfg)
        await interaction.response.send_message(embed=create_embed("✅ Каналы успешно обновлены!", theme="success"), ephemeral=True)

class SetupIntervalModal(discord.ui.Modal, title='Интервал авто-постинга'):
    interval = discord.ui.TextInput(label='Минуты', required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.interval.value)
            if val <= 0: raise ValueError
            
            cfg = load_config()
            cfg["auto_post_interval_minutes"] = val
            save_config(cfg)
            
            if cog := interaction.client.get_cog("ContentCog"):
                from cogs.content import auto_post_loop
                auto_post_loop.change_interval(minutes=val)
                
            await interaction.response.send_message(embed=create_embed(f"✅ Интервал установлен на {val} минут.", theme="success"), ephemeral=True)
        except ValueError:
            await interaction.response.send_message(embed=create_embed("❌ Введите корректное положительное число.", theme="error"), ephemeral=True)

class SetupRolesModal(discord.ui.Modal, title='Роли управления'):
    roles_input = discord.ui.TextInput(label='Названия (через запятую)', required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        roles = [r.strip() for r in self.roles_input.value.split(',')]
        
        cfg = load_config()
        cfg["allowed_roles"] = [r for r in roles if r] or ["Content"]
        save_config(cfg)
        
        await interaction.response.send_message(embed=create_embed(f"✅ Роли обновлены: `{', '.join(cfg['allowed_roles'])}`", theme="success"), ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self): super().__init__(timeout=120)

    @discord.ui.button(label="Каналы", style=discord.ButtonStyle.primary, emoji="📺")
    async def btn_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetupChannelModal()
        cfg = load_config()
        modal.main_ch.default, modal.nsfw_ch.default = str(cfg.get("main_channel_id", "")), str(cfg.get("nsfw_channel_id", ""))
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Интервал", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def btn_interval(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetupIntervalModal()
        modal.interval.default = str(load_config().get("auto_post_interval_minutes", 120))
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Роли", style=discord.ButtonStyle.success, emoji="👥")
    async def btn_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetupRolesModal()
        modal.roles_input.default = ", ".join(load_config().get("allowed_roles", ["Content"]))
        await interaction.response.send_modal(modal)

@discord.app_commands.command(name="setup", description="Настройка бота")
async def setup_command(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message(embed=create_embed("Только владелец!", theme="error"), ephemeral=True)
        
    cfg = load_config()
    desc = (
        f"📺 **Основной:** <#{cfg.get('main_channel_id')}>" + ("" if cfg.get('main_channel_id') else " Нет") + "\n"
        f"<:18:1530644654758826155> **NSFW:** <#{cfg.get('nsfw_channel_id')}>" + ("" if cfg.get('nsfw_channel_id') else " Нет") + "\n"
        f"⏱️ **Интервал:** {cfg.get('auto_post_interval_minutes', 120)} мин.\n"
        f"👥 **Роли:** `{', '.join(cfg.get('allowed_roles', ['Content']))}`\n\n"
        "Выберите настройку:"
    )
    await interaction.response.send_message(embed=create_embed(desc, "Настройки", "settings"), view=SetupView(), ephemeral=True)

async def setup(bot):
    class SetupCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.bot.tree.add_command(setup_command)
    await bot.add_cog(SetupCog(bot))
