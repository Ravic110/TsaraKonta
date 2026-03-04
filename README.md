## Application Comptable Refactorisée

### 📁 Structure du Projet

```
apifactorise_refactored/
├── config.py                      # Configuration centralisée
├── main.py                        # Point d'entrée de l'application
│
├── models/                        # Gestion des données
│   ├── __init__.py
│   └── data.py                   # DataManager, PCGManager
│
├── ui/                           # Interface utilisateur
│   ├── __init__.py
│   ├── comptabilite_app.py       # ComptabiliteApp (interface principale)
│   └── journal_dialogs.py        # DialogueLigne (dialogue d'édition)
│
├── services/                     # Logique metier/testable
│   ├── journal_service.py
│   ├── financial_calculations.py
│   └── invoice_ocr.py
│
├── docs/
│   ├── guides/                   # Guides et scripts de reference
│   └── audit/                    # Rapports d'audit technique
│
└── utils/                        # Fonctions utilitaires
    ├── __init__.py
    └── formatters.py             # Formatage et parsing de données
```

### 🎯 Objectifs de la Refactorisation

1. **Séparation des préoccupations** : Code organisé en modules logiques
2. **Réutilisabilité** : Les composants peuvent être importés indépendamment
3. **Maintenabilité** : Chaque module a une responsabilité unique
4. **Testabilité** : Les classes et fonctions sont plus faciles à tester

### 📋 Description des Modules

#### **config.py**
Configuration centralisée de l'application :
- Chemin du fichier Excel par défaut
- Noms des feuilles Excel
- Colonnes du journal
- États financiers disponibles
- Largeurs des colonnes dans l'interface

#### **models/data.py**
Gestion complète des données Excel :
- `DataManager` : Lecture/écriture de feuilles Excel
- `PCGManager` : Gestion du Plan Comptable Général

#### **ui/comptabilite_app.py**
Interface principale comptable :
- `ComptabiliteApp` : Application Tkinter complète
  - Menu Fichier et États Financiers
  - Tableau des écritures
  - Barres de recherche et statistiques
  - Actions : Ajouter, Modifier, Supprimer, Balance

#### **ui/journal_dialogs.py**
Dialogues modaux :
- `DialogueLigne` : Dialogue pour créer/modifier une écriture
  - Champs de date, libellé, montants
  - Sélection de comptes avec autocomplétion
  - Validation des données

#### **utils/formatters.py**
Fonctions utilitaires :
- `format_montant()` : Formate un nombre pour l'affichage
- `parse_montant()` : Convertit une chaîne en montant
- `extraire_numero_compte()` : Extrait le numéro d'un compte

### 🚀 Utilisation

#### Lancer l'application
```bash
python main.py
```

### 🧾 OCR Factures

Une action `Fichier > Scanner facture (OCR)` permet d'importer une facture (image/PDF), extraire automatiquement date/montant/libelle, puis pre-remplir une ecriture comptable.

Prerequis OCR:
```bash
pip install -r requirements.txt
```
- Optionnel: installer le binaire systeme **Tesseract OCR** (commande `tesseract`) pour activer le fallback `pytesseract`.
- Le moteur par defaut est **EasyOCR** (installe via `pip install -r requirements.txt`).
- Tesseract reste disponible en fallback si EasyOCR est indisponible.
- Formats supportes: `PNG/JPG/...` et `PDF` (3 premieres pages).
- Pour PDF: extraction texte native + OCR de secours (meilleure robustesse sur PDF mixtes).
- L'ecran de previsualisation affiche un score de confiance OCR et des alertes de verification.

### ✅ Qualite code

Installer les outils dev:
```bash
pip install -r requirements-dev.txt
```

Executer les controles:
```bash
ruff check .
black --check .
python -m unittest discover -s tests -p "test_*.py"
```

#### Importer les modules individuels
```python
from models.data import DataManager, PCGManager
from config import CONFIG
from utils.formatters import format_montant, parse_montant

# Charger une feuille Excel
df = DataManager.charger_feuille("fichier.xlsx", "Journal")

# Charger le PCG
comptes, numeros, dict_comptes = PCGManager.charger_pcg("fichier.xlsx")

# Formater un montant
montant_affiche = format_montant(1234.56)  # "1 234,56"
```

### ✨ Avantages de cette Architecture

1. **Modulaire** : Chaque fichier a une responsabilité bien définie
2. **Extensible** : Facile d'ajouter de nouveaux états financiers ou fonctionnalités
3. **Testable** : Les modules peuvent être testés indépendamment
4. **Réutilisable** : Les utilitaires et managers peuvent être utilisés dans d'autres projets
5. **Maintenable** : Code bien organisé et documenté

### 📝 Notes d'Implémentation

- Les imports Python sont alignes sur la structure paquet (`ui/`, `services/`, `models/`, `utils/`)
- Les messages d'erreur Tkinter sont conservés pour l'expérience utilisateur
- La structure pandas est maintenue pour la compatibilité avec Excel
- Les commentaires docstring suivent la convention standard Python

### 🔄 Migration de l'Ancienne Version

Si vous aviez du code qui utilisait `apifactorise.py` directement, remplacez-le par :

```python
# Ancien
from apifactorise import ComptabiliteApp

# Nouveau
from ui.comptabilite_app import ComptabiliteApp
from models.data import DataManager, PCGManager
from config import CONFIG
```

Tous les éléments sont maintenant organisés en modules logiques mais conservent les mêmes signatures et comportements.
