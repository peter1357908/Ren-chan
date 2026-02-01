import datetime
import discord
import gspread
import logging
from discord.ext import commands
from discord import app_commands, Interaction
from typing import *

from .config import *
from .helpers import *


class Utilities(commands.Cog):
    """
    Utility commands for club management
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    """
    =====================================================
    SLASH COMMANDS
    =====================================================
    """

    def _register_on_one_leaderboard(
            self,
            old_registration_cell: Optional[gspread.cell.Cell],
            discord_name: str,
            name: str,
            registry: gspread.Worksheet
        ) -> None:
        # this helper should only be called within a `registry_lock`

        found_old_registration = old_registration_cell is not None

        # TODO: ensure consistency of paid membership status across both leaderboards
        paid_membership = "no"

        # grab existing paid membership status & remove old registration if it exists
        if found_old_registration:
            [_, _, paid_membership] = registry.row_values(old_registration_cell.row)
            registry.delete_rows(old_registration_cell.row)

        # add new registration information
        data = [
            discord_name,
            name,
            paid_membership
        ]
        registry.append_row(data)
    
    async def _register(self, server_member: discord.Member, name: str) -> str:
        """
        Add player to the registry on both leaderboards, removing any existing registration first.
        Assumes input is already sanitized (e.g., `name` isn't 200 chars long).
        Requires a unique `name`.
        Returns the response string.
        """
        if len(name) > REGISTRY_NAME_LENGTH:
            return f"Please keep your preferred name within {REGISTRY_NAME_LENGTH} characters and `/register` again."

        async with registry_lock:
            # check if the `name` is already taken on either leaderboard
            # since the registry should be consistent across both leaderboards,
            # we complain when it's only taken on one of the leaderboards
            found_name_cell = club_leaderboard_registry.find(name, in_column=2)
            name_taken_club = found_name_cell is not None
            
            found_name_cell = friendly_leaderboard_registry.find(name, in_column=2)
            name_taken_friendly = found_name_cell is not None

            if name_taken_club or name_taken_friendly:
                if name_taken_club and name_taken_friendly:
                    return f"The name **\"{name}\"** is already taken. Please choose a different name."
                elif name_taken_club:
                    return f"The name **\"{name}\"** is already taken on the Club Leaderboard, but it's not present on the Friendly Leaderboard. Please contact <@{BOT_MAINTAINER_ID}> to resolve this inconsistency."
                else:
                    return f"The name **\"{name}\"** is already taken on the Friendly Leaderboard, but it's not present on the Club Leaderboard. Please contact <@{BOT_MAINTAINER_ID}> to resolve this inconsistency."

            # similarly, check if the current member is already registered, by Discord ID.
            # since the registry should be consistent across both leaderboards,
            # we complain when it only shows up on one of the leaderboards
            discord_name = get_discord_name(server_member)

            found_discord_cell_club = club_leaderboard_registry.find(discord_name, in_column=1)
            discord_taken_club = found_discord_cell_club is not None
            
            found_discord_cell_friendly = friendly_leaderboard_registry.find(discord_name, in_column=1)
            discord_taken_friendly = found_discord_cell_friendly is not None

            if discord_taken_club and not discord_taken_friendly:
                return f"You are already registered on the Club Leaderboard, but not on the Friendly Leaderboard. Please contact <@{BOT_MAINTAINER_ID}> to resolve this inconsistency."
            elif discord_taken_friendly and not discord_taken_club:
                return f"You are already registered on the Friendly Leaderboard, but not on the Club Leaderboard. Please contact <@{BOT_MAINTAINER_ID}> to resolve this inconsistency."

            self._register_on_one_leaderboard(found_discord_cell_club, discord_name, name, club_leaderboard_registry)
            self._register_on_one_leaderboard(found_discord_cell_friendly, discord_name, name, friendly_leaderboard_registry)

            if discord_taken_club:
                return f"{server_member.mention} updated their registration with name **\"{name}\"**."
            else:
                return f"{server_member.mention} registered with name **\"{name}\"**."
            
    
    @app_commands.command(name="register", description="Register with your name (or update your current registration) on our leaderboards.")
    @app_commands.describe(
        real_name=f"Your preferred, real-life name (no more than {REGISTRY_NAME_LENGTH} characters)")
    async def register(self, interaction: Interaction,
                       real_name: str):
        await interaction.response.defer()
        response = await self._register(interaction.user, real_name)
        await interaction.followup.send(content=response)
    
    @app_commands.command(name="register_other", description=f"Register any server member. Only usable by @{OFFICER_ROLE}.")
    @app_commands.describe(
        server_member="The server member you want to register.",
        real_name=f"The member's preferred, real-life name (no more than {REGISTRY_NAME_LENGTH} characters)")
    @app_commands.checks.has_role(OFFICER_ROLE)
    async def register_other(self, interaction: Interaction,
                       server_member: discord.Member,
                       real_name: str):
        await interaction.response.defer()
        response = await self._register(server_member, real_name)
        await interaction.followup.send(content=response)

    async def _unregister(self, server_member: discord.Member) -> str:
        discord_name = get_discord_name(server_member)

        # since we are just unregistering, we don't need to worry about consistency checks
        # just remove any existing registration on both leaderboards
        async with registry_lock:
            found_discord_cell_club = club_leaderboard_registry.find(discord_name, in_column=1)
            registered_club = found_discord_cell_club is not None
            if registered_club:
                club_leaderboard_registry.delete_rows(found_discord_cell_club.row)

            found_discord_cell_friendly = friendly_leaderboard_registry.find(discord_name, in_column=1)
            registered_friendly = found_discord_cell_friendly is not None
            if registered_friendly:
                friendly_leaderboard_registry.delete_rows(found_discord_cell_friendly.row)

            if registered_club or registered_friendly:
                return f"{server_member.mention} has been unregistered."
            else:
                return f"{server_member.mention} is not registered."

    @app_commands.command(name="unregister", description="Remove your registered information.")
    async def unregister(self, interaction: Interaction):
        await interaction.response.defer()
        response = await self._unregister(interaction.user)
        await interaction.followup.send(content=response)

    @app_commands.command(name="unregister_other", description=f"Unregister a given server member. Only usable by @{OFFICER_ROLE}.")
    @app_commands.describe(server_member="The server member you want to unregister.")
    @app_commands.checks.has_role(OFFICER_ROLE)
    async def unregister_other(self, interaction: Interaction,
                               server_member: discord.Member):
        await interaction.response.defer()
        response = await self._unregister(server_member)
        await interaction.followup.send(content=response)

    async def _enter_scores(self,
                            leaderboard_type: str,
                            game_type: str,
                            player_east: discord.Member, score_east: int,
                            player_south: discord.Member, score_south: int,
                            player_west: discord.Member, score_west: int,
                            player_north: Optional[discord.Member] = None, score_north: Optional[int] = None,
                            leftover_points: int = 0,
                            chombo_east: int = 0,
                            chombo_south: int = 0,
                            chombo_west: int = 0,
                            chombo_north: int = 0) -> str:
        # INPUT CHECKING LOGIC
        # =======================
        if chombo_east < 0 or chombo_south < 0 or chombo_west < 0 or chombo_north < 0:
            return "Error: negative chombo count."

        if player_north is None:
            if len(set([player_east, player_south, player_west])) != 3:
                return "Error: duplicate player entered."
            
            expected_total = 3*35000
            player_score_east = PlayerScore(player_east, score_east, chombo_east)
            player_score_south = PlayerScore(player_south, score_south, chombo_south)
            player_score_west = PlayerScore(player_west, score_west, chombo_west)
            player_scores = [player_score_east, player_score_south, player_score_west]
            game_style = "Sanma"
        else:
            if len(set([player_east, player_south, player_west, player_north])) != 4:
                return "Error: duplicate player entered."
            if score_north is None:
                return "Error: missing Player 4's score."
            
            expected_total = 4*25000
            player_score_east = PlayerScore(player_east, score_east, chombo_east)
            player_score_south = PlayerScore(player_south, score_south, chombo_south)
            player_score_west = PlayerScore(player_west, score_west, chombo_west)
            player_score_north = PlayerScore(player_north, score_north, chombo_north)
            player_scores = [player_score_east, player_score_south, player_score_west, player_score_north]
            game_style = "Yonma"
        
        # TODO: make more elegant!!
        total_score = score_east + score_south + score_west + leftover_points
        if game_style == "Yonma":
            total_score += score_north
        gamemode = f"{game_style} {game_type}"

        if total_score != expected_total:
            return f"Error: Entered scores sum up to be {total_score}.\nExpected {expected_total} for {gamemode}."

        # OUTPUT CONSTRUCTION LOGIC
        # =======================
        # TODO: explicitly implement the tie breaker
        ordered_players = sorted(player_scores, reverse=True)
        
        timestamp = str(datetime.datetime.now(TIME_ZONE)).split(".")[0]
        if game_style == "Yonma":
            row = [timestamp, gamemode, "yes",
                ordered_players[0].discord_name, ordered_players[0].raw_score,
                ordered_players[1].discord_name, ordered_players[1].raw_score,
                ordered_players[2].discord_name, ordered_players[2].raw_score,
                ordered_players[3].discord_name, ordered_players[3].raw_score,
                leftover_points,
                ordered_players[0].num_chombo,
                ordered_players[1].num_chombo,
                ordered_players[2].num_chombo,
                ordered_players[3].num_chombo]
        else:
            row = [timestamp, gamemode, "yes",
                ordered_players[0].discord_name, ordered_players[0].raw_score,
                ordered_players[1].discord_name, ordered_players[1].raw_score,
                ordered_players[2].discord_name, ordered_players[2].raw_score,
                "", "",
                leftover_points,
                ordered_players[0].num_chombo,
                ordered_players[1].num_chombo,
                ordered_players[2].num_chombo,
                ""]
        
        # enter the scores into the sheet
        if leaderboard_type == "Club Leaderboard":
            raw_scores = club_leaderboard_raw_scores
            raw_scores_lock = club_leaderboard_raw_scores_lock
            url = CLUB_LEADERBOARD_URL
        else:
            raw_scores = friendly_leaderboard_raw_scores
            raw_scores_lock = friendly_leaderboard_raw_scores_lock
            url = FRIENDLY_LEADERBOARD_URL

        async with raw_scores_lock:
            raw_scores.append_row(row)

        score_printout = f"Successfully entered scores for a {gamemode} game onto **[{leaderboard_type}]({url})**:\n" \
                            f"- **1st**: {ordered_players[0]}\n" \
                            f"- **2nd**: {ordered_players[1]}\n" \
                            f"- **3rd**: {ordered_players[2]}"
        if game_style == "Yonma":
            score_printout += f"\n- **4th**: {ordered_players[3]}"

        return score_printout

    @app_commands.command(name="enter_scores_club", description=f"Enter scores for a club game. Only usable by @{OFFICER_ROLE} and @{ELDER_ROLE}.")
    @app_commands.describe(game_type="Hanchan or tonpuu?",
                           player_east="The East player you want to record the score for.",
                           score_east="Score for East player.",
                           player_south="The South player you want to record the score for.",
                           score_south="Score for South player.",
                           player_west="The West player you want to record the score for.",
                           score_west="Score for West player.",
                           player_north="The North player (if Yonma) you want to record the score for.",
                           score_north="Score for North player (if Yonma).",
                           leftover_points="(optional) Leftover points (e.g., leftover riichi sticks).",
                           chombo_east="The number of chombo East player committed",
                           chombo_south="The number of chombo South player committed",
                           chombo_west="The number of chombo West player committed",
                           chombo_north="The number of chombo North player committed")
    @app_commands.checks.has_any_role(OFFICER_ROLE, ELDER_ROLE)
    async def enter_scores_club(self,
                                interaction: Interaction,
                                game_type: Literal["Hanchan", "Tonpuu"],
                                player_east: discord.Member, score_east: int,
                                player_south: discord.Member, score_south: int,
                                player_west: discord.Member, score_west: int,
                                player_north: Optional[discord.Member] = None, score_north: Optional[int] = None,
                                leftover_points: int = 0,
                                chombo_east: int = 0,
                                chombo_south: int = 0,
                                chombo_west: int = 0,
                                chombo_north: int = 0):

        await interaction.response.defer()

        response = await self._enter_scores(
            leaderboard_type="Club Leaderboard",
            game_type=game_type,
            player_east=player_east, score_east=score_east,
            player_south=player_south, score_south=score_south,
            player_west=player_west, score_west=score_west,
            player_north=player_north, score_north=score_north,
            leftover_points=leftover_points,
            chombo_east=chombo_east,
            chombo_south=chombo_south,
            chombo_west=chombo_west,
            chombo_north=chombo_north
        )

        await interaction.followup.send(content=response, suppress_embeds=True)

    @app_commands.command(name="enter_scores_friendly", description=f"Enter scores for an IRL friendly game, starting with the East player.")
    @app_commands.describe(game_type="Hanchan or tonpuu?",
                           player_east="The East player you want to record the score for.",
                           score_east="Score for East player.",
                           player_south="The South player you want to record the score for.",
                           score_south="Score for South player.",
                           player_west="The West player you want to record the score for.",
                           score_west="Score for West player.",
                           player_north="The North player (if Yonma) you want to record the score for.",
                           score_north="Score for North player (if Yonma).",
                           leftover_points="(optional) Leftover points (e.g., leftover riichi sticks).",
                           chombo_east="The number of chombo East player committed",
                           chombo_south="The number of chombo South player committed",
                           chombo_west="The number of chombo West player committed",
                           chombo_north="The number of chombo North player committed")
    async def enter_scores_friendly(self, interaction: Interaction,
                                game_type: Literal["Hanchan", "Tonpuu"],
                                player_east: discord.Member, score_east: int,
                                player_south: discord.Member, score_south: int,
                                player_west: discord.Member, score_west: int,
                                player_north: Optional[discord.Member] = None, score_north: Optional[int] = None,
                                leftover_points: int = 0,
                                chombo_east: int = 0,
                                chombo_south: int = 0,
                                chombo_west: int = 0,
                                chombo_north: int = 0):

        await interaction.response.defer()

        response = await self._enter_scores(
            leaderboard_type="Friendly Leaderboard",
            game_type=game_type,
            player_east=player_east, score_east=score_east,
            player_south=player_south, score_south=score_south,
            player_west=player_west, score_west=score_west,
            player_north=player_north, score_north=score_north,
            leftover_points=leftover_points,
            chombo_east=chombo_east,
            chombo_south=chombo_south,
            chombo_west=chombo_west,
            chombo_north=chombo_north
        )

        await interaction.followup.send(content=response, suppress_embeds=True)

        

async def setup(bot: commands.Bot):
    logging.info(f"Loading cog `{Utilities.__name__}`...")
    instance = Utilities(bot)
    await bot.add_cog(instance, guild=discord.Object(id=GUILD_ID))


