import asyncio
import datetime
import discord
import logging
from discord.ext import commands, tasks
from typing import *
from .same_day_event import RecurringSameDayEvent

from global_stuff import assert_getenv

GUILD_ID                 = int(assert_getenv("guild_id"))
ANNOUNCEMENTS_CHANNEL_ID = int(assert_getenv("announcements_channel_id"))

tournament_dates = {
    datetime.date(2025, 9, 6)  # QCR local tournament 2025
}

events = [
    RecurringSameDayEvent(
        starting_date=datetime.date(year=2025, month=7, day=12),
        frequency=datetime.timedelta(weeks=4),
        name="Saturday Afternoon Riichi",
        description="This is our 4-weekly Saturday meetup! No experience required -- we'll be happy to teach!",
        start_time=datetime.time(hour=13),
        end_time=datetime.time(hour=18),
        location="Element Eatery (5350 Medpace Way, Cincinnati, OH 45227)",
        excluded_dates=tournament_dates
    ),
    RecurringSameDayEvent(
        starting_date=datetime.date(year=2025, month=7, day=6),
        frequency=datetime.timedelta(weeks=2),
        name="Sunday Afternoon Riichi",
        description="This is our biweekly Sunday meetup! No experience required -- we'll be happy to teach!",
        start_time=datetime.time(hour=13),
        end_time=datetime.time(hour=18),
        location="Element Eatery (5350 Medpace Way, Cincinnati, OH 45227)",
        excluded_dates=tournament_dates
    )
]

class EventPoster(commands.Cog):
    def __init__(self, bot: commands.Bot, events: List[RecurringSameDayEvent]):
        self.bot = bot
        self.events = events
        # the following are fetched in `self.async_setup()`
        self.guild: discord.Guild = None
        self.announcements_channel: discord.abc.GuildChannel = None

    @tasks.loop(hours=24, reconnect=True)
    async def try_post_events(self):
        logging.info("Checking if any event needs to be posted...")
        
        curr_events = await self.guild.fetch_scheduled_events()
        curr_event_names = {e.name for e in curr_events}

        for e in self.events:
            if e.name in curr_event_names:
                continue

            asyncio.create_task(e.post_next_event(self.guild))

    async def async_setup(self):
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(GUILD_ID)
        self.announcements_channel = self.guild.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
        if self.announcements_channel is None:
            logging.warning(f"Announcements channel ID specified ({ANNOUNCEMENTS_CHANNEL_ID})but no channel found! Won't be able to post announcements on regular events.")
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