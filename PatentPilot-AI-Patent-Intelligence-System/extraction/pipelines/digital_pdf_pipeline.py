import fitz  # PyMuPDF
import pdfplumber
from docling.document_converter import DocumentConverter
from pathlib import Path
from typing import Optional
import uuid
from loguru import logger

from schemas.document_schema import (
    ExtractedDocument, DocumentMetadata, Section,
    Table, Figure, ExtractionMethod
)
from processors.figure_extractor import FigureExtractor

class DigitalPDFPipeline:
    """
    Handles extraction from native/born-digital PDFs where text is
    embedded directly (not scanned images).
    
    Uses:
    - PyMuPDF: Fast text, metadata, and image extraction
    - pdfplumber: Precise table extraction
    - Docling: High-quality structure understanding
    """

    def __init__(self, output_dir: str = "outputs/figures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figure_extractor = FigureExtractor(str(self.output_dir))

    def extract(self, pdf_path: str) -> ExtractedDocument:
        logger.info(f"Starting digital PDF extraction: {pdf_path}")
        doc_id = str(uuid.uuid4())

        # --- PyMuPDF: Fast metadata + text extraction ---
        fitz_doc = fitz.open(pdf_path)
        metadata = self._extract_metadata(fitz_doc)
        full_text, sections = self._extract_text_and_sections(fitz_doc)
        figures = self.figure_extractor.extract_figures(fitz_doc, doc_id)
        fitz_doc.close()

        # --- pdfplumber: Table extraction ---
        tables = self._extract_tables(pdf_path, doc_id)

        # --- Docling: Enhanced structure (optional, more accurate) ---
        try:
            docling_sections = self._extract_with_docling(pdf_path, doc_id)
            if docling_sections:
                sections = docling_sections
                logger.info("Using Docling-enhanced section structure")
        except Exception as e:
            logger.warning(f"Docling failed, using PyMuPDF sections: {e}")

        return ExtractedDocument(
            document_id=doc_id,
            source_path=pdf_path,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            metadata=metadata,
            full_text=full_text,
            sections=sections,
            tables=tables,
            figures=figures,
            confidence_score=0.98,
            ocr_applied=False,
        )

    def _extract_metadata(self, fitz_doc: fitz.Document) -> DocumentMetadata:
        """Extract document metadata using PyMuPDF."""
        meta = fitz_doc.metadata or {}
        
        # Try to find abstract from first page text
        first_page_text = fitz_doc[0].get_text() if fitz_doc.page_count > 0 else ""
        abstract = self._find_abstract(first_page_text)

        return DocumentMetadata(
            title=meta.get("title", "").strip() or None,
            authors=self._parse_authors(meta.get("author", "")),
            abstract=abstract,
            doi=self._find_doi(first_page_text),
            page_count=fitz_doc.page_count,
        )

    def _extract_text_and_sections(self, fitz_doc: fitz.Document):
        """
        Extract full text and attempt to identify sections
        using heading detection heuristics.
        """
        full_text_parts = []
        sections = []
        section_counter = 0

        for page_num, page in enumerate(fitz_doc):
            blocks = page.get_text("dict")["blocks"]
            page_text_parts = []

            for block in blocks:
                if block.get("type") != 0:  # type 0 = text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        font_size = span.get("size", 0)
                        flags = span.get("flags", 0)
                        is_bold = bool(flags & 2**4)

                        if text:
                            page_text_parts.append(text)

                            # Heuristic: large/bold text is likely a section heading
                            if (font_size > 12 and is_bold and len(text) < 100
                                    and not text[0].isdigit()):
                                section_counter += 1
                                sections.append(Section(
                                    section_id=f"sec_{section_counter}",
                                    title=text,
                                    content="",   # filled in post-processing
                                    page_number=page_num + 1,
                                    section_type=self._classify_section(text),
                                ))

            full_text_parts.append(" ".join(page_text_parts))

        return "\n\n".join(full_text_parts), sections

    def _extract_tables(self, pdf_path: str, doc_id: str):
        """Use pdfplumber for accurate table extraction."""
        tables = []
        table_counter = 0

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                for raw_table in page.extract_tables():
                    if not raw_table:
                        continue
                    
                    headers = raw_table[0] if raw_table else []
                    rows = raw_table[1:] if len(raw_table) > 1 else []
                    table_counter += 1

                    tables.append(Table(
                        table_id=f"{doc_id}_table_{table_counter}",
                        headers=[str(h) for h in headers if h],
                        rows=[[str(cell) for cell in row] for row in rows],
                        page_number=page_num + 1,
                    ))

        logger.info(f"Extracted {len(tables)} tables")
        return tables

    def _extract_with_docling(self, pdf_path: str, doc_id: str):
        """
        Docling provides much better document structure understanding —
        it handles multi-column layouts, figure captions, and references
        better than raw PyMuPDF.
        """
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        doc = result.document

        sections = []
        for i, item in enumerate(doc.body.children):
            text_content = item.export_to_markdown() if hasattr(item, 'export_to_markdown') else str(item)
            if text_content.strip():
                sections.append(Section(
                    section_id=f"docling_sec_{i}",
                    title=getattr(item, 'heading', None),
                    content=text_content,
                    page_number=1,
                ))
        return sections

    def _find_abstract(self, text: str) -> Optional[str]:
        """Simple heuristic to locate abstract text."""
        lower = text.lower()
        abstract_start = lower.find("abstract")
        if abstract_start == -1:
            return None
        intro_start = lower.find("introduction", abstract_start)
        end = intro_start if intro_start != -1 else abstract_start + 1500
        return text[abstract_start:end].strip()

    def _find_doi(self, text: str) -> Optional[str]:
        import re
        pattern = r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else None

    def _parse_authors(self, author_str: str):
        if not author_str:
            return []
        return [a.strip() for a in author_str.replace(";", ",").split(",") if a.strip()]

    def _classify_section(self, title: str) -> Optional[str]:
        title_lower = title.lower()
        mapping = {
            "abstract": "abstract",
            "introduction": "introduction",
            "method": "methods",
            "material": "methods",
            "result": "results",
            "discussion": "discussion",
            "conclusion": "conclusion",
            "reference": "references",
            "related work": "related_work",
        }
        for key, value in mapping.items():
            if key in title_lower:
                return value
        return None