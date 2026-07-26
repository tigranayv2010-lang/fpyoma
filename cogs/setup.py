import discord
from discord.ext import commands
from utils.ui import create_embed
from utils.config import load_config, save_config, check_user_allowed

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
                cog.auto_post.change_interval(minutes=val)
                
            await interaction.response.send_message(embed=create_embed(f"✅ Интервал установлен на {val} минут.", theme="success"), ephemeral=True)
        except ValueError:
            await interaction.response.send_message(embed=create_embed("❌ Введите корректное положительное число.", theme="error"), ephemeral=True)

class SetupRolesModal(discord.ui.Modal, title='Роли управления'):
    roles_input = discord.ui.TextInput(label='ID ролей (через запятую)', required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        role_ids = []
        for r in self.roles_input.value.split(','):
            r = r.strip()
            if r.isdigit():
                role_ids.append(int(r))
        
        if not role_ids:
            return await interaction.response.send_message(
                embed=create_embed("❌ Введите хотя бы один корректный ID роли.", theme="error"), ephemeral=True
            )
        
        cfg = load_config()
        cfg["allowed_role_ids"] = role_ids
        save_config(cfg)
        
        names = []
        for rid in role_ids:
            role = interaction.guild.get_role(rid)
            names.append(f"{role.name} ({rid})" if role else str(rid))
        
        await interaction.response.send_message(
            embed=create_embed(f"✅ Роли обновлены:\n{chr(10).join(names)}", theme="success"), ephemeral=True
        )

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
        modal.roles_input.default = ", ".join(str(i) for i in load_config().get("allowed_role_ids", []))
        await interaction.response.send_modal(modal)

@discord.app_commands.command(name="setup", description="Настройка бота")
async def setup_command(interaction: discord.Interaction):
    if not check_user_allowed(interaction.user, interaction.guild.owner_id):
        return await interaction.response.send_message(embed=create_embed("Нет доступа!", theme="error"), ephemeral=True)
        
    cfg = load_config()
    main_id = cfg.get('main_channel_id')
    nsfw_id = cfg.get('nsfw_channel_id')
    main_str = f"<#{main_id}>" if main_id else "Не установлен"
    nsfw_str = f"<#{nsfw_id}>" if nsfw_id else "Не установлен"
    desc = (
        f"📺 **Основной:** {main_str}\n"
        f"<:18:1530644654758826155> **NSFW:** {nsfw_str}\n"
        f"⏱️ **Интервал:** {cfg.get('auto_post_interval_minutes', 120)} мин.\n"
        f"👥 **Роли:** {' '.join(f'<@&{rid}>' for rid in cfg.get('allowed_role_ids', [])) or 'Не установлены'}\n\n"
        "Выберите настройку:"
    )
    await interaction.response.send_message(embed=create_embed(desc, "Настройки", "settings"), view=SetupView(), ephemeral=True)

async def setup(bot):
    class SetupCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.bot.tree.add_command(setup_command)
    await bot.add_cog(SetupCog(bot))
