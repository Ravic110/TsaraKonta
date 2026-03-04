# Audit Technique Complet - TsaraKonta

Date de l'audit: 2026-03-03

## 1) Perimetre analyse

- Analyse statique du code Python (`models/`, `ui/`, `utils/`, `tools/`, `main.py`, `config.py`, `README.md`)
- Verification structure/repertoires et configuration
- Verification execution: compilation Python et script de test existant

## 2) Vue d'ensemble du projet

- Type: application desktop Tkinter pour gestion comptable + editions d'etats financiers
- Taille code Python: 5 135 lignes
- Organisation:
  - `models/`: acces donnees Excel + PCG
  - `ui/`: ecrans metier (journal, bilan, resultats, flux, ratios, settings)
  - `utils/`: formatage et exports Excel/PDF
  - `tools/`: scripts utilitaires
- Donnees: fichiers `.xlsx` et mappings CSV dans `EtatFiFolder/`

## 3) Verification technique executee

- `python3 -m compileall -q .` -> OK (0 erreur de syntaxe)
- `python3 docs/guides/import_smoke_tests.py` -> echecs imports si environnement global sans dependances (`pandas` absent)
- `./.venv/bin/python docs/guides/import_smoke_tests.py` -> imports OK, structure OK, config OK
- Ecart detecte dans tests utilitaires:
  - `format_montant(1234.56)` renvoie `1 234.56` (point decimal), alors que le projet manipule majoritairement le format francais a virgule

## 4) Points forts

- Architecture modulaire claire (separation `models/ui/utils`)
- Couverture fonctionnelle metier riche (journal + plusieurs etats financiers + ratios + exports)
- Code defensif present sur la lecture de fichiers et creation des repertoires
- Workflow utilisateur complet (saisie, edition, suppression, export)

## 5) Risques et constats majeurs

### Critique

1. Incoherence de format monetaire (risque de mauvaise interpretation comptable)
   - Reference: `utils/formatters.py:16`
   - `format_montant()` conserve le point decimal (`1 234.56`) alors que le parseur attend aussi la virgule.
   - Impact: confusion utilisateur, incoherence entre vues et saisies.

### Eleve

1. Couplage fort a Windows (`os.startfile`)
   - References: `ui/comptabilite_app.py:62`, `ui/etat_resultat.py:341`, `ui/etat_resultat.py:348`, `ui/flux_tresorerie_direct.py:552`, `ui/flux_tresorerie_indirect.py:512`
   - Impact: fonctionnalites "ouvrir dossier/fichier" non portables Linux/macOS.

2. Exceptions larges et silencieuses
   - References: `ui/etat_resultat.py:210`, `ui/etat_resultat.py:220` (`except:`), et plusieurs `except Exception` dans `ui/`, `utils/`.
   - Impact: erreurs metier masquees, diagnostic difficile.

3. `sys.path.insert` dans les modules UI
   - References: `ui/comptabilite_app.py:11`, `ui/journal_dialogs.py:11`
   - Impact: imports fragiles selon le mode d'execution; dette technique packaging.

### Moyen

1. Incoherence de source de fichier principal
   - `config.py:6` (`EtatFidata.xlsx`) vs `ui/comptabilite_app.py:33` (`LivreCompta.xlsx`)
   - Impact: comportement inattendu selon le point d'entree.

2. `.gitignore` ignore tous les CSV (`*.csv`)
   - Reference: `.gitignore:107`
   - Impact: les mappings metier (`EtatFiFolder/mapping_*.csv`) risquent d'etre non versionnes alors qu'ils portent la logique comptable.

3. Taille et complexite de certains modules UI (>500 lignes)
   - `ui/bilan_passif.py`, `ui/flux_tresorerie_direct.py`, `ui/flux_tresorerie_indirect.py`, `ui/ratios.py`
   - Impact: maintenance difficile, regression probable lors des evolutions.

## 6) Dette qualite / tests

- Pas de suite de tests automatises standard (`pytest`) pour les calculs metier critiques.
- `docs/guides/import_smoke_tests.py` verifie principalement les imports et la presence des fichiers, pas la validite des formules comptables.
- Plusieurs formules longues hardcodees dans les fenetres UI (couplage interface + logique metier).

## 7) Priorites recommandees

1. Corriger `format_montant()` pour un format coherent (virgule decimale) et ajouter tests unitaires associes.
2. Extraire la logique comptable (calculs bilans/resultats/flux/ratios) vers un module service dedie, testable hors UI.
3. Remplacer `os.startfile` par une fonction cross-platform (`xdg-open`/`open`/`start` selon OS).
4. Remplacer `except:` par des exceptions ciblees + logs explicites.
5. Unifier la configuration du fichier principal via `CONFIG` et retirer les valeurs dupliquees.
6. Revoir la regle `*.csv` dans `.gitignore` pour versionner les mappings metier.

## 8) Conclusion

Le projet est fonctionnel et deja bien structure pour une application Tkinter metier. Le risque principal porte sur la fiabilite des calculs et leur maintenabilite (logique dense dans l'UI, peu de tests metier). Une phase de stabilisation orientee qualite (tests unitaires + factorisation logique + robustesse multiplateforme) est recommande avant toute extension majeure.
