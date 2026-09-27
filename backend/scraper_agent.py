import os
import requests
from bs4 import BeautifulSoup
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import json

def fetch_html(url: str) -> str:
    """
    Fetches the raw HTML from the target URL.
    For production, consider using Playwright/Selenium for JS-heavy sites.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""

def extract_data_with_llm(html_content: str, data_schema: dict) -> list:
    """
    Uses the LLM to extract and structure data from HTML based on the provided schema.
    """
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found. Returning mock extracted data.")
        # Mock data based on schema keys
        mock_record = {key: "mock_value" for key in data_schema.keys()}
        return [mock_record]

    # Clean HTML slightly to save tokens
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text(separator=' ', strip=True)
    
    # Truncate to avoid exceeding context window for this simple example
    text_content = text_content[:8000]

    llm = ChatOpenAI(temperature=0, model_name="gpt-4")
    
    system_prompt = (
        "You are an expert data extraction agent. Your job is to extract records from the following web page text "
        "that match the requested JSON schema. Clean and validate the data as you extract it.\n"
        "Return ONLY a valid JSON array of objects matching this schema, with no markdown formatting or extra text.\n"
        f"Schema:\n{json.dumps(data_schema, indent=2)}"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Web Page Text:\n{text_content}")
    ]

    try:
        response = llm(messages)
        # Clean up potential markdown formatting in response
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        records = json.loads(content)
        if isinstance(records, list):
            return records
        return []
    except Exception as e:
        print(f"Extraction failed: {e}")
        return []

def run_scraping_job(target_sources: list, data_schema: dict) -> list:
    """
    Orchestrates the scraping process across multiple sources.
    """
    all_extracted_records = []
    
    for url in target_sources:
        if "(Requires Approval)" in url:
            print(f"Skipping unapproved source: {url}")
            continue
            
        print(f"Scraping {url}...")
        # Ensure it's a valid URL format for requests
        if not url.startswith('http'):
            url = 'https://' + url
            
        html = fetch_html(url)
        if not html:
            continue
            
        records = extract_data_with_llm(html, data_schema)
        
        # Traceability Mapping: Attach the source URL to each extracted record
        for record in records:
            record["_source_url"] = url
            
        all_extracted_records.extend(records)
        
    return all_extracted_records
