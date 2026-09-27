from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
import models

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Powered Data Intelligence Platform API",
    description="Core AI Orchestrator API for translating business requirements into data collection workflows.",
    version="0.1.0"
)

# CORS Setup for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from worker import execute_data_collection_workflow
from models import CollectionTask

class PromptRequest(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI Data Intelligence Platform API is running."}

@app.post("/api/tasks")
def create_task(request: PromptRequest, db: Session = Depends(get_db)):
    # Create a new collection task in the database
    new_task = CollectionTask(original_prompt=request.prompt, status="Planning")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Parse the prompt into a workflow plan using the AI Orchestrator
    from ai_orchestrator import generate_workflow_plan
    workflow_plan = generate_workflow_plan(request.prompt)
    workflow_plan["original_prompt"] = request.prompt
    
    # Save the generated plan to the database
    from models import WorkflowPlan
    db_plan = WorkflowPlan(
        task_id=new_task.id,
        steps=workflow_plan.get("steps", []),
        target_sources=workflow_plan.get("target_sources", []),
        data_schema=workflow_plan.get("data_schema", {})
    )
    db.add(db_plan)
    db.commit()

    # Send task to Celery worker
    workflow_plan["task_id"] = new_task.id # Pass the DB task ID to the worker
    task = execute_data_collection_workflow.delay(workflow_plan)
    
    # Update DB with Celery task ID
    new_task.celery_task_id = task.id
    db.commit()
    db.refresh(new_task)
    
    return {
        "id": new_task.id,
        "celery_task_id": task.id,
        "status": "Task submitted to queue.",
        "plan": workflow_plan
    }
