from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class DocumentType(str, Enum):
    RESEARCH_PAPER = "research_paper"
    PATENT = "patent"
    LAB_NOTEBOOK = "lab_notebook"
    DATASET_DESCRIPTION = "dataset_description"
    REVIEW_ARTICLE = "review_article"
    UNKNOWN = "unknown"

class ExtractionMethod(str, Enum):
    DIGITAL_PDF = "digital_pdf"
    OCR_PADDLE = "ocr_paddleocr"
    OCR_EASY = "ocr_easyocr"
    DOCLING = "docling"
    HYBRID = "hybrid"

class Figure(BaseModel):
    figure_id: str
    caption: Optional[str] = None
    image_path: str                      # saved locally or S3 path
    page_number: int
    bounding_box: Optional[List[float]] = None

class Table(BaseModel):
    table_id: 
    caption: Optional[str] = None
    headers: List[str]
    rows: List[List[Any]]
    page_number: int
    raw_text: Optional[str] = None

class Section(BaseModel):
    section_id: str
    title: Optional[str] = None
    content: str
    page_number: int
    section_type: Optional[str] = None  # abstract, intro, methods, results, etc.

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = []
    abstract: Optional[str] = None
    doi: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    keywords: Optional[List[str]] = []
    page_count: int = 0
    language: Optional[str] = "en"

class ExtractedDocument(BaseModel):
    """
    The canonical output schema for the Document AI Agent.
    Every downstream agent in SciNexus consumes this format.
    """
    document_id: str = Field(..., description="Unique identifier for this document")
    source_path: str = Field(..., description="Original file path or URL")
    document_type: DocumentType = DocumentType.UNKNOWN
    extraction_method: ExtractionMethod
    extraction_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Core content
    metadata: DocumentMetadata
    full_text: str = ""
    sections: List[Section] = []
    tables: List[Table] = []
    figures: List[Figure] = []
    references: List[str] = []
    
    # Quality metrics
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    ocr_applied: bool = False
    warnings: List[str] = []
    
    class Config:
        use_enum_values = True