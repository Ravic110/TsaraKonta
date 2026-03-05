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

    def test_load_operation_types_from_settings_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = os.path.join(tmp, "sittings.xlsx")
            df = pd.DataFrame(
                {
                    "ID_PARAMETRE": [1, 2],
                    "TYPE OPERATION": ["ACHAT COMPTANT", "ACHAT A CREDIT"],
                    "DEBIT": [607, 607],
                    "CREDIT": [512, 401],
                }
            )
            with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Feuil1", index=False)

            ops = DataManager.load_operation_types(settings_file=xlsx)
            self.assertEqual(len(ops), 2)
            self.assertEqual(ops[0]["type_operation"], "ACHAT COMPTANT")
            self.assertEqual(ops[0]["debit"], "607")
            self.assertEqual(ops[0]["credit"], "512")

    def test_load_and_save_operation_types_dataframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = os.path.join(tmp, "sittings.xlsx")
            source = pd.DataFrame(
                {
                    "ID_PARAMETRE": ["1"],
                    "TYPE OPERATION": ["ACHAT COMPTANT"],
                    "DEBIT": ["607"],
                    "CREDIT": ["512"],
                }
            )
            with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
                source.to_excel(writer, sheet_name="Feuil1", index=False)

            loaded, loaded_path = DataManager.load_operation_types_dataframe(settings_file=xlsx)
            self.assertEqual(os.path.normpath(loaded_path), os.path.normpath(xlsx))
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded.iloc[0]["TYPE OPERATION"], "ACHAT COMPTANT")

            loaded.loc[0, "CREDIT"] = "401"
            ok = DataManager.save_operation_types_dataframe(loaded, settings_file=xlsx)
            self.assertTrue(ok)

            reloaded = pd.read_excel(xlsx, sheet_name="Feuil1")
            self.assertEqual(str(reloaded.iloc[0]["CREDIT"]), "401")

    def test_load_and_save_pcg_dataframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = os.path.join(tmp, "pcg.xlsx")
            source = pd.DataFrame(
                {
                    "Compte": ["401", "512"],
                    "Libelle": ["Fournisseurs", "Banque"],
                }
            )
            with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
                source.to_excel(writer, sheet_name="pcg", index=False)

            loaded, loaded_path = DataManager.load_pcg_dataframe(pcg_file=xlsx)
            self.assertEqual(os.path.normpath(loaded_path), os.path.normpath(xlsx))
            self.assertEqual(list(loaded.columns), ["NUMERO", "LIBELLE"])
            self.assertEqual(loaded.iloc[0]["NUMERO"], "401")
            self.assertEqual(loaded.iloc[1]["LIBELLE"], "Banque")

            loaded.loc[1, "LIBELLE"] = "Banque principale"
            ok = DataManager.save_pcg_dataframe(loaded, pcg_file=xlsx)
            self.assertTrue(ok)

            reloaded = pd.read_excel(xlsx, sheet_name="pcg")
            self.assertEqual(str(reloaded.iloc[1]["LIBELLE"]), "Banque principale")


if __name__ == "__main__":
    unittest.main()
