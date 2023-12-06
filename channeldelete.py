import discord
from discord.ext import commands
import pathlib
import configparser
import os

config = configparser.ConfigParser()
py_path = pathlib.Path(__file__).parent.resolve()
config.read(os.path.join(py_path, "config.ini"))


intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

target_guild_id = int(config["DISCORD SETTINGS"]["GUILD"])  # Replace with your actual guild ID

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    guild = bot.get_guild(target_guild_id)
    if guild:
        print(f'Connected to guild: {guild.name}')
        await delete_channels(guild)
    else:
        print(f'Guild with ID {target_guild_id} not found.')

async def delete_channels(guild):
    # Iterate through all channels in the guild
    for channel in guild.channels:
        # Check if the channel is not the "general" channel
        if channel.name != 'general':
            try:
                # Attempt to delete the channel
                await channel.delete()
                print(f'Deleted channel: {channel.name}')
            except Exception as e:
                print(f'Error deleting channel {channel.name}: {e}')

bot.run(config["DISCORD SETTINGS"]["BOT TOKEN"])
