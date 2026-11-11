
import os
import discord
from discord.ext import commands

TOKEN = os.getenv("TOKEN")

# ID каналу "Створити казалку"
CREATE_CHANNEL_ID = 1467171259271090434

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID каналу -> ID власника
temporary_channels = {}


# -----------------------------
# Допоміжні функції
# -----------------------------

async def require_owned_channel(interaction):
    voice = getattr(interaction.user, "voice", None)

    if not voice or not voice.channel:
        await interaction.response.send_message(
            "Зайди у свою тимчасову казалку.",
            ephemeral=True
        )
        return None

    channel = voice.channel

    if temporary_channels.get(channel.id) != interaction.user.id:
        await interaction.response.send_message(
            "Ти не власник цієї казалки.",
            ephemeral=True
        )
        return None

    return channel


# -----------------------------
# Зміна назви
# -----------------------------

class RenameModal(discord.ui.Modal, title="Зміна назви каналу"):

    new_name = discord.ui.TextInput(
        label="Нова назва каналу",
        placeholder="Введи нову назву",
        max_length=100
    )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.new_name.default = channel.name

    async def on_submit(self, interaction):
        if temporary_channels.get(self.channel.id) != interaction.user.id:
            await interaction.response.send_message(
                "Ти більше не власник цього каналу.",
                ephemeral=True
            )
            return

        name = self.new_name.value.strip()

        if not name:
            await interaction.response.send_message(
                "Назва не може бути порожньою.",
                ephemeral=True
            )
            return

        await self.channel.edit(name=name)

        await interaction.response.send_message(
            f"Назву змінено на **{name}**.",
            ephemeral=True
        )


# -----------------------------
# Зміна ліміту
# -----------------------------

class LimitModal(discord.ui.Modal, title="Ліміт учасників"):

    limit_input = discord.ui.TextInput(
        label="Максимальна кількість учасників",
        placeholder="0 = без обмежень",
        max_length=2
    )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.limit_input.default = str(channel.user_limit)

    async def on_submit(self, interaction):
        if temporary_channels.get(self.channel.id) != interaction.user.id:
            await interaction.response.send_message(
                "Ти більше не власник цього каналу.",
                ephemeral=True
            )
            return

        try:
            limit = int(self.limit_input.value)

            if not 0 <= limit <= 99:
                raise ValueError

        except ValueError:
            await interaction.response.send_message(
                "Введи число від 0 до 99. 0 = без обмежень.",
                ephemeral=True
            )
            return

        await self.channel.edit(user_limit=limit)

        message = (
            "Ліміт учасників вимкнено."
            if limit == 0
            else f"Ліміт встановлено: **{limit}** учасників."
        )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


# -----------------------------
# Меню керування /channel
# -----------------------------

class ChannelControlView(discord.ui.View):

    def __init__(self, channel, owner_id):
        super().__init__(timeout=180)
        self.channel = channel
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Це меню доступне лише власнику каналу.",
                ephemeral=True
            )
            return False

        if temporary_channels.get(self.channel.id) != self.owner_id:
            await interaction.response.send_message(
                "Цей канал більше не належить тобі.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Змінити назву",
        style=discord.ButtonStyle.primary,
        emoji="✏️"
    )
    async def rename_button(self, interaction, button):
        await interaction.response.send_modal(
            RenameModal(self.channel)
        )

    @discord.ui.button(
        label="Змінити ліміт",
        style=discord.ButtonStyle.primary,
        emoji="👥"
    )
    async def limit_button(self, interaction, button):
        await interaction.response.send_modal(
            LimitModal(self.channel)
        )


# -----------------------------
# /channel
# -----------------------------

@bot.tree.command(
    name="channel",
    description="Керування власною тимчасовою казалкою"
)
async def channel_control(interaction):
    channel = await require_owned_channel(interaction)

    if channel is None:
        return

    await interaction.response.send_message(
        f"**Керування каналом: {channel.name}**",
        view=ChannelControlView(channel, interaction.user.id),
        ephemeral=True
    )


# -----------------------------
# /rename
# -----------------------------

@bot.tree.command(
    name="rename",
    description="Змінити назву власної казалки"
)
async def rename_command(interaction):
    channel = await require_owned_channel(interaction)

    if channel is None:
        return

    await interaction.response.send_modal(
        RenameModal(channel)
    )


# -----------------------------
# /limit
# -----------------------------

@bot.tree.command(
    name="limit",
    description="Змінити ліміт учасників власної казалки"
)
async def limit_command(interaction):
    channel = await require_owned_channel(interaction)

    if channel is None:
        return

    await interaction.response.send_modal(
        LimitModal(channel)
    )


# -----------------------------
# /close
# -----------------------------

@bot.tree.command(
    name="close",
    description="Видалити власну тимчасову казалку"
)
async def close_command(interaction):
    channel = await require_owned_channel(interaction)

    if channel is None:
        return

    temporary_channels.pop(channel.id, None)
    await channel.delete()

    await interaction.response.send_message(
        "Твою казалку видалено.",
        ephemeral=True
    )


# -----------------------------
# /transfer
# -----------------------------

@bot.tree.command(
    name="transfer",
    description="Передати власність на казалку іншому учаснику"
)
async def transfer_command(interaction, member: discord.Member):
    channel = await require_owned_channel(interaction)

    if channel is None:
        return

    if member.bot:
        await interaction.response.send_message(
            "Не можна передати власність боту.",
            ephemeral=True
        )
        return

    if member.id == interaction.user.id:
        await interaction.response.send_message(
            "Ти вже є власником цього каналу.",
            ephemeral=True
        )
        return

    temporary_channels[channel.id] = member.id

    await interaction.response.send_message(
        f"Власником каналу **{channel.name}** тепер є {member.mention}.",
        ephemeral=True
    )


# -----------------------------
# /help
# -----------------------------

@bot.tree.command(
    name="help",
    description="Список команд PODBOT"
)
async def help_command(interaction):
    embed = discord.Embed(
        title="PODBOT — Команди",
        description="Керування тимчасовими голосовими каналами.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="/channel",
        value="Меню керування казалкою.",
        inline=False
    )
    embed.add_field(
        name="/rename",
        value="Змінити назву казалки.",
        inline=False
    )
    embed.add_field(
        name="/limit",
        value="Змінити ліміт учасників.",
        inline=False
    )
    embed.add_field(
        name="/close",
        value="Видалити власну казалку.",
        inline=False
    )
    embed.add_field(
        name="/transfer @учасник",
        value="Передати власність на казалку.",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# -----------------------------
# Синхронізація команд
# -----------------------------

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Синхронізовано команд: {len(synced)}")
    except Exception as error:
        print(f"Помилка синхронізації команд: {error}")

    print(f"Бот запущений як {bot.user}")


# -----------------------------
# Створення та видалення каналів
# -----------------------------

@bot.event
async def on_voice_state_update(member, before, after):

    # Створення казалки
    if after.channel and after.channel.id == CREATE_CHANNEL_ID:
        guild = member.guild
        category = after.channel.category

        new_channel = await guild.create_voice_channel(
            f"Казалка {member.display_name}",
            category=category
        )

        temporary_channels[new_channel.id] = member.id

        await member.move_to(new_channel)

    # Видалення порожніх казалок
    if before.channel and before.channel.id in temporary_channels:
        if len(before.channel.members) == 0:
            temporary_channels.pop(before.channel.id, None)
            await before.channel.delete()


# -----------------------------
# Запуск бота
# -----------------------------

if not TOKEN:
    print("ПОМИЛКА: TOKEN не встановлений!")
else:
    bot.run(TOKEN)
