import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from ext.Utilities.lobby import LobbyView, MESSAGE_LIMIT


def interaction(user_id: int, officer: bool = False):
    user = MagicMock(spec=discord.Member)
    user.id = user_id
    user.roles = [SimpleNamespace(name="Officer")] if officer else []
    return SimpleNamespace(
        user=user,
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        message=SimpleNamespace(edit=AsyncMock()),
    )


class LobbyViewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.view = LobbyView("Leaderboard Games", "Officer", 123)

    async def test_join_leave_and_duplicate_actions(self):
        first = interaction(1)
        await self.view.join.callback(first)
        self.assertEqual(self.view.player_ids, [1])
        self.assertIn("<@1>", first.message.edit.await_args.kwargs["content"])
        self.assertFalse(first.message.edit.await_args.kwargs["allowed_mentions"].users)

        duplicate = interaction(1)
        await self.view.join.callback(duplicate)
        duplicate.followup.send.assert_awaited_once_with("You are already in this lobby.", ephemeral=True)

        missing = interaction(2)
        await self.view.leave.callback(missing)
        missing.followup.send.assert_awaited_once_with("You are not in this lobby.", ephemeral=True)

        await self.view.leave.callback(first)
        self.assertEqual(self.view.player_ids, [])
        self.assertIn("No players yet.", first.message.edit.await_args.kwargs["content"])

    async def test_only_officer_can_assign_and_at_least_three_are_required(self):
        self.view.player_ids = [1, 2, 3]
        non_officer = interaction(1)
        await self.view.assign.callback(non_officer)
        self.assertIn("Officer", non_officer.followup.send.await_args.args[0])
        self.assertTrue(non_officer.followup.send.await_args.kwargs["ephemeral"])
        self.assertFalse(self.view.closed)

        self.view.player_ids = [1, 2]
        officer = interaction(10, officer=True)
        await self.view.assign.callback(officer)
        officer.followup.send.assert_awaited_once_with(
            "At least three players are required to assign tables.", ephemeral=True
        )
        self.assertFalse(self.view.closed)

    async def test_lobbies_have_independent_rosters_and_closing(self):
        other = LobbyView("Leaderboard Games", "Officer", 123)
        await asyncio.gather(
            self.view.join.callback(interaction(1)),
            other.join.callback(interaction(1)),
        )
        await self.view.join.callback(interaction(2))
        await self.view.join.callback(interaction(3))
        self.assertEqual(self.view.player_ids, [1, 2, 3])
        self.assertEqual(other.player_ids, [1])

        await self.view.assign.callback(interaction(10, officer=True))
        await other.join.callback(interaction(4))
        self.assertTrue(self.view.closed)
        self.assertFalse(other.closed)
        self.assertEqual(other.player_ids, [1, 4])

    async def test_assign_closes_lobby_and_announces_seats_and_sit_out(self):
        self.view.player_ids = [1, 2, 3, 4, 5]
        officer = interaction(10, officer=True)
        with patch("ext.Utilities.lobby.assign_tables", return_value=([[4, 3, 2, 1]], [5])):
            await self.view.assign.callback(officer)
        self.assertTrue(self.view.closed)
        self.assertTrue(all(child.disabled for child in self.view.children))
        self.assertIn("(closed)", officer.message.edit.await_args.kwargs["content"])
        announcement = officer.followup.send.await_args.args[0]
        self.assertIn("**Table 1**\nEast: <@4>\nSouth: <@3>\nWest: <@2>\nNorth: <@1>", announcement)
        self.assertIn("**Sitting out:** <@5>", announcement)
        self.assertTrue(officer.followup.send.await_args.kwargs["allowed_mentions"].users)

        late_join = interaction(6)
        await self.view.join.callback(late_join)
        late_join.followup.send.assert_awaited_once_with("This lobby is closed.", ephemeral=True)

    async def test_concurrent_duplicate_joins_only_add_once(self):
        first, second = interaction(1), interaction(1)
        await asyncio.gather(self.view.join.callback(first), self.view.join.callback(second))
        self.assertEqual(self.view.player_ids, [1])
        self.assertEqual(first.message.edit.await_count + second.message.edit.await_count, 1)

    async def test_failed_roster_edits_restore_lobby_state(self):
        joining = interaction(1)
        joining.message.edit.side_effect = RuntimeError("edit failed")
        with self.assertRaises(RuntimeError):
            await self.view.join.callback(joining)
        self.assertEqual(self.view.player_ids, [])

        self.view.player_ids = [1, 2, 3]
        leaving = interaction(2)
        leaving.message.edit.side_effect = RuntimeError("edit failed")
        with self.assertRaises(RuntimeError):
            await self.view.leave.callback(leaving)
        self.assertEqual(self.view.player_ids, [1, 2, 3])

        officer = interaction(10, officer=True)
        officer.message.edit.side_effect = RuntimeError("edit failed")
        with self.assertRaises(RuntimeError):
            await self.view.assign.callback(officer)
        self.assertFalse(self.view.closed)
        self.assertTrue(all(not child.disabled for child in self.view.children))
        officer.followup.send.assert_not_awaited()

    async def test_concurrent_assignments_publish_only_once(self):
        self.view.player_ids = [1, 2, 3]
        first, second = interaction(10, officer=True), interaction(11, officer=True)
        await asyncio.gather(self.view.assign.callback(first), self.view.assign.callback(second))
        messages = [first.followup.send.await_args.args[0], second.followup.send.await_args.args[0]]
        self.assertEqual(sum("**Table 1**" in message for message in messages), 1)
        self.assertEqual(sum(message == "This lobby is closed." for message in messages), 1)

    async def test_large_announcement_is_split_on_table_boundaries(self):
        self.view.player_ids = list(range(10**18, 10**18 + 80))
        officer = interaction(1, officer=True)
        await self.view.assign.callback(officer)
        messages = [call.args[0] for call in officer.followup.send.await_args_list]
        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(message) <= MESSAGE_LIMIT for message in messages))
        for number in range(1, 21):
            self.assertEqual(sum(f"**Table {number}**" in message for message in messages), 1)

    async def test_lobby_rejects_join_when_roster_would_be_too_long(self):
        self.view.player_ids = list(range(10**18, 10**18 + 100))
        new_player = interaction(42)
        await self.view.join.callback(new_player)
        self.assertNotIn(42, self.view.player_ids)
        self.assertIn("lobby is full", new_player.followup.send.await_args.args[0])
        new_player.message.edit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
