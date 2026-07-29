import re
from typing import List, Dict, Any

class PatentChunker:
    """
    Section-aware & Claim-aware chunking strategy:
    - CLAIMS section: split numbered claims into individual chunks (never break across chunks).
    - Other sections: 512 tokens (~2000 chars) recursive window with 64 tokens (~250 chars) overlap.
    """
    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size_char = chunk_size * 4
        self.overlap_char = overlap * 4

    def chunk_patent(self, patent_number: str, cleaned_text: str, s3_key: str, claims_text: str = "") -> List[Dict[str, Any]]:
        chunks = []
        chunk_index = 0

        # Process Claims Section explicitly first
        if claims_text:
            # Match claims starting with number e.g. "1.", "2."
            claim_pattern = re.compile(r'(\d+)\.\s+(.*?)(?=\n\d+\.|\Z)', re.DOTALL)
            found_claims = claim_pattern.findall(claims_text)
            
            if found_claims:
                for claim_num_str, claim_body in found_claims:
                    chunk_index += 1
                    chunks.append({
                        "patent_number": patent_number,
                        "section_name": "CLAIMS",
                        "claim_number": int(claim_num_str),
                        "chunk_index": chunk_index,
                        "chunk_text": f"Claim {claim_num_str}: {claim_body.strip()}",
                        "source_s3_key": s3_key
                    })
            else:
                chunk_index += 1
                chunks.append({
                    "patent_number": patent_number,
                    "section_name": "CLAIMS",
                    "claim_number": 1,
                    "chunk_index": chunk_index,
                    "chunk_text": f"Claims: {claims_text.strip()}",
                    "source_s3_key": s3_key
                })

        # Process standard prose sections
        sections = re.split(r'===\s*([A-Z\s]+)\s*===', cleaned_text)
        current_section = "DESCRIPTION"

        for i in range(len(sections)):
            part = sections[i].strip()
            if not part:
                continue
            if part in ["CLAIMS", "ABSTRACT", "DESCRIPTION", "BACKGROUND", "SUMMARY", "BRIEF DESCRIPTION OF DRAWINGS"]:
                current_section = part
                continue

            if current_section == "CLAIMS":
                continue # Already handled in claims processing above

            # Perform recursive sliding window chunking
            start = 0
            text_len = len(part)
            while start < text_len:
                end = min(start + self.chunk_size_char, text_len)
                segment = part[start:end].strip()
                if segment:
                    chunk_index += 1
                    chunks.append({
                        "patent_number": patent_number,
                        "section_name": current_section,
                        "claim_number": None,
                        "chunk_index": chunk_index,
                        "chunk_text": segment,
                        "source_s3_key": s3_key
                    })
                start += (self.chunk_size_char - self.overlap_char)

        return chunks
