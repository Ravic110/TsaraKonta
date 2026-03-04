"""Tests unitaires pour les calculs financiers partages."""

import unittest

from services.financial_calculations import compute_resultat_net_exercice


class TestFinancialCalculations(unittest.TestCase):
    def test_compute_resultat_net_exercice_nominal_case(self):
        charges = {
            '60': 400.0,
            '61': 100.0,
            '64': 200.0,
            '63': 50.0,
            '65': 40.0,
            '68': 30.0,
            '66': 10.0,
            '67': 2.0,
            '69': 60.0,
            '692': 3.0,
        }
        produits = {
            '70': 1000.0,
            '71': 100.0,
            '72': 50.0,
            '74': 80.0,
            '76': 20.0,
            '77': 5.0,
        }

        def sum_charge(prefixes):
            return sum(charges.get(p, 0.0) for p in prefixes)

        def sum_produit(prefixes):
            return sum(produits.get(p, 0.0) for p in prefixes)

        self.assertEqual(compute_resultat_net_exercice(sum_charge, sum_produit), 366.0)

    def test_compute_resultat_net_exercice_supports_personnel_override(self):
        charges = {'644': 10.0}

        def sum_charge(prefixes):
            return sum(charges.get(p, 0.0) for p in prefixes)

        def sum_produit(prefixes):
            return 0.0

        base = compute_resultat_net_exercice(sum_charge, sum_produit)
        with_duplicate = compute_resultat_net_exercice(
            sum_charge,
            sum_produit,
            charges_personnel_prefixes=['644', '644'],
        )

        self.assertEqual(base, -10.0)
        self.assertEqual(with_duplicate, -20.0)


if __name__ == "__main__":
    unittest.main()
