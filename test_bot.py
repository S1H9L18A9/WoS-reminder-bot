import os
import discord
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("👋 Bot is now online!")
    else:
        print("❌ Could not find the channel. Check your CHANNEL_ID.")

client.run(TOKEN)
