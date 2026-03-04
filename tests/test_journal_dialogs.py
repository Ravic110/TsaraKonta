"""Tests unitaires pour la normalisation des dtypes du journal."""

import unittest

import pandas as pd

from ui.journal_dialogs import coerce_journal_dtypes


class TestJournalDialogs(unittest.TestCase):
    def test_coerce_journal_dtypes_allows_string_account_assignment(self):
        df = pd.DataFrame(
            {
                "Date": ["01/01/2026"],
                "Libellé": ["Achat"],
                "DateValeur": ["01/01/2026"],
                "MontantDébit": [120],
                "MontantCrédit": [0],
                "CompteDébit": [120],
                "CompteCrédit": [401],
                "Année": [2026],
            }
        )

        normalized = coerce_journal_dtypes(df)
        normalized.iloc[0, normalized.columns.get_loc("CompteDébit")] = "120"
        normalized.iloc[0, normalized.columns.get_loc("Année")] = "2026"

        self.assertEqual(normalized.loc[0, "CompteDébit"], "120")
        self.assertEqual(normalized.loc[0, "Année"], "2026")
        self.assertEqual(normalized["MontantDébit"].dtype.kind, "f")


if __name__ == "__main__":
    unittest.main()
