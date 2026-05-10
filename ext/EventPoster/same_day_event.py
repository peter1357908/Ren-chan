import asyncio
import datetime
import zoneinfo
import discord
import logging
from typing import Sequence, Set

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
        excluded_dates: Set[datetime.date] | None = None):
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
        self._pending_reminder_event_ids: Set[int] = set()  # tracks event IDs with scheduled reminder tasks

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
    
    async def wait_and_send_reminder(self, delay: float, scheduled_event: discord.ScheduledEvent):
        await asyncio.sleep(delay)
        await self._send_reminder(scheduled_event)
        self._pending_reminder_event_ids.discard(scheduled_event.id)
    
    def _schedule_reminder(self, event_datetime: datetime.datetime, scheduled_event: discord.ScheduledEvent):
        reminder_datetime = event_datetime - self.remind_before
        delay_td = reminder_datetime - datetime.datetime.now(TIME_ZONE)

        logging.info(f"Scheduling reminder for \"{self.name}\" in {delay_td}.")
        self._pending_reminder_event_ids.add(scheduled_event.id)
        asyncio.create_task(self.wait_and_send_reminder(delay_td.total_seconds(), scheduled_event))

    def _build_reminder_message(self, scheduled_event: discord.ScheduledEvent) -> str:
        return (
            f"⏰ Reminder: **{self.name}** is coming up! We'll see you there!\n"
            f"Please RSVP in the event widget below:\n"
            f"{scheduled_event.url}"
        )

    async def _send_reminder(self, scheduled_event: discord.ScheduledEvent):
        logging.info(f"Sending reminder for \"{self.name}\".")
        await self.reminder_channel.send(self._build_reminder_message(scheduled_event))

    async def _reminder_already_posted(self, scheduled_event: discord.ScheduledEvent, reminder_datetime: datetime.datetime) -> bool:
        # Search a bounded range to avoid scanning entire channel history.
        # (1 hour before reminder time to 1 hour after event start time)
        search_after = reminder_datetime - datetime.timedelta(hours=1)
        search_before = scheduled_event.start_time + datetime.timedelta(hours=1)
        me = self.guild.me

        # 20 should be more than enough; few messages are sent in the reminder channel
        async for message in self.reminder_channel.history(limit=20, after=search_after, before=search_before):
            if me is not None and message.author.id != me.id:
                continue
            if scheduled_event.url in message.content:
                return True

        return False
    
    async def reconcile_event_reminder(self, existing_events: Sequence[discord.ScheduledEvent]):
        """
        Ensure the reminder is/will be posted for the next upcoming event in existing_events.
        This is idempotent and can be called every startup/loop.
        """
        # filter for the next upcoming event, if there are multiple events with the same name.
        now = datetime.datetime.now(TIME_ZONE)
        upcoming = [e for e in existing_events if e.start_time is not None and e.start_time > now]
        if not upcoming:
            return # no upcoming event, so nothing to reconcile
        
        scheduled_event = min(upcoming, key=lambda e: e.start_time)
        event_datetime = scheduled_event.start_time
        reminder_datetime = event_datetime - self.remind_before

        # unschedule the reminder task if the reminder has already been posted
        if await self._reminder_already_posted(scheduled_event, reminder_datetime):
            self._pending_reminder_event_ids.discard(scheduled_event.id)
            logging.info(
                f"Reminder already exists for event \"{self.name}\" ({scheduled_event.id}). Removed the event from pending set."
            )
            return

        # skip if a reminder task is already scheduled for this event
        if scheduled_event.id in self._pending_reminder_event_ids:
            return

        # reminder not scheduled but the post time has already passed, so send the
        # reminder now to catch up
        if now >= reminder_datetime:
            logging.info(
                f"Reminder time has passed for \"{self.name}\" ({scheduled_event.id}); sending catch-up reminder now."
            )
            await self._send_reminder(scheduled_event)
            return

        # otherwise, schedule the reminder for the future
        self._schedule_reminder(event_datetime, scheduled_event)
    
    async def post_next_event_and_schedule_reminder(self):
        """
        Post the next event unless its date is excluded. Then schedule a reminder
        to be sent before the event starts.

        NOTE: we don't schedule the posting of the next recurrence here intentionally.
        It's easier to schedule next events based on the presence of events (e.g., so
        we don't post a new one every restart)

        Reminders are reconciled against Discord state (scheduled event + message history)
        so restart does not lose them.
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

        # Schedule reminder and let regular reconciliation keep things correct after restarts.
        await self.reconcile_event_reminder([scheduled_event])
