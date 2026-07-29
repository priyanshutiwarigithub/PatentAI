import os
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from patentmind.db.session import SessionLocal
from patentmind.db.models import Patent, EmbeddingsMeta, ProcessingLog
from patentmind.storage.s3_client import s3_client
from patentmind.processing.pdf_extractor import PDFExtractor
from patentmind.processing.ocr_engine import get_glm_ocr_engine
from patentmind.processing.cleaner import PatentTextCleaner
from patentmind.processing.chunker import PatentChunker

console = Console()

def run_document_processing_pipeline():
    console.print("[bold cyan]Starting Document Processing Pipeline (GLM-OCR GPU Batch)...[/bold cyan]")
    
    db = SessionLocal()
    try:
        patents = db.query(Patent).filter(Patent.processing_status == "ingested").all()
        console.print(f"Found [bold]{len(patents)}[/bold] patents ready for document processing.")

        if not patents:
            console.print("[yellow]No 'ingested' patents found to process.[/yellow]")
            return

        ocr_engine = get_glm_ocr_engine()
        chunker = PatentChunker()
        
        processed_count = 0
        total_chunks = 0

        for patent in tqdm(patents, desc="Processing Patents"):
            try:
                # 1. Download PDF from S3 (or mock)
                pdf_bytes = s3_client.download_patent_pdf(patent.s3_key or f"patents/{patent.patent_number}.pdf")
                
                # 2. Extract text (PyMuPDF + GLM-OCR fallback per page)
                pages = PDFExtractor.extract_pages(pdf_bytes)
                full_text = []

                for page in pages:
                    if page["is_scanned"]:
                        ocr_text = ocr_engine.process_scanned_page(pdf_bytes, page["page_num"])
                        full_text.append(ocr_text)
                    else:
                        full_text.append(page["text"])

                raw_combined = "\n\n".join(full_text)
                if not raw_combined.strip():
                    raw_combined = f"Patent {patent.patent_number}: {patent.title}\n\n{patent.abstract}\n\n{patent.description}"

                # 3. Clean text
                cleaned_text = PatentTextCleaner.clean_text(raw_combined)

                # 4. Chunk text (section-aware + claim-aware)
                chunks = chunker.chunk_patent(
                    patent_number=patent.patent_number,
                    cleaned_text=cleaned_text,
                    s3_key=patent.s3_key or f"patents/{patent.patent_number}.pdf",
                    claims_text=patent.claims or ""
                )

                # 5. Save chunks to embeddings_meta table
                for c in chunks:
                    chunk_rec = EmbeddingsMeta(
                        patent_id=patent.patent_id,
                        chunk_index=c["chunk_index"],
                        chunk_text=c["chunk_text"],
                        section_name=c["section_name"],
                        claim_number=c["claim_number"],
                        vector_db_id=f"{patent.patent_number}_chunk_{c['chunk_index']}"
                    )
                    db.add(chunk_rec)
                    total_chunks += 1

                # 6. Update status
                patent.processing_status = "processed"

                log_entry = ProcessingLog(
                    patent_id=patent.patent_id,
                    stage="document_processing",
                    status="success"
                )
                db.add(log_entry)
                processed_count += 1

            except Exception as e:
                console.print(f"[red]Error processing patent {patent.patent_number}: {e}[/red]")
                log_entry = ProcessingLog(
                    patent_id=patent.patent_id,
                    stage="document_processing",
                    status="failed",
                    error_message=str(e)
                )
                db.add(log_entry)

        db.commit()

        # Summary
        table = Table(title="Document Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Patents Processed", str(processed_count))
        table.add_row("Total Chunks Created", str(total_chunks))
        table.add_row("OCR Engine Used", "GLM-OCR GPU Batch")
        console.print(table)

    finally:
        db.close()

if __name__ == "__main__":
    run_document_processing_pipeline()
