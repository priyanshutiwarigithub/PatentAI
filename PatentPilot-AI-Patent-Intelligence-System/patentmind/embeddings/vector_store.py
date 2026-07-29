import os
from typing import List, Dict, Any, Optional
from rich.console import Console
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()
console = Console()

class VectorStore:
    """
    Qdrant Vector Database client (Exclusive Vector Engine).
    Target Host: QDRANT_HOST:QDRANT_PORT (GPU server 192.168.6.50:6333).
    """
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "127.0.0.1")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = "patent_chunks"
        self.backend = "qdrant"

        console.print(f"[bold blue]Connecting to Qdrant Vector DB at {self.qdrant_host}:{self.qdrant_port}...[/bold blue]")
        try:
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
                timeout=5.0,
                check_compatibility=False
            )
            # Ensure collection exists
            collections = [c.name for c in self.qdrant_client.get_collections().collections]
            if self.collection_name not in collections:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
            console.print(f"[bold green]Successfully initialized Qdrant collection '{self.collection_name}'[/bold green]")
        except Exception as e:
            console.print(f"[yellow]Qdrant client initialized in offline/in-memory mode for environment testing: {e}[/yellow]")
            # Fallback to in-memory Qdrant instance if remote host is not reachable during local run
            self.qdrant_client = QdrantClient(":memory:", check_compatibility=False)
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def upsert(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> str:
        import uuid
        points = []
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            payload = {
                "patent_number": chunk["patent_number"],
                "section_name": chunk.get("section_name", ""),
                "claim_number": chunk.get("claim_number"),
                "chunk_index": chunk["chunk_index"],
                "chunk_text": chunk["chunk_text"],
                "source_s3_key": chunk.get("source_s3_key", "")
            }
            # Use UUIDs instead of 1, 2, 3 to prevent overwriting vectors from other patents
            point_id = str(uuid.uuid4())
            points.append(PointStruct(id=point_id, vector=emb, payload=payload))
        
        self.qdrant_client.upsert(collection_name=self.collection_name, points=points)
        console.print(f"[bold green]Successfully upserted {len(points)} vectors into Qdrant.[/bold green]")
        return "qdrant"

    def search(self, query_embedding: List[float], top_k: int = 5, section_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        hits = []
        try:
            if hasattr(self.qdrant_client, "query_points"):
                res = self.qdrant_client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,
                    limit=top_k
                )
                hits = getattr(res, "points", [])
            else:
                hits = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    limit=top_k
                )
        except Exception as e:
            console.print(f"[yellow]Qdrant search error: {e}[/yellow]")

        results = []
        for hit in hits:
            payload = getattr(hit, "payload", {}) or {}
            score = getattr(hit, "score", 0.0)
            results.append({
                "chunk_text": payload.get("chunk_text", ""),
                "patent_number": payload.get("patent_number", ""),
                "section_name": payload.get("section_name", ""),
                "claim_number": payload.get("claim_number"),
                "score": round(float(score), 4)
            })
        return results

    def patent_exists(self, patent_number: str) -> bool:
        """Check if a patent has already been vectorized in Qdrant."""
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            count_result = self.qdrant_client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[FieldCondition(key="patent_number", match=MatchValue(value=patent_number))]
                )
            )
            return count_result.count > 0
        except Exception as e:
            console.print(f"[yellow]Error checking existence in Qdrant for {patent_number}: {e}[/yellow]")
            return False

_vector_store_instance = None

def get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
