import os
import pytest
from app.services.extraction_service import extract_txt
from app.services.chunking_service import chunk_text, get_token_count

def test_extract_txt(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is a test document.\nIt has multiple lines.")
    
    extracted = extract_txt(str(test_file))
    assert len(extracted) == 1
    assert "This is a test document" in extracted[0]["text"]

def test_chunk_text():
    extracted_data = [
        {"page_number": "1", "text": "Sentence 1.\nSentence 2.", "section_title": "Intro"}
    ]
    # We set max_tokens=1 to force splitting at paragraphs
    chunks = chunk_text(extracted_data, max_tokens=1)
    
    assert len(chunks) == 2
    assert chunks[0]["content"] == "Sentence 1."
    assert chunks[1]["content"] == "Sentence 2."
    
def test_token_count():
    count = get_token_count("Hello world")
    assert count > 0
