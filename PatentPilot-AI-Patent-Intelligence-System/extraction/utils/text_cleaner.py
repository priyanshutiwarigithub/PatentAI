import re

class TextCleaner:
    """Clean and normalize extracted text for downstream NLP tasks."""

    def clean(self, text: str) -> str:
        if not text:
            return ""
        text = self._fix_hyphenation(text)
        text = self._normalize_whitespace(text)
        text = self._remove_control_chars(text)
        text = self._fix_common_ocr_errors(text)
        return text.strip()

    def _fix_hyphenation(self, text: str) -> str:
        """Join words broken across lines (common in PDFs): 'discov-\nery' → 'discovery'"""
        return re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r'[ \t]+', ' ', text)       # Multiple spaces → single
        text = re.sub(r'\n{3,}', '\n\n', text)    # 3+ newlines → 2
        return text

    def _remove_control_chars(self, text: str) -> str:
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    def _fix_common_ocr_errors(self, text: str) -> str:
        fixes = {
            r'\bl\b': '1',           # Lowercase 'l' alone → '1'
            r'\bO\b': '0',           # Letter 'O' alone → '0'
            r'tbe\b': 'the',         # Common OCR mistake
            r'arid\b': 'and',
        }
        for pattern, replacement in fixes.items():
            text = re.sub(pattern, replacement, text)
        return text