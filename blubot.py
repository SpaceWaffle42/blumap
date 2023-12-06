import os
import csv
import discord
from discord.ext import commands, tasks
from pathlib import Path
import re
import datetime
import configparser
import pathlib
import copy  # Added import for copy module

config = configparser.ConfigParser()
py_path = pathlib.Path(__file__).parent.resolve()

config.read(os.path.join(py_path, "config.ini"))

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

py_path = Path(__file__).parent.resolve()
DIR_DATA = os.path.join(py_path, "data")

# Store previous data and last modification time to check for changes
previous_data = {}
last_modification_time = {}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await scan_csv_and_post.start()

@tasks.loop(seconds=3)
async def scan_csv_and_post():
    data_path = Path(DIR_DATA)

    for file_path in data_path.glob("*_scan.csv"):
        file_name = file_path.stem

        # Read the CSV file
        data = read_csv(file_path)

        # Check if data has changed
        if data != previous_data.get(file_name):
            print(f"Change detected in {file_name}.csv. Updating...")

            # Additional debugging info
            last_mod_time = os.path.getmtime(file_path)
            print(f"Last Modification Time: {last_mod_time}")
            print(f"Previous Modification Time: {last_modification_time.get(file_name)}")

            # Post to channels
            guild_id = int(config["DISCORD SETTINGS"]["GUILD"])  # Replace with your actual guild ID
            guild = discord.utils.get(bot.guilds, id=guild_id)

            # Create a new embed with changes
            await post_to_channels(guild, data, file_name)

            # Update previous_data and last_modification_time
            previous_data[file_name] = copy.deepcopy(data)
            last_modification_time[file_name] = last_mod_time

def read_csv(file_path):
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

async def post_to_channels(guild, data, file_name):
    subnet_category_name = file_name.replace("_scan", "")
    subnet_category_name = re.sub(r'\.\d+$', '.0', subnet_category_name)  # Replace the last octet with .0

    category = discord.utils.get(guild.categories, name=subnet_category_name)
    if category is None:
        category = await guild.create_category_channel(subnet_category_name)

    channel_name = str(file_name).replace('.', '_').replace('_scan', '')  # You can change this as needed
    channel = discord.utils.get(guild.channels, name=channel_name, category=category)

    if channel is None:
        channel = await guild.create_text_channel(channel_name, category=category)
    else:
        await purge_old_messages(channel, limit=2)

    # Check for changes and get the row number(s) of the changed item(s)
    changes = get_changes(data, file_name)

    # If changes are detected, create a new embed with highlighted changes
    if changes:
        embed = create_embed(data, changes)
        await channel.send(embed=embed, content="**Changes Detected in the following item(s):**")
    else:
        embed = create_embed(data)
        await channel.send(embed=embed)

async def purge_old_messages(channel, limit):
    # Fetch the messages in the channel
    messages = []
    async for message in channel.history(limit=None):
        messages.append(message)

    # Check if the number of messages exceeds the limit
    if len(messages) > limit:
        # Sort messages by creation time (oldest first)
        messages.sort(key=lambda x: x.created_at)

        # Calculate the number of messages to delete
        delete_count = len(messages) - limit

        # Delete the oldest messages
        for i in range(delete_count):
            await messages[i].delete()

def create_embed(data, changes=None):
    try:
        opsys = data[0]['os']
    except:
        opsys = [0]
    try:
        opsysacc = data[0]['os accuracy']
    except:
        opsysacc = data[0]
    embed_color = discord.Color.red() if changes else discord.Color.blurple()
    embed = discord.Embed(title=f'{opsys} ({opsysacc})', color=embed_color)

    # Create lists for each field
    port_id_protocol_list = []
    state_list = []
    reason_ttl_list = []

    # Populate the lists with data from each row
    for row in data:
        port_id_protocol_list.append(f"{row.get('portid', 'N/A')} ({row.get('protocol', 'N/A')})")
        state_list.append(row.get("state", "N/A"))
        reason_ttl_list.append(f"{row.get('reason', 'N/A')} ({row.get('reason_ttl','N/A')})")

    # Check if changes are provided and highlight them
    if changes:
        # Keep only the changed items in the lists
        port_id_protocol_list = [port_id_protocol_list[i] for i in changes]
        state_list = [state_list[i] for i in changes]
        reason_ttl_list = [reason_ttl_list[i] for i in changes]

    time_now = datetime.datetime.now().strftime("%Y-%m-%d @%H:%M")
    port_id_protocol_list.pop(0)
    state_list.pop(0)
    reason_ttl_list.pop(0)
    # Join the lists with '\n' and set as field values
    embed.add_field(name="PortID (protocol)", value='\n'.join(port_id_protocol_list), inline=True)
    embed.add_field(name="State", value='\n'.join(state_list), inline=True)
    embed.add_field(name="Reason (TTL)", value='\n'.join(reason_ttl_list), inline=True)
    embed.set_footer(text=f'Updated: {time_now}')
    return embed

def get_changes(data, file_name):
    changes = []
    if file_name in previous_data:
        previous_rows = previous_data[file_name]
        for i, row in enumerate(data):
            if row != previous_rows[i]:
                changes.append(i)
    return changes

bot.run(config["DISCORD SETTINGS"]["BOT TOKEN"])
