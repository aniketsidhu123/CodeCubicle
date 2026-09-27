import os
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
import json

# Define the output structure we expect from the LLM
class WorkflowPlanSchema(BaseModel):
    steps: List[str] = Field(description="A step-by-step data collection workflow.")
    target_sources: List[str] = Field(description="List of search strategies or permitted target URLs.")
    data_schema: dict = Field(description="JSON schema defining how the scraped data should be structured.")

# Source verification allowlist mock
PERMITTED_DOMAINS = ["example.com", "linkedin.com/jobs", "ycombinator.com/jobs", "crunchbase.com"]

def verify_sources(target_sources: List[str]) -> List[str]:
    """
    Checks the AI's proposed scraping targets against an allowlist.
    """
    # A simple demonstration check
    verified = []
    for source in target_sources:
        if any(domain in source.lower() for domain in PERMITTED_DOMAINS):
            verified.append(source)
        else:
            # In a real app, you might flag this or use a safe search engine API instead.
            verified.append(f"{source} (Requires Approval)")
    return verified

def generate_workflow_plan(prompt: str) -> dict:
    """
    Uses LangChain and an LLM to parse the natural language requirement
    and generate a structured workflow plan.
    """
    # If OPENAI_API_KEY is not set, we return a mock response to allow frontend/backend dev to proceed.
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found. Returning a mock workflow plan.")
        return {
            "steps": ["Parse user prompt", "Identify target companies", "Scrape job boards", "Clean data"],
            "target_sources": ["linkedin.com/jobs"],
            "data_schema": {
                "job_title": "string",
                "company": "string",
                "url": "string"
            }
        }

    # Setup the LLM
    llm = ChatOpenAI(temperature=0.2, model_name="gpt-4")
    parser = PydanticOutputParser(pydantic_object=WorkflowPlanSchema)

    # System Prompt from the implementation plan
    system_prompt = (
        "You are the core intelligence engine for an AI-Powered Data Intelligence Platform. "
        "Your primary objective is to receive business requirements described in plain English and translate them into actionable data collection workflows.\n\n"
        "Upon receiving a user prompt, you must:\n"
        "1. Parse the natural language to understand the specific data requirements (e.g., job openings, sales leads, market data).\n"
        "2. Dynamically design a step-by-step data-collection workflow tailored to the request.\n"
        "3. Identify and generate search strategies for permitted, relevant web sources.\n"
        "4. Define the JSON schema for how the resulting data should be structured, cleaned, validated, and deduplicated.\n"
        "5. Ensure every data point you return includes metadata linking it to a traceable source.\n\n"
        f"{parser.get_format_instructions()}"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Business Requirement: {prompt}")
    ]

    # Execute the LLM
    response = llm(messages)
    
    # Parse the output
    try:
        parsed_plan = parser.parse(response.content)
        plan_dict = parsed_plan.dict()
        
        # Apply Source Verification
        plan_dict["target_sources"] = verify_sources(plan_dict["target_sources"])
        
        return plan_dict
    except Exception as e:
        print(f"Failed to parse LLM response: {e}")
        # Fallback error state
        return {
            "steps": ["Error parsing plan"],
            "target_sources": [],
            "data_schema": {}
        }
