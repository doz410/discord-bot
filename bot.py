import discord
from discord.ext import commands

# ВСТАВ СВІЙ ТОКЕН
TOKEN = "MTQ2NzE1NzY0MTE0NTg3NjY0NQ.Gv65m8.cpyeW5p6j2R0zsFhicoTDltHbUFn8wvpdTv4ik"

# ID голосового каналу "Створити казалку"
CREATE_CHANNEL_ID = 1467171259271090434

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# список тимчасових каналів
temporary_channels = set()


@bot.event
async def on_ready():
    print(f"Бот запущений як {bot.user}")


@bot.event
async def on_voice_state_update(member, before, after):

    # Якщо користувач зайшов у канал створення
    if after.channel and after.channel.id == CREATE_CHANNEL_ID:
        guild = member.guild
        category = after.channel.category

        # створення нового каналу
        new_channel = await guild.create_voice_channel(
            f"Казалка {member.display_name}",
            category=category
        )

        temporary_channels.add(new_channel.id)

        # перенос користувача
        await member.move_to(new_channel)

    # видалення пустих тимчасових каналів
    if before.channel and before.channel.id in temporary_channels:
        if len(before.channel.members) == 0:
            temporary_channels.remove(before.channel.id)
            await before.channel.delete()


bot.run(TOKEN)
