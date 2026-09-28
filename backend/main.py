import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import datetime
import random
import time
import threading
import json
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from database import engine, Base, get_db, SessionLocal
import models
from models import CollectionTask, WorkflowPlan, ScrapedData
from ai_orchestrator import generate_workflow_plan
from scraper_agent import run_scraping_job

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tracelight · AI Data Intelligence Platform API",
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

# ---------------------------------------------------------------------------
# Demo data generation (used when no external services are available)
# ---------------------------------------------------------------------------

DEMO_SOURCES = [
    "boards.hirewell.io", "careers.nimbus.dev", "jobs.stackpond.com",
    "openings.kestrel.co", "work.lumenhub.in", "talent.orbitdesk.io"
]
DEMO_ROLES = [
    "Senior Data Engineer", "Data Platform Engineer", "Analytics Engineer",
    "ML Engineer", "Backend Engineer", "Product Designer", "Data Analyst", "Staff Engineer"
]
DEMO_COMPANIES = [
    "Northwind", "Nimbus", "Kestrel Labs", "Pinecrest",
    "Orbital", "Lumen", "Vantage", "Helix"
]
DEMO_LOCATIONS = [
    "Remote (India)", "Bengaluru", "Gurugram", "Hyderabad", "Pune", "Delhi NCR"
]
DEMO_METHODS = ["JSON-LD JobPosting", "DOM selectors", "LLM field extraction"]


def _slug(s: str) -> str:
    import re
    return re.sub(r'\W+', '-', s.lower())


def generate_demo_records(prompt: str, count: int = 22):
    """Generate realistic demo data records."""
    records = []
    seed = hash(prompt) % 9973
    rng = random.Random(seed)

    for i in range(count):
        src_idx = rng.randint(0, len(DEMO_SOURCES) - 1)
        role = rng.choice(DEMO_ROLES)
        company = rng.choice(DEMO_COMPANIES)
        location = rng.choice(DEMO_LOCATIONS)
        salary_low = 18 + rng.randint(0, 40)
        salary_high = 45 + rng.randint(0, 40)
        confidence = round(78 + rng.random() * 21, 1)
        posted = 1 + rng.randint(0, 27)
        method = rng.choice(DEMO_METHODS)
        source_host = DEMO_SOURCES[src_idx]
        source_url = f"https://{source_host}/{_slug(company)}/{_slug(role)}-{1000 + i}"
        fetched_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=rng.randint(0, 300))

        records.append({
            "role": role,
            "company": company,
            "location": location,
            "salary": f"₹{salary_low}–{salary_high} LPA",
            "posted_days_ago": posted,
            "source_url": source_url,
            "source_host": source_host,
            "fetched_at": fetched_at.isoformat() + "Z",
            "extraction_method": method,
            "confidence": confidence,
        })
    return records


def run_demo_workflow(task_id: int, prompt: str, plan: dict):
    """Simulates a data collection workflow in the background (demo mode)."""
    time.sleep(1)  # Simulate planning

    db = SessionLocal()
    try:
        task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
        if not task:
            return

        # Step 1: Planning → Finding sources
        task.status = "Finding sources"
        db.commit()
        time.sleep(1)

        # Step 2: Finding sources → Collecting
        task.status = "Collecting"
        db.commit()

        records = generate_demo_records(prompt)

        # Step 3: Save records one-by-one (simulating real-time arrival)
        sources_seen = set()
        for rec in records:
            db_record = ScrapedData(
                task_id=task_id,
                source_url=rec["source_url"],
                extracted_data={
                    "role": rec["role"],
                    "company": rec["company"],
                    "location": rec["location"],
                    "salary": rec["salary"],
                    "posted_days_ago": rec["posted_days_ago"],
                    "source_host": rec["source_host"],
                },
                confidence=rec["confidence"],
                extraction_method=rec["extraction_method"],
                fetched_at=datetime.datetime.fromisoformat(rec["fetched_at"].rstrip("Z")),
            )
            db.add(db_record)
            sources_seen.add(rec["source_host"])
            time.sleep(0.08)  # Simulate streaming

        # Step 4: Cleaning
        task.status = "Cleaning"
        db.commit()
        time.sleep(0.8)

        # Finalize
        dupes = random.randint(2, 5)
        avg_conf = round(sum(r["confidence"] for r in records) / len(records), 1) if records else 0
        task.status = "Ready"
        task.records_count = len(records)
        task.sources_count = len(sources_seen)
        task.duplicates_removed = dupes
        task.avg_confidence = avg_conf
        db.commit()

    except Exception as e:
        print(f"Demo workflow failed: {e}")
        if task:
            task.status = "Failed"
            db.commit()
    finally:
        db.close()


