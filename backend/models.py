import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class CollectionTask(Base):
    """
    Represents a user's prompt and the overarching data collection job.
    """
    __tablename__ = "collection_tasks"

    id = Column(Integer, primary key=True, index=True)
    celery_task_id = Column(String, index=True, nullable=True)
    original_prompt = Column(Text, nullable=False)
    status = Column(String, default="Planning") # e.g., Planning, Scraping, Processing, Completed, Failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    workflow_plan = relationship("WorkflowPlan", back_populates="task", uselist=False)
    scraped_data = relationship("ScrapedData", back_populates="task")


class WorkflowPlan(Base):
    """
    The AI-generated step-by-step plan and schema for the collection task.
    """
    __tablename__ = "workflow_plans"

    id = Column(Integer, primary key=True, index=True)
    task_id = Column(Integer, ForeignKey("collection_tasks.id"))
    steps = Column(JSON, nullable=False)           # List of steps to execute
    target_sources = Column(JSON, nullable=False)  # List of URLs or search strategies
    data_schema = Column(JSON, nullable=False)     # Expected output JSON schema
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("CollectionTask", back_populates="workflow_plan")


class ScrapedData(Base):
    """
    The structured data entities collected by the workflow, including traceability.
    """
    __tablename__ = "scraped_data"

    id = Column(Integer, primary key=True, index=True)
    task_id = Column(Integer, ForeignKey("collection_tasks.id"))
    source_url = Column(String, nullable=False)
    extracted_data = Column(JSON, nullable=False) # The actual structured data matching data_schema
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("CollectionTask", back_populates="scraped_data")
