import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api import auth, users, subjects, materials, examinations, questions, system
import app.models

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(subjects.router, prefix="/api/subjects", tags=["subjects"])
app.include_router(materials.router, prefix="/api/materials", tags=["materials"])
app.include_router(examinations.router, prefix="/api/examinations", tags=["examinations"])
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(system.router, prefix="/api/system", tags=["system"])

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(os.path.join(frontend_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "AI Exam Generator API is running. Build frontend with 'npm run build' in frontend/ to serve UI."}

