import os
import json
from typing import List
import concurrent.futures
import threading

llm_lock = threading.Lock()


def fetch_html(url: str) -> str:
    """
    Fetches the raw HTML from the target URL.
    For production, consider using Playwright/Selenium for JS-heavy sites.
    """
    try:
        import requests  # type: ignore
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""


def _get_llm():
    local_url = os.getenv("LOCAL_LLM_URL", "").strip()
    local_model = os.getenv("LOCAL_LLM_MODEL", "llama3.2").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if local_url:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(base_url=local_url, api_key="ollama")
            return ("openai_compat", client, local_model)
        except ImportError:
            return None

    if openai_key:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=openai_key)
            return ("openai_compat", client, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        except ImportError:
            return None
    return None

def extract_data_with_llm(html_content: str, data_schema: dict) -> list:
    """
    Uses the LLM to extract and structure data from HTML based on the provided schema.
    Falls back to mock data if no LLM is configured.
    """
    llm_info = _get_llm()
    
    if not llm_info:
        print("Warning: No LLM configured. Returning mock extracted data.")
        mock_record = {key: "mock_value" for key in data_schema.keys()}
        return [mock_record]

    # Lazy imports
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as e:
        print(f"BeautifulSoup not installed ({e}). Skipping LLM extraction.")
        return []

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text(separator=" ", strip=True)[:8000]

        kind, client, model = llm_info

        system_prompt = (
            "You are an expert data extraction agent. Extract records from the following "
            "web page text that match the requested JSON schema. Clean and validate the data.\n"
            "Return ONLY a valid JSON array of objects matching this schema, no markdown.\n"
            f"Schema:\n{json.dumps(data_schema, indent=2)}"
        )

        # We lock the local LLM inference so we don't blow up the GPU VRAM
        with llm_lock:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Web Page Text:\n{text_content}"}
                ],
                temperature=0,
                max_tokens=2048,
            )

        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]

        records = json.loads(content)
        return records if isinstance(records, list) else []

    except Exception as e:
        print(f"Extraction failed: {e}")
        return []


def run_scraping_job(target_sources: list, data_schema: dict) -> list:
    """
    Orchestrates the scraping process across multiple sources concurrently for speed.
    """
    all_records: List[dict] = []

    def process_url(url: str):
        if "(Requires Approval)" in url:
            print(f"Skipping unapproved source: {url}")
            return []
            
        print(f"Scraping {url}...")
        if not url.startswith("http"):
            url = "https://" + url

        html = fetch_html(url)
        if not html:
            return []

        records = extract_data_with_llm(html, data_schema)
        for record in records:
            record["_source_url"] = url
        return records

    # Run scraping concurrently!
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_url, target_sources)
        
        for records in results:
            all_records.extend(records)

    return all_records
