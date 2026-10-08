import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db

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
def teacher_data():
    client.post(
        "/api/auth/register",
        json={
            "email": "teacher_exam@example.com",
            "password": "teacherpassword",
            "first_name": "Teacher",
            "last_name": "User",
            "role": "teacher"
        },
    )
    res = client.post(
        "/api/auth/login",
        data={"username": "teacher_exam@example.com", "password": "teacherpassword"},
    )
    token = res.json()["access_token"]
    
    # Create a subject to attach examination
    res_sub = client.post(
        "/api/subjects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Science 101", "code": "SCI101"}
    )
    subject_id = res_sub.json()["id"]
    return {"token": token, "subject_id": subject_id}


def test_create_examination(teacher_data):
    token = teacher_data["token"]
    subject_id = teacher_data["subject_id"]

    response = client.post(
        "/api/examinations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject_id": subject_id,
            "title": "Midterm Exam",
            "description": "Midterm for Science 101",
            "total_questions": 50,
            "time_limit_minutes": 60,
            "passing_score": 75,
            "blueprints": [
                {
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "quantity": 30,
                    "points": 1
                },
                {
                    "question_type": "true_false",
                    "difficulty": "easy",
                    "quantity": 20,
                    "points": 1
                }
            ]
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Midterm Exam"
    assert len(data["blueprints"]) == 2

def test_create_examination_invalid_totals(teacher_data):
    token = teacher_data["token"]
    subject_id = teacher_data["subject_id"]

    response = client.post(
        "/api/examinations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject_id": subject_id,
            "title": "Bad Exam",
            "total_questions": 50,
            "time_limit_minutes": 60,
            "passing_score": 75,
            "blueprints": [
                {
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "quantity": 10, # Doesn't add up to 50
                    "points": 1
                }
            ]
        }
    )
    assert response.status_code == 422 # Pydantic validation error
