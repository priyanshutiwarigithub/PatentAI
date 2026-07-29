import fitz  # PyMuPDF
from typing import List, Dict, Any

class PDFExtractor:
    @staticmethod
    def extract_pages(pdf_bytes: bytes) -> List[Dict[str, Any]]:
        pages = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()
                is_scanned = len(text) < 100
                pages.append({
                    "page_num": page_num + 1,
                    "text": text,
                    "is_scanned": is_scanned
                })
            doc.close()
        except Exception as e:
            # Fallback if fitz fails to parse stream
            pages.append({
                "page_num": 1,
                "text": "",
                "is_scanned": True
            })
        return pages
