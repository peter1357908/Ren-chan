"""Keep table assignment independent of Discord for easier testing."""

import random


def assign_tables(player_ids: list[int]) -> tuple[list[list[int]], list[int]]:
    """Return tables in seat order and any players sitting out."""
    if len(player_ids) < 3:
        raise ValueError("At least three players are required to assign tables.")
    if len(set(player_ids)) != len(player_ids):
        raise ValueError("Players must not appear more than once.")

    players = player_ids.copy()
    random.shuffle(players)
    sitting_out = [players.pop()] if len(players) == 5 else []

    four_player_tables = len(players) // 4
    while (len(players) - 4 * four_player_tables) % 3:
        four_player_tables -= 1
    three_player_tables = (len(players) - 4 * four_player_tables) // 3

    # Split the shuffled players into consecutive groups of four, then three.
    tables = []
    offset = 0
    for size in [4] * four_player_tables + [3] * three_player_tables:
        tables.append(players[offset:(offset + size)])
        offset += size
    return tables, sitting_out
