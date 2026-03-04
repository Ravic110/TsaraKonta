"""Unit tests for monetary and account formatting helpers."""

import unittest

from utils.formatters import extraire_numero_compte, format_montant, parse_montant


class TestFormatters(unittest.TestCase):
    def test_format_montant_uses_french_decimal_separator(self):
        self.assertEqual(format_montant(1234.56), "1 234,56")

    def test_format_montant_handles_negative_values(self):
        self.assertEqual(format_montant(-42.5), "-42,50")

    def test_parse_montant_accepts_french_format(self):
        self.assertEqual(parse_montant("1 234,56"), 1234.56)

    def test_parse_montant_empty_returns_zero(self):
        self.assertEqual(parse_montant("   "), 0.0)

    def test_extraire_numero_compte_with_label(self):
        self.assertEqual(extraire_numero_compte("401 - Client"), "401")

    def test_extraire_numero_compte_without_label(self):
        self.assertEqual(extraire_numero_compte("512"), "512")


if __name__ == "__main__":
    unittest.main()
