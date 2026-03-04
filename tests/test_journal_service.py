"""Tests des services de chargement journal."""

import unittest
from unittest.mock import patch

import pandas as pd

from services.journal_service import extract_years, load_journal_dataframe


class TestJournalService(unittest.TestCase):
    def test_extract_years_merges_fixed_and_data(self):
        df = pd.DataFrame({"Année": ["2026", "2024", "x"]})
        years = extract_years(df, start_year=2024, end_year=2026)
        self.assertEqual(years[0], "2026")
        self.assertIn("2025", years)
        self.assertIn("x", years)

    def test_load_journal_dataframe_uses_fallback_when_no_file(self):
        fallback = pd.DataFrame({"Année": ["2026"]})
        with patch("services.journal_service.DataManager.resolve_journal_file", return_value=None):
            df = load_journal_dataframe(df_fallback=fallback)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["Année"], "2026")


if __name__ == "__main__":
    unittest.main()
