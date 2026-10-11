import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.material import Material, ProcessingStatus
from app.models.document_chunk import DocumentChunk
from app.models.examination_blueprint import QuestionDifficulty, QuestionType
from app.schemas.material import (
    DocumentAnalysis,
    DocumentStats,
    QuestionTypeDistribution,
)
from app.services.ai_service import ai_service
from app.services.chunking_service import get_token_count

logger = logging.getLogger(__name__)


def _load_prompt_template(filename: str) -> str:
    path = os.path.join(os.getcwd(), "prompts", filename)
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _calculate_document_stats(
    chunks: List[DocumentChunk],
    original_file_name: str = "",
    file_type: str = "",
) -> DocumentStats:
    total_tokens = sum(c.token_count or 0 for c in chunks)
    total_chars = sum(len(c.content or "") for c in chunks)
    estimated_words = sum(len((c.content or "").split()) for c in chunks)
    return DocumentStats(
        chunk_count=len(chunks),
        total_tokens=total_tokens,
        total_characters=total_chars,
        estimated_words=estimated_words,
        file_type=file_type,
        original_file_name=original_file_name,
    )


def _heuristic_analysis(
    chunks: List[DocumentChunk],
    original_file_name: str,
    file_type: str,
) -> DocumentAnalysis:
    """Fallback heuristic analyzer when AI service is unavailable or in offline testing."""
    stats = _calculate_document_stats(chunks, original_file_name, file_type)
    
    # Extract candidate title
    clean_base_name = re.sub(r"[-_]+", " ", os.path.splitext(original_file_name)[0]).title()
    suggested_title = f"Examination: {clean_base_name}"
    
    # Try finding title in first chunk
    first_lines = []
    if chunks and chunks[0].content:
        first_lines = [line.strip() for line in chunks[0].content.split("\n") if line.strip()]
        if first_lines:
            candidate = first_lines[0]
            if len(candidate) < 80 and not candidate.endswith("."):
                suggested_title = f"Examination: {candidate}"
    
    # Extract topics from section titles or recurring capitalized terms
    topics = []
    for c in chunks:
        if c.section_title and c.section_title not in topics:
            topics.append(c.section_title)
            
    if not topics and first_lines:
        topics = [line[:40] for line in first_lines[1:5] if len(line) > 5]
        
    if not topics:
        topics = [f"{clean_base_name} - Core Principles", f"{clean_base_name} - Applications"]

    # Recommended question count based on token count
    if stats.total_tokens < 500:
        rec_questions = 5
    elif stats.total_tokens < 2000:
        rec_questions = 10
    else:
        rec_questions = min(20, max(10, stats.chunk_count * 3))
        
    rec_time = max(15, rec_questions * 3)

    # Balanced distribution
    mc_qty = max(2, int(rec_questions * 0.4))
    tf_qty = max(1, int(rec_questions * 0.2))
    id_qty = max(1, int(rec_questions * 0.2))
    essay_qty = max(1, int(rec_questions * 0.1))
    matching_qty = max(0, rec_questions - (mc_qty + tf_qty + id_qty + essay_qty))
    if matching_qty < 2 and matching_qty > 0:
        # matching requires at least 2 pairs or fold into multiple choice
        mc_qty += matching_qty
        matching_qty = 0

    distribution = QuestionTypeDistribution(
        multiple_choice=mc_qty,
        true_false=tf_qty,
        identification=id_qty,
        essay=essay_qty,
        matching=matching_qty,
    )

    summary = (
        f"This material covers {clean_base_name}, detailing core principles, structure, "
        f"and key concepts across {len(chunks)} document section(s)."
    )

    return DocumentAnalysis(
        title_suggestion=suggested_title,
        summary=summary,
        key_topics=topics[:6],
        key_concepts=[f"Concept: {t}" for t in topics[:5]],
        learning_objectives=[
            f"Understand the fundamental principles of {clean_base_name}",
            f"Identify key mechanisms and definitions discussed in the material",
            f"Apply the concepts to solve domain-specific problems",
        ],
        estimated_difficulty=QuestionDifficulty.medium,
        difficulty_reasoning="Assessed as medium based on foundational coverage and technical scope.",
        recommended_total_questions=rec_questions,
        recommended_time_minutes=rec_time,
        recommended_distribution=distribution,
        document_stats=stats,
    )


