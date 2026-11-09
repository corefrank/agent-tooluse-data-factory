"""Offline regression tests, no LLM requests and no third-party libraries."""
import unittest
from p07_date_facts import extract_iso_dates, match_date_fact


class DateFactTests(unittest.TestCase):
    def test_iso(self):
        self.assertTrue(match_date_fact('2026-12-04', '2026-12-04'))

    def test_english_month(self):
        self.assertTrue(match_date_fact('The date is December 4, 2026.', '2026-12-04'))
        self.assertTrue(match_date_fact('The date is Dec. 4, 2026.', '2026-12-04'))

    def test_day_first(self):
        self.assertTrue(match_date_fact('Updated 4 December 2026.', '2026-12-04'))

    def test_chinese(self):
        self.assertTrue(match_date_fact('2026 年 5 月 20 日', '2026-05-20'))

    def test_slashes(self):
        self.assertTrue(match_date_fact('2026/12/4', '2026-12-04'))

    def test_wrong_date(self):
        self.assertFalse(match_date_fact('December 5, 2026', '2026-12-04'))

    def test_invalid(self):
        self.assertFalse(match_date_fact('2026-13-40', '2026-12-04'))
        self.assertFalse(match_date_fact('December 4, 2026', '2026-13-40'))

    def test_nondate_not_intercepted(self):
        self.assertIsNone(match_date_fact('refund policy', 'refund'))

    def test_number_not_date(self):
        self.assertEqual(extract_iso_dates('ticket 20261204'), set())


if __name__ == '__main__':
    unittest.main()
