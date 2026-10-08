import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.document_chunk import DocumentChunk
from app.models.material import Material, ProcessingStatus
from app.models.question import GenerationMethod, Question, QuestionStatus
from app.models.question_choice import QuestionChoice
from app.models.question_source import QuestionSource
from app.models.examination_blueprint import QuestionDifficulty, QuestionType
from app.models.examination_question import ExaminationQuestion

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _use_isolated_db():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous is not None:
        app.dependency_overrides[get_db] = previous
    else:
        app.dependency_overrides.pop(get_db, None)


def _register_teacher(email: str) -> str:
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "teacherpassword",
            "first_name": "Teacher",
            "last_name": "User",
            "role": "teacher",
        },
    )
    res = client.post(
        "/api/auth/login",
        data={"username": email, "password": "teacherpassword"},
    )
    return res.json()["access_token"]


def test_validate_question_endpoint_and_authorization():
    token = _register_teacher("teacher_val@example.com")
    other_token = _register_teacher("teacher_other@example.com")

    subject = client.post(
        "/api/subjects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Biology Validation", "code": "BIOVAL101"},
    )
    subject_id = subject.json()["id"]

    db = TestingSessionLocal()
    material = Material(
        subject_id=subject_id,
        uploaded_by=1,
        file_name="cells.txt",
        original_file_name="cells.txt",
        file_type="txt",
        file_size=120,
        file_path="cells.txt",
        processing_status=ProcessingStatus.processed,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    chunk = DocumentChunk(
        material_id=material.id,
        chunk_index=0,
        content="The mitochondria is the powerhouse of the cell and produces ATP.",
        page_number="3",
        section_title="Cell Structure",
        token_count=12,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    question = Question(
        subject_id=subject_id,
        question_text="Which organelle is the powerhouse of the cell?",
        question_type=QuestionType.multiple_choice,
        difficulty=QuestionDifficulty.easy,
        explanation="The mitochondria is the powerhouse of the cell.",
        status=QuestionStatus.draft,
        generation_method=GenerationMethod.ai,
        created_by=1,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    db.add_all(
        [
            QuestionChoice(question_id=question.id, choice_text="Mitochondria", choice_order=0, is_correct=True),
            QuestionChoice(question_id=question.id, choice_text="Nucleus", choice_order=1, is_correct=False),
            QuestionSource(question_id=question.id, chunk_id=chunk.id, relevance_score=0.8),
        ]
    )
    db.commit()
    question_id = question.id
    db.close()

    student_res = client.post(
        "/api/auth/register",
        json={
            "email": "student_val@example.com",
            "password": "studentpassword",
            "first_name": "Student",
            "last_name": "User",
            "role": "student",
        },
    )
    assert student_res.status_code in (200, 201)
    student_login = client.post(
        "/api/auth/login",
        data={"username": "student_val@example.com", "password": "studentpassword"},
    )
    student_token = student_login.json()["access_token"]

    forbidden = client.post(
        f"/api/questions/{question_id}/validate",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert forbidden.status_code == 403

    other = client.post(
        f"/api/questions/{question_id}/validate",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other.status_code == 403

    response = client.post(
        f"/api/questions/{question_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["validation"]["valid"] is True
    assert data["validation"]["source_supported"] is True
    assert data["question"]["status"] == "review"
    assert data["question"]["sources"][0]["page_number"] == "3"

    listed = client.get(
        f"/api/questions?subject_id={subject_id}&status=review",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert data["validation"]["recommended_action"] == "review"

    exam = client.post(
        "/api/examinations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject_id": subject_id,
            "title": "Validation Exam",
            "total_questions": 1,
            "time_limit_minutes": 10,
            "passing_score": 1,
            "blueprints": [
                {
                    "question_type": "multiple_choice",
                    "difficulty": "easy",
                    "quantity": 1,
                    "points": 1,
                }
            ],
        },
    )
    assert exam.status_code in (200, 201), exam.text
    exam_id = exam.json()["id"]
    db = TestingSessionLocal()
    db.add(
        ExaminationQuestion(
            examination_id=exam_id,
            question_id=question_id,
            question_order=1,
            points=1,
        )
    )
    db.commit()
    db.close()

    batch = client.post(
        f"/api/examinations/{exam_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert batch.status_code == 200, batch.text
    batch_data = batch.json()
    assert batch_data["status"] == "success"
    assert batch_data["invalid_count"] == 0
    assert batch_data["needs_regeneration"] == 0
