import os
import discord
from discord.ext import commands

# Токен береться із змінної середовища
TOKEN = os.getenv("TOKEN")

# ID каналу "Створити казалку"
CREATE_CHANNEL_ID = 1467171259271090434  # <-- заміни на свій

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

temporary_channels = set()


@bot.event
async def on_ready():
    print(f"Бот запущений як {bot.user}")


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

        temporary_channels.add(new_channel.id)

        await member.move_to(new_channel)

    # Видалення порожніх тимчасових каналів
    if before.channel and before.channel.id in temporary_channels:
        if len(before.channel.members) == 0:
            temporary_channels.remove(before.channel.id)
            await before.channel.delete()


if not TOKEN:
    print("ПОМИЛКА: TOKEN не встановлений!")
else:
    bot.run(TOKEN)
