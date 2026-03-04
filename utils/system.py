"""Utilitaires systeme multiplateforme."""

from __future__ import annotations

import os
import platform
import subprocess


def open_path(path: str) -> bool:
    """Ouvre un fichier ou dossier avec l'application systeme par defaut."""
    if not path or not os.path.exists(path):
        return False

    system = platform.system().lower()
    try:
        if system.startswith("windows"):
            os.startfile(path)  # type: ignore[attr-defined]
            return True
        if system == "darwin":
            return subprocess.call(["open", path]) == 0
        return subprocess.call(["xdg-open", path]) == 0
    except Exception:
        return False