def run_real_workflow(task_id: int, plan: dict):
    """Runs the true end-to-end data collection workflow using the scraper agent natively."""
    db = SessionLocal()
    task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
    if not task:
        db.close()
        return

    try:
        task.status = "Scraping"
        db.commit()

        target_sources = plan.get("target_sources", [])
        data_schema = plan.get("data_schema", {})
        
        # This will actually fetch the HTML and use the LLM to extract records!
        extracted_records = run_scraping_job(target_sources, data_schema)

        task.status = "Processing"
        db.commit()

        sources_seen = set()
        for record in extracted_records:
            source_url = record.pop("_source_url", "unknown")
            sources_seen.add(source_url)
            
            db_record = ScrapedData(
                task_id=task_id,
                source_url=source_url,
                extracted_data=record
            )
            db.add(db_record)

        task.status = "Ready"
        task.records_count = len(extracted_records)
        task.sources_count = len(sources_seen)
        db.commit()

    except Exception as e:
        print(f"Real workflow failed: {e}")
        task.status = "Failed"
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    prompt: str


class TaskResponse(BaseModel):
    id: int
    status: str
    prompt: str
    records_count: int
    sources_count: int
    duplicates_removed: int
    avg_confidence: Optional[float]
    created_at: str
    plan: Optional[dict] = None


class RecordResponse(BaseModel):
    id: int
    role: str
    company: str
    location: str
    salary: str
    source_url: str
    source_host: str
    fetched_at: str
    extraction_method: str
    confidence: float
    posted_days_ago: int


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Tracelight · AI Data Intelligence Platform API is running."}


