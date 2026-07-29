# PatentMind AI — Enterprise Patent Intelligence Platform

Enterprise-grade Big Data, RAG, and Large Language Model platform designed to process, index, and analyze 200+ AI/ML patents across USPTO, WIPO, and Google Patents.

## Key Features
- **15-Stage Locked Pipeline**: End-to-end ingestion, deduplication, PyMuPDF + GLM-OCR GPU batching, section-aware chunking, SentenceTransformers GPU embedding, dual-backend Vector DB (Qdrant + ChromaDB), and RAG synthesis.
- **GPU Server Acceleration (`192.168.6.50:22`)**: Batch OCR processing using **GLM-OCR** and query synthesis powered by **Qwen3-4B via Ollama**.
- **Automated Fallbacks**:
  - Vector DB: Qdrant Primary → ChromaDB Local Fallback
  - LLM Pipeline: Qwen3-4B Ollama → Groq API (`llama-3.3-70b-versatile`)
- **Terraform AWS Architecture**: Infrastructure-as-code configuration provisioning S3 bucket (`patentmind-patent-storage`) and PostgreSQL RDS database.
- **Full Stack Application**: FastAPI REST API serving static React + Tailwind CSS dashboard.

## Directory Structure
```
patentmind/
├── terraform/          ← AWS Infrastructure (S3, RDS PostgreSQL, Security Groups)
├── ingestion/          ← USPTO, WIPO, Google Patents API clients & pipeline
├── processing/         ← PyMuPDF text layer + GLM-OCR GPU batch engine + Chunker
├── embeddings/         ← sentence-transformers + Qdrant (Primary) & ChromaDB (Fallback)
├── retrieval/          ← RAG pipeline, context assembler & research paper analyzer
├── llm/                ← Qwen3-4B Ollama client + Groq API router
├── api/                ← FastAPI REST API routes & Swagger documentation
├── db/                 ← SQLAlchemy 2.0 ORM models & session management
├── storage/            ← Boto3 S3 client with retry logic & mock fallback
├── frontend/           ← React + Tailwind CSS single page web dashboard
├── tests/              ← Unit & integration test suite
├── docs/               ← SSH deployment checklist (DEPLOY.md)
├── .env.example        ← Environment configuration template
└── docker-compose.yml  ← PostgreSQL 15 & Neo4j Community services
```

## Quickstart

### 1. Environment & Services
```bash
cp .env.example .env
docker-compose up -d
```

### 2. Run Ingestion, Document Processing & Embeddings
```bash
python -m patentmind.ingestion.pipeline
python -m patentmind.processing.pipeline
python -m patentmind.embeddings.pipeline
```

### 3. Launch Web Platform
```bash
uvicorn patentmind.api.main:app --reload --port 8000
```
Open `http://localhost:8000` in your browser.
