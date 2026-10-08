from typing import List, Dict, Any
import tiktoken

def get_token_count(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Fallback approximation
        return len(text.split())

def chunk_text(extracted_data: List[Dict[str, Any]], max_tokens: int = 1000) -> List[Dict[str, Any]]:
    chunks = []
    chunk_index = 0
    
    for item in extracted_data:
        text = item["text"]
        page_number = item["page_number"]
        section_title = item["section_title"]
        
        # Simple splitting by paragraphs for MVP chunking
        paragraphs = text.split("\n")
        current_chunk_text = ""
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = get_token_count(para)
            if current_tokens + para_tokens > max_tokens and current_chunk_text:
                chunks.append({
                    "chunk_index": chunk_index,
                    "content": current_chunk_text.strip(),
                    "page_number": page_number,
                    "section_title": section_title,
                    "token_count": current_tokens
                })
                chunk_index += 1
                current_chunk_text = para + "\n"
                current_tokens = para_tokens
            else:
                current_chunk_text += para + "\n"
                current_tokens += para_tokens
                
        if current_chunk_text.strip():
            chunks.append({
                "chunk_index": chunk_index,
                "content": current_chunk_text.strip(),
                "page_number": page_number,
                "section_title": section_title,
                "token_count": current_tokens
            })
            chunk_index += 1
            
    return chunks
