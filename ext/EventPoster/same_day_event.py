import datetime
import zoneinfo
import discord
import logging
from typing import Optional, Set

from global_stuff import assert_getenv

TIMEZONE = zoneinfo.ZoneInfo(assert_getenv("time_zone"))

class RecurringSameDayEvent():
    def __init__(self,
        starting_date: datetime.date,
        frequency: datetime.timedelta,
        name: str,
        description: str,
        start_time: datetime.time,
        end_time: datetime.time,
        location: str,
        excluded_dates: Optional[Set[datetime.date]] = None):
        self.starting_date = starting_date
        self.frequency = frequency
        self.name = name
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.excluded_dates = excluded_dates
    
    def get_next_event_date(self) -> datetime.date:
        """
        find the next date of an event, given the first event's date
        and the frequency.
        """
        today = datetime.date.today()
        if today < self.starting_date:
            return self.starting_date
        
        time_since_start = today - self.starting_date
        time_since_last_event = time_since_start % self.frequency
        last_event_date = today - time_since_last_event

        return last_event_date + self.frequency
    
    async def post_next_event(self, guild: discord.Guild):
        """
        Post the next event unless its date is excluded
        """
        
        next_event_date = self.get_next_event_date()
        
        if self.excluded_dates is not None and next_event_date in self.excluded_dates:
            logging.info(f"Did not post event \"{self.name}\" because its date ({next_event_date}) is excluded.")
            return

        logging.info(f"Posting event \"{self.name}\".")
        await guild.create_scheduled_event(
            name = self.name,
            description = self.description,
            start_time = datetime.datetime.combine(date=next_event_date, time=self.start_time, tzinfo=TIMEZONE),
            end_time = datetime.datetime.combine(date=next_event_date, time=self.end_time, tzinfo=TIMEZONE),
            entity_type = discord.EntityType.external,
            privacy_level = discord.PrivacyLevel.guild_only,
            location = self.location)
