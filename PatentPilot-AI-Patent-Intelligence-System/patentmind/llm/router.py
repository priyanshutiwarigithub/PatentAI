from rich.console import Console
from patentmind.llm.ollama_client import OllamaClient, OllamaUnavailableError
from patentmind.llm.groq_client import GroqClient

console = Console()

class LLMRouter:
    def __init__(self):
        self.ollama = OllamaClient()
        self.groq = GroqClient()

    def generate(self, prompt: str) -> dict:
        # Try Ollama (Qwen3-4B on GPU) first
        try:
            console.print("[cyan]Attempting generation via Ollama (Qwen3-4B on GPU)...[/cyan]")
            answer = self.ollama.generate(prompt)
            return {"answer": answer, "llm_backend_used": "Qwen3-4B (Ollama GPU)"}
        except OllamaUnavailableError:
            console.print("[bold yellow]Ollama unavailable. Automatically routing request to Groq API (llama-3.3-70b-versatile)...[/bold yellow]")
            answer = self.groq.generate(prompt)
            return {"answer": answer, "llm_backend_used": "llama-3.3-70b-versatile (Groq Fallback)"}

_router_instance = None

def get_llm_router() -> LLMRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance
