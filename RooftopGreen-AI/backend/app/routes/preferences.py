from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project
from app.schemas import PreferencesResponse
import uuid

router = APIRouter(tags=["preferences"])

@router.post("/preferences", response_model=PreferencesResponse)
async def save_preferences(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    session_id = data.get("session_id") or f"sess_{uuid.uuid4().hex[:10]}"
    
    project = db.query(Project).filter(Project.session_id == session_id).first()
    if not project:
        project = Project(session_id=session_id, preferences=data)
        db.add(project)
    else:
        project.preferences = data
    
    db.commit()
    db.refresh(project)
    
    return {
        "session_id": session_id,
        "project_id": project.id,
        "status": "ok"
    }

@router.get("/preferences/{session_id}")
def get_preferences(session_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.session_id == session_id).first()
    if not project:
        return {"session_id": session_id, "preferences": {}}
    return {"session_id": session_id, "preferences": project.preferences or {}}
