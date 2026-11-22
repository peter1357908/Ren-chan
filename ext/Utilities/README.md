# Utilities

The [cog](./cog.py) registers the utility commands and delegates lobby
interactions to [lobby.py](./lobby.py) and table assignment to
[lobby_assignments.py](./lobby_assignments.py).

## Lobby

Use `/lobby` to create a lobby, optionally specifying a name (default:
`Leaderboard Games`). Join and Leave update the shared roster; if an action
does not apply to you, the bot replies privately. The lobby creator or an
officer can use Assign Tables to close the lobby and announce randomized tables
and seats, mentioning the players. Three-player tables use East, South, and
West; four-player tables also use North.

The lobby creator or an officer can close it without assigning tables. A lobby
also expires after one hour without any button interaction. Its roster and
buttons remain visible, but the buttons no longer work.

At least three players are needed. With five players, four are assigned to a
table and one randomly selected player sits out. Otherwise, tables contain
three or four players, maximizing the number of four-player tables.

Every number of players greater than five can be partitioned into threes and
fours.
<details>
<summary>Proof by Induction</summary>
6 = 3 + 3, 7 = 3 + 4, and 8 = 4 + 4. By induction, for any number
of at least 9, subtracting 3 leaves a number of at least 6 that can already
be partitioned; adding a table of 3 gives a partition for the original number.
</details>

Lobbies are held in memory. After the bot restarts, create a new lobby; buttons
on old lobby messages no longer work. Discord's message-size limit also limits
the number of players that fit in a lobby.

Run the lobby tests from the repository root with
`python -m unittest discover -s ext/Utilities/tests`.
