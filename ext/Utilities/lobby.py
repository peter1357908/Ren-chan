import asyncio
import logging

import discord

from .lobby_assignments import assign_tables


SEATS = ("East", "South", "West", "North")
MESSAGE_LIMIT = 2000  # set to the Discord message content limit
# See: https://docs.discord.com/developers/resources/message#create-message


class LobbyView(discord.ui.View):
    def __init__(self, name: str, officer_role: str, maintainer_id: int, creator_id: int):
        super().__init__(timeout=3600)
        self.name = discord.utils.escape_mentions(name)
        self.officer_role = officer_role
        self.maintainer_id = maintainer_id
        self.creator_id = creator_id
        self.player_ids: list[int] = []
        self.closed = False
        self.lock = asyncio.Lock()

    def roster(self) -> str:
        status = " (closed)" if self.closed else ""
        players = "\n".join(f"<@{player_id}>" for player_id in self.player_ids)
        return (
            f"**Lobby: {self.name}**{status}\n{players or 'No players yet.'}"
            "\n\n**Menus:** top = Add Others; bottom = Remove Others"
        )

    def can_manage(self, user: discord.User | discord.Member) -> bool:
        return user.id == self.creator_id or (
            isinstance(user, discord.Member)
            and any(role.name == self.officer_role for role in user.roles)
        )

    async def update_roster_message(self, interaction: discord.Interaction) -> None:
        # Every roster edit must suppress mentions; Discord does not retain
        # the original message's allowed-mentions setting.
        if interaction.message is None:
            raise RuntimeError("Lobby interaction has no message.")
        await interaction.message.edit(
            content=self.roster(), view=self, allowed_mentions=discord.AllowedMentions.none()
        )

    async def close_lobby(self, interaction: discord.Interaction) -> None:
        self.closed = True
        for child in self.children:
            child.disabled = True
        updated = False
        try:
            await self.update_roster_message(interaction)
            updated = True
        finally:
            if not updated:
                self.closed = False
                for child in self.children:
                    child.disabled = False
        self.stop()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ) -> None:
        logging.error("Lobby interaction failed", exc_info=(type(error), error, error.__traceback__))
        if self.closed:
            message = f"The lobby is closed, but the table announcement may be incomplete. Please contact <@{self.maintainer_id}>."
        else:
            message = f"An error occurred while updating the lobby. Please contact an officer or <@{self.maintainer_id}>."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def add_player(self, interaction: discord.Interaction, player_id: int) -> None:
        self.player_ids.append(player_id)
        # Leave room for the closed marker.
        if len(self.roster()) + len(" (closed)") > MESSAGE_LIMIT:
            self.player_ids.pop()
            await interaction.followup.send("This lobby is full; its roster cannot fit in a Discord message.", ephemeral=True)
            return
        updated = False
        try:
            await self.update_roster_message(interaction)
            updated = True
        finally:
            if not updated:
                self.player_ids.pop()

    async def remove_player(self, interaction: discord.Interaction, player_id: int) -> None:
        index = self.player_ids.index(player_id)
        self.player_ids.pop(index)
        updated = False
        try:
            await self.update_roster_message(interaction)
            updated = True
        finally:
            if not updated:
                self.player_ids.insert(index, player_id)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        async with self.lock:
            if self.closed:
                await interaction.followup.send("This lobby is closed.", ephemeral=True)
            elif interaction.user.id in self.player_ids:
                await interaction.followup.send("You are already in this lobby.", ephemeral=True)
            else:
                await self.add_player(interaction, interaction.user.id)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Add Others", row=1)
    async def add_others(self, interaction: discord.Interaction, select: discord.ui.UserSelect) -> None:
        await interaction.response.defer()
        async with self.lock:
            if self.closed:
                await interaction.followup.send("This lobby is closed.", ephemeral=True)
            elif not self.can_manage(interaction.user):
                await interaction.followup.send("Only the lobby creator or an officer can add others.", ephemeral=True)
            elif select.values[0].id in self.player_ids:
                await interaction.followup.send("That user is already in this lobby.", ephemeral=True)
            else:
                await self.add_player(interaction, select.values[0].id)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Remove Others", row=2)
    async def remove_others(self, interaction: discord.Interaction, select: discord.ui.UserSelect) -> None:
        await interaction.response.defer()
        async with self.lock:
            if self.closed:
                await interaction.followup.send("This lobby is closed.", ephemeral=True)
            elif not self.can_manage(interaction.user):
                await interaction.followup.send("Only the lobby creator or an officer can remove others.", ephemeral=True)
            elif select.values[0].id not in self.player_ids:
                await interaction.followup.send("That user is not in this lobby.", ephemeral=True)
            else:
                await self.remove_player(interaction, select.values[0].id)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        async with self.lock:
            if self.closed:
                await interaction.followup.send("This lobby is closed.", ephemeral=True)
            elif interaction.user.id not in self.player_ids:
                await interaction.followup.send("You are not in this lobby.", ephemeral=True)
            else:
                await self.remove_player(interaction, interaction.user.id)

    @discord.ui.button(label="Assign Tables", style=discord.ButtonStyle.primary)
    async def assign(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        async with self.lock:
            if self.closed:
                await interaction.followup.send("This lobby is closed.", ephemeral=True)
                return
            if not self.can_manage(interaction.user):
                await interaction.followup.send(
                    "Only the lobby creator or an officer can assign tables.",
                    ephemeral=True,
                )
                return
            if len(self.player_ids) < 3:
                await interaction.followup.send("At least three players are required to assign tables.", ephemeral=True)
                return

            tables, sitting_out = assign_tables(self.player_ids)
            await self.close_lobby(interaction)

            sections = [
                f"**Table {number}**\n" + "\n".join(
                    f"{seat}: <@{player_id}>" for seat, player_id in zip(SEATS, table)
                )
                for number, table in enumerate(tables, start=1)
            ]
            if sitting_out:
                sections.append(f"**Sitting out:** <@{sitting_out[0]}>")

            messages = [f"**Table assignments: {self.name}**"]
            for section in sections:
                if len(messages[-1]) + len(section) + 2 > MESSAGE_LIMIT:
                    messages.append(section)
                else:
                    messages[-1] += f"\n\n{section}"

            for message in messages:
                await interaction.followup.send(
                    message,
                    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
                )

    @discord.ui.button(label="Close Lobby", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        async with self.lock:
            if self.closed:
                await interaction.followup.send("This lobby is closed.", ephemeral=True)
            elif not self.can_manage(interaction.user):
                await interaction.followup.send("Only the lobby creator or an officer can close this lobby.", ephemeral=True)
            else:
                await self.close_lobby(interaction)
