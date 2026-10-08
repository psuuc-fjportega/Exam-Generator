"""Tests for the upload-and-generate endpoint and matching question type."""
import io
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.models.examination_blueprint import QuestionType, QuestionDifficulty
from app.api.materials import _resolve_question_types, _build_blueprints_from_types

# ---------------------------------------------------------------------------
# In-memory test DB (mirrors the pattern in other test files)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Shared auth helpers
# ---------------------------------------------------------------------------

def _register_and_login(email: str = "gen_teacher@test.com",
                         password: str = "pass1234",
                         role: str = "teacher") -> dict:
    """Register (idempotent) and return auth headers."""
    client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Gen",
        "last_name": "Teacher",
        "role": role,
    })
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_subject(headers: dict, name: str = "Test Subject") -> int:
    import random
    code = f"TEST{random.randint(100, 999)}"
    resp = client.post(
        "/api/subjects",
        json={"name": name, "code": code, "description": "A test subject"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Subject creation failed: {resp.text}"
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Unit tests – helper functions
# ---------------------------------------------------------------------------

class TestResolveQuestionTypes:
    def test_all_preset_returns_every_type(self):
        result = _resolve_question_types("all")
        assert set(result) == set(QuestionType)

    def test_single_type_multiple_choice(self):
        result = _resolve_question_types("multiple_choice")
        assert result == [QuestionType.multiple_choice]

    def test_single_type_matching(self):
        result = _resolve_question_types("matching")
        assert result == [QuestionType.matching]

    def test_case_insensitive(self):
        result = _resolve_question_types("ESSAY")
        assert result == [QuestionType.essay]

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid exam_type"):
            _resolve_question_types("invalid_type")


class TestBuildBlueprintsFromTypes:
    def test_single_type_gets_all_questions(self):
        types = [QuestionType.multiple_choice]
        blueprints = _build_blueprints_from_types(types, 10, QuestionDifficulty.medium)
        assert len(blueprints) == 1
        assert blueprints[0]["quantity"] == 10
        assert blueprints[0]["question_type"] == QuestionType.multiple_choice

    def test_total_quantity_equals_requested(self):
        types = list(QuestionType)  # 5 types
        blueprints = _build_blueprints_from_types(types, 12, QuestionDifficulty.easy)
        total = sum(bp["quantity"] for bp in blueprints)
        assert total == 12

    def test_even_distribution(self):
        types = [QuestionType.multiple_choice, QuestionType.essay]
        blueprints = _build_blueprints_from_types(types, 10, QuestionDifficulty.hard)
        assert len(blueprints) == 2
        assert all(bp["quantity"] == 5 for bp in blueprints)

    def test_remainder_goes_to_first(self):
        types = [QuestionType.identification, QuestionType.true_false]
        blueprints = _build_blueprints_from_types(types, 3, QuestionDifficulty.medium)
        quantities = [bp["quantity"] for bp in blueprints]
        assert quantities[0] == 2  # first gets the extra
        assert quantities[1] == 1

    def test_correct_difficulty_assigned(self):
        types = [QuestionType.matching]
        blueprints = _build_blueprints_from_types(types, 5, QuestionDifficulty.hard)
        assert blueprints[0]["difficulty"] == QuestionDifficulty.hard


# ---------------------------------------------------------------------------
# Matching question type – QuestionType enum
# ---------------------------------------------------------------------------

class TestMatchingQuestionType:
    def test_matching_in_enum(self):
        assert "matching" in {qt.value for qt in QuestionType}

    def test_enum_has_five_values(self):
        assert len(list(QuestionType)) == 5


# ---------------------------------------------------------------------------
# Integration tests – upload-and-generate endpoint
# ---------------------------------------------------------------------------

class TestUploadAndGenerateEndpoint:
    def test_endpoint_is_registered(self):
        from app.api.materials import router
        mat_paths = [r.path for r in router.routes]
        assert "/upload-and-generate" in mat_paths

    def test_invalid_exam_type_returns_422(self):
        headers = _register_and_login()
        subject_id = _create_subject(headers, "Subject A")
        fake_file = io.BytesIO(b"Some learning material content for testing purposes.")
        resp = client.post(
            "/api/materials/upload-and-generate",
            headers=headers,
            data={
                "subject_id": subject_id,
                "exam_title": "Test Exam",
                "exam_type": "not_a_real_type",
                "total_questions": "5",
                "difficulty": "medium",
                "time_limit_minutes": "30",
                "passing_score": "50",
            },
            files={"file": ("test.txt", fake_file, "text/plain")},
        )
        assert resp.status_code == 422

    def test_invalid_difficulty_returns_422(self):
        headers = _register_and_login()
        subject_id = _create_subject(headers, "Subject B")
        fake_file = io.BytesIO(b"Some learning material content.")
        resp = client.post(
            "/api/materials/upload-and-generate",
            headers=headers,
            data={
                "subject_id": subject_id,
                "exam_title": "Test Exam",
                "exam_type": "multiple_choice",
                "total_questions": "5",
                "difficulty": "ultra_hard",
                "time_limit_minutes": "30",
                "passing_score": "50",
            },
            files={"file": ("test.txt", fake_file, "text/plain")},
        )
        assert resp.status_code == 422

    def test_successful_upload_and_generate_txt(self):
        """End-to-end: upload a TXT file and generate a multiple-choice exam (uses mock AI)."""
        from unittest.mock import patch
        headers = _register_and_login()
        subject_id = _create_subject(headers, "Python Subject")
        content = (
            b"Chapter 1: Introduction to Python\n"
            b"Python is a high-level programming language created by Guido van Rossum in 1991.\n"
            b"It supports procedural, object-oriented, and functional programming paradigms.\n"
            b"Python uses dynamic typing and garbage collection.\n"
            b"The Zen of Python is a collection of guiding principles for Python code.\n"
        )
        fake_file = io.BytesIO(content)

        # Patch the document_service to use the test session instead of the real SessionLocal
        with patch("app.services.document_service.SessionLocal", TestingSessionLocal):
            resp = client.post(
                "/api/materials/upload-and-generate",
                headers=headers,
                data={
                    "subject_id": subject_id,
                    "exam_title": "Python Intro Quiz",
                    "exam_type": "multiple_choice",
                    "total_questions": "5",
                    "difficulty": "easy",
                    "time_limit_minutes": "30",
                    "passing_score": "60",
                },
                files={"file": ("python_notes.txt", fake_file, "text/plain")},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "material" in data
        assert "examination" in data
        assert "generation" in data
        assert data["examination"]["title"] == "Python Intro Quiz"
        assert data["examination"]["total_questions"] == 5
        # Blueprint should be multiple_choice only
        assert len(data["examination"]["blueprints"]) == 1
        assert data["examination"]["blueprints"][0]["question_type"] == "multiple_choice"

    def test_matching_type_accepted(self):
        """Verify that exam_type='matching' is accepted by the endpoint."""
        from unittest.mock import patch
        headers = _register_and_login()
        subject_id = _create_subject(headers, "Matching Subject")
        content = b"Term A: Definition one. Term B: Definition two. Term C: Definition three."
        fake_file = io.BytesIO(content)
        with patch("app.services.document_service.SessionLocal", TestingSessionLocal):
            resp = client.post(
                "/api/materials/upload-and-generate",
                headers=headers,
                data={
                    "subject_id": subject_id,
                    "exam_title": "Matching Quiz",
                    "exam_type": "matching",
                    "total_questions": "4",
                    "difficulty": "medium",
                    "time_limit_minutes": "20",
                    "passing_score": "50",
                },
                files={"file": ("terms.txt", fake_file, "text/plain")},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["examination"]["blueprints"][0]["question_type"] == "matching"

    def test_all_types_creates_multiple_blueprints(self):
        """exam_type='all' should produce blueprints for every question type."""
        from unittest.mock import patch
        headers = _register_and_login()
        subject_id = _create_subject(headers, "Mixed Subject")
        content = (
            b"Machine learning is a subset of artificial intelligence.\n"
            b"Supervised learning uses labeled training data to make predictions.\n"
            b"Unsupervised learning finds patterns in unlabeled data.\n"
            b"Neural networks are inspired by the structure of the human brain.\n"
            b"Deep learning uses multiple layers of neural networks for complex tasks.\n"
        ) * 5  # repeat for enough text
        fake_file = io.BytesIO(content)
        with patch("app.services.document_service.SessionLocal", TestingSessionLocal):
            resp = client.post(
                "/api/materials/upload-and-generate",
                headers=headers,
                data={
                    "subject_id": subject_id,
                    "exam_title": "Mixed Exam",
                    "exam_type": "all",
                    "total_questions": "10",
                    "difficulty": "medium",
                    "time_limit_minutes": "60",
                    "passing_score": "50",
                },
                files={"file": ("notes.txt", fake_file, "text/plain")},
            )
        assert resp.status_code == 200, resp.text
        blueprints = resp.json()["examination"]["blueprints"]
        generated_types = {bp["question_type"] for bp in blueprints}
        # All 5 QuestionType values should appear
        assert generated_types == {qt.value for qt in QuestionType}

    def test_unauthenticated_returns_401(self):
        """Requests without a token should be rejected."""
        fake_file = io.BytesIO(b"content")
        resp = client.post(
            "/api/materials/upload-and-generate",
            data={
                "subject_id": "1",
                "exam_title": "No Auth Exam",
                "exam_type": "multiple_choice",
                "total_questions": "5",
                "difficulty": "medium",
                "time_limit_minutes": "30",
                "passing_score": "50",
            },
            files={"file": ("file.txt", fake_file, "text/plain")},
        )
        assert resp.status_code == 401
