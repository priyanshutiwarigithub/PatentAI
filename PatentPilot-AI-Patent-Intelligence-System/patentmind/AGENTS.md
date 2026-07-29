# PatentMind AI — Agent Rules

## Project
Enterprise patent intelligence platform. Big Data + RAG + LLM.
Collects, processes, and semantically indexes 200+ AI/ML patents.
Enables natural language querying via a RAG pipeline and Qwen3-4B.

## Locked 15-stage workflow (do not modify without being asked)
1.  Patent Extraction          — USPTO, WIPO, Google Patents APIs
2.  Duplicate Detection        — cross-source dedup by patent number
3.  Metadata Validation        — required fields check before storage
4.  S3 Storage                 — original PDFs to Amazon S3
5.  PDF Text Extraction        — PyMuPDF for text-layer PDFs
6.  OCR Processing             — GLM-OCR for scanned pages (batch, GPU)
7.  Patent Text Cleaning       — noise, headers, footers removed
8.  Metadata Enrichment        — IPC/CPC normalisation, inventor dedup
9.  Patent Chunking            — section-aware + claim-aware chunking
10. Embedding Generation       — sentence-transformers, GPU batch
11. Vector DB Storage          — Qdrant (exclusive vector database on GPU server)
12. Semantic Retrieval         — query embedding + hybrid search
13. Context Generation         — top-k chunks assembled with metadata
14. LLM Answer Generation      — Qwen3-4B via Ollama; Groq fallback
15. User Interface             — React + Tailwind, FastAPI backend

## GPU server rules (192.168.6.50:22)
- OCR (GLM-OCR) runs as a batch ingestion job — NEVER at query time.
- Qwen3-4B loads for query serving — do not load during OCR batch.
- Never run both simultaneously — OOM risk on 20GB VRAM.
- Embedding generation runs as a separate batch after OCR is complete.

## Tech stack
fastapi==0.116.1, uvicorn==0.35.0, sqlalchemy==2.0.43, psycopg2-binary==2.9.10, alembic==1.16.5, langgraph==0.6.6, langchain==0.3.27, langchain-community==0.3.29, langchain-core==0.3.75, chromadb==1.0.20, neo4j==5.28.2, networkx==3.5, sentence-transformers==5.1.0, pandas==2.3.2, numpy==2.3.2, httpx==0.28.1, requests==2.32.5, PyMuPDF==1.26.4, transformers==4.55.4, accelerate==1.10.0, groq==0.31.0, qdrant-client==1.9.1, boto3==1.35.0

## Coding rules
- Every module goes in its designated folder.
- All API keys via python-dotenv from .env — never hardcoded.
- New required env vars must be added to .env.example.
- Qdrant client must wrap every call in a try/except that falls back to ChromaDB automatically.
- Qwen3-4B calls must wrap in try/except that falls back to Groq API.
- OCR pipeline must check PyMuPDF text layer first; run GLM-OCR only if extracted text length < 100 characters per page.
- Write a test for every new function before marking a task done.
