import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
from datetime import datetime, timedelta,timezone
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('TOKEN')
# GUILD_ID = YOUR_GUILD_ID_HERE  # Replace with your actual guild ID
EVENT_FILE = 'events.json'
ALLOWED_ROLES = ["MOD", "leadership"]

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # Required for role checks
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load or initialize event list
if os.path.exists(EVENT_FILE):
    with open(EVENT_FILE, 'r') as f:
        events = json.load(f)
else:
    events = []

next_event_task = None

# Helper to save events to file
def save_events():
    with open(EVENT_FILE, 'w') as f:
        json.dump(events, f, indent=4)

# Helper to get next event
def get_next_event(limit = 1):
    global events
    #print('In get next event')
    now = datetime.utcnow()
    upcoming = sorted(events, key=lambda e: e['time'])
    next_events = []
    for event in upcoming:
        event_time = datetime.strptime(event['time'], "%Y-%m-%d %H:%M")
        if (event_time > now) and (len(next_events) >= limit):
            next_events.append(event)
        else:
            #print(event)
            #print('Now removing')
            events = [i for i in events if i != event]
            save_events()
    return next_events
    #return None

# Helper to schedule the next reminder
async def schedule_next_event():
    global next_event_task

    if next_event_task and not next_event_task.done():
        next_event_task.cancel()

    next_event = get_next_event()
    if not next_event:
        return
    else:
        next_event = next_event[0]

    event_time = datetime.strptime(next_event['time'], "%Y-%m-%d %H:%M")
    reminder_offsets = next_event.get("reminders", [0])
    reminder_offsets = sorted(set(int(r) for r in reminder_offsets if isinstance(r, int) or r.isdigit()), reverse=True)

    async def send_reminders():
        for offset in reminder_offsets:
            send_time = event_time - timedelta(minutes=offset)
            delay = (send_time - datetime.utcnow()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
            channel_id = next_event.get("channel_id")
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(f"Reminder ({offset} min before): {next_event['message']}")

        # Final reminder at event time
        delay = (event_time - datetime.utcnow()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        channel_id = next_event.get("channel_id")
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(f"Event starting now: {next_event['message']}")

        # Handle repeat logic
        if 'repeat_hours' in next_event:
            repeat = int(next_event['repeat_hours'])
            next_time = event_time + timedelta(hours=repeat)
            next_event['time'] = next_time.strftime("%Y-%m-%d %H:%M")
        else:
            events.remove(next_event)

        save_events()
        await schedule_next_event()

    next_event_task = asyncio.create_task(send_reminders())

# Permission check
async def is_allowed(interaction: discord.Interaction) -> bool:
    if not interaction.user.guild_permissions.administrator:
        member = interaction.user
        roles = [r.name for r in member.roles]
        return any(role in ALLOWED_ROLES for role in roles)
    return True

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await bot.tree.sync()
    await schedule_next_event()
    #await bot.get_channel(1326788129872543755).send("🤖 Bot is waking up!")

@bot.tree.command(name="addevent", description="Add a reminder event")
@app_commands.describe(message="Reminder message", time="Time in HH:MM UTC",tags="(Optional) Roles to tag" ,repeat_hours="(Optional) Hours after which to repeat", reminders="(Optional)Minutes before to remind, comma separated (e.g. 15,10,5)")
async def addevent(interaction: discord.Interaction, message: str, time: str,tags: str, repeat_hours: int = None, reminders: str = "0"):
    if not await is_allowed(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    now = datetime.utcnow()
    event_time = datetime.strptime(time, "%H:%M")
    event_datetime = now.replace(hour=event_time.hour, minute=event_time.minute, second=0, microsecond=0)
    if event_datetime < now:
        event_datetime += timedelta(days=1)

    reminder_list = [int(x.strip()) for x in reminders.split(",") if x.strip().isdigit()]

    event = {
        "message": message,
        "time": event_datetime.strftime("%Y-%m-%d %H:%M"),
        "channel_id": interaction.channel_id,
        "reminders": reminder_list
    }
    if repeat_hours:
        event["repeat_hours"] = repeat_hours
    
    events.append(event)
    save_events()
    await schedule_next_event()

    await interaction.response.send_message(f"Event added: {message} at {event_datetime.strftime('%H:%M UTC')} with reminders at {reminder_list} minutes before.")

@bot.tree.command(name="deleteevent", description="Delete a reminder event")
@app_commands.describe(message="Message of the event to delete")
async def deleteevent(interaction: discord.Interaction, message: str):
    if not await is_allowed(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    global events
    before = len(events)
    events = [e for e in events if e["message"] != message]
    after = len(events)
    save_events()
    await schedule_next_event()
    if before == after:
        await interaction.response.send_message("No matching event found.")
    else:
        await interaction.response.send_message(f"Event '{message}' deleted.")

@bot.tree.command(name="whatsnext", description="Shows the next upcoming event")
async def whatsnext(interaction: discord.Interaction):
    next_event = get_next_event()
    if not next_event:
        await interaction.response.send_message("No upcoming events.")
        return
    date_thing = datetime.strptime(next_event['time'], "%Y-%m-%d %H:%M")
    date_thing = date_thing.replace(tzinfo=timezone.utc)
    await interaction.response.send_message(
        f"{next_event['message']} <t:{int(date_thing.timestamp())}:R>")

bot.run(TOKEN)
