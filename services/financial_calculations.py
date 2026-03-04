"""Calculs financiers metier reutilisables, independants des ecrans UI."""

from typing import Callable, Iterable


Prefixes = Iterable[str]
SumFn = Callable[[Prefixes], float]


def compute_resultat_net_exercice(
    sum_charge: SumFn,
    sum_produit: SumFn,
    charges_personnel_prefixes: Prefixes | None = None,
) -> float:
    """Calcule le resultat net de l'exercice via fonctions de somme injectees."""
    chiffres_affaires = sum_produit(['70', '701', '702', '703', '705', '706', '707', '708', '7082', '7083', '7085', '7086', '7088'])
    production_stockee = sum_produit(['71', '711', '713', '714'])
    production_immobilisee = sum_produit(['72', '721', '722'])

    achat_consommes = sum_charge(['60', '601', '602', '6022', '6023', '60231', '60232', '60237', '60221', '60222', '60223', '60225', '603', '6031', '6032', '6037', '604', '605', '606', '6061', '6062', '6063', '6064', '6068', '607', '608'])
    services_exterieurs = sum_charge(['61', '611', '612', '613', '6132', '6135', '6136', '614', '615', '616', '617', '618', '62', '621', '622', '623', '624', '6241', '6242', '625', '626', '627', '628'])
    charges_personnel = sum_charge(list(charges_personnel_prefixes or ['64', '641', '644', '645', '646', '647', '648']))
    impots_taxes = sum_charge(['63', '631', '635'])

    autres_produits = sum_produit(['74', '741', '748', '75', '751', '752', '753', '754', '755', '756', '757', '758'])
    autres_charges = sum_charge(['65', '651', '652', '653', '654', '655', '656', '657', '658'])

    dotations = sum_charge(['68', '681', '685'])
    produits_financiers = sum_produit(['76', '761', '762', '763', '764', '766', '767', '768'])
    charges_financieres = sum_charge(['66', '661', '664', '665', '666', '667', '668'])

    extra_produits = sum_produit(['77'])
    extra_charges = sum_charge(['67'])

    impots_exigibles = sum_charge(['69', '695', '698'])
    impots_differes = sum_charge(['692', '693'])

    production_exercice = chiffres_affaires + production_stockee + production_immobilisee
    consommation_exercice = achat_consommes + services_exterieurs
    valeur_ajoutee = production_exercice - consommation_exercice
    excedent_brut_exploitation = valeur_ajoutee - charges_personnel - impots_taxes
    resultat_operationnel = autres_produits - autres_charges
    resultat_financier = produits_financiers - charges_financieres
    resultat_avant_impot = excedent_brut_exploitation - dotations + resultat_operationnel + resultat_financier
    resultat_extraordinaire = extra_produits - extra_charges
    return resultat_avant_impot - impots_exigibles + impots_differes + resultat_extraordinaire
