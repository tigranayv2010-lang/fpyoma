import discord
from discord.ext import commands
from utils.ui import create_embed
from utils.config import load_config, save_config, get_roles_str

class SetupChannelModal(discord.ui.Modal, title='Настройка каналов (укажите ID)'):
    main_ch = discord.ui.TextInput(label='ID основного канала', style=discord.TextStyle.short, required=False)
    nsfw_ch = discord.ui.TextInput(label='ID NSFW канала', style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = load_config()
        if self.main_ch.value.isdigit():
            cfg["main_channel_id"] = int(self.main_ch.value)
        if self.nsfw_ch.value.isdigit():
            cfg["nsfw_channel_id"] = int(self.nsfw_ch.value)
            
        save_config(cfg)
        embed = create_embed(description="✅ Каналы успешно обновлены!", theme="success")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SetupIntervalModal(discord.ui.Modal, title='Интервал авто-постинга'):
    interval = discord.ui.TextInput(
        label='Часы (например: 2)',
        style=discord.TextStyle.short,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.interval.value)
            if val <= 0: raise ValueError
            
            cfg = load_config()
            cfg["auto_post_interval_hours"] = val
            save_config(cfg)
            
            # Update running loop if possible
            cog = interaction.client.get_cog("ContentCog")
            if cog:
                from cogs.content import auto_post_loop
                auto_post_loop.change_interval(hours=val)
                
            embed = create_embed(description=f"✅ Интервал авто-поста установлен на {val} часов.", theme="success")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message(embed=create_embed(description="❌ Пожалуйста, введите корректное положительное число.", theme="error"), ephemeral=True)

class SetupRolesModal(discord.ui.Modal, title='Роли управления (через запятую)'):
    roles_input = discord.ui.TextInput(
        label='Названия ролей',
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        roles_list = [r.strip() for r in self.roles_input.value.split(',') if r.strip()]
        if not roles_list: 
            roles_list = ["Content"]
            
        cfg = load_config()
        cfg["allowed_roles"] = roles_list
        save_config(cfg)
        
        embed = create_embed(description=f"✅ Роли обновлены: `{', '.join(roles_list)}`", theme="success")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Каналы", style=discord.ButtonStyle.primary, emoji="📺")
    async def btn_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetupChannelModal()
        cfg = load_config()
        modal.main_ch.default = str(cfg.get("main_channel_id", ""))
        modal.nsfw_ch.default = str(cfg.get("nsfw_channel_id", ""))
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Интервал", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def btn_interval(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetupIntervalModal()
        modal.interval.default = str(load_config().get("auto_post_interval_hours", 2))
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Роли", style=discord.ButtonStyle.success, emoji="👥")
    async def btn_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetupRolesModal()
        modal.roles_input.default = ", ".join(load_config().get("allowed_roles", ["Content"]))
        await interaction.response.send_modal(modal)

@discord.app_commands.command(name="setup", description="Настройка каналов, интервалов и ролей")
async def setup_command(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        embed = create_embed(description="Эту команду может использовать только владелец сервера!", theme="error")
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
    class SetupCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.bot.tree.add_command(setup_command)
    await bot.add_cog(SetupCog(bot))
