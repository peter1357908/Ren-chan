import asyncio
import datetime
import discord
import logging
import zoneinfo
from discord.ext import commands, tasks
from typing import *

from global_stuff import assert_getenv

GUILD_ID: int                    = int(assert_getenv("guild_id"))

SATURDAY_EVENT_NAME: str         = "Saturday Afternoon Riichi"
STARTING_SATURDAY: datetime.date = datetime.date(year=2025, month=7, day=12)
SATURDAY_EVENT_FREQUENCY: int    = 28  # unit: days

def get_next_Saturday_event_date() -> datetime.date:
    today = datetime.date.today()
    if today < STARTING_SATURDAY:
        return STARTING_SATURDAY
    
    days_since_start = (today - STARTING_SATURDAY).days
    days_since_last_event = days_since_start % SATURDAY_EVENT_FREQUENCY

    return today + datetime.timedelta(days=SATURDAY_EVENT_FREQUENCY - days_since_last_event)
    

class EventPoster(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timezone = zoneinfo.ZoneInfo("America/New_York")
        self.guild: discord.Guild = None # bot.get_guild(GUILD_ID) doesn't work; needs to be fetched via API

    async def post_saturday_event(self):
        next_event_date = get_next_Saturday_event_date()

        one_pm = datetime.time(hour=13)
        six_pm = datetime.time(hour=18)
        await self.guild.create_scheduled_event(
            name = SATURDAY_EVENT_NAME,
            description = "This is our 4-weekly Saturday meetup!",
            start_time = datetime.datetime.combine(date=next_event_date, time=one_pm, tzinfo=self.timezone),
            end_time = datetime.datetime.combine(date=next_event_date, time=six_pm, tzinfo=self.timezone),
            entity_type = discord.EntityType.external,
            privacy_level = discord.PrivacyLevel.guild_only,
            location = "Element Eatery (5350 Medpace Way, Cincinnati, OH 45227)")

    @tasks.loop(hours=24, reconnect=True)
    async def try_post_events(self):
        logging.info("Checking if Saturday event already exists...")
        
        curr_events = await self.guild.fetch_scheduled_events()
        saturday_event_exists = False
        for event in curr_events:
            if event.name == SATURDAY_EVENT_NAME:
                saturday_event_exists = True
                break

        if not saturday_event_exists:
            logging.info("No existing Saturday event. Posting saturday event!")
            await self.post_saturday_event()

    async def async_setup(self):
        self.guild = await self.bot.fetch_guild(GUILD_ID)
        self.try_post_events.start()

    # ensure bot is ready before try_post_events is called
    @try_post_events.before_loop
    async def try_post_events_ready(self):
        await self.bot.wait_until_ready()

    @try_post_events.error
    async def try_post_events_error(self, error):
        logging.error(f"Error in posting events: {error}")

async def setup(bot: commands.Bot):
    logging.info(f"Loading cog `{EventPoster.__name__}`...")
    instance = EventPoster(bot)
    asyncio.create_task(instance.async_setup())
    await bot.add_cog(instance, guild=discord.Object(id=GUILD_ID))