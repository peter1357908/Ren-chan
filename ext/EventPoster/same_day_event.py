import asyncio
import datetime
import zoneinfo
import discord
import logging
from typing import Optional, Set

from global_stuff import assert_getenv

TIME_ZONE = zoneinfo.ZoneInfo(assert_getenv("time_zone"))

class RecurringSameDayEvent():
    """
    Must provide guild and channel with `self.set_guild_and_channel()`
    before calling self.post_next_event()
    """
    def __init__(self,
        starting_date: datetime.date,
        frequency: datetime.timedelta,
        remind_before: datetime.timedelta,
        name: str,
        description: str,
        start_time: datetime.time,
        end_time: datetime.time,
        location: str,
        excluded_dates: Optional[Set[datetime.date]] = None):
        """
        NOTE: frequency's precision is up to "days" -- hours, etc. are discarded
        when used for calculation in self.get_next_event_date()
        """

        self.starting_date = starting_date
        self.frequency = frequency
        self.remind_before = remind_before
        self.name = name
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.excluded_dates = excluded_dates

        # the following must be set with self.set_guild_and_channel()
        self.reminder_channel: discord.TextChannel = None
        self.guild: discord.Guild = None

    def set_guild_and_channel(self, guild: discord.Guild, reminder_channel: discord.TextChannel):
        self.reminder_channel = reminder_channel
        self.guild = guild
    
    def get_next_event_date(self) -> datetime.date:
        """
        find the next date of an event, given the first event's date
        and the frequency.
        """
        today = datetime.datetime.now(TIME_ZONE).date()
        if today <= self.starting_date:
            return self.starting_date
        
        time_since_start = today - self.starting_date
        time_since_last_event = time_since_start % self.frequency
        last_event_date = today - time_since_last_event

        return last_event_date + self.frequency
    
    async def _delayed_reminder(self, delay: float, scheduled_event: discord.ScheduledEvent):
        await asyncio.sleep(delay)
        logging.info(f"Sending reminder for \"{self.name}\".")
        await self.reminder_channel.send(
            f"⏰ Reminder: **{self.name}** is coming up! We'll see you there!\n"
            f"Please RSVP in the event widget below:\n"
            f"{scheduled_event.url}"
        )
    
    def _schedule_reminder(self, event_datetime: datetime.datetime, scheduled_event: discord.ScheduledEvent):
        reminder_datetime = event_datetime - self.remind_before
        delay = (reminder_datetime - datetime.datetime.now(TIME_ZONE)).total_seconds()

        if delay < 0:
            logging.warning(f"Reminder time for event \"{self.name}\" is in the past -- skipping.")
            return

        logging.info(f"Scheduling reminder for \"{self.name}\" in {delay} seconds.")
        asyncio.create_task(self._delayed_reminder(delay, scheduled_event))
    
    async def post_next_event(self):
        """
        Post the next event unless its date is excluded. Then schedule a reminder
        to be sent before the event starts.

        NOTE: we don't schedule the posting of the next recurrence here intentionally.
        It's easier for schedule next events based on the presence of events (e.g., so
        we don't post a new one every restart)

        On the other hand, we can't easily check the presence of a reminder message by polling,
        so we schedule one to be send. However, we lose the scheduled reminder if the bot
        restarts after posting the event... welp.
        """
        
        next_event_date = self.get_next_event_date()
        
        if self.excluded_dates is not None and next_event_date in self.excluded_dates:
            logging.info(f"Did not post event \"{self.name}\" because its date ({next_event_date}) is excluded.")
            return
        
        start_datetime = datetime.datetime.combine(date=next_event_date, time=self.start_time, tzinfo=TIME_ZONE)
        end_datetime = datetime.datetime.combine(date=next_event_date, time=self.end_time, tzinfo=TIME_ZONE)

        logging.info(f"Posting event \"{self.name}\".")
        scheduled_event = await self.guild.create_scheduled_event(
            name = self.name,
            description = self.description,
            start_time = start_datetime,
            end_time = end_datetime,
            entity_type = discord.EntityType.external,
            privacy_level = discord.PrivacyLevel.guild_only,
            location = self.location)
        
        # Schedule the reminder
        self._schedule_reminder(start_datetime, scheduled_event)
