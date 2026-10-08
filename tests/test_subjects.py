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
def teacher_token():
    client.post(
        "/api/auth/register",
        json={
            "email": "teacher@example.com",
            "password": "teacherpassword",
            "first_name": "Teacher",
            "last_name": "User",
            "role": "teacher"
        },
    )
    res = client.post(
        "/api/auth/login",
        data={"username": "teacher@example.com", "password": "teacherpassword"},
    )
    return res.json()["access_token"]

@pytest.fixture(scope="module")
def student_token():
    client.post(
        "/api/auth/register",
        json={
            "email": "student@example.com",
            "password": "studentpassword",
            "first_name": "Student",
            "last_name": "User",
            "role": "student"
        },
    )
    res = client.post(
        "/api/auth/login",
        data={"username": "student@example.com", "password": "studentpassword"},
    )
    return res.json()["access_token"]

def test_create_subject(teacher_token):
    response = client.post(
        "/api/subjects",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "name": "Biology 101",
            "code": "BIO101",
            "description": "Introduction to Biology"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Biology 101"
    assert data["code"] == "BIO101"
    assert "id" in data

def test_create_subject_student_forbidden(student_token):
    response = client.post(
        "/api/subjects",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "name": "Math 101",
            "code": "MATH101"
        }
    )
    assert response.status_code == 403

def test_read_subjects(teacher_token):
    response = client.get(
        "/api/subjects",
        headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) > 0
