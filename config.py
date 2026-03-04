"""
Configuration centralisée de l'application comptable
"""
import os

CONFIG = {
    'base_dir': os.path.dirname(os.path.abspath(__file__)),
    'fichier_defaut': os.path.join("EtatFiFolder", "LivreCompta.xlsx"),
    'fichier_pcg': "pcg.xlsx",
    'feuille_journal': "Journal",
    'feuille_pcg': "pcg",
    'colonnes_journal': ['Date', 'Libellé', 'DateValeur', 'MontantDébit', 'MontantCrédit', 
                        'CompteDébit', 'CompteCrédit', 'Année'],
    'largeurs_colonnes': {
        'Libellé': 200, 
        'DateValeur': 100, 
        'Date': 100, 
        'MontantDébit': 120, 
        'MontantCrédit': 120, 
        'CompteDébit': 100, 
        'CompteCrédit': 100
    },
    'etats_financiers': [
        "Bilan actif", 
        "Bilan passif", 
        "Compte de résultat par nature",
        "Compte de résultat par fonction", 
        "Tableau de flux de trésorerie (méthode directe)",
        "Tableau de flux de trésorerie (méthode indirecte)", 
        "Etat de variation des capitaux propres"
    ]
}
