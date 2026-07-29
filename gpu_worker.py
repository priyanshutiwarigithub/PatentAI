import os
import sys

# Ensure the root directory is in sys.path so 'patentmind' module can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import json
import boto3
from sentence_transformers import SentenceTransformer
from patentmind.storage.s3_client import s3_client
from patentmind.processing.ocr_engine import get_glm_ocr_engine
from patentmind.processing.pdf_extractor import PDFExtractor
from patentmind.processing.cleaner import PatentTextCleaner
from patentmind.processing.chunker import PatentChunker
from patentmind.embeddings.vector_store import get_vector_store
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()

def run_gpu_worker():
    console.print("[bold cyan]Starting Standalone GPU Worker (S3 -> Qdrant)...[/bold cyan]")
    
    # 1. Initialize S3 via Boto3 directly to scan bucket
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        console.print("[red]S3_BUCKET_NAME not set in environment![/red]")
        return
        
    s3 = boto3.client('s3', 
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'), 
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'), 
        region_name=os.getenv('AWS_REGION')
    )

    console.print(f"[cyan]Scanning S3 Bucket: {bucket_name} for PDFs...[/cyan]")
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' not in response:
            console.print("[yellow]Bucket is empty![/yellow]")
            return
        
        pdf_keys = [obj['Key'] for obj in response['Contents'] if obj['Key'].lower().endswith('.pdf')]
        console.print(f"[green]Found {len(pdf_keys)} PDFs in S3 to process.[/green]")
    except Exception as e:
        console.print(f"[red]Error scanning S3: {e}[/red]")
        return
    
    # 2. Load Vector DB (Qdrant)
    console.print("[cyan]Connecting to Qdrant...[/cyan]")
    vector_store = get_vector_store()

    # 3. Load Embedder (Using CPU Fallback due to Blackwell sm_120 PyTorch crash)
    console.print("[cyan]Loading SentenceTransformer (all-MiniLM-L6-v2) on CPU (Fallback)...[/cyan]")
    embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

    # 4. Load OCR & chunker
    ocr_engine = get_glm_ocr_engine() # PaddleOCR
    chunker = PatentChunker()
        
    for s3_key in pdf_keys:
        # Extract patent number from file name, e.g., dataset/0706.0550v1.pdf -> 0706.0550v1
        patent_number = os.path.basename(s3_key).replace(".pdf", "").replace(".PDF", "")
        console.print(f"\n[bold magenta]Processing Patent: {patent_number}[/bold magenta]")
        
        if vector_store.patent_exists(patent_number):
            console.print(f"[yellow]Skipping {patent_number}, vectors already exist in Qdrant![/yellow]")
            continue
        
        try:
            # Download from AWS S3 using our project's s3_client
            console.print(f"Downloading {s3_key}...")
            pdf_bytes = s3_client.download_patent_pdf(s3_key)
            if not pdf_bytes:
                console.print(f"[yellow]Could not download {s3_key} from S3.[/yellow]")
                continue
                
            # PyMuPDF + PaddleOCR
            console.print("Extracting text and running OCR...")
            pages = PDFExtractor.extract_pages(pdf_bytes)
            full_text = []
            for page in pages:
                if page["is_scanned"]:
                    full_text.append(ocr_engine.process_scanned_page(pdf_bytes, page["page_num"]))
                else:
                    full_text.append(page["text"])
                    
            raw_combined = "\n\n".join(full_text)
            console.print("Cleaning extracted text...")
            cleaned_text = PatentTextCleaner.clean_text(raw_combined)
            
            # Chunking
            console.print("Chunking document...")
            chunks = chunker.chunk_patent(
                patent_number=patent_number,
                cleaned_text=cleaned_text,
                s3_key=s3_key,
                claims_text="S3 Direct Ingestion - Claims extracted from body"
            )
            
            console.print(f"Generated {len(chunks)} chunks. Embedding and pushing to Qdrant...")
            embeddings_list = []
            for c in chunks:
                emb = embedder.encode(c["chunk_text"]).tolist()
                embeddings_list.append(emb)

            # Upsert all vectors to Qdrant
            if chunks:
                vector_store.upsert(chunks=chunks, embeddings=embeddings_list)
                
            console.print(f"[bold green]✅ Successfully processed and embedded {patent_number}[/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error processing {patent_number}: {e}[/red]")

    console.print("\n[bold green]GPU Worker Finished Processing All S3 Documents![/bold green]")

if __name__ == "__main__":
    run_gpu_worker()
