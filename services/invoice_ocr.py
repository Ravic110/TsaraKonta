"""Helpers OCR pour extraire des informations de facture."""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime

from utils.logging_config import get_app_logger

logger = get_app_logger(__name__)
_EASYOCR_READER = None
_AMOUNT_MIN = 0.01
_AMOUNT_MAX = 1_000_000_000.0

_FRENCH_MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}


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


def _is_plausible_amount(value: float | None) -> bool:
    if value is None:
        return False
    return _AMOUNT_MIN <= float(value) <= _AMOUNT_MAX


def _extract_currency(text: str) -> str:
    low = (text or "").lower()
    if "mga" in low or re.search(r"\bar\b", low):
        return "MGA"
    if "eur" in low or "€" in low:
        return "EUR"
    if "usd" in low or "$" in low:
        return "USD"
    return ""


def _extract_invoice_number(text: str) -> str | None:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    patterns = [
        r"(?:facture|invoice)[ \t]*(?:n[o°]*|no|number)?[ \t]*[:#]?[ \t]*([A-Z0-9][A-Z0-9\-\/]{1,})",
        r"(?:ref(?:erence)?|réf(?:érence)?)[ \t]*[:#]?[ \t]*([A-Z0-9][A-Z0-9\-\/]{1,})",
    ]
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                return _normalize_spaces(match.group(1))
    return None


def _is_generic_invoice_line(line: str) -> bool:
    low = (line or "").strip().lower()
    if not low:
        return True
    generic_markers = [
        "facture",
        "invoice",
        "date",
        "page",
        "client",
        "fournisseur",
        "total",
        "ttc",
        "ht",
        "tva",
        "net a payer",
        "net à payer",
    ]
    return any(marker in low for marker in generic_markers)


def _extract_supplier_name(lines: list[str]) -> str | None:
    for line in lines[:10]:
        normalized = _normalize_spaces(line)
        if len(normalized) < 3 or len(normalized) > 80:
            continue
        if re.search(r"\d", normalized):
            continue
        if _is_generic_invoice_line(normalized):
            continue
        return normalized
    return None


def _extract_invoice_subject(lines: list[str], supplier_name: str | None = None) -> str | None:
    subject_keywords = ["objet", "designation", "désignation", "description", "prestation", "achat"]
    for line in lines:
        normalized = _normalize_spaces(line)
        low = normalized.lower()
        if supplier_name and normalized.lower() == supplier_name.lower():
            continue
        if any(k in low for k in subject_keywords):
            parts = re.split(r"[:\-]", normalized, maxsplit=1)
            if len(parts) == 2:
                value = _normalize_spaces(parts[1])
                if len(value) >= 4:
                    return value
            if len(normalized) >= 6:
                return normalized

    for line in lines:
        normalized = _normalize_spaces(line)
        if len(normalized) < 8 or len(normalized) > 90:
            continue
        if supplier_name and normalized.lower() == supplier_name.lower():
            continue
        if _is_generic_invoice_line(normalized):
            continue
        if re.search(r"\d[\d\s.,]*", normalized):
            continue
        return normalized
    return None


def _build_invoice_label(invoice_no: str | None, supplier: str | None, subject: str | None, fallback_line: str) -> str:
    parts = ["Facture"]
    if invoice_no:
        parts.append(invoice_no)
    if supplier:
        parts.append(supplier[:40])
    if subject:
        parts.append(subject[:50])
    elif fallback_line:
        parts.append(fallback_line[:40])
    return " - ".join(parts)[:120]


