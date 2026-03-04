"""
Gestion des données Excel et du Plan Comptable Général
"""
import os
import pandas as pd
from tkinter import messagebox
from config import CONFIG


class DataManager:
    """Gestion des données Excel - chargement et sauvegarde"""

    @staticmethod
    def journal_candidates():
        """Retourne les chemins candidats pour le journal comptable."""
        base_dir = CONFIG.get('base_dir') or os.path.dirname(os.path.dirname(__file__))
        configured = CONFIG.get('fichier_defaut') or "LivreCompta.xlsx"

        candidates = [
            configured if os.path.isabs(configured) else os.path.join(base_dir, configured),
            os.path.join(base_dir, "LivreCompta.xlsx"),
            os.path.join(base_dir, "EtatFiFolder", "LivreCompta.xlsx"),
        ]

        ordered = []
        seen = set()
        for path in candidates:
            norm = os.path.normpath(path)
            if norm not in seen:
                seen.add(norm)
                ordered.append(path)
        return ordered

    @staticmethod
    def resolve_journal_file():
        """Retourne le meilleur fichier journal disponible.

        Priorite:
        - fichier existant contenant des ecritures dans la feuille Journal
        - sinon premier fichier existant
        - sinon chemin configure
        """
        candidates = DataManager.journal_candidates()
        existing = []
        for fichier in candidates:
            if os.path.exists(fichier):
                existing.append(fichier)

        if not existing:
            return candidates[0] if candidates else None

        best_file = None
        best_rows = -1
        for fichier in existing:
            try:
                df = DataManager.charger_feuille(fichier, CONFIG['feuille_journal'])
                rows = len(df) if df is not None else 0
            except Exception:
                rows = 0

            if rows > best_rows:
                best_rows = rows
                best_file = fichier

        return best_file if best_file else existing[0]
    
    @staticmethod
    def charger_feuille(fichier, feuille):
        """
        Charge une feuille Excel spécifique
        
        Args:
            fichier: chemin du fichier Excel
            feuille: nom de la feuille
            
        Returns:
            DataFrame ou None si erreur
        """
        if not os.path.exists(fichier):
            return None
        try:
            xl_file = pd.ExcelFile(fichier)
            if feuille in xl_file.sheet_names:
                return pd.read_excel(fichier, sheet_name=feuille)
            return None
        except Exception as e:
            print(f"Erreur lecture {feuille}: {e}")
            return None
    
    @staticmethod
    def sauvegarder_df(df, fichier, feuille):
        """
        Sauvegarde un DataFrame dans une feuille Excel
        
        Args:
            df: DataFrame à sauvegarder
            fichier: chemin du fichier Excel
            feuille: nom de la feuille
            
        Returns:
            True si succès, False sinon
        """
        try:
            folder = os.path.dirname(fichier)
            if folder:
                os.makedirs(folder, exist_ok=True)

            if os.path.exists(fichier):
                with pd.ExcelWriter(fichier, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df.to_excel(writer, sheet_name=feuille, index=False)
            else:
                df.to_excel(fichier, sheet_name=feuille, index=False)
            return True
        except PermissionError:
            messagebox.showerror("Erreur", "FERMEZ EXCEL avant de sauvegarder !")
            return False
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur sauvegarde: {str(e)}")
            return False

    @staticmethod
    def append_row_to_sheet(fichier, feuille, row_dict):
        """Ajoute une ligne dans une feuille Excel en conservant les données existantes."""
        existing = DataManager.charger_feuille(fichier, feuille)
        if existing is None:
            existing = pd.DataFrame()
        row_df = pd.DataFrame([row_dict])
        combined = pd.concat([existing, row_df], ignore_index=True)
        return DataManager.sauvegarder_df(combined, fichier, feuille)


class PCGManager:
    """Gestion du Plan Comptable Général"""
    
    @staticmethod
    def charger_pcg(fichier=None):
        """
        Charge le Plan Comptable Général depuis Excel
        
        Args:
            fichier: chemin du fichier Excel contenant le PCG
            
        Returns:
            tuple: (liste_comptes, liste_numeros, dict_comptes)
        """
        pcg_comptes = []
        pcg_numeros = []
        pcg_dict = {}
        
        # Prefer a dedicated PCG file if configured, otherwise fall back to the provided file
        pcg_df = None
        pcg_file = CONFIG.get('fichier_pcg')
        if pcg_file and os.path.exists(pcg_file):
            pcg_df = DataManager.charger_feuille(pcg_file, CONFIG['feuille_pcg'])

        if pcg_df is None and fichier:
            # fallback: try the provided file (ex: journal comptable)
            pcg_df = DataManager.charger_feuille(fichier, CONFIG['feuille_pcg'])
        
        if pcg_df is not None and len(pcg_df.columns) >= 2:
            col_numero = pcg_df.columns[0]
            col_libelle = pcg_df.columns[1]
            
            for _, row in pcg_df.iterrows():
                numero = str(row[col_numero]).strip()
                libelle = str(row[col_libelle]).strip()
                
                if numero and libelle:
                    affichage = f"{numero} - {libelle}"
                    pcg_comptes.append(affichage)
                    pcg_numeros.append(numero)
                    pcg_dict[numero] = libelle
            
            print(f"✅ PCG chargé: {len(pcg_comptes)} comptes")
        else:
            print("ℹ️ PCG vide - saisie manuelle autorisée")
        
        return pcg_comptes, pcg_numeros, pcg_dict