def analyze_material_content(
    chunks: List[DocumentChunk],
    original_file_name: str,
    file_type: str,
) -> DocumentAnalysis:
    """Analyze document chunks using Gemini AI with fallback to heuristic analysis."""
    stats = _calculate_document_stats(chunks, original_file_name, file_type)
    
    if not chunks:
        return _heuristic_analysis(chunks, original_file_name, file_type)

    # Build representative source text (cap at 20,000 tokens to stay fast & responsive)
    source_parts = []
    current_tokens = 0
    for chunk in chunks:
        part = f"[CHUNK {chunk.chunk_index}]: {chunk.content}\n\n"
        part_tokens = chunk.token_count or get_token_count(part)
        if current_tokens + part_tokens > 20000:
            source_parts.append("... [Additional content truncated for analysis] ...")
            break
        source_parts.append(part)
        current_tokens += part_tokens

    source_material_text = "".join(source_parts)

    try:
        template = _load_prompt_template("document_analysis.txt")
        prompt = template.format(source_material=source_material_text)

        result_dict = ai_service.generate_structured_json(
            prompt=prompt,
            response_schema=DocumentAnalysis,
        )

        # Parse distribution if dict
        dist_data = result_dict.get("recommended_distribution", {})
        if isinstance(dist_data, dict):
            distribution = QuestionTypeDistribution(
                multiple_choice=dist_data.get("multiple_choice", 4),
                true_false=dist_data.get("true_false", 2),
                identification=dist_data.get("identification", 2),
                essay=dist_data.get("essay", 1),
                matching=dist_data.get("matching", 1),
            )
        else:
            distribution = QuestionTypeDistribution()

        diff_str = str(result_dict.get("estimated_difficulty", "medium")).lower()
        try:
            difficulty = QuestionDifficulty(diff_str)
        except ValueError:
            difficulty = QuestionDifficulty.medium

        analysis = DocumentAnalysis(
            title_suggestion=result_dict.get("title_suggestion") or f"Exam: {original_file_name}",
            summary=result_dict.get("summary") or "Document analysis summary.",
            key_topics=result_dict.get("key_topics") or ["Overview"],
            key_concepts=result_dict.get("key_concepts") or ["Foundational Concept"],
            learning_objectives=result_dict.get("learning_objectives") or ["Understand material"],
            estimated_difficulty=difficulty,
            difficulty_reasoning=result_dict.get("difficulty_reasoning", "Standard cognitive depth."),
            recommended_total_questions=result_dict.get("recommended_total_questions", 10),
            recommended_time_minutes=result_dict.get("recommended_time_minutes", 60),
            recommended_distribution=distribution,
            document_stats=stats,
        )
        return analysis

    except Exception as exc:
        logger.warning("AI document analysis encountered error, using heuristic fallback: %s", exc)
        return _heuristic_analysis(chunks, original_file_name, file_type)


def analyze_material_record(
    db: Session,
    material_id: int,
    refresh: bool = False,
) -> DocumentAnalysis:
    """
    Retrieve or compute the AI document analysis for a stored Material record.
    Persists the resulting analysis into the database.
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise ValueError(f"Material with id {material_id} not found.")

    # Return cached analysis if available and not forced to refresh
    if not refresh and material.analysis_json:
        try:
            cached_dict = json.loads(material.analysis_json)
            return DocumentAnalysis.model_validate(cached_dict)
        except Exception:
            pass

    # Ensure material chunks are extracted
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.material_id == material.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    if not chunks:
        from app.services.document_service import process_material_sync
        process_material_sync(material.id)
        db.refresh(material)
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.material_id == material.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

    analysis = analyze_material_content(
        chunks=chunks,
        original_file_name=material.original_file_name,
        file_type=material.file_type,
    )

    # Persist analysis on Material
    material.summary = analysis.summary
    material.analysis_json = json.dumps(analysis.model_dump())
    db.commit()
    db.refresh(material)

    return analysis