@app.post("/api/tasks")
def create_task(request: PromptRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Create a new data collection task from a natural language prompt."""
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    # Create a new collection task
    new_task = CollectionTask(original_prompt=prompt, status="Planning")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Generate the workflow plan
    workflow_plan = generate_workflow_plan(prompt)

    # Save the plan to DB
    db_plan = WorkflowPlan(
        task_id=new_task.id,
        steps=workflow_plan.get("steps", []),
        target_sources=workflow_plan.get("target_sources", []),
        data_schema=workflow_plan.get("data_schema", {}),
    )
    db.add(db_plan)
    db.commit()

    # Try Celery first, fall back to native background threads
    use_celery = os.getenv("USE_CELERY", "false").lower() == "true"
    use_real_scraping = os.getenv("REAL_SCRAPING", "false").lower() == "true"

    if use_celery:
        try:
            from worker import execute_data_collection_workflow
            workflow_plan["task_id"] = new_task.id
            workflow_plan["original_prompt"] = prompt
            celery_task = execute_data_collection_workflow.delay(workflow_plan)
            new_task.celery_task_id = celery_task.id
            db.commit()
        except Exception as e:
            print(f"Celery unavailable, falling back to local processing: {e}")
            use_celery = False

    if not use_celery:
        if use_real_scraping:
            # Run the REAL agentic scraping in a background thread natively!
            thread = threading.Thread(
                target=run_real_workflow,
                args=(new_task.id, workflow_plan),
                daemon=True,
            )
            thread.start()
        else:
            # Run demo workflow
            thread = threading.Thread(
                target=run_demo_workflow,
                args=(new_task.id, prompt, workflow_plan),
                daemon=True,
            )
            thread.start()

    # Build full plan for the response
    full_plan = {
        "intent": prompt,
        "workflow": [
            {"step": "Plan", "do": "Parse request into fields, filters and freshness window"},
            {"step": "Find sources", "do": "Pick sources from the allowlist; honor robots.txt and rate limits"},
            {"step": "Collect", "do": "Fetch listing pages, follow detail links, extract fields"},
            {"step": "Clean", "do": "Normalize salary and location, validate, dedupe on role+company+location"},
            {"step": "Ready", "do": "Attach source_url and fetched_at to every record"},
        ],
        "sources": [{"host": s, "allowlisted": True} for s in DEMO_SOURCES],
        "schema": workflow_plan.get("data_schema", {}),
        "dedupe_key": ["role", "company", "location"],
    }

    return {
        "id": new_task.id,
        "status": new_task.status,
        "prompt": prompt,
        "plan": full_plan,
    }


@app.get("/api/tasks")
def list_tasks(db: Session = Depends(get_db)):
    """List all collection tasks (past runs), most recent first."""
    tasks = db.query(CollectionTask).order_by(CollectionTask.created_at.desc()).all()
    result = []
    for t in tasks:
        result.append({
            "id": t.id,
            "status": t.status,
            "prompt": t.original_prompt,
            "records_count": t.records_count or 0,
            "sources_count": t.sources_count or 0,
            "duplicates_removed": t.duplicates_removed or 0,
            "avg_confidence": t.avg_confidence,
            "created_at": t.created_at.isoformat() + "Z" if t.created_at else "",
        })
    return result


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get detailed info about a specific task including plan and records."""
    task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    # Get plan
    plan_data = None
    if task.workflow_plan:
        plan_data = {
            "intent": task.original_prompt,
            "workflow": [
                {"step": "Plan", "do": "Parse request into fields, filters and freshness window"},
                {"step": "Find sources", "do": "Pick sources from the allowlist; honor robots.txt and rate limits"},
                {"step": "Collect", "do": "Fetch listing pages, follow detail links, extract fields"},
                {"step": "Clean", "do": "Normalize salary and location, validate, dedupe on role+company+location"},
                {"step": "Ready", "do": "Attach source_url and fetched_at to every record"},
            ],
            "sources": [{"host": s, "allowlisted": True} for s in DEMO_SOURCES],
            "schema": task.workflow_plan.data_schema or {},
            "dedupe_key": ["role", "company", "location"],
        }

    # Get records
    records = []
    for r in task.scraped_data:
        data = r.extracted_data or {}
        records.append({
            "id": r.id,
            "role": data.get("role", ""),
            "company": data.get("company", ""),
            "location": data.get("location", ""),
            "salary": data.get("salary", ""),
            "posted_days_ago": data.get("posted_days_ago", 0),
            "source_url": r.source_url,
            "source_host": data.get("source_host", ""),
            "fetched_at": r.fetched_at.isoformat() + "Z" if r.fetched_at else "",
            "extraction_method": r.extraction_method or "",
            "confidence": r.confidence or 0,
        })

    return {
        "id": task.id,
        "status": task.status,
        "prompt": task.original_prompt,
        "records_count": task.records_count or 0,
        "sources_count": task.sources_count or 0,
        "duplicates_removed": task.duplicates_removed or 0,
        "avg_confidence": task.avg_confidence,
        "created_at": task.created_at.isoformat() + "Z" if task.created_at else "",
        "plan": plan_data,
        "records": records,
    }


@app.get("/api/tasks/{task_id}/status")
def get_task_status(task_id: int, db: Session = Depends(get_db)):
    """Lightweight polling endpoint: returns just the task status and stats."""
    task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    records_count = db.query(ScrapedData).filter(ScrapedData.task_id == task_id).count()

    return {
        "id": task.id,
        "status": task.status,
        "records_count": task.records_count or records_count,
        "sources_count": task.sources_count or 0,
        "duplicates_removed": task.duplicates_removed or 0,
        "avg_confidence": task.avg_confidence,
    }
