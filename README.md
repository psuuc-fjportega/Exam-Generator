# AI-Powered Examination Generator System

Phase 1 Foundation.

## Setup Instructions

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows)
3. Install requirements: `pip install -r requirements.txt`
4. Setup database: `alembic upgrade head`
5. Run the backend app: `uvicorn app.main:app --reload`
6. Run tests: `pytest`

## AI Service Configuration (Google Gemini)

To generate examinations using AI:
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. Configure it in `.env`:
   ```bash
   AI_API_KEY=your_gemini_api_key_here
   ```
   *(Also accepts `GEMINI_API_KEY` or `GOOGLE_API_KEY`)*
3. **In-App Configuration**: You can also configure or update your Gemini API key directly from the web interface using the **AI Key** status button in the top navigation bar.
4. **Deploying on Render**: Since `.env` is not committed to git, add `AI_API_KEY` under **Environment Variables** in your Render service dashboard.

## Frontend (React + Vite + Tailwind CSS)

1. Navigate to frontend: `cd frontend`
2. Install dependencies: `npm install`
3. Run dev server: `npm run dev` (runs at http://localhost:5173 with proxy to backend at http://localhost:8000)
4. Or build for production: `npm run build` (compiled to `frontend/dist` and automatically served by FastAPI at http://localhost:8000)


