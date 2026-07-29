import unittest
from fastapi.testclient import TestClient
from patentmind.db.session import SessionLocal, init_db
from patentmind.db.models import Patent, EmbeddingsMeta
from patentmind.storage.s3_client import s3_client
from patentmind.embeddings.vector_store import VectorStore
from patentmind.llm.router import LLMRouter
from patentmind.api.main import app

client = TestClient(app)

def setup_database():
    init_db()

def test_database_crud():
    db = SessionLocal()
    try:
        pat_num = "TEST_US_99999"
        # Cleanup
        db.query(Patent).filter(Patent.patent_number == pat_num).delete()
        db.commit()

        p = Patent(
            patent_number=pat_num,
            title="Test AI Patent Title",
            abstract="Test AI patent abstract text",
            processing_status="ingested"
        )
        db.add(p)
        db.commit()

        fetched = db.query(Patent).filter(Patent.patent_number == pat_num).first()
        assert fetched is not None
        assert fetched.title == "Test AI Patent Title"

        db.delete(fetched)
        db.commit()
    finally:
        db.close()

def test_s3_storage():
    test_key = s3_client.upload_patent_pdf("TEST_999", b"%PDF-1.4 Mock Test Content")
    assert test_key is not None
    content = s3_client.download_patent_pdf(test_key)
    assert len(content) > 0

def test_vector_store_qdrant():
    vs = VectorStore()
    assert vs.backend == "qdrant"
    
    dummy_chunks = [{
        "patent_number": "TEST_VEC_1",
        "section_name": "CLAIMS",
        "claim_number": 1,
        "chunk_index": 1,
        "chunk_text": "Claim 1: A system comprising a neural processor.",
        "vector_db_id": "test_vec_1"
    }]
    dummy_embeddings = [[0.1] * 384]
    
    backend_used = vs.upsert(dummy_chunks, dummy_embeddings)
    assert backend_used == "qdrant"

    results = vs.search([0.1] * 384, top_k=1)
    assert len(results) > 0
    assert "chunk_text" in results[0]

def test_llm_router_failover():
    router = LLMRouter()
    res = router.generate("Test prompt for LLM router")
    assert "answer" in res
    assert "llm_backend_used" in res
    assert len(res["answer"]) > 0

def test_fastapi_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_patents" in data
    assert "vector_backend" in data

def test_fastapi_query_endpoint():
    payload = {"query": "What methods exist for neural network attention optimization?"}
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "llm_backend_used" in data
