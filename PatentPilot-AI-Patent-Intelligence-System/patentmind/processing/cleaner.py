import re

class PatentTextCleaner:
    @staticmethod
    def clean_text(raw_text: str) -> str:
        if not raw_text:
            return ""

        # Remove page numbers, watermarks, and OCR headers
        text = re.sub(r'Page\s+\d+(\s+of\s+\d+)?', '', raw_text, flags=re.IGNORECASE)
        text = re.sub(r'United States Patent\s+[A-Z0-9]+', '', text, flags=re.IGNORECASE)

        # Normalize line-wrapping hyphens and extra spaces
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        text = re.sub(r'\r\n|\r', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Preserve key section headings
        headings = ["CLAIMS", "ABSTRACT", "DESCRIPTION", "BACKGROUND", "SUMMARY", "BRIEF DESCRIPTION OF DRAWINGS"]
        for heading in headings:
            pattern = re.compile(rf'\b({heading})\b', re.IGNORECASE)
            text = pattern.sub(rf'\n\n=== \1 ===\n', text)

        return text.strip()
