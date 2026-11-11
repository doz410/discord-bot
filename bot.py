
import os
import discord
from discord.ext import commands

# Токен береться із змінної середовища
TOKEN = os.getenv("TOKEN")

# ID каналу "Створити казалку"
CREATE_CHANNEL_ID = 1467171259271090434

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID тимчасового каналу -> ID його власника
temporary_channels = {}


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Бот запущений як {bot.user}")


# -----------------------------
# Модальне вікно зміни назви
# -----------------------------

class RenameModal(discord.ui.Modal):

    def __init__(self, channel):
        super().__init__(title="Зміна назви каналу")

        self.channel = channel

        self.new_name = discord.ui.TextInput(
            label="Нова назва каналу",
            placeholder="Введи нову назву",
            default=channel.name,
            max_length=100
        )

        self.add_item(self.new_name)

    async def on_submit(self, interaction: discord.Interaction):
        await self.channel.edit(name=self.new_name.value)

        await interaction.response.send_message(
            f"Назву змінено на **{self.new_name.value}**",
            ephemeral=True
        )


# -----------------------------
# Модальне вікно зміни ліміту
# -----------------------------

class LimitModal(discord.ui.Modal):

    def __init__(self, channel):
        super().__init__(title="Ліміт учасників")

        self.channel = channel

        self.limit = discord.ui.TextInput(
            label="Максимальна кількість учасників",
            placeholder="0 = без обмежень",
            default=str(channel.user_limit),
            max_length=2
        )

        self.add_item(self.limit)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            limit = int(self.limit.value)

            if limit < 0 or limit > 99:
                raise ValueError

        except ValueError:
            await interaction.response.send_message(
                "Введи число від 0 до 99.",
                ephemeral=True
            )
            return

        await self.channel.edit(user_limit=limit)

        if limit == 0:
            message = "Ліміт учасників вимкнено."
        else:
            message = f"Ліміт встановлено: **{limit}** учасників."

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


# -----------------------------
# Кнопки керування каналом
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

        return True

    @discord.ui.button(
        label="Змінити назву",
        style=discord.ButtonStyle.primary,
        emoji="✏️"
    )
    async def rename_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            RenameModal(self.channel)
        )

    @discord.ui.button(
        label="Змінити ліміт",
        style=discord.ButtonStyle.primary,
        emoji="👥"
    )
    async def limit_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            LimitModal(self.channel)
        )


# -----------------------------
# Команда керування каналом
# -----------------------------

@bot.tree.command(
    name="channel",
    description="Керування власною тимчасовою казалкою"
)
async def channel_control(interaction: discord.Interaction):

    # Перевіряємо, чи користувач у голосовому каналі
    if not interaction.user.voice:
        await interaction.response.send_message(
            "Спочатку зайди у свою казалку.",
            ephemeral=True
        )
        return

    channel = interaction.user.voice.channel

    # Перевіряємо, чи канал тимчасовий
    owner_id = temporary_channels.get(channel.id)

    if owner_id is None:
        await interaction.response.send_message(
            "Цей канал не є тимчасовою казалкою.",
            ephemeral=True
        )
        return

    # Перевіряємо власника
    if owner_id != interaction.user.id:
        await interaction.response.send_message(
            "Ти не власник цієї казалки.",
            ephemeral=True
        )
        return

    # Відкриваємо меню
    await interaction.response.send_message(
        f"**Керування каналом: {channel.name}**",
        view=ChannelControlView(channel, owner_id),
        ephemeral=True
    )


# -----------------------------
# Створення та видалення каналів
# -----------------------------

@bot.event
async def on_voice_state_update(member, before, after):

    # Якщо зайшли у канал створення
    if after.channel and after.channel.id == CREATE_CHANNEL_ID:

        guild = member.guild
        category = after.channel.category

        new_channel = await guild.create_voice_channel(
            f"Казалка {member.display_name}",
            category=category
        )

        # Записуємо власника каналу
        temporary_channels[new_channel.id] = member.id

        # Переміщуємо користувача
        await member.move_to(new_channel)

    # Видалення порожніх тимчасових каналів
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
