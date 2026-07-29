import re
from typing import Dict, List, Any, Optional
from rich.console import Console
from patentmind.embeddings.encoder import get_encoder
from patentmind.embeddings.vector_store import get_vector_store
from patentmind.llm.router import get_llm_router
from patentmind.processing.pdf_extractor import PDFExtractor
from patentmind.processing.cleaner import PatentTextCleaner

console = Console()

class RAGPipeline:
    def __init__(self):
        self.encoder = get_encoder()
        self.vector_store = get_vector_store()
        self.router = get_llm_router()

    def process_query(self, query: str, paper_bytes: Optional[bytes] = None, top_k: int = 8) -> Dict[str, Any]:
        console.print(f"[bold cyan]Running RAG Pipeline for query:[/bold cyan] '{query}'")

        # 1. Query Preprocessing & Filtering Detection
        cleaned_query = query.strip()
        section_filter = None
        if "claim" in cleaned_query.lower() or "prior art" in cleaned_query.lower():
            section_filter = "CLAIMS"

        # 2. Extract research paper text if uploaded
        paper_context = ""
        if paper_bytes:
            pages = PDFExtractor.extract_pages(paper_bytes)
            raw_paper = "\n".join([p["text"] for p in pages])
            paper_context = PatentTextCleaner.clean_text(raw_paper)
            console.print("[green]Research paper PDF context extracted and prepended.[/green]")

        # 3. Vector Retrieval
        query_embedding = self.encoder.batch_encode([cleaned_query])[0]
        hits = self.vector_store.search(query_embedding, top_k=top_k, section_filter=section_filter)

        # 4. Context Assembly (Limit total context to 6000 tokens / ~24000 chars)
        context_blocks = []
        if paper_context:
            context_blocks.append(f"=== UPLOADED RESEARCH PAPER CONTEXT ===\n{paper_context[:3000]}\n")

        sources = []
        for idx, hit in enumerate(hits, 1):
            block = f"[Patent {hit['patent_number']} | {hit['section_name']}]\n{hit['chunk_text']}"
            context_blocks.append(block)
            sources.append({
                "patent_number": hit["patent_number"],
                "section": hit["section_name"],
                "score": hit["score"],
                "chunk_text": hit["chunk_text"]
            })

        assembled_context = "\n\n".join(context_blocks)
        if len(assembled_context) > 24000:
            assembled_context = assembled_context[:24000] + "\n...[Context truncated for token limit]"

        # 5. Prompt Construction
        system_instructions = (
            "You are a Patent Intelligence Analyst. Answer the user's question using ONLY the provided patent context. "
            "Cite the specific patent number (e.g. Patent US110000001) for every claim or technical detail you mention. "
            "If the context is insufficient, explicitly state that. Do not hallucinate patent details."
        )

        full_prompt = (
            f"{system_instructions}\n\n"
            f"=== RETRIEVED PATENT CONTEXT ===\n{assembled_context}\n\n"
            f"User Question: {cleaned_query}"
        )

        # 6. LLM Generation via Router
        llm_response = self.router.generate(full_prompt)

        return {
            "query": query,
            "answer": llm_response["answer"],
            "sources": sources,
            "llm_backend_used": llm_response["llm_backend_used"],
            "vector_backend_used": self.vector_store.backend.upper()
        }

_rag_pipeline_instance = None

def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGPipeline()
    return _rag_pipeline_instance
