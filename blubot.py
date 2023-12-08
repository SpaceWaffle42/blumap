import os
import csv
import discord
from discord.ext import commands, tasks
from pathlib import Path
import re
import datetime
import configparser
import pathlib
import copy
import aioping

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

# Store previous data, last modification time, and last IP status to check for changes
previous_data = {}
last_modification_time = {}
last_ip_status = {}

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
            print(f"\nChange detected in {file_name}.csv. Updating...")

            # Additional debugging info
            last_mod_time = os.path.getmtime(file_path)

            # Post to channels
            guild_id = int(config["DISCORD SETTINGS"]["GUILD"])  # Replace with your actual guild ID
            guild = discord.utils.get(bot.guilds, id=guild_id)

            # Check if dedicated channel for port changes is configured
            if config["DISCORD SETTINGS"]["PORT CHANGES CHANNEL"] == 'True':
                # Check for changes and get the row number(s) of the changed item(s)
                changes = get_changes(data, file_name)

                # If changes are detected, create a new embed with highlighted changes
                if changes:
                    port_changes_channel = discord.utils.get(guild.channels, name='port-changes')
                    if port_changes_channel is None:
                        port_changes_channel = await guild.create_text_channel('port-changes')
                    channel = port_changes_channel

                    # Get the original channel where the CSV was initially posted
                    original_channel_name = str(file_name).replace('.', '_').replace('_scan', '')
                    original_channel = discord.utils.get(guild.channels, name=original_channel_name)
                    original_channel_mention = f"<#{original_channel.id}>"
                else:
                    # Use the regular channel creation logic
                    subnet_name = file_name.replace("_scan", "")
                    subnet_category_name = re.sub(r'\.\d+$', '.0', subnet_name)  # Replace the last octet with .0
                    category = discord.utils.get(guild.categories, name=subnet_category_name)
                    if category is None:
                        category = await guild.create_category_channel(subnet_category_name)

                    channel_name = str(file_name).replace('.', '_').replace('_scan', '')
                    channel = discord.utils.get(guild.channels, name=channel_name, category=category)

                    if channel is None:
                        channel = await guild.create_text_channel(channel_name, category=category)
                    else:
                        await purge_old_messages(channel, limit=100)

                    # Get the channel mention ID
                    original_channel_mention = f"<#{channel.id}>"

                # If changes are detected, create a new embed with highlighted changes
                if changes:
                    embed = create_embed(data, changes)
                    time_now = datetime.datetime.now().strftime("%Y-%m-%d @%H:%M")
                    await channel.send(embed=embed, content=f"**@everyone Changes Detected in {original_channel_mention} on {time_now} in the following item(s):**")
                else:
                    embed = create_embed(data)
                    await channel.send(embed=embed)

            # Update previous_data, last_modification_time, and last IP status
            previous_data[file_name] = copy.deepcopy(data)
            last_modification_time[file_name] = last_mod_time

            # Asynchronously check IP availability every 3 seconds
            await check_ip_availability(guild, data, file_name)

def read_csv(file_path):
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

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
    if port_id_protocol_list and port_id_protocol_list[0] == " ()" or port_id_protocol_list[0] =='':
            port_id_protocol_list.pop(0)
    if state_list and state_list[0] == " ()" or state_list[0] =='':
        state_list.pop(0)
    if reason_ttl_list and reason_ttl_list[0] == " ()" or reason_ttl_list[0] =='':
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

async def check_ip_availability(guild, data, file_name):
    time_now = datetime.datetime.now().strftime("%Y-%m-%d @%H:%M")
    subnet_name = file_name.replace("_scan", "")
    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', subnet_name)
    
    channel = None
    if ip_match:
        ip_address = ip_match.group()
        try:
            await aioping.ping(ip_address)
            current_ip_status = "up"
            disc_colour = discord.Color.green()
        except TimeoutError:
            current_ip_status = "down"
            disc_colour = discord.Color.gold()

        # Check if the IP status has changed
        if current_ip_status != last_ip_status.get(file_name):
            last_ip_status[file_name] = current_ip_status

            # IP status has changed, send a message
            channel_name = str(file_name).replace('.', '_').replace('_scan', '')
            channel = discord.utils.get(guild.channels, name=channel_name)
            ip_states_channel_mention = f"<#{channel.id}>" if channel is not None else ''
            if config["DISCORD SETTINGS"]["IP STATE CHANNEL"] == 'False':
                # Use the original channel's name for the IP States channel
                channel_name = str(file_name).replace('.', '_').replace('_scan', '')


                # Create the IP States channel if it doesn't exist
                if channel is None:
                    try:
                        channel = await guild.create_text_channel(channel_name)
                        print(f"Created IP States Channel: {channel_name}")
                    except discord.Forbidden:
                        print("Bot lacks 'manage_channels' permission to create channels.")
                        # Handle this situation according to your needs

            else:
                # Use the predefined "IP-States" channel
                channel = discord.utils.get(guild.channels, name='ip-states')
                # ip_states_channel_mention = '<#IP-States>'  # Mention the "IP-States" channel
                if channel is None:
                                    try:
                                        channel = await guild.create_text_channel('ip-states')
                                    except discord.Forbidden:
                                        print("Bot lacks 'manage_channels' permission to create channels.")
                                        # Handle this situation according to your needs
        if channel is not None:
            # Send the IP status with a mention of the original channel
            await channel.send(embed=discord.Embed(
                title=f"{ip_address} is {current_ip_status}!\nas of {time_now}",
                description=f"Original Channel: {ip_states_channel_mention}",
                color=disc_colour
            ))

bot.run(config["DISCORD SETTINGS"]["BOT TOKEN"])
