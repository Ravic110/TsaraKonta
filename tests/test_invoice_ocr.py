"""Tests de parsing OCR facture (sans moteur OCR externe)."""

import unittest

from services.invoice_ocr import parse_invoice_text


class TestInvoiceOCRParsing(unittest.TestCase):
    def test_parse_invoice_text_with_ttc_total(self):
        sample = """
        ACME SARL
        FACTURE N: FAC-2026-0012
        Date: 14/02/2026
        Objet: Fournitures bureau
        Total TTC : 1 234,56 MGA
        """
        data = parse_invoice_text(sample)
        self.assertEqual(data["date"], "14/02/2026")
        self.assertAlmostEqual(data["montant_debit"], 1234.56)
        self.assertEqual(data["compte_debit"], "607")
        self.assertEqual(data["compte_credit"], "401")
        self.assertIn("FAC-2026-0012", data["libelle"])
        self.assertIn("ACME SARL", data["libelle"])
        self.assertIn("Fournitures bureau", data["libelle"])
        self.assertGreaterEqual(data["confidence_score"], 0.8)
        self.assertFalse(data["needs_review"])

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
        self.assertGreaterEqual(data["confidence_score"], 0.8)

    def test_parse_invoice_text_supports_french_month_name(self):
        sample = """
        BOUTIQUE TEST
        Facture n° FAC-2026-77
        Date: 5 février 2026
        Net à payer : 550,00 MGA
        """
        data = parse_invoice_text(sample)
        self.assertEqual(data["date"], "05/02/2026")
        self.assertAlmostEqual(data["montant_debit"], 550.0)
        self.assertFalse(data["needs_review"])
        self.assertEqual(data["currency"], "MGA")

    def test_parse_invoice_text_flags_low_confidence(self):
        sample = """
        Prestataire inconnu
        Date 2026-01-10
        Montant: 120.00
        """
        data = parse_invoice_text(sample)
        self.assertTrue(data["needs_review"])
        self.assertLess(data["confidence_score"], 0.75)
        self.assertGreater(len(data["parse_warnings"]), 0)

    def test_parse_invoice_text_extracts_tax_breakdown(self):
        sample = """
        ACME
        Facture N: FAC-99
        Date: 10/02/2026
        Total HT : 100,00 EUR
        TVA 20% : 20,00 EUR
        Total TTC : 120,00 EUR
        """
        data = parse_invoice_text(sample)
        self.assertAlmostEqual(data["montant_debit"], 120.0)
        self.assertAlmostEqual(data["montant_ht"], 100.0)
        self.assertAlmostEqual(data["montant_tva"], 20.0)
        self.assertAlmostEqual(data["montant_ttc"], 120.0)
        self.assertEqual(data["currency"], "EUR")
        self.assertEqual(data["supplier_name"], "ACME")

    def test_parse_invoice_text_ignores_implausible_large_values(self):
        sample = """
        FACTURE
        Date: 12/02/2026
        Total TTC : 85 304 112 019 011 340 MGA
        Net à payer: 12 500,00 MGA
        """
        data = parse_invoice_text(sample)
        self.assertAlmostEqual(data["montant_debit"], 12500.0)

    def test_parse_invoice_text_picks_supplier_when_first_line_is_generic(self):
        sample = """
        FACTURE
        TSARA SERVICES SARL
        Date: 10/02/2026
        Description: Maintenance mensuelle
        Total TTC : 80 000 MGA
        """
        data = parse_invoice_text(sample)
        self.assertEqual(data["supplier_name"], "TSARA SERVICES SARL")
        self.assertIn("TSARA SERVICES SARL", data["libelle"])
        self.assertIn("Maintenance mensuelle", data["libelle"])

    def test_parse_invoice_text_raises_when_no_amount(self):
        sample = "Facture test\nDate: 01/01/2026\nAucun montant ici"
        with self.assertRaises(ValueError):
            parse_invoice_text(sample)


if __name__ == "__main__":
    unittest.main()
