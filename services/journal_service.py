"""Services de lecture journal comptable reutilisables hors UI."""

from __future__ import annotations

import pandas as pd

from config import CONFIG
from models.data import DataManager


def empty_journal_df() -> pd.DataFrame:
    return pd.DataFrame(columns=CONFIG['colonnes_journal'])


def load_journal_dataframe(df_fallback: pd.DataFrame | None = None) -> pd.DataFrame:
    """Charge le journal depuis la source configuree, sinon fallback fourni."""
    journal_file = DataManager.resolve_journal_file()
    if journal_file:
        df = DataManager.charger_feuille(journal_file, CONFIG['feuille_journal'])
        if df is not None:
            return df

    if df_fallback is not None:
        return df_fallback
    return empty_journal_df()


def extract_years(df: pd.DataFrame, start_year: int = 2020, end_year: int = 2030) -> list[str]:
    """Retourne les annees triees desc en combinant bornes fixes + donnees journal."""
    annees_data = df['Année'].dropna().astype(str).unique().tolist() if 'Année' in df.columns else []
    annees_fixes = [str(y) for y in range(start_year, end_year + 1)]
    toutes_annees = set(annees_fixes) | set(annees_data)

    def _sort_key(v):
        try:
            return int(v)
        except Exception:
            return -9999

    return sorted(toutes_annees, key=_sort_key, reverse=True)
