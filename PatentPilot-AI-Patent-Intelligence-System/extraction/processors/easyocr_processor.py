import easyocr
import numpy as np
from loguru import logger
from typing import Tuple, List

class EasyOCRProcessor:
    """
    EasyOCR as a secondary/validation OCR engine.
    Used when PaddleOCR confidence is low, or for specialized content
    like handwritten text, chemical symbols, and mixed-language docs.
    """

    def __init__(self, languages: List[str] = ["en"], use_gpu: bool = False):
        logger.info(f"Initializing EasyOCR (languages={languages})")
        self.reader = easyocr.Reader(languages, gpu=use_gpu)

    def extract_text(self, image: np.ndarray) -> Tuple[str, float]:
        """Run EasyOCR on image, return (text, confidence)."""
        results = self.reader.readtext(image)
        
        lines = []
        confidences = []
        for (bbox, text, confidence) in results:
            lines.append(text)
            confidences.append(confidence)

        full_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        logger.info(f"EasyOCR extracted {len(lines)} lines, avg confidence: {avg_confidence:.3f}")
        return full_text, avg_confidence

    def extract_math_and_formulas(self, image: np.ndarray) -> List[str]:
        """
        EasyOCR is better at detecting mathematical notation.
        Returns list of potential formula strings detected.
        """
        results = self.reader.readtext(image, detail=1)
        formulas = []
        
        for (bbox, text, conf) in results:
            # Simple heuristic: text with many special chars is likely a formula
            special_chars = set("∑∫∂∇αβγδεζηθλμνξπρστφψω=+-*/^{}[]")
            if any(c in special_chars for c in text) and conf > 0.5:
                formulas.append(text)
        
        return formulas