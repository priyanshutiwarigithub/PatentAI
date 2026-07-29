import fitz
import numpy as np
from PIL import Image
from loguru import logger
import uuid
from typing import List

from schemas.document_schema import (
    ExtractedDocument, DocumentMetadata, Section,
    ExtractionMethod
)
from processors.image_preprocessor import ImagePreprocessor
from processors.paddle_ocr_processor import PaddleOCRProcessor
from processors.easyocr_processor import EasyOCRProcessor

CONFIDENCE_THRESHOLD = 0.75  # If PaddleOCR is below this, use EasyOCR


class ScannedPDFPipeline:
    """
    Handles PDFs that are scanned images (no embedded text).
    Each page is rendered as an image and passed through OCR.
    
    Strategy:
    1. Render each PDF page as high-resolution image
    2. Preprocess image (deskew, denoise, threshold)
    3. Run PaddleOCR
    4. If confidence < threshold, fallback to EasyOCR
    5. Assemble full text
    """

    def __init__(self, use_gpu: bool = False, render_dpi: int = 300):
        self.render_dpi = render_dpi
        self.preprocessor = ImagePreprocessor(target_dpi=render_dpi)
        self.paddle_ocr = PaddleOCRProcessor(use_gpu=use_gpu)
        self.easy_ocr = EasyOCRProcessor(use_gpu=use_gpu)

    def extract(self, pdf_path: str) -> ExtractedDocument:
        logger.info(f"Starting scanned PDF OCR extraction: {pdf_path}")
        doc_id = str(uuid.uuid4())
        
        fitz_doc = fitz.open(pdf_path)
        all_sections = []
        full_text_parts = []
        total_confidence = 0
        page_count = fitz_doc.page_count

        for page_num in range(page_count):
            logger.info(f"Processing page {page_num + 1}/{page_count}")
            page = fitz_doc[page_num]

            # Render page at high DPI for better OCR accuracy
            matrix = fitz.Matrix(self.render_dpi / 72, self.render_dpi / 72)
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Preprocess
            cv2_image = self.preprocessor.pil_to_cv2(pil_image)
            processed = self.preprocessor.preprocess(cv2_image)

            # PaddleOCR first
            text, confidence = self.paddle_ocr.extract_text(processed)
            method_used = "paddle"

            # Fallback to EasyOCR if confidence is low
            if confidence < CONFIDENCE_THRESHOLD:
                logger.warning(f"Page {page_num+1}: Low PaddleOCR confidence ({confidence:.2f}), trying EasyOCR")
                easy_text, easy_confidence = self.easy_ocr.extract_text(processed)
                if easy_confidence > confidence:
                    text, confidence = easy_text, easy_confidence
                    method_used = "easyocr"

            total_confidence += confidence
            full_text_parts.append(text)

            all_sections.append(Section(
                section_id=f"page_{page_num + 1}",
                title=f"Page {page_num + 1}",
                content=text,
                page_number=page_num + 1,
            ))

        fitz_doc.close()

        avg_confidence = total_confidence / page_count if page_count > 0 else 0.0

        return ExtractedDocument(
            document_id=doc_id,
            source_path=pdf_path,
            extraction_method=ExtractionMethod.OCR_PADDLE,
            metadata=DocumentMetadata(page_count=page_count),
            full_text="\n\n--- PAGE BREAK ---\n\n".join(full_text_parts),
            sections=all_sections,
            confidence_score=avg_confidence,
            ocr_applied=True,
            warnings=["Document was scanned. OCR applied. Review for accuracy."] if avg_confidence < 0.85 else [],
        )

    def is_scanned_pdf(self, pdf_path: str, sample_pages: int = 3) -> bool:
        """
        Detect if a PDF is scanned (image-only) by checking
        if text extraction yields almost no characters.
        """
        fitz_doc = fitz.open(pdf_path)
        total_text_chars = 0
        pages_to_check = min(sample_pages, fitz_doc.page_count)

        for i in range(pages_to_check):
            text = fitz_doc[i].get_text().strip()
            total_text_chars += len(text)

        fitz_doc.close()
        avg_chars_per_page = total_text_chars / pages_to_check if pages_to_check > 0 else 0

        is_scanned = avg_chars_per_page < 100  # Less than 100 chars → probably scanned
        logger.info(f"PDF scan detection: avg_chars={avg_chars_per_page:.0f}, is_scanned={is_scanned}")
        return is_scanned