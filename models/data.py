"""
Gestion des données Excel et du Plan Comptable Général
"""
import os
import re
import unicodedata
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

    @staticmethod
    def _normalize_column_name(name: str) -> str:
        text = unicodedata.normalize("NFKD", str(name or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower().strip()
        return re.sub(r"[^a-z0-9]+", "", text)

    @staticmethod
    def operation_settings_candidates(settings_file: str | None = None):
        """Retourne les chemins candidats du fichier de parametres operations."""
        base_dir = CONFIG.get('base_dir') or os.path.dirname(os.path.dirname(__file__))
        candidates = []
        if settings_file:
            candidates.append(settings_file)
        candidates.extend(
            [
                os.path.join(base_dir, "sittings.xlsx"),
                os.path.join(base_dir, "Sittings.xlsx"),
                os.path.join(base_dir, "Settings.xlsx"),
            ]
        )

        seen = set()
        ordered = []
        for path in candidates:
            norm = os.path.normpath(path)
            if norm not in seen:
                seen.add(norm)
                ordered.append(path)
        return ordered

    @staticmethod
    def resolve_operation_settings_file(settings_file: str | None = None):
        """Retourne le meilleur chemin pour le fichier de parametrage operations."""
        candidates = DataManager.operation_settings_candidates(settings_file)
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0] if candidates else None

    @staticmethod
    def load_operation_types_dataframe(settings_file: str | None = None):
        """Charge la table operations en DataFrame normalise.

        Colonnes attendues (variantes acceptees): TYPE OPERATION, DEBIT, CREDIT.
        """
        empty = pd.DataFrame(columns=["ID_PARAMETRE", "TYPE OPERATION", "DEBIT", "CREDIT"])
        for path in DataManager.operation_settings_candidates(settings_file):
            if not os.path.exists(path):
                continue
            try:
                xl = pd.ExcelFile(path)
            except Exception:
                continue

            for sheet_name in xl.sheet_names:
                try:
                    df = pd.read_excel(path, sheet_name=sheet_name)
                except Exception:
                    continue
                if df is None or df.empty:
                    continue

                normalized_cols = {
                    DataManager._normalize_column_name(col): col for col in df.columns
                }
                type_col = normalized_cols.get("typeoperation")
                debit_col = normalized_cols.get("debit")
                credit_col = normalized_cols.get("credit")
                id_col = normalized_cols.get("idparametre")

                if not type_col or not debit_col or not credit_col:
                    continue

                result = []
                for _, row in df.iterrows():
                    label = str(row.get(type_col, "") or "").strip()
                    if not label:
                        continue
                    result.append(
                        {
                            "id_parametre": str(row.get(id_col, "") or "").strip() if id_col else "",
                            "type_operation": label,
                            "debit": str(row.get(debit_col, "") or "").strip(),
                            "credit": str(row.get(credit_col, "") or "").strip(),
                        }
                    )
                if result:
                    normalized = pd.DataFrame(result).rename(
                        columns={
                            "id_parametre": "ID_PARAMETRE",
                            "type_operation": "TYPE OPERATION",
                            "debit": "DEBIT",
                            "credit": "CREDIT",
                        }
                    )
                    return normalized[["ID_PARAMETRE", "TYPE OPERATION", "DEBIT", "CREDIT"]], path
                return empty.copy(), path
        return empty.copy(), DataManager.resolve_operation_settings_file(settings_file)

    @staticmethod
    def save_operation_types_dataframe(df: pd.DataFrame, settings_file: str | None = None):
        """Sauvegarde la table operations dans le fichier de parametrage."""
        target = DataManager.resolve_operation_settings_file(settings_file)
        if not target:
            return False
        payload = df.copy()
        expected = ["ID_PARAMETRE", "TYPE OPERATION", "DEBIT", "CREDIT"]
        for col in expected:
            if col not in payload.columns:
                payload[col] = ""
        payload = payload[expected]
        return DataManager.sauvegarder_df(payload, target, "Feuil1")

    @staticmethod
    def load_operation_types(settings_file: str | None = None):
        """Charge les types d'operations depuis un fichier Excel de parametrage."""
        df, _path = DataManager.load_operation_types_dataframe(settings_file=settings_file)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.iterrows():
            result.append(
                {
                    "id_parametre": str(row.get("ID_PARAMETRE", "") or "").strip(),
                    "type_operation": str(row.get("TYPE OPERATION", "") or "").strip(),
                    "debit": str(row.get("DEBIT", "") or "").strip(),
                    "credit": str(row.get("CREDIT", "") or "").strip(),
                }
            )
        return result

    @staticmethod
    def resolve_pcg_file(pcg_file: str | None = None):
        """Retourne le chemin du fichier PCG."""
        base_dir = CONFIG.get('base_dir') or os.path.dirname(os.path.dirname(__file__))
        configured = pcg_file or CONFIG.get('fichier_pcg') or "pcg.xlsx"
        return configured if os.path.isabs(configured) else os.path.join(base_dir, configured)

    @staticmethod
    def load_pcg_dataframe(pcg_file: str | None = None):
        """Charge le PCG en DataFrame normalise (colonnes: NUMERO, LIBELLE)."""
        path = DataManager.resolve_pcg_file(pcg_file)
        empty = pd.DataFrame(columns=["NUMERO", "LIBELLE"])
        if not path or not os.path.exists(path):
            return empty.copy(), path
        df = DataManager.charger_feuille(path, CONFIG['feuille_pcg'])
        if df is None or df.empty or len(df.columns) < 2:
            return empty.copy(), path
        normalized = pd.DataFrame(
            {
                "NUMERO": df.iloc[:, 0].fillna("").astype(str).str.strip(),
                "LIBELLE": df.iloc[:, 1].fillna("").astype(str).str.strip(),
            }
        )
        normalized = normalized[(normalized["NUMERO"] != "") | (normalized["LIBELLE"] != "")]
        normalized = normalized.reset_index(drop=True)
        return normalized, path

    @staticmethod
    def save_pcg_dataframe(df: pd.DataFrame, pcg_file: str | None = None):
        """Sauvegarde le DataFrame PCG dans la feuille configuree."""
        target = DataManager.resolve_pcg_file(pcg_file)
        if not target:
            return False
        payload = df.copy()
        for col in ["NUMERO", "LIBELLE"]:
            if col not in payload.columns:
                payload[col] = ""
        payload = payload[["NUMERO", "LIBELLE"]]
        return DataManager.sauvegarder_df(payload, target, CONFIG['feuille_pcg'])


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
