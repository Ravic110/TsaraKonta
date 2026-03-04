"""Helpers OCR pour extraire des informations de facture."""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime

from utils.logging_config import get_app_logger

logger = get_app_logger(__name__)
_EASYOCR_READER = None


def _find_tesseract_binary() -> str | None:
    """Trouve le binaire tesseract via PATH puis emplacements systeme classiques."""
    in_path = shutil.which("tesseract")
    if in_path and os.path.exists(in_path):
        return in_path

    candidates = [
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/snap/bin/tesseract",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def _normalize_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", (text or "")).strip()


def _parse_amount(raw: str) -> float | None:
    cleaned = (raw or "").replace("\u00a0", " ").strip()
    cleaned = cleaned.replace(" ", "").replace(",", ".")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_invoice_number(text: str) -> str | None:
    patterns = [
        r"(?:facture|invoice)\s*(?:n[o°]*|no|number)?\s*[:#]?\s*([A-Z0-9\-\/]+)",
        r"(?:ref(?:erence)?|réf(?:érence)?)\s*[:#]?\s*([A-Z0-9\-\/]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _normalize_spaces(match.group(1))
    return None


def _extract_invoice_date(text: str) -> str:
    patterns = [
        r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
        r"\b(\d{4}[/-]\d{2}[/-]\d{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw = match.group(1)
        try:
            if raw[4] in "-/" and raw[:4].isdigit():
                dt = datetime.strptime(raw.replace("/", "-"), "%Y-%m-%d")
            else:
                dt = datetime.strptime(raw.replace("-", "/"), "%d/%m/%Y")
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return datetime.now().strftime("%d/%m/%Y")


def _extract_total_amount(text: str) -> float | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    priority_keywords = [
        "total ttc",
        "montant ttc",
        "net a payer",
        "net à payer",
        "amount due",
        "total due",
        "total",
    ]

    for keyword in priority_keywords:
        for line in lines:
            low = line.lower()
            if keyword not in low:
                continue
            candidates = re.findall(r"-?\d[\d\s.,]*\d|-?\d", line)
            for candidate in reversed(candidates):
                value = _parse_amount(candidate)
                if value is not None and value > 0:
                    return value

    # fallback prudent: lignes contenant un contexte monetaire
    money_hints = ["mga", "ar", "eur", "usd", "$", "ttc", "total", "payer", "due", "montant"]
    fallback_values = []
    for line in lines:
        low = line.lower()
        if not any(hint in low for hint in money_hints):
            continue
        candidates = re.findall(r"-?\d[\d\s.,]*\d|-?\d", line)
        for candidate in candidates:
            value = _parse_amount(candidate)
            if value is not None and value > 0:
                fallback_values.append(value)
    return max(fallback_values) if fallback_values else None


def parse_invoice_text(text: str) -> dict:
    """Parse texte OCR et renvoie les champs utiles pour pre-remplir une ecriture."""
    cleaned = text or ""
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    first_line = _normalize_spaces(lines[0]) if lines else "Facture"

    invoice_no = _extract_invoice_number(cleaned)
    invoice_date = _extract_invoice_date(cleaned)
    amount = _extract_total_amount(cleaned)

    if amount is None:
        raise ValueError("Montant introuvable dans la facture OCR.")

    label_parts = ["Facture"]
    if invoice_no:
        label_parts.append(invoice_no)
    label_parts.append(first_line[:40])
    label = " - ".join(label_parts)

    year = invoice_date[-4:] if len(invoice_date) >= 4 else datetime.now().strftime("%Y")

    return {
        "date": invoice_date,
        "date_valeur": invoice_date,
        "montant_debit": amount,
        "montant_credit": 0.0,
        "compte_debit": "607",
        "compte_credit": "401",
        "annee": year,
        "libelle": label[:120],
        "invoice_number": invoice_no or "",
        "source_hint": first_line[:120],
    }


def _ocr_image(image):
    try:
        return _ocr_image_easyocr(image)
    except Exception as exc:
        logger.warning("EasyOCR indisponible (%s), tentative Tesseract.", exc)

    try:
        import pytesseract  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on runtime
        logger.exception("pytesseract indisponible apres echec EasyOCR.")
        raise RuntimeError(
            "EasyOCR et pytesseract indisponibles.\n"
            "Installez EasyOCR (recommande):\n"
            "  pip install easyocr\n"
            "Ou installez Tesseract systeme:\n"
            "  sudo apt-get install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng\n"
        ) from exc

    tesseract_bin = _find_tesseract_binary()
    if not tesseract_bin:
        logger.error("Binaire tesseract introuvable apres echec EasyOCR.")
        raise RuntimeError(
            "EasyOCR indisponible et binaire tesseract introuvable.\n"
            "Installez EasyOCR (recommande):\n"
            "  pip install easyocr\n"
            "Ou installez Tesseract systeme:\n"
            "  sudo apt-get install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng\n"
        )

    pytesseract.pytesseract.tesseract_cmd = tesseract_bin
    logger.info("Binaire tesseract utilise: %s", tesseract_bin)

    try:
        return pytesseract.image_to_string(image, lang="fra+eng")
    except Exception as exc:
        logger.warning("OCR Tesseract fra+eng echoue (%s), tentative sans langue explicite.", exc)
        try:
            return pytesseract.image_to_string(image)
        except Exception as exc2:
            logger.exception("OCR Tesseract echoue completement apres echec EasyOCR.")
            raise RuntimeError(
                "Aucun moteur OCR exploitable.\n"
                "Installez EasyOCR (recommande):\n"
                "  pip install easyocr\n"
                "Ou verifiez votre installation Tesseract:\n"
                "  which tesseract && tesseract --version\n"
            ) from exc2


def _ocr_image_easyocr(image):
    global _EASYOCR_READER
    try:
        import easyocr  # type: ignore
    except Exception as exc:
        logger.exception("EasyOCR indisponible.")
        raise RuntimeError(
            "Aucun moteur OCR disponible.\n"
            "Option 1 (recommandee):\n"
            "  pip install easyocr\n"
            "Option 2 (Linux systeme):\n"
            "  sudo apt-get install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng\n"
        ) from exc

    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        logger.exception("Numpy indisponible pour EasyOCR.")
        raise RuntimeError("Le module 'numpy' est requis pour EasyOCR.") from exc

    if _EASYOCR_READER is None:
        logger.info("Initialisation EasyOCR reader (langues: fr,en).")
        _EASYOCR_READER = easyocr.Reader(['fr', 'en'], gpu=False)

    np_image = np.array(image)
    results = _EASYOCR_READER.readtext(np_image, detail=0, paragraph=True)
    text = "\n".join([str(x) for x in results if str(x).strip()])
    logger.info("OCR EasyOCR termine: %d caracteres", len(text))
    return text


def extract_text_from_file(path: str) -> str:
    """Extrait du texte OCR depuis une image ou un PDF."""
    logger.info("Demarrage OCR fichier: %s", path)
    if not os.path.exists(path):
        logger.error("Fichier OCR introuvable: %s", path)
        raise FileNotFoundError(path)

    ext = os.path.splitext(path.lower())[1]
    if ext in [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"]:
        try:
            from PIL import Image  # type: ignore
        except Exception as exc:
            logger.exception("Lecture image impossible: Pillow indisponible.")
            raise RuntimeError("Le module 'Pillow' est requis pour lire les images.") from exc
        with Image.open(path) as image:
            text = _ocr_image(image)
            logger.info("OCR image termine (%s): %d caracteres", ext, len(text or ""))
            return text

    if ext == ".pdf":
        try:
            import pypdfium2 as pdfium  # type: ignore
        except Exception as exc:
            logger.exception("Lecture PDF OCR impossible: pypdfium2 indisponible.")
            raise RuntimeError(
                "Pour OCR PDF, installez 'pypdfium2' (ou utilisez une image JPG/PNG)."
            ) from exc

        text_chunks = []
        pdf = pdfium.PdfDocument(path)
        page_count = len(pdf)
        max_pages = min(page_count, 3)
        logger.info("OCR PDF detecte: %d pages (analyse %d pages max).", page_count, max_pages)
        for idx in range(max_pages):
            page = pdf[idx]
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            text_chunks.append(_ocr_image(pil_image))
            page.close()
        pdf.close()
        text = "\n".join(text_chunks)
        logger.info("OCR PDF termine: %d caracteres extraits", len(text or ""))
        return text

    logger.error("Format facture non supporte: %s", ext)
    raise ValueError("Format non supporte. Utilisez une image (PNG/JPG) ou un PDF.")


def extract_invoice_data_from_file(path: str) -> dict:
    """OCR complet + parsing facture."""
    try:
        text = extract_text_from_file(path)
        parsed = parse_invoice_text(text)
        parsed["ocr_text"] = text
        logger.info(
            "Facture OCR parsee: date=%s montant=%s libelle=%s",
            parsed.get("date"),
            parsed.get("montant_debit"),
            parsed.get("libelle"),
        )
        return parsed
    except Exception:
        logger.exception("Echec OCR facture pour le fichier: %s", path)
        raise
