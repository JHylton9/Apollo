from __future__ import annotations

import numpy as np
import pymupdf

from apollo.text import clean_text


class PageOCR:
    """Lazy local OCR shared by both ingestion strategies."""

    def __init__(self) -> None:
        self._engine = None

    @staticmethod
    def needed(page: pymupdf.Page, extracted: str) -> bool:
        # OCR sparse pages and pages where images occupy a meaningful area.
        if len(extracted) < 180:
            return True
        page_area = max(page.rect.width * page.rect.height, 1)
        image_area = 0.0
        for image in page.get_images(full=True):
            for rect in page.get_image_rects(image[0]):
                image_area += max(rect.width * rect.height, 0)
        return image_area / page_area >= 0.12

    def extract(self, page: pymupdf.Page) -> str:
        # Load the OCR model only when a page actually requires it.
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0), alpha=False)
        pixels = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width, pixmap.n
        )
        result, _ = self._engine(pixels)
        if not result:
            return ""
        return clean_text("\n".join(str(item[1]) for item in result if len(item) > 1))
