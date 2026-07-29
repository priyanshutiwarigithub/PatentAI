from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from pathlib import Path
from loguru import logger

from pipelines.digital_pdf_pipeline import DigitalPDFPipeline
from pipelines.scanned_pdf_pipeline import ScannedPDFPipeline
from schemas.document_schema import ExtractedDocument
from utils.document_classifier import DocumentClassifier
from utils.text_cleaner import TextCleaner

# ── Agent State ────────────────────────────────────────────────────────────────

class DocAgentState(TypedDict):
    input_path: str
    is_scanned: Optional[bool]
    raw_document: Optional[ExtractedDocument]
    cleaned_document: Optional[ExtractedDocument]
    classified_document: Optional[ExtractedDocument]
    errors: List[str]
    status: str  # "pending" | "extracted" | "cleaned" | "classified" | "done" | "error"

# ── Node Functions ──────────────────────────────────────────────────────────────

digital_pipeline = DigitalPDFPipeline()
scanned_pipeline = ScannedPDFPipeline()
classifier = DocumentClassifier()
cleaner = TextCleaner()

def detect_document_type(state: DocAgentState) -> DocAgentState:
    """Node 1: Detect if PDF is digital or scanned."""
    path = state["input_path"]
    logger.info(f"[Agent] Detecting document type for: {path}")

    if not Path(path).exists():
        return {**state, "errors": ["File not found"], "status": "error"}

    try:
        is_scanned = scanned_pipeline.is_scanned_pdf(path)
        return {**state, "is_scanned": is_scanned, "status": "detected"}
    except Exception as e:
        return {**state, "errors": [str(e)], "status": "error"}


def extract_content(state: DocAgentState) -> DocAgentState:
    """Node 2: Route to appropriate extraction pipeline."""
    path = state["input_path"]
    
    try:
        if state["is_scanned"]:
            logger.info("[Agent] Using Scanned PDF pipeline (OCR)")
            doc = scanned_pipeline.extract(path)
        else:
            logger.info("[Agent] Using Digital PDF pipeline (PyMuPDF + Docling)")
            doc = digital_pipeline.extract(path)
        
        return {**state, "raw_document": doc, "status": "extracted"}
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {**state, "errors": [str(e)], "status": "error"}


def clean_and_normalize(state: DocAgentState) -> DocAgentState:
    """Node 3: Clean extracted text (remove noise, normalize whitespace)."""
    doc = state["raw_document"]
    
    try:
        cleaned_text = cleaner.clean(doc.full_text)
        doc.full_text = cleaned_text
        for section in doc.sections:
            section.content = cleaner.clean(section.content)
        
        return {**state, "cleaned_document": doc, "status": "cleaned"}
    except Exception as e:
        return {**state, "errors": [str(e)], "status": "error"}


def classify_document(state: DocAgentState) -> DocAgentState:
    """Node 4: Classify document type (paper, patent, lab notebook...)."""
    doc = state["cleaned_document"]
    
    try:
        doc_type = classifier.classify(doc.full_text, doc.metadata)
        doc.document_type = doc_type
        return {**state, "classified_document": doc, "status": "done"}
    except Exception as e:
        return {**state, "errors": [str(e)], "status": "error"}


def should_continue(state: DocAgentState) -> str:
    """Conditional edge: stop on error."""
    return "error_handler" if state["status"] == "error" else "continue"


def handle_error(state: DocAgentState) -> DocAgentState:
    logger.error(f"[Agent] Error: {state['errors']}")
    return state

# ── Build Graph ─────────────────────────────────────────────────────────────────

def build_document_extraction_agent():
    graph = StateGraph(DocAgentState)

    graph.add_node("detect", detect_document_type)
    graph.add_node("extract", extract_content)
    graph.add_node("clean", clean_and_normalize)
    graph.add_node("classify", classify_document)
    graph.add_node("error_handler", handle_error)

    graph.set_entry_point("detect")
    
    graph.add_conditional_edges("detect", should_continue, {
        "continue": "extract",
        "error_handler": "error_handler"
    })
    graph.add_conditional_edges("extract", should_continue, {
        "continue": "clean",
        "error_handler": "error_handler"
    })
    graph.add_conditional_edges("clean", should_continue, {
        "continue": "classify",
        "error_handler": "error_handler"
    })
    
    graph.add_edge("classify", END)
    graph.add_edge("error_handler", END)

    return graph.compile()

# Singleton agent
document_agent = build_document_extraction_agent()

def run_extraction(file_path: str) -> ExtractedDocument:
    """Public entrypoint to run the document extraction agent."""
    initial_state: DocAgentState = {
        "input_path": file_path,
        "is_scanned": None,
        "raw_document": None,
        "cleaned_document": None,
        "classified_document": None,
        "errors": [],
        "status": "pending",
    }
    
    final_state = document_agent.invoke(initial_state)
    
    if final_state["status"] == "error":
        raise RuntimeError(f"Extraction failed: {final_state['errors']}")
    
    return final_state["classified_document"]