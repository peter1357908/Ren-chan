
import datetime
import zoneinfo
import discord

TIMEZONE = zoneinfo.ZoneInfo("America/New_York")

class SameDayEvent():
    def __init__(self,
        starting_date: datetime.date,
        frequency: int,
        name: str,
        description: str,
        start_time: datetime.time,
        end_time: datetime.time,
        location: str):
        self.starting_date = starting_date
        self.frequency = frequency
        self.name = name
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
    
    @staticmethod
    def get_next_event_date(starting_date: datetime.date, frequency: int) -> datetime.date:
        """
        find the next date of an event, given the first event's date
        and the frequency.

        Args:
            starting_date (datetime.date): date of the first event
            frequency (int): number of days between 2 events 
        """
        today = datetime.date.today()
        if today < starting_date:
            return starting_date
        
        days_since_start = (today - starting_date).days
        days_since_last_event = days_since_start % frequency

        return today + datetime.timedelta(days=frequency - days_since_last_event)
    
    async def post_next_event(self, guild: discord.Guild):
        """
        Post same-day events
        """
        
        next_event_date = SameDayEvent.get_next_event_date(self.starting_date, self.frequency)

        await guild.create_scheduled_event(
            name = self.name,
            description = self.description,
            start_time = datetime.datetime.combine(date=next_event_date, time=self.start_time, tzinfo=TIMEZONE),
            end_time = datetime.datetime.combine(date=next_event_date, time=self.end_time, tzinfo=TIMEZONE),
            entity_type = discord.EntityType.external,
            privacy_level = discord.PrivacyLevel.guild_only,
            location = self.location)