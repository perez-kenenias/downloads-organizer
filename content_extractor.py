import os
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Optional

MAX_CHARS = 3000
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json", ".xml", ".html", ".htm"}


def extract_text(filepath: str) -> Optional[str]:
    """
    Extract a text snippet from a file for content-based classification.
    Returns None when the format is unsupported or extraction fails.
    Supported: PDF (needs pypdf), DOCX (stdlib), plain-text files.
    """
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            return _extract_pdf(filepath)
        if ext == ".docx":
            return _extract_docx(filepath)
        if ext in TEXT_EXTENSIONS:
            return _extract_plain(filepath)
    except Exception:
        return None
    return None


def _clean(text: str) -> Optional[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 20:
        return None
    return text[:MAX_CHARS]


def _extract_pdf(filepath: str) -> Optional[str]:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # older installs
        except ImportError:
            return None
    reader = PdfReader(filepath)
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            return None
    chunks = []
    for page in reader.pages[:3]:
        chunks.append(page.extract_text() or "")
        if sum(len(c) for c in chunks) >= MAX_CHARS:
            break
    return _clean(" ".join(chunks))


def _extract_docx(filepath: str) -> Optional[str]:
    """DOCX is a zip with word/document.xml — no external library needed."""
    with zipfile.ZipFile(filepath) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    texts = [node.text for node in tree.iter(f"{ns}t") if node.text]
    return _clean(" ".join(texts))


def _extract_plain(filepath: str) -> Optional[str]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return _clean(f.read(MAX_CHARS * 2))


def pdf_support_available() -> bool:
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        try:
            import PyPDF2  # noqa: F401
            return True
        except ImportError:
            return False
