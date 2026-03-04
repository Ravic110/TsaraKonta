"""Tests de parsing OCR facture (sans moteur OCR externe)."""

import unittest

from ui.invoice_ocr import parse_invoice_text


class TestInvoiceOCRParsing(unittest.TestCase):
    def test_parse_invoice_text_with_ttc_total(self):
        sample = """
        ACME SARL
        FACTURE N: FAC-2026-0012
        Date: 14/02/2026
        Total TTC : 1 234,56 MGA
        """
        data = parse_invoice_text(sample)
        self.assertEqual(data["date"], "14/02/2026")
        self.assertAlmostEqual(data["montant_debit"], 1234.56)
        self.assertEqual(data["compte_debit"], "607")
        self.assertEqual(data["compte_credit"], "401")
        self.assertIn("FAC-2026-0012", data["libelle"])

    def test_parse_invoice_text_fallback_largest_amount(self):
        sample = """
        Demo Shop
        Invoice # INV-44
        Date 2026-01-10
        Subtotal 100.00
        TVA 20.00
        Amount due 120.00
        """
        data = parse_invoice_text(sample)
        self.assertEqual(data["date"], "10/01/2026")
        self.assertAlmostEqual(data["montant_debit"], 120.0)

    def test_parse_invoice_text_raises_when_no_amount(self):
        sample = "Facture test\nDate: 01/01/2026\nAucun montant ici"
        with self.assertRaises(ValueError):
            parse_invoice_text(sample)


if __name__ == "__main__":
    unittest.main()
