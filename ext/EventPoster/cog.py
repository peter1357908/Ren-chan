import asyncio
import datetime
import discord
import logging
from discord.ext import commands, tasks
from typing import *
from same_day_event import SameDayEvent

from global_stuff import assert_getenv

GUILD_ID = int(assert_getenv("guild_id"))

events = [
    SameDayEvent(
        starting_date=datetime.date(year=2025, month=7, day=12),
        frequency=28,
        name="Saturday Afternoon Riichi",
        description="This is our 4-weekly Saturday meetup! No experience required -- we'll be happy to teach!",
        start_time=datetime.time(hour=13),
        end_time=datetime.time(hour=18),
        location="Element Eatery (5350 Medpace Way, Cincinnati, OH 45227)"
    ),
    SameDayEvent(
        starting_date=datetime.date(year=2025, month=7, day=6),
        frequency=14,
        name="Sunday Afternoon Riichi",
        description="This is our biweekly Sunday meetup! No experience required -- we'll be happy to teach!",
        start_time=datetime.time(hour=13),
        end_time=datetime.time(hour=18),
        location="Element Eatery (5350 Medpace Way, Cincinnati, OH 45227)"
    )
]

class EventPoster(commands.Cog):
    def __init__(self, bot: commands.Bot, events: List[SameDayEvent]):
        self.bot = bot
        self.events = events
        self.guild: discord.Guild = None # bot.get_guild(GUILD_ID) doesn't work; needs to be fetched via API

    @tasks.loop(hours=24, reconnect=True)
    async def try_post_events(self):
        logging.info("Checking if any event needs to be posted...")
        
        curr_events = await self.guild.fetch_scheduled_events()
        curr_event_names = {e.name for e in curr_events}

        for e in self.events:
            if e.name in curr_event_names:
                continue

            logging.info(f"Posting event \"{e.name}\".")
            asyncio.create_task(e.post_next_event())

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
    instance = EventPoster(bot, events)
    asyncio.create_task(instance.async_setup())
    await bot.add_cog(instance, guild=discord.Object(id=GUILD_ID))