import datetime
import discord
import gspread
import logging
from discord.ext import commands
from discord import app_commands, Interaction
from typing import *
from global_stuff import assert_getenv

GUILD_ID: int                 = int(assert_getenv("guild_id"))
OFFICER_ROLE: str             = assert_getenv("officer_role")
ELDER_ROLE: str               = assert_getenv("elder_role")
# PAID_MEMBER_ROLE_ID: int      = int(assert_getenv("paid_member_role_id"))
# PAST_PAID_MEMBER_ROLE_ID: int = int(assert_getenv("past_paid_member_role_id"))
CLUB_LEADERBOARD_URL: str     = assert_getenv("club_leaderboard_url")
FRIENDLY_LEADERBOARD_URL: str = assert_getenv("friendly_leaderboard_url")
REGISTRY_NAME_LENGTH: int     = int(assert_getenv("max_name_len"))

# Google Sheets stuff
import gspread
import asyncio
gs_client = gspread.service_account(filename='gs_service_account.json')
# club leaderboard
club_leaderboard_ss = gs_client.open_by_url(assert_getenv("club_leaderboard_url"))
club_leaderboard_registry = club_leaderboard_ss.worksheet("Registry")
club_leaderboard_raw_scores = club_leaderboard_ss.worksheet("Raw Scores")
club_leaderboard_registry_lock = asyncio.Lock()
club_leaderboard_raw_scores_lock = asyncio.Lock()
# friendly leaderboard
friendly_leaderboard_ss = gs_client.open_by_url(assert_getenv("friendly_leaderboard_url"))
friendly_leaderboard_registry = friendly_leaderboard_ss.worksheet("Registry")
friendly_leaderboard_raw_scores = friendly_leaderboard_ss.worksheet("Raw Scores")
friendly_leaderboard_registry_lock = asyncio.Lock()
friendly_leaderboard_raw_scores_lock = asyncio.Lock()


def get_discord_name(member: discord.Member) -> str:
    discord_name = member.name
    # add "#1234" if it exists
    discriminator = str(member.discriminator)
    if discriminator != "0":
        discord_name += "#" + discriminator
    return discord_name

class PlayerScore:
    def __init__(self, member: discord.Member,
                       raw_score: int,
                       num_chombo: int=0):
        # the default values correspond to an AI opponent (not a real player)
        self.discord_name = get_discord_name(member)
        self.mention = member.mention
        self.raw_score = raw_score
        self.num_chombo = num_chombo

    # comparisons are for the scores only (i.e., not discord names)
    def __eq__(self, other: object) -> bool:
        if isinstance(other, PlayerScore):
            return self.raw_score == other.raw_score
        return NotImplemented
    
    def __lt__(self, other):
        if isinstance(other, PlayerScore):
            return self.raw_score < other.raw_score
        return NotImplemented

    def __str__(self) -> str:
        """
        used for rendering the player score in output
        """
        if self.num_chombo > 0:
            return f"{self.mention}: {self.raw_score} with {self.num_chombo} chombo"
        else:
            return f"{self.mention}: {self.raw_score}"

    def __repr__(self) -> str:
        return self.__str__()

