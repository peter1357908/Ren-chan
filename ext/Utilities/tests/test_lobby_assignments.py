import unittest
from unittest.mock import patch

from ext.Utilities.lobby_assignments import assign_tables


class TableAssignmentTests(unittest.TestCase):
    def test_table_sizes_and_players(self):
        examples = {
            3: [3], 4: [4], 5: [4], 6: [3, 3], 7: [4, 3],
            8: [4, 4], 10: [4, 3, 3], 11: [4, 4, 3],
            12: [4, 4, 4], 19: [4, 4, 4, 4, 3],
        }
        for count, sizes in examples.items():
            with self.subTest(count=count):
                players = list(range(count))
                tables, sitting_out = assign_tables(players)
                self.assertEqual([len(table) for table in tables], sizes)
                self.assertEqual(len(sitting_out), int(count == 5))
                assigned = [player for table in tables for player in table] + sitting_out
                self.assertCountEqual(assigned, players)
                self.assertEqual(players, list(range(count)))

    def test_all_larger_counts_maximize_four_player_tables(self):
        for count in range(6, 201):
            with self.subTest(count=count):
                tables, sitting_out = assign_tables(list(range(count)))
                number_of_fours = sum(len(table) == 4 for table in tables)
                self.assertEqual(sitting_out, [])
                self.assertEqual(sum(map(len, tables)), count)
                self.assertTrue(all(len(table) in (3, 4) for table in tables))
                # Enumerate possible four-table counts and choose the largest
                # that leaves a multiple of three players.
                self.assertEqual(
                    number_of_fours,
                    max(fours for fours in range(count // 4 + 1) if (count - 4 * fours) % 3 == 0),
                )

    def test_shuffled_order_determines_who_sits_out(self):
        with patch("ext.Utilities.lobby_assignments.random.shuffle", side_effect=lambda players: players.reverse()) as shuffle:
            tables, sitting_out = assign_tables([1, 2, 3, 4, 5])
        shuffle.assert_called_once()
        self.assertEqual(tables, [[5, 4, 3, 2]])
        self.assertEqual(sitting_out, [1])

    def test_invalid_inputs(self):
        for players in ([], [1], [1, 2], [1, 1, 2]):
            with self.subTest(players=players), self.assertRaises(ValueError):
                assign_tables(players)


if __name__ == "__main__":
    unittest.main()
