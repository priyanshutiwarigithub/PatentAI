import time
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from patentmind.db.session import SessionLocal
from patentmind.db.models import Patent, EmbeddingsMeta
from patentmind.embeddings.encoder import get_encoder
from patentmind.embeddings.vector_store import get_vector_store

console = Console()

def run_embedding_pipeline():
    console.print("[bold cyan]Starting Embedding Generation & Vector Storage Pipeline...[/bold cyan]")
    
    db = SessionLocal()
    try:
        # Fetch patents ready for embedding
        patents = db.query(Patent).filter(Patent.processing_status == "processed").all()
        console.print(f"Found [bold]{len(patents)}[/bold] patents with chunks ready to embed.")

        if not patents:
            console.print("[yellow]No 'processed' patents found ready for embedding.[/yellow]")
            return

        encoder = get_encoder()
        vector_store = get_vector_store()

        start_time = time.time()
        total_chunks = 0
        all_chunks_payload = []

        for patent in tqdm(patents, desc="Embedding Patent Chunks"):
            chunk_records = db.query(EmbeddingsMeta).filter(EmbeddingsMeta.patent_id == patent.patent_id).all()
            for chk in chunk_records:
                all_chunks_payload.append({
                    "patent_number": patent.patent_number,
                    "section_name": chk.section_name or "DESCRIPTION",
                    "claim_number": chk.claim_number,
                    "chunk_index": chk.chunk_index,
                    "chunk_text": chk.chunk_text,
                    "source_s3_key": patent.s3_key,
                    "vector_db_id": chk.vector_db_id or f"{patent.patent_number}_chk_{chk.chunk_index}"
                })
                total_chunks += 1
            
            patent.processing_status = "embedded"

        if all_chunks_payload:
            texts = [c["chunk_text"] for c in all_chunks_payload]
            console.print(f"Batch encoding [bold]{len(texts)}[/bold] chunk texts on GPU...")
            embeddings = encoder.batch_encode(texts, batch_size=64)

            console.print(f"Upserting vectors into [bold]{vector_store.backend.upper()}[/bold]...")
            backend_used = vector_store.upsert(all_chunks_payload, embeddings)

            db.commit()
        else:
            backend_used = vector_store.backend

        elapsed = round(time.time() - start_time, 2)

        # Print summary table
        table = Table(title="Embedding Pipeline Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Patents Processed", str(len(patents)))
        table.add_row("Total Chunks Embedded", str(total_chunks))
        table.add_row("Vector Store Backend Active", backend_used.upper())
        table.add_row("Time Taken (s)", str(elapsed))
        console.print(table)

    finally:
        db.close()

if __name__ == "__main__":
    run_embedding_pipeline()
