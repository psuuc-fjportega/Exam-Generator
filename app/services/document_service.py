from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.material import Material, ProcessingStatus
from app.models.document_chunk import DocumentChunk
from app.services.extraction_service import extract_text_from_file
from app.services.chunking_service import chunk_text

def process_material_sync(material_id: int):
    # Using a new session for background processing
    db: Session = SessionLocal()
    try:
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            return
            
        material.processing_status = ProcessingStatus.processing
        db.commit()
        
        try:
            extracted_data = extract_text_from_file(material.file_path, material.file_type)
            chunks_data = chunk_text(extracted_data)
            
            for chunk_dict in chunks_data:
                chunk = DocumentChunk(
                    material_id=material.id,
                    chunk_index=chunk_dict["chunk_index"],
                    content=chunk_dict["content"],
                    page_number=chunk_dict["page_number"],
                    section_title=chunk_dict["section_title"],
                    token_count=chunk_dict["token_count"]
                )
                db.add(chunk)
                
            material.processing_status = ProcessingStatus.processed
            db.commit()
        except Exception as e:
            material.processing_status = ProcessingStatus.failed
            material.processing_error = str(e)
            db.commit()
            
    finally:
        db.close()
