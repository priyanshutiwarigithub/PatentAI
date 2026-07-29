from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
from loguru import logger
from typing import List, Tuple

class PaddleOCRProcessor:
    """
    Wrapper around PaddleOCR for scientific document text extraction.
    PaddleOCR supports 80+ languages and handles printed + handwritten text.
    """

    def __init__(self, language: str = "en", use_gpu: bool = False):
        logger.info(f"Initializing PaddleOCR (lang={language}, gpu={use_gpu})")
        self.ocr_engine = PaddleOCR(
            use_angle_cls=True,    # Handles rotated text
            lang=language,
            use_gpu=use_gpu,
            show_log=False,
            det_model_dir=None,    # Uses default pretrained model
            rec_model_dir=None,
        )

    def extract_text(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Run OCR on a preprocessed image.
        
        Returns:
            (full_text, average_confidence)
        """
        results = self.ocr_engine.ocr(image, cls=True)

        if not results or results[0] is None:
            logger.warning("PaddleOCR returned no results")
            return "", 0.0

        lines = []
        confidences = []

        for result_page in results:
            for line in result_page:
                bbox, (text, confidence) = line
                lines.append(text)
                confidences.append(confidence)

        full_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        logger.info(f"PaddleOCR extracted {len(lines)} lines, avg confidence: {avg_confidence:.3f}")
        return full_text, avg_confidence

    def extract_with_layout(self, image: np.ndarray) -> List[dict]:
        """
        Extract text WITH bounding box positions.
        Useful for understanding document layout (multi-column papers).
        """
        results = self.ocr_engine.ocr(image, cls=True)
        layout_blocks = []

        if not results or results[0] is None:
            return layout_blocks

        for result_page in results:
            for line in result_page:
                bbox, (text, confidence) = line
                layout_blocks.append({
                    "text": text,
                    "confidence": confidence,
                    "bbox": bbox,  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    "x_center": sum(p[0] for p in bbox) / 4,
                    "y_center": sum(p[1] for p in bbox) / 4,
                })

        # Sort by vertical position (reading order)
        layout_blocks.sort(key=lambda b: b["y_center"])
        return layout_blocks