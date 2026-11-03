import unittest
from datetime import date

from bot.db import Database
from bot.logic import expected_steps, is_workout_due, parse_steps, steps_reaction


class ParseStepsTests(unittest.TestCase):
    def test_plain_numbers(self):
        self.assertEqual(parse_steps("8500"), 8500)
        self.assertEqual(parse_steps("  7 500 "), 7500)

    def test_k_suffix(self):
        self.assertEqual(parse_steps("8.5к"), 8500)
        self.assertEqual(parse_steps("8,5k"), 8500)
        self.assertEqual(parse_steps("10к"), 10000)

    def test_with_word(self):
        self.assertEqual(parse_steps("6300 шагов"), 6300)

    def test_invalid(self):
        for text in ["привет", "", "8.5", "1000000", "abc123"]:
            self.assertIsNone(parse_steps(text), text)


class WorkoutTests(unittest.TestCase):
    def test_first_workout_is_today(self):
        self.assertTrue(is_workout_due(None, date(2026, 11, 3)))

    def test_every_other_day(self):
        last = date(2026, 11, 3)
        self.assertFalse(is_workout_due(last, date(2026, 11, 3)))
        self.assertFalse(is_workout_due(last, date(2026, 11, 4)))
        self.assertTrue(is_workout_due(last, date(2026, 11, 5)))
        self.assertTrue(is_workout_due(last, date(2026, 11, 8)))  # пропущенная


class ReactionTests(unittest.TestCase):
    def test_goal_reached(self):
        self.assertIn("Норма выполнена", steps_reaction(10_500, 10_000, 20))

    def test_far_above_goal(self):
        self.assertIn("больше нормы", steps_reaction(16_000, 10_000, 20))

    def test_almost(self):
        self.assertIn("Почти у цели", steps_reaction(8_500, 10_000, 20))

    def test_on_track(self):
        # к 15:00 «положено» ~5000
        self.assertIn("по графику", steps_reaction(5_500, 10_000, 15))

    def test_late_and_low(self):
        self.assertIn("день заканчивается", steps_reaction(2_000, 10_000, 20))

    def test_expected_bounds(self):
        self.assertEqual(expected_steps(10_000, 6), 0)
        self.assertEqual(expected_steps(10_000, 23), 10_000)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.db.add_user(1)

    def test_steps_overwrite(self):
        d = date(2026, 11, 3)
        self.db.set_steps(1, d, 3000)
        self.db.set_steps(1, d, 5000)
        self.assertEqual(self.db.get_steps(1, d), 5000)

    def test_last_workout(self):
        self.assertIsNone(self.db.last_workout(1))
        self.db.log_workout(1, date(2026, 11, 1))
        self.db.log_workout(1, date(2026, 11, 3))
        self.assertEqual(self.db.last_workout(1), date(2026, 11, 3))

    def test_pause_and_skip(self):
        self.db.set_paused(1, True)
        self.assertEqual(self.db.active_users(), [])
        self.db.add_user(1)
        self.assertEqual(self.db.active_users(), [1])
        self.db.set_skip(1, date(2026, 11, 3))
        self.assertTrue(self.db.skipped_on(1, date(2026, 11, 3)))
        self.assertFalse(self.db.skipped_on(1, date(2026, 11, 4)))


if __name__ == "__main__":
    unittest.main()
