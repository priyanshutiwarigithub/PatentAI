import os
import httpx
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()

class OllamaUnavailableError(Exception):
    pass

class OllamaClient:
    """
    Ollama client connecting to Qwen3-4B on remote GPU server (192.168.6.50:11434).
    """
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = "qwen2.5:3b"

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_ctx": 8192,
                "num_predict": 1024
            }
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
                else:
                    raise OllamaUnavailableError(f"Ollama HTTP {response.status_code}: {response.text}")
        except Exception as e:
            console.print(f"[yellow]Ollama Qwen3-4B connection error ({e}). Flagging for fallback.[/yellow]")
            raise OllamaUnavailableError(str(e))
