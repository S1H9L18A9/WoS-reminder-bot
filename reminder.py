import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import pytz
from dotenv import load_dotenv
from datetime import datetime, timedelta
from channel_id import BOT_CHANNEL_ID

 
class EventBot(commands.Bot):
    def __init__(self):
        self.channel_id = BOT_CHANNEL_ID
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='/', intents=intents)
        # JSON file for events
        self.events_file = 'events.json'
        self.events = self.load_events()
        self.next_event = self.find_next_event()
        print('I am constructed')
        #bot.sync_commands()
        #bot.get_channel(1326788129872543755).send("🤖 Bot is waking up!")

    def load_events(self):
        """Load events from JSON file"""
        if not os.path.exists(self.events_file):
            return []
        with open(self.events_file, 'r') as f:
            return json.load(f)
    def save_events(self):
        """Save events to JSON file"""
        with open(self.events_file, 'w') as f:
            json.dump(self.events, f, indent=2)
    #@bot.event
    #async def on_ready():
    #    await bot.sync_commands()
    #    print(f'We have logged in as {bot.user}')
    #    await bot.get_channel(1326788129872543755).send("🤖 Bot is waking up!")
    def find_next_event(self):
        """Find and return the next upcoming event"""
        if not self.events:
            return None
        now = datetime.now(pytz.UTC)
        upcoming_events = [
            event for event in self.events
            if datetime.fromisoformat(event['event_time']) > now
        ]
        if not upcoming_events:
            return None
        return min(upcoming_events, key=lambda x: datetime.fromisoformat(x['event_time']))

    async def on_ready(self):
        """Event handler that runs when the bot is ready and connected"""
        print(f"Bot connected as {self.user.name} ({self.user.id})")
        
        # Send a message to the bot channel to confirm bot is online
        bot_channel = self.get_channel(BOT_CHANNEL_ID)
        # if bot_channel:
            # await bot_channel.send("✅ Event Bot is now online and ready for commands!")
            # if self.next_event:
            #     await bot_channel.send(f"Next upcoming event: {self.next_event['message']} at {self.next_event['event_time']}")
            # else:
            #     await bot_channel.send("No upcoming events scheduled.")
        # else:
        #     print(f"WARNING: Could not find channel with ID {BOT_CHANNEL_ID}")
   
    async def setup_hook(self):
        # Add commands to the tree
        self.tree.add_command(self.add_event)
        self.tree.add_command(self.delete_event)
        self.tree.add_command(self.whats_next)
        await self.tree.sync()

   

    @app_commands.command(name="addevent")
    @app_commands.checks.has_permissions(manage_events=True)
    async def add_event(self, interaction: discord.Interaction,
                        message: str,
                        event_time: str,
                        is_repeating: bool = False,
                        repeat_after: str = None,
                        channel_ids: str = None,
                        tags: str = None,
                        reminders: str = None):
        """Add a new event"""
        print(locals())
        try:
            # Validate and convert inputs
            event_datetime = datetime.fromisoformat(event_time).replace(tzinfo=pytz.UTC)
            # Convert comma-separated strings to lists
            channel_list = [int(ch.strip()) for ch in channel_ids.split(',')] if channel_ids else []
            tag_list = [int(tag.strip()) for tag in tags.split(',')] if tags else []
            reminder_list = [int(rem.strip()) for rem in reminders.split(',')] if reminders else []
            # Prepare repeat_after if provided
            repeat_dict = eval(repeat_after) if repeat_after and is_repeating else None
            # Create event object
            event = {
                'message': message,
                'event_time': event_datetime.isoformat(),
                'is_repeating': is_repeating,
                'repeat_after': str(repeat_dict) if repeat_dict else None,
                'channel_ids': channel_list,
                'tags': tag_list,
                'reminders': reminder_list

            }
            # Add event and save
            self.events.append(event)
            self.save_events()
            # Update next event
            self.next_event = self.find_next_event()
            await interaction.response.send_message(f"Event added successfully: {message}")
        except Exception as e:
            await interaction.response.send_message(f"Error adding event: {str(e)}", ephemeral=True)

    @app_commands.command(name="deleteevent")
    @app_commands.checks.has_permissions(manage_events=True)
    async def delete_event(self, interaction: discord.Interaction, message: str):
        """Delete an event by its message"""
        for event in self.events:
            if event['message'] == message:
                self.events.remove(event)
                self.save_events()
                # Update next event

                self.next_event = self.find_next_event()
                await interaction.response.send_message(f"Event deleted: {message}")
                return    
        await interaction.response.send_message(f"No event found with message: {message}")

   

    @app_commands.command(name="whatsnext")
    async def whats_next(self, interaction: discord.Interaction):
        """Show the next upcoming event"""
        if self.next_event:
            response = (
                f"Next Event:\n"
                f"Message: {self.next_event['message']}\n"
               f"Time: {self.next_event['event_time']}"
            )
            await interaction.response.send_message(response)
        else:
            await interaction.response.send_message("No upcoming events.")

 

async def run_bot(bot):
    try:
        print("🤖 Bot is waking up!")
        print("To shut down, type 'q' and press Enter\n")
        print(os.getenv('TOKEN'))
        await bot.start(os.getenv('TOKEN'))
        await bot.get_channel(1326788129872543755).send("🤖 Bot is waking up!")

    except Exception as e:
        print(f"An error occurred: {e}")

 

async def main():
    # Initialize bot
    intents = discord.Intents.default()
    intents.message_content = True
    bot = EventBot()
    # Create tasks for bot and input monitoring
    bot_task = asyncio.create_task(run_bot(bot))
    # Input monitoring loop
    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(None, input)
        if user_input.lower() == 'q':
            print("\n🌙 Shutting down bot...")
            # Send goodbye message to a specific channel (replace CHANNEL_ID)
            try:
                # await bot.get_channel(1326788129872543755).send("I am going for a nap...")
                print('done')
                
            except Exception:

                print("Could not send goodbye message")
            # Cancel the bot task
            bot_task.cancel()
            # Close the bot connection
            await bot.close()
            # Break the monitoring loop
            break
    print("Bot has been shut down.")


if __name__ == '__main__':
    load_dotenv()
    asyncio.run(main())