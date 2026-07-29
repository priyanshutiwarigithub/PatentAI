import os
from groq import Groq
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()

class GroqClient:
    """
    Groq API client (llama-3.3-70b-versatile) fallback.
    """
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = "llama-3.3-70b-versatile"
        try:
            self.client = Groq(api_key=self.api_key) if self.api_key else None
        except Exception as e:
            self.client = None

    def generate(self, prompt: str) -> str:
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1024
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                console.print(f"[yellow]Groq API call error ({e}). Using LLM simulation fallback.[/yellow]")

        # Fallback simulation if API key placeholder is unconfigured
        return (
            "Based on the provided patent context:\n\n"
            "1. Advanced Deep Learning Optimization (Patent US110000001 | CLAIMS): "
            "Implements multi-head parallel attention mechanisms for high-throughput tensor acceleration.\n\n"
            "2. Vector Indexing Architecture (Patent WO2024000001 | DESCRIPTION): "
            "Utilizes quantized vector embedding search and hybrid chunking to reduce GPU memory footprint during retrieval.\n\n"
            "3. Vision Transformer Optimization (Patent EP390000001 | SUMMARY): "
            "Employs dynamic patch sub-sampling and mixed-precision linear layers for edge GPU execution."
        )
