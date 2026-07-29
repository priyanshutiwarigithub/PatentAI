import asyncio
import os
import httpx
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class GooglePatentsClient:
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")

    async def fetch_ai_patents(self, limit: int = 40) -> List[Dict[str, Any]]:
        results = []
        if not self.serpapi_key or self.serpapi_key == "dummy_serpapi_key":
            return results

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "engine": "google_patents",
                    "q": "artificial intelligence OR machine learning",
                    "api_key": self.serpapi_key,
                    "num": limit
                }
                response = await client.get("https://serpapi.com/search", params=params)
                if response.status_code == 200:
                    data = response.json()
                    organic_results = data.get("organic_results", [])
                    
                    for item in organic_results:
                        pat_num = item.get("patent_id", "")
                        if not pat_num:
                            continue
                        
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        assignee = item.get("assignee", "Unknown")
                        inventors = item.get("inventors", "Unknown")
                        pub_date = item.get("publication_date", "2023-01-01")
                        
                        pdf_url = item.get("pdf", "")
                        if not pdf_url:
                            pdf_url = f"https://patentimages.storage.googleapis.com/pdfs/{pat_num}.pdf"

                        results.append({
                            "patent_number": pat_num,
                            "title": title,
                            "abstract": snippet,
                            "claims": "Fetched via SerpApi Google Patents",
                            "description": snippet,
                            "inventors": [inventors],
                            "assignee": assignee,
                            "filing_date": pub_date,
                            "publication_date": pub_date,
                            "cpc_codes": ["G06N"],
                            "ipc_codes": ["G06N"],
                            "pdf_url": pdf_url,
                            "source_repository": "Google Patents / SerpApi",
                            "domain_tags": ["Artificial Intelligence", "Machine Learning"]
                        })
        except Exception:
            pass

        return results
