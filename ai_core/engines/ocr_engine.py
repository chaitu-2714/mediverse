"""
MediVerse AI — OCR Engine.
Extracts text from PDFs using PyMuPDF with EasyOCR fallback for scanned pages.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from config.settings import get_settings
from core.exceptions import OCRError

logger = logging.getLogger("mediverse.ai.ocr")


class PageText:
    """Text content extracted from a single PDF page."""
    def __init__(self, page_number: int, text: str, used_ocr: bool = False) -> None:
        self.page_number = page_number
        self.text = text.strip()
        self.used_ocr = used_ocr
        self.char_count = len(self.text)

    @property
    def is_empty(self) -> bool:
        return self.char_count < 10


class OCREngine:
    """
    Extracts text from PDF documents.
    - Primary: PyMuPDF (fast, accurate for digital PDFs)
    - Fallback: EasyOCR (for scanned/image-based pages)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._ocr_reader = None  # Lazy-loaded EasyOCR
        self._ocr_available = False
        self._min_text_len = self._settings.min_text_length_for_ocr

    def _get_ocr_reader(self):
        """Lazy-initialize EasyOCR reader (heavy model load)."""
        if self._ocr_reader is None:
            try:
                import easyocr
                self._ocr_reader = easyocr.Reader(
                    ["en"], gpu=False, verbose=False
                )
                self._ocr_available = True
                logger.info("EasyOCR reader initialized")
            except Exception as e:
                logger.warning(f"EasyOCR not available: {e}. OCR fallback disabled.")
                self._ocr_available = False
        return self._ocr_reader

    def extract_text_from_pdf(self, file_path: str) -> list[PageText]:
        """
        Extract text from all pages of a PDF.
        Uses OCR for pages with insufficient text content.
        """
        path = Path(file_path)
        if not path.exists():
            raise OCRError(f"File not found: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise OCRError(f"Expected PDF, got: {path.suffix}")

        pages: list[PageText] = []

        try:
            doc = fitz.open(str(path))
            total_pages = len(doc)
            logger.info(f"Extracting text from {total_pages}-page PDF: {path.name}")

            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text("text", sort=True)

                used_ocr = False
                if len(text.strip()) < self._min_text_len:
                    # Attempt OCR on the rendered page image
                    ocr_text = self._ocr_page(page)
                    if ocr_text:
                        text = ocr_text
                        used_ocr = True

                pages.append(PageText(
                    page_number=page_num + 1,
                    text=text,
                    used_ocr=used_ocr,
                ))

            doc.close()

            total_chars = sum(p.char_count for p in pages)
            ocr_pages = sum(1 for p in pages if p.used_ocr)
            logger.info(
                f"Extracted {total_chars:,} chars from {total_pages} pages "
                f"({ocr_pages} via OCR)"
            )
            return pages

        except fitz.FileDataError as e:
            raise OCRError(f"Corrupted PDF: {e}") from e
        except Exception as e:
            raise OCRError(str(e)) from e

    def _ocr_page(self, page: fitz.Page) -> Optional[str]:
        """Render a page as image and run EasyOCR on it."""
        reader = self._get_ocr_reader()
        if not self._ocr_available or reader is None:
            return None

        try:
            # Render page to image at 2x resolution for better OCR accuracy
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")

            results = reader.readtext(img_bytes, detail=1)
            # Filter by confidence threshold
            min_conf = self._settings.ocr_confidence_threshold
            texts = [
                r[1] for r in results
                if r[2] >= min_conf
            ]
            return " ".join(texts)

        except Exception as e:
            logger.warning(f"OCR failed on page: {e}")
            return None

    def extract_text_from_txt(self, file_path: str) -> list[PageText]:
        """Extract text from a plain text file (treated as single page)."""
        path = Path(file_path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [PageText(page_number=1, text=text)]

    def extract_text_from_image(self, file_path: str) -> list[PageText]:
        """Extract text from a standalone image using EasyOCR."""
        path = Path(file_path)
        if not path.exists():
            raise OCRError(f"File not found: {file_path}")
            
        reader = self._get_ocr_reader()
        if not self._ocr_available or reader is None:
            return [PageText(page_number=1, text=f"Scanned image report: {path.name}", used_ocr=False)]

        try:
            results = reader.readtext(str(path), detail=1)
            min_conf = self._settings.ocr_confidence_threshold
            texts = [r[1] for r in results if r[2] >= min_conf]
            text = " ".join(texts)
            if not text.strip():
                text = f"Scanned image report placeholder: {path.name}"
            return [PageText(page_number=1, text=text, used_ocr=True)]
        except Exception as e:
            logger.warning(f"OCR failed on image file: {e}")
            return [PageText(page_number=1, text=f"Scanned image report parsing error: {path.name}", used_ocr=False)]

    def get_pdf_metadata(self, file_path: str) -> dict:
        """Extract PDF metadata (title, author, dates, page count)."""
        try:
            doc = fitz.open(file_path)
            meta = doc.metadata or {}
            page_count = len(doc)
            doc.close()
            return {
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "page_count": page_count,
            }
        except Exception as e:
            logger.warning(f"Could not extract PDF metadata: {e}")
            return {"page_count": 0}
