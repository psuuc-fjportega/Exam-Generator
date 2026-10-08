import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import io
import os

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
            "email": "teacher_mat@example.com",
            "password": "teacherpassword",
            "first_name": "Teacher",
            "last_name": "User",
            "role": "teacher"
        },
    )
    res = client.post(
        "/api/auth/login",
        data={"username": "teacher_mat@example.com", "password": "teacherpassword"},
    )
    token = res.json()["access_token"]
    
    # Create a subject to attach material
    res_sub = client.post(
        "/api/subjects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "History 101", "code": "HIST101"}
    )
    subject_id = res_sub.json()["id"]
    return {"token": token, "subject_id": subject_id}


def test_upload_material(teacher_data):
    token = teacher_data["token"]
    subject_id = teacher_data["subject_id"]
    
    # Mock a PDF file upload
    file_content = b"Mock PDF Content"
    file = io.BytesIO(file_content)
    file.name = "test_document.pdf"

    response = client.post(
        "/api/materials/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"subject_id": subject_id},
        files={"file": ("test_document.pdf", file, "application/pdf")}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["original_file_name"] == "test_document.pdf"
    assert data["file_type"] == "pdf"
    assert data["processing_status"] == "uploaded"

def test_read_materials(teacher_data):
    token = teacher_data["token"]
    
    response = client.get(
        "/api/materials",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) > 0
