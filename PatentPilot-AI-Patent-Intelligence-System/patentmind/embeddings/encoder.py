import torch
from sentence_transformers import SentenceTransformer
from typing import List
from rich.console import Console

console = Console()

class EmbeddingEncoder:
    """
    SentenceTransformer all-MiniLM-L6-v2 GPU batch encoder.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        console.print(f"[bold blue]Loading SentenceTransformer '{model_name}' on {self.device}...[/bold blue]")
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            console.print(f"[yellow]Encoder model fallback: {e}[/yellow]")
            self.model = SentenceTransformer(model_name, device="cpu")

    def batch_encode(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()

_encoder_instance = None

def get_encoder() -> EmbeddingEncoder:
    global _encoder_instance
    if _encoder_instance is None:
        _encoder_instance = EmbeddingEncoder()
    return _encoder_instance
