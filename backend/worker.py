import os
from celery import Celery

# Configure Celery to use Redis as the broker and result backend
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ai_data_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

from database import SessionLocal
from models import CollectionTask, ScrapedData
from scraper_agent import run_scraping_job

@celery_app.task(bind=True, name="execute_data_collection_workflow")
def execute_data_collection_workflow(self, workflow_plan: dict):
    """
    The main background task that executes the data collection workflow.
    """
    print(f"Executing workflow plan: {workflow_plan}")
    task_id = workflow_plan.get("task_id")
    target_sources = workflow_plan.get("target_sources", [])
    data_schema = workflow_plan.get("data_schema", {})
    
    db = SessionLocal()
    try:
        # Update status to Scraping
        db_task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
        if db_task:
            db_task.status = "Scraping"
            db.commit()

        # Run the agentic scraping layer
        extracted_records = run_scraping_job(target_sources, data_schema)
        
        if db_task:
            db_task.status = "Processing"
            db.commit()

        # Save the scraped data to the database
        for record in extracted_records:
            source_url = record.pop("_source_url", "unknown")
            db_record = ScrapedData(
                task_id=task_id,
                source_url=source_url,
                extracted_data=record
            )
            db.add(db_record)
            
        if db_task:
            db_task.status = "Completed"
            db.commit()
            
        return {"status": "completed", "records_collected": len(extracted_records)}
        
    except Exception as e:
        print(f"Task failed: {e}")
        if 'db_task' in locals() and db_task:
            db_task.status = "Failed"
            db.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
