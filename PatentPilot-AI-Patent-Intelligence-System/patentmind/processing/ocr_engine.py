import os
import io
import fitz
import numpy as np
from PIL import Image
from rich.console import Console

console = Console()

class PaddleOCREngine:
    """
    PaddleOCR Engine for GPU-accelerated document OCR processing.
    """
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.model_loaded = False
        console.print("[bold blue]Initializing PaddleOCR GPU Engine...[/bold blue]")
        try:
            from paddleocr import PaddleOCR
            # Using english language, and enable GPU if requested
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=self.use_gpu)
            console.print(f"[green]PaddleOCR initialized (GPU={self.use_gpu})[/green]")
            self.model_loaded = True
        except Exception as e:
            console.print(f"[yellow]PaddleOCR initialization failed: {e}[/yellow]")
            self.ocr = None

    def process_scanned_page(self, pdf_bytes: bytes, page_num: int) -> str:
        """
        Renders the PDF page to an image and runs PaddleOCR extraction.
        """
        if not self.model_loaded or not self.ocr:
            return f"[OCR Fallback for Page {page_num}]"

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if page_num - 1 < len(doc):
                page = doc[page_num - 1]
                # High resolution for OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
                
                # Convert fitz pixmap to numpy array for PaddleOCR
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                if pix.n == 4: # RGBA to RGB
                    img_data = img_data[:, :, :3]
                
                # Run OCR
                result = self.ocr.ocr(img_data, cls=True)
                
                extracted_text = []
                if result and result[0]:
                    for line in result[0]:
                        text = line[1][0]
                        extracted_text.append(text)
                
                doc.close()
                return "\n".join(extracted_text)
            doc.close()
        except Exception as e:
            console.print(f"[red]PaddleOCR page processing error: {e}[/red]")
        
        return f"[OCR Processing Error for Page {page_num}]"

_paddle_ocr_instance = None

def get_glm_ocr_engine() -> PaddleOCREngine:
    # Keeping the same function name so we don't break existing pipeline imports,
    # but returning the new PaddleOCREngine instead.
    global _paddle_ocr_instance
    if _paddle_ocr_instance is None:
        _paddle_ocr_instance = PaddleOCREngine(use_gpu=True)
    return _paddle_ocr_instance
