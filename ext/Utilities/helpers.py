import discord
from typing import Literal

from .config import *

def get_discord_name(member: discord.Member) -> str:
    discord_name = member.name
    # add "#1234" if it exists
    discriminator = str(member.discriminator)
    if discriminator != "0":
        discord_name += "#" + discriminator
    return discord_name

# for "seat" tiebreaker method
SEAT_SORT_KEY = {
    "East": 4,
    "South": 3,
    "West": 2,
    "North": 1,
}

PLACEMENT_KEY = {
    1: "1st",
    2: "2nd",
    3: "3rd",
    4: "4th",
}

# placement uma lookup table based on ruleset, game type, and placement
PLACEMENT_UMA = {
    "Yonma": {
        "Hanchan": {
            1: YONMA_HANCHAN_UMA_1,
            2: YONMA_HANCHAN_UMA_2,
            3: YONMA_HANCHAN_UMA_3,
            4: YONMA_HANCHAN_UMA_4,
        },
        "Tonpuu": {
            1: YONMA_TONPUU_UMA_1,
            2: YONMA_TONPUU_UMA_2,
            3: YONMA_TONPUU_UMA_3,
            4: YONMA_TONPUU_UMA_4,
        },
    },
    "Sanma": {
        "Hanchan": {
            1: SANMA_HANCHAN_UMA_1,
            2: SANMA_HANCHAN_UMA_2,
            3: SANMA_HANCHAN_UMA_3,
        },
        "Tonpuu": {
            1: SANMA_TONPUU_UMA_1,
            2: SANMA_TONPUU_UMA_2,
            3: SANMA_TONPUU_UMA_3,
        },
    },
}


class PlayerScore:
    def __init__(
        self,
        seat: str,
        member: discord.Member,
        raw_score: int,
        penalty: float=0.0
    ):
        # columns of the "Scores" worksheet
        assert seat in SEAT_SORT_KEY, f"Invalid seat: {seat}. Must be one of {list(SEAT_SORT_KEY.keys())}."
        self.seat: str = seat
        self.discord_name: str = get_discord_name(member)
        assert raw_score % 100 == 0, f"Invalid raw score: {raw_score}. Must be a multiple of 100."
        self.raw_score: int = raw_score
        self.placement: int | None = None  # to be assigned later
        self.uma: float | None = None  # to be assigned later based on placement and ruleset
        assert penalty <= 0, f"Invalid penalty: {penalty}. Must be non-positive."
        self.penalty: float = penalty
        self.final_score: float | None = None  # to be calculated later based on placement and tiebreaker

        # for Discord announcement
        self.mention: str = member.mention
        
    # instead of implementing the rich comparison methods,
    # we provide a sort key function for easier use 
    # with different tiebreaker methods.
    def sort_key(self) -> tuple:
        """
        Returns a tuple usable for sorting.
        Higher raw_score is always better.
        """
        if TIEBREAKER_METHOD == "split":
            # Only raw score matters; ties remain ties
            return (self.raw_score,)
        elif TIEBREAKER_METHOD == "seat":
            # Raw score first, then seat priority
            return (
                self.raw_score,
                SEAT_SORT_KEY[self.seat],
            )
        else:
            raise ValueError(f"Unknown tiebreaker: {TIEBREAKER_METHOD}")

    # TODO: turn this include a rich embed with a table
    def __str__(self) -> str:
        """
        used for rendering the player score in output
        """
        assert self.placement is not None, "Placement not calculated."
        assert self.final_score is not None, "Final score not calculated."

        output = \
            f"{self.seat:<5} — {self.mention}\n" \
            f"Raw: {self.raw_score:>8,} | {PLACEMENT_KEY[self.placement]:<4} | Final: **{self.final_score:.1f}**"

        if self.penalty < 0:
            output += f" (including {self.penalty} penalty)"

        return output

    def __repr__(self) -> str:
        return self.__str__()
    


def calculate_placement_and_final_score(
    game_mode: Literal["Yonma", "Sanma"],
    game_length: Literal["Hanchan", "Tonpuu"],
    players: list[PlayerScore]
) -> None:
    """
    Takes in a list of PlayerScore objects representing results of a single game.
    
    Modifies the PlayerScore objects in-place to assign placements and final scores
    based on game mode, game length, and tiebreaker method.
    
    Does not modify the input list order.
    """
    if game_mode == "Yonma":
        starting_points = YONMA_STARTING_POINTS
    else:
        starting_points = SANMA_STARTING_POINTS

    # first, sort the players without explicit placement assignment
    sorted_players = sorted(
        players,
        key=lambda p: p.sort_key(),
        reverse=True
    )

    # then, assign placement, uma, final_score based on tiebreaker (implemented as a sort key)
    i = 0
    while i < len(sorted_players):
        player = sorted_players[i]
        current_placement = i + 1  # placements are 1-indexed

        # look ahead to find ties; if found, resolve all ties at once
        if i < len(sorted_players) - 1 and player.sort_key() == sorted_players[i+1].sort_key():
            # find all players in this tie group
            tie_group = [player, sorted_players[i+1]]  # at least these two are tied
            
            for j in range(i+2, len(sorted_players)):
                if sorted_players[j].sort_key() == player.sort_key():
                    tie_group.append(sorted_players[j])
                else:
                    break
            
            # calculate the combined uma, then divide into equal shares for the tie group
            combined_uma = 0
            for k in range(current_placement, current_placement + len(tie_group)):
                combined_uma += PLACEMENT_UMA[game_mode][game_length][k]
            individual_uma = combined_uma / len(tie_group)

            for tied_player in tie_group:
                tied_player.placement = current_placement
                tied_player.uma = individual_uma
                tied_player.final_score = (tied_player.raw_score - starting_points) / 1000 + tied_player.uma + tied_player.penalty
            
            # skip ahead by the size of the tie group
            i += len(tie_group)
            continue
        
        # the normal case: no tie, just assign placement, uma, and final_score directly
        player.placement = current_placement
        player.uma = PLACEMENT_UMA[game_mode][game_length][current_placement]
        player.final_score = (player.raw_score - starting_points) / 1000 + player.uma + player.penalty
        i += 1
