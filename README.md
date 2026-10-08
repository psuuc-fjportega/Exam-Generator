# AI-Powered Examination Generator System

Phase 1 Foundation.

## Setup Instructions

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows)
3. Install requirements: `pip install -r requirements.txt`
4. Setup database: `alembic upgrade head`
5. Run the backend app: `uvicorn app.main:app --reload`
6. Run tests: `pytest`

## Frontend (React + Vite + Tailwind CSS)

1. Navigate to frontend: `cd frontend`
2. Install dependencies: `npm install`
3. Run dev server: `npm run dev` (runs at http://localhost:5173 with proxy to backend at http://localhost:8000)
4. Or build for production: `npm run build` (compiled to `frontend/dist` and automatically served by FastAPI at http://localhost:8000)

