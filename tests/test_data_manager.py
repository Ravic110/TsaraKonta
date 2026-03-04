"""Tests DataManager pour sauvegarde multi-feuilles et append."""

import os
import tempfile
import unittest

import pandas as pd

from models.data import DataManager


class TestDataManager(unittest.TestCase):
    def test_sauvegarder_df_preserves_other_sheets(self):
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = os.path.join(tmp, "book.xlsx")
            with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
                pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="Sheet1", index=False)
                pd.DataFrame({"B": [2]}).to_excel(writer, sheet_name="Other", index=False)

            ok = DataManager.sauvegarder_df(pd.DataFrame({"A": [3]}), xlsx, "Sheet1")
            self.assertTrue(ok)

            with pd.ExcelFile(xlsx) as xl:
                self.assertIn("Sheet1", xl.sheet_names)
                self.assertIn("Other", xl.sheet_names)
            df1 = pd.read_excel(xlsx, sheet_name="Sheet1")
            dfo = pd.read_excel(xlsx, sheet_name="Other")
            self.assertEqual(df1.iloc[0]["A"], 3)
            self.assertEqual(dfo.iloc[0]["B"], 2)

    def test_append_row_to_sheet_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = os.path.join(tmp, "book.xlsx")
            with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
                pd.DataFrame({"k": ["x"]}).to_excel(writer, sheet_name="OCR_Imports", index=False)

            ok = DataManager.append_row_to_sheet(xlsx, "OCR_Imports", {"k": "y"})
            self.assertTrue(ok)

            df = pd.read_excel(xlsx, sheet_name="OCR_Imports")
            self.assertEqual(len(df), 2)
            self.assertEqual(df.iloc[1]["k"], "y")


if __name__ == "__main__":
    unittest.main()