def _extract_invoice_date(text: str) -> tuple[str, bool]:
    """Retourne (date formatee dd/mm/YYYY, is_fallback)."""
    patterns = [
        r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
        r"\b(\d{4}[/-]\d{2}[/-]\d{2})\b",
        r"\b(\d{2}[.]\d{2}[.]\d{4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw = match.group(1)
        try:
            normalized = raw.replace(".", "/")
            if normalized[4] in "-/" and normalized[:4].isdigit():
                dt = datetime.strptime(normalized.replace("/", "-"), "%Y-%m-%d")
            else:
                dt = datetime.strptime(normalized.replace("-", "/"), "%d/%m/%Y")
            return dt.strftime("%d/%m/%Y"), False
        except ValueError:
            continue

    lower = text.lower()
    month_pattern = re.compile(
        r"\b(\d{1,2})\s+(janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre)\s+(\d{4})\b"
    )
    month_match = month_pattern.search(lower)
    if month_match:
        day, month_name, year = month_match.groups()
        month = _FRENCH_MONTHS.get(month_name)
        if month:
            try:
                dt = datetime(int(year), month, int(day))
                return dt.strftime("%d/%m/%Y"), False
            except ValueError:
                pass

    return datetime.now().strftime("%d/%m/%Y"), True


def _extract_total_amount(text: str) -> tuple[float | None, bool]:
    """Retourne (montant, matched_priority_keyword)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    scored_candidates: list[tuple[int, float]] = []
    amount_regex = r"-?\d[\d\s.,]*\d|-?\d"

    for line in lines:
        low = line.lower()
        line_score = 0
        strong_hint = False
        has_context = any(
            token in low for token in ["total", "ttc", "ht", "tva", "payer", "due", "montant", "mga", "eur", "usd", "$", "€", "ar"]
        )

        if "net a payer" in low or "net à payer" in low or "amount due" in low or "total due" in low:
            line_score += 110
            strong_hint = True
        elif "total ttc" in low or "montant ttc" in low:
            line_score += 100
            strong_hint = True
        elif "ttc" in low:
            line_score += 85
            strong_hint = True
        elif "total" in low:
            line_score += 60

        if "ht" in low or "hors taxe" in low or "subtotal" in low:
            line_score -= 40
        if "tva" in low or "vat" in low or "tax" in low:
            line_score -= 30
        if "remise" in low or "discount" in low:
            line_score -= 20
        if any(c in low for c in ["mga", "eur", "usd", "$", "€", "ar"]):
            line_score += 15

        candidates = re.findall(amount_regex, line)
        for idx, candidate in enumerate(candidates):
            value = _parse_amount(candidate)
            if not _is_plausible_amount(value):
                continue
            looks_like_amount = ("," in candidate) or ("." in candidate) or (" " in candidate)
            if not has_context and not strong_hint and not looks_like_amount:
                # Evite de prendre des dates/ids comme montants.
                continue
            score = line_score
            if idx == len(candidates) - 1:
                score += 8
            if strong_hint:
                score += 10
            scored_candidates.append((score, float(value)))

    if not scored_candidates:
        return None, False

    # Priorite au score, puis au montant le plus eleve en cas d'egalite.
    scored_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, best_value = scored_candidates[0]
    return best_value, best_score >= 100


def _extract_tax_breakdown(text: str) -> dict:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    out = {"montant_ht": None, "montant_tva": None, "montant_ttc": None}

    keyword_map = {
        "montant_ht": ["ht", "hors taxe", "subtotal"],
        "montant_tva": ["tva", "vat", "tax"],
        "montant_ttc": ["ttc", "net a payer", "net à payer", "amount due", "total due", "total ttc"],
    }

    for key, words in keyword_map.items():
        for line in lines:
            low = line.lower()
            if not any(w in low for w in words):
                continue
            candidates = re.findall(r"-?\d[\d\s.,]*\d|-?\d", line)
            for candidate in reversed(candidates):
                value = _parse_amount(candidate)
                if _is_plausible_amount(value):
                    out[key] = float(value)
                    break
            if out[key] is not None:
                break
    return out


def _score_invoice_parse(invoice_no: str | None, is_date_fallback: bool, amount_keyword_hit: bool) -> tuple[float, bool, list[str]]:
    score = 0.0
    warnings: list[str] = []

    if invoice_no:
        score += 0.2
    else:
        warnings.append("Numero de facture non detecte")

    if is_date_fallback:
        warnings.append("Date incertaine (date du jour utilisee)")
    else:
        score += 0.3

    if amount_keyword_hit:
        score += 0.5
    else:
        score += 0.3
        warnings.append("Montant detecte sans mot-cle prioritaire")

    score = max(0.0, min(1.0, score))
    return round(score, 2), score < 0.75, warnings


def parse_invoice_text(text: str) -> dict:
    """Parse texte OCR et renvoie les champs utiles pour pre-remplir une ecriture."""
    cleaned = text or ""
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    first_line = _normalize_spaces(lines[0]) if lines else "Facture"
    supplier_name = _extract_supplier_name(lines)
    invoice_subject = _extract_invoice_subject(lines, supplier_name=supplier_name)

    invoice_no = _extract_invoice_number(cleaned)
    invoice_date, is_date_fallback = _extract_invoice_date(cleaned)
    amount, amount_keyword_hit = _extract_total_amount(cleaned)
    tax_data = _extract_tax_breakdown(cleaned)
    currency = _extract_currency(cleaned)

    if amount is None and tax_data.get("montant_ttc") is not None:
        amount = float(tax_data["montant_ttc"])
        amount_keyword_hit = True

    if amount is None:
        raise ValueError("Montant introuvable dans la facture OCR.")

    label = _build_invoice_label(invoice_no, supplier_name, invoice_subject, first_line)

    year = invoice_date[-4:] if len(invoice_date) >= 4 else datetime.now().strftime("%Y")
    confidence_score, needs_review, warnings = _score_invoice_parse(
        invoice_no=invoice_no,
        is_date_fallback=is_date_fallback,
        amount_keyword_hit=amount_keyword_hit,
    )

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
        "supplier_name": supplier_name or "",
        "invoice_subject": invoice_subject or "",
        "source_hint": first_line[:120],
        "currency": currency,
        "montant_ht": tax_data.get("montant_ht"),
        "montant_tva": tax_data.get("montant_tva"),
        "montant_ttc": tax_data.get("montant_ttc") if tax_data.get("montant_ttc") is not None else amount,
        "confidence_score": confidence_score,
        "needs_review": needs_review,
        "parse_warnings": warnings,
    }


def _preprocess_image_for_ocr(image):
    try:
        from PIL import ImageFilter, ImageOps  # type: ignore
    except Exception:
        return image

    gray = ImageOps.grayscale(image)
    contrasted = ImageOps.autocontrast(gray)
    sharpened = contrasted.filter(ImageFilter.SHARPEN)

    # Binarisation simple pour clarifier du texte pale.
    return sharpened.point(lambda px: 255 if px > 160 else 0)


def _ocr_image(image):
    processed = _preprocess_image_for_ocr(image)

    try:
        raw_text = _ocr_image_easyocr(image)
        processed_text = _ocr_image_easyocr(processed)
        best = processed_text if len(processed_text or "") > len(raw_text or "") else raw_text
        if best:
            return best
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
        text = pytesseract.image_to_string(processed, lang="fra+eng")
        if text and text.strip():
            return text
    except Exception as exc:
        logger.warning("OCR Tesseract fra+eng echoue (%s), tentative sans langue explicite.", exc)

    try:
        return pytesseract.image_to_string(processed)
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
        _EASYOCR_READER = easyocr.Reader(["fr", "en"], gpu=False)

    np_image = np.array(image)
    results = _EASYOCR_READER.readtext(np_image, detail=0, paragraph=True)
    text = "\n".join([str(x) for x in results if str(x).strip()])
    logger.info("OCR EasyOCR termine: %d caracteres", len(text))
    return text


def _extract_pdf_native_text(page) -> str:
    """Extrait du texte natif depuis une page PDF (si disponible)."""
    try:
        text_page = page.get_textpage()
    except Exception:
        return ""

    try:
        text = text_page.get_text_bounded()
    except Exception:
        text = ""
    finally:
        try:
            text_page.close()
        except Exception:
            pass

    return text or ""


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
            native_text = _extract_pdf_native_text(page)
            if len(native_text.strip()) >= 40:
                text_chunks.append(native_text)

            # OCR en complement si texte natif pauvre ou absent.
            if len(native_text.strip()) < 120:
                bitmap = page.render(scale=2)
                pil_image = bitmap.to_pil()
                text_chunks.append(_ocr_image(pil_image))
            page.close()

        pdf.close()
        text = "\n".join([chunk for chunk in text_chunks if chunk and chunk.strip()])
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
            "Facture OCR parsee: date=%s montant=%s libelle=%s score=%s",
            parsed.get("date"),
            parsed.get("montant_debit"),
            parsed.get("libelle"),
            parsed.get("confidence_score"),
        )
        return parsed
    except Exception:
        logger.exception("Echec OCR facture pour le fichier: %s", path)
        raise
