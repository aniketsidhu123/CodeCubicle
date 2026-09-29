"""
Scraper Agent — Fetches web pages and extracts structured data using the LLM Manager.
"""

import os
import json
from typing import List
import concurrent.futures


def fetch_html(url: str) -> str:
    """
    Fetches the raw HTML from the target URL using Playwright.
    This properly renders JS-heavy frameworks (React, Angular, Vue)
    and successfully bypasses basic bot walls.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Launch Chromium in headless mode
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            # wait_until="networkidle" ensures client-side rendering completes
            page.goto(url, wait_until="networkidle", timeout=20000)
            html = page.content()
            browser.close()
            return html
    except ImportError:
        print("Playwright not installed! Falling back to requests...")
        try:
            import requests  # type: ignore
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as fallback_e:
            print(f"Fallback fetch failed for {url}: {fallback_e}")
            return ""
    except Exception as e:
        print(f"Playwright failed to fetch {url}: {e}")
        return ""


def extract_data_with_llm(html_content: str, data_schema: dict) -> list:
    """
    Uses the LLM Manager to extract and structure data from HTML.
    The LLM Manager handles server lifecycle, GPU memory, and crash recovery automatically.
    """
    # Lazy import to avoid circular dependency at module load time
    from llm_manager import llm_manager

    # Lazy imports
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as e:
        print(f"BeautifulSoup not installed ({e}). Skipping LLM extraction.")
        return []

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove noisy elements to drastically reduce context size for faster GPU inference
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form", "iframe"]):
            tag.extract()

        text_content = soup.get_text(separator=" ", strip=True)[:2000]

        if not text_content.strip():
            print("Warning: No extractable text content found in HTML.")
            return []

        system_prompt = (
            "You are an expert data extraction agent. Extract records from the following "
            "web page text that match the requested JSON schema. Clean and validate the data.\n"
            "Return ONLY a valid JSON array of objects matching this schema, no markdown.\n"
            f"Schema:\n{json.dumps(data_schema, indent=2)}"
        )

        # The LLM Manager handles thread safety, GPU memory, and crash recovery
        content = llm_manager.infer(
            system_prompt=system_prompt,
            user_prompt=f"Web Page Text:\n{text_content}",
            temperature=0.0,
            max_tokens=2048,
        )

        if not content:
            print("Warning: LLM returned empty response.")
            return []

        content = content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]

        records = json.loads(content)
        return records if isinstance(records, list) else []

    except json.JSONDecodeError as e:
        print(f"LLM returned invalid JSON: {e}")
        return []
    except Exception as e:
        print(f"Extraction failed: {e}")
        return []


def run_scraping_job(target_sources: list, data_schema: dict) -> list:
    """
    Orchestrates the scraping process across multiple sources.
    Network fetches run concurrently; LLM inference is serialized by the LLM Manager.
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

    # Run scraping concurrently — network I/O is parallel, LLM is serialized by llm_manager
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_url, target_sources)

        for records in results:
            all_records.extend(records)

    return all_records