class Utilities(commands.Cog):
    """
    Utility commands specific to Longhorn Riichi
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    """
    =====================================================
    HELPERS
    =====================================================
    """
    
    """
    =====================================================
    SLASH COMMANDS
    =====================================================
    """
        
    async def _register(self, server_member: discord.Member, name: str, leaderboard_type: str) -> str:
        """
        Add player to the registry on target leaderboard(s), removing any existing registration first.
        Assumes input is already sanitized (e.g., `name` isn't 200 chars long)
        Returns the response string.
        """
        if len(name) > REGISTRY_NAME_LENGTH:
            return f"Please keep your preferred name within {REGISTRY_NAME_LENGTH} characters and `/register` again."
        
        discord_name = get_discord_name(server_member)

        response = f"{server_member.mention}"

        if leaderboard_type == "both leaderboards" or leaderboard_type == "Club Leaderboard":
            curr_leaderboard_type = "Club Leaderboard"
            registry = club_leaderboard_registry
            registry_lock = club_leaderboard_registry_lock

            async with registry_lock:
                # find and delete any existing registration, while recording extra info like membership status
                found_cell: gspread.cell.Cell = registry.find(discord_name, in_column=2)
                found_old_registration = found_cell is not None

                paid_membership = "no"
                if found_old_registration:
                    [_, _, paid_membership, *mahjongsoul_fields] = registry.row_values(found_cell.row)
                    registry.delete_rows(found_cell.row)
                # add new registration information
                data = [name,
                    discord_name,
                    paid_membership]
                registry.append_row(data)

                if found_old_registration:
                    response += f" updated **{curr_leaderboard_type}** registration"
                else:
                    response += f" registered on **{curr_leaderboard_type}**"

        if leaderboard_type == "both leaderboards" or leaderboard_type == "Friendly Leaderboard":
            curr_leaderboard_type = "Friendly Leaderboard"
            registry = friendly_leaderboard_registry
            registry_lock = friendly_leaderboard_registry_lock

            async with registry_lock:
                # find and delete any existing registration, while recording extra info like membership status
                found_cell: gspread.cell.Cell = registry.find(discord_name, in_column=2)
                found_old_registration = found_cell is not None

                paid_membership = "no"
                if found_old_registration:
                    [_, _, paid_membership, *mahjongsoul_fields] = registry.row_values(found_cell.row)
                    registry.delete_rows(found_cell.row)
                # add new registration information
                data = [name,
                    discord_name,
                    paid_membership]
                registry.append_row(data)
                
                if leaderboard_type != "Friendly Leaderboard":
                    response += " and"

                if found_old_registration:
                    response += f" updated **{curr_leaderboard_type}** registration"
                else:
                    response += f" registered on **{curr_leaderboard_type}**"

        return response + f" with name **\"{name}\"**."
    
    @app_commands.command(name="register", description="Register with your name (or update your current registration) on a leaderboard.")
    @app_commands.describe(
        real_name=f"Your preferred, real-life name (no more than {REGISTRY_NAME_LENGTH} characters)",
        leaderboard_type="Both leaderboards (default), or just one of them?")
    async def register(self, interaction: Interaction,
                       real_name: str,
                       leaderboard_type: Literal["both leaderboards", "Club Leaderboard", "Friendly Leaderboard"] = "both leaderboards"):
        await interaction.response.defer()
        response = await self._register(interaction.user, real_name, leaderboard_type)
        await interaction.followup.send(content=response)
    
    @app_commands.command(name="register_other", description=f"Register any server member. Only usable by @{OFFICER_ROLE}.")
    @app_commands.describe(
        server_member="The server member you want to register.",
        real_name=f"The member's preferred, real-life name (no more than {REGISTRY_NAME_LENGTH} characters)",
        leaderboard_type="Both leaderboards (default), or just one of them?")
    @app_commands.checks.has_role(OFFICER_ROLE)
    async def register_other(self, interaction: Interaction,
                       server_member: discord.Member,
                       real_name: str,
                       leaderboard_type: Literal["both leaderboards", "Club Leaderboard", "Friendly Leaderboard"] = "both leaderboards"):
        await interaction.response.defer()
        response = await self._register(server_member, real_name, leaderboard_type)
        await interaction.followup.send(content=response)

    async def _unregister(self, server_member: discord.Member, leaderboard_type: str) -> str:
        discord_name = get_discord_name(server_member)

        response = ""

        if leaderboard_type == "both leaderboards" or leaderboard_type == "Club Leaderboard":
            curr_leaderboard_type = "Club Leaderboard"
            registry = club_leaderboard_registry
            registry_lock = club_leaderboard_registry_lock

            async with registry_lock:
                found_cell: gspread.cell.Cell = registry.find(discord_name, in_column=2)
                if found_cell is None:
                    response += f"{server_member.mention} is not a registered member on **{curr_leaderboard_type}**."
                else:
                    registry.delete_rows(found_cell.row)
                    response += f"{server_member.mention}'s registration has been removed from **{curr_leaderboard_type}**."

        if leaderboard_type == "both leaderboards" or leaderboard_type == "Friendly Leaderboard":
            curr_leaderboard_type = "Friendly Leaderboard"
            registry = friendly_leaderboard_registry
            registry_lock = friendly_leaderboard_registry_lock

            if leaderboard_type != "Friendly Leaderboard":
                response += '\n'

            async with registry_lock:
                found_cell: gspread.cell.Cell = registry.find(discord_name, in_column=2)
                if found_cell is None:
                    response += f"{server_member.mention} is not a registered member on **{curr_leaderboard_type}**."
                else:
                    registry.delete_rows(found_cell.row)
                    response += f"{server_member.mention}'s registration has been removed from **{curr_leaderboard_type}**."
        
        return response

    @app_commands.command(name="unregister", description="Remove your registered information from a leaderboard.")
    @app_commands.describe(leaderboard_type="Both leaderboards (default), or just one of them?")
    async def unregister(self, interaction: Interaction,
                         leaderboard_type: Literal["both leaderboards", "Club Leaderboard", "Friendly Leaderboard"] = "both leaderboards"):
        await interaction.response.defer()
        response = await self._unregister(interaction.user, leaderboard_type)
        await interaction.followup.send(content=response)

    @app_commands.command(name="unregister_other", description=f"Unregister a given server member from a leaderboard. Only usable by @{OFFICER_ROLE}.")
    @app_commands.describe(server_member="The server member you want to unregister.",
                           leaderboard_type="Both leaderboards (default), or just one of them?")
    @app_commands.checks.has_role(OFFICER_ROLE)
    async def unregister_other(self, interaction: Interaction,
                               server_member: discord.Member,
                               leaderboard_type: Literal["both leaderboards", "Club Leaderboard", "Friendly Leaderboard"] = "both leaderboards"):
        await interaction.response.defer()
        response = await self._unregister(server_member, leaderboard_type)
        await interaction.followup.send(content=response)

    async def _enter_score(self,
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
        ordered_players = sorted(player_scores, reverse=True)

        timestamp = str(datetime.datetime.now()).split(".")[0]
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
        else:
            raw_scores = friendly_leaderboard_raw_scores
            raw_scores_lock = friendly_leaderboard_raw_scores_lock

        async with raw_scores_lock:
            raw_scores.append_row(row)

        score_printout = f"Successfully entered scores for a {gamemode} game onto **{leaderboard_type}**:\n" \
                            f"- **1st**: {ordered_players[0]}\n" \
                            f"- **2nd**: {ordered_players[1]}\n" \
                            f"- **3rd**: {ordered_players[2]}"
        if game_style == "Yonma":
            score_printout += f"\n- **4th**: {ordered_players[3]}"

        return score_printout

    @app_commands.command(name="enter_scores_club", description=f"Enter scores for an IRL club game, starting with the East player. Only usable by @{OFFICER_ROLE} and @{ELDER_ROLE}.")
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
    async def enter_scores_club(self, interaction: Interaction,
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

        response = await self._enter_score(
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

        await interaction.followup.send(content=response)

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

        response = await self._enter_score(
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

        await interaction.followup.send(content=response)

        

async def setup(bot: commands.Bot):
    logging.info(f"Loading cog `{Utilities.__name__}`...")
    instance = Utilities(bot)
    await bot.add_cog(instance, guild=discord.Object(id=GUILD_ID))


