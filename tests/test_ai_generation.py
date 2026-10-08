import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.document_chunk import DocumentChunk
from app.models.material import Material, ProcessingStatus

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="module")
def teacher_and_exam():
    # Setup user
    client.post(
        "/api/auth/register",
        json={
            "email": "teacher_gen@example.com",
            "password": "teacherpassword",
            "first_name": "Teacher",
            "last_name": "User",
            "role": "teacher"
        },
    )
    res = client.post(
        "/api/auth/login",
        data={"username": "teacher_gen@example.com", "password": "teacherpassword"},
    )
    token = res.json()["access_token"]
    
    # Setup subject
    res_sub = client.post(
        "/api/subjects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Geography 101", "code": "GEO101"}
    )
    subject_id = res_sub.json()["id"]
    
    # Setup exam
    res_exam = client.post(
        "/api/examinations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject_id": subject_id,
            "title": "History Quiz",
            "total_questions": 1,
            "time_limit_minutes": 10,
            "passing_score": 1,
            "blueprints": [
                {
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "quantity": 1,
                    "points": 1
                }
            ]
        }
    )
    exam_id = res_exam.json()["id"]
    
    return {"token": token, "subject_id": subject_id, "exam_id": exam_id}


def test_generate_exam_questions(teacher_and_exam):
    token = teacher_and_exam["token"]
    subject_id = teacher_and_exam["subject_id"]
    exam_id = teacher_and_exam["exam_id"]
    
    db_gen = app.dependency_overrides.get(get_db, get_db)()
    db = next(db_gen)
    
    mat = Material(
        subject_id=subject_id, 
        uploaded_by=1, 
        file_name="mock.txt", 
        original_file_name="mock.txt",
        file_type="txt",
        file_size=100,
        file_path="mock.txt",
        processing_status=ProcessingStatus.processed
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    
    chunk = DocumentChunk(
        material_id=mat.id,
        chunk_index=0,
        content="This is history content for the mock.",
        token_count=10
    )
    db.add(chunk)
    db.commit()
    try:
        next(db_gen)
    except StopIteration:
        pass
    
    # Trigger generation
    response = client.post(
        f"/api/examinations/{exam_id}/generate",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert "questions" in data["generated_data"]
    assert len(data["generated_data"]["questions"]) > 0
