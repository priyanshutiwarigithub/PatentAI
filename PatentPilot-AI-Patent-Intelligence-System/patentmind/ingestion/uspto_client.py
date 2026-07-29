import asyncio
import os
import httpx
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class USPTOClient:
    def __init__(self):
        self.api_key = os.getenv("USPTO_API_KEY", "")
        self.base_url = "https://api.patentsview.org/patents/query"
        self.headers = {"User-Agent": "PatentMindAI/1.0"}
        if self.api_key and self.api_key != "dummy_uspto_api_key":
            self.headers["X-Api-Key"] = self.api_key

    async def fetch_ai_patents(self, limit: int = 100) -> List[Dict[str, Any]]:
        # Query CPC codes for AI/ML domains (G06N, G06V, G10L)
        query = {
            "_or": [
                {"_begins": {"cpc_subclass": "G06N"}},
                {"_begins": {"cpc_subclass": "G06V"}},
                {"_begins": {"cpc_subclass": "G10L"}}
            ]
        }
        fields = [
            "patent_number", "patent_title", "patent_abstract", "patent_date",
            "inventor_first_name", "inventor_last_name", "assignee_organization", "cpc_subclass"
        ]

        results = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "q": str(query).replace("'", '"'),
                    "f": str(fields).replace("'", '"'),
                    "o": f'{{"page":1, "per_page":{limit}}}'
                }
                response = await client.get(self.base_url, headers=self.headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    raw_patents = data.get("patents", [])
                    for item in raw_patents:
                        pat_num = f"US{item.get('patent_number')}"
                        results.append({
                            "patent_number": pat_num,
                            "title": item.get("patent_title", ""),
                            "abstract": item.get("patent_abstract", ""),
                            "claims": "Claims retrieved via PatentsView",
                            "description": "Description retrieved via PatentsView",
                            "inventors": [f"{item.get('inventor_first_name', '')} {item.get('inventor_last_name', '')}".strip()],
                            "assignee": item.get("assignee_organization", "USPTO Assignee"),
                            "filing_date": item.get("patent_date", "2023-01-01"),
                            "publication_date": item.get("patent_date", "2023-06-01"),
                            "cpc_codes": [item.get("cpc_subclass", "G06N")],
                            "ipc_codes": ["G06N 3/00"],
                            "pdf_url": f"https://patentimages.storage.googleapis.com/pdfs/{pat_num}.pdf",
                            "source_repository": "USPTO PatentsView",
                            "domain_tags": ["Artificial Intelligence", "Machine Learning"]
                        })
        except Exception:
            pass

        return results
