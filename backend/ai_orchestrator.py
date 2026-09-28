import os
import json
from typing import List

# ---------------------------------------------------------------------------
# Source verification allowlist
# ---------------------------------------------------------------------------
PERMITTED_DOMAINS = [
    "linkedin.com/jobs",
    "ycombinator.com/jobs",
    "crunchbase.com",
    "example.com",
]


def verify_sources(target_sources: List[str]) -> List[str]:
    """Checks the AI's proposed scraping targets against an allowlist."""
    verified = []
    for source in target_sources:
        if any(domain in source.lower() for domain in PERMITTED_DOMAINS):
            verified.append(source)
        else:
            verified.append(f"{source} (Requires Approval)")
    return verified


# ---------------------------------------------------------------------------
# LLM backend selector
# ---------------------------------------------------------------------------

def _get_llm():
    """
    Returns an LLM client based on environment config.

    Priority:
      1. LOCAL_LLM_URL is set  → Ollama / LM Studio (local, no cost)
      2. OPENAI_API_KEY is set → OpenAI API (cloud)
      3. Neither               → None  (mock plan returned)
    """
    local_url = os.getenv("LOCAL_LLM_URL", "").strip()
    local_model = os.getenv("LOCAL_LLM_MODEL", "llama3.2").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if local_url:
        # Ollama / LM Studio — OpenAI-compatible endpoint
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(base_url=local_url, api_key="ollama")
            return ("openai_compat", client, local_model)
        except ImportError:
            print("Warning: 'openai' package not installed. Run: pip install openai")
            return None

    if openai_key:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=openai_key)
            return ("openai_compat", client, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        except ImportError:
            print("Warning: 'openai' package not installed. Run: pip install openai")
            return None

    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_workflow_plan(prompt: str) -> dict:
    """
    Generates a structured data-collection workflow plan from a plain-English prompt.

    Backends (in priority order):
      - Local model via Ollama / LM Studio  (set LOCAL_LLM_URL)
      - OpenAI cloud API                    (set OPENAI_API_KEY)
      - Mock plan                           (no config needed)
    """
    llm_info = _get_llm()

    if llm_info is None:
        print("Info: No LLM configured. Using mock workflow plan.")
        return _mock_plan(prompt)

    kind, client, model = llm_info

    system_prompt = (
        "You are the core intelligence engine for an AI-Powered Data Intelligence Platform. "
        "Receive business requirements in plain English and translate them into actionable "
        "data collection workflows.\n\n"
        "Given a user prompt, respond with ONLY a valid JSON object (no markdown, no commentary) "
        "with exactly these keys:\n"
        '  "steps": [list of step strings],\n'
        '  "target_sources": [list of domain/URL strings],\n'
        '  "data_schema": {field_name: type_string, ...}\n\n'
        "Example:\n"
        '{"steps":["Parse prompt","Find sources","Scrape","Clean","Done"],'
        '"target_sources":["linkedin.com/jobs"],'
        '"data_schema":{"role":"string","company":"string","location":"string","salary":"string"}}'
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Business requirement: {prompt}"},
            ],
            temperature=0.2,
            max_tokens=512,
        )
        content = response.choices[0].message.content.strip()

        # Strip markdown fences if the model added them
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        plan_dict = json.loads(content)

        # Validate required keys; fall back if malformed
        for key in ("steps", "target_sources", "data_schema"):
            if key not in plan_dict:
                raise ValueError(f"Missing key: {key}")

        plan_dict["target_sources"] = verify_sources(plan_dict["target_sources"])
        return plan_dict

    except Exception as e:
        print(f"LLM call failed ({model}): {e}. Falling back to mock plan.")
        return _mock_plan(prompt)


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------

def _mock_plan(prompt: str) -> dict:
    """Returns a deterministic mock plan — used when no LLM is configured."""
    return {
        "steps": [
            "Parse user prompt",
            "Identify target job boards",
            "Scrape listing pages",
            "Extract structured fields",
            "Clean and deduplicate",
        ],
        "target_sources": [
            "linkedin.com/jobs",
            "ycombinator.com/jobs",
        ],
        "data_schema": {
            "role": "string",
            "company": "string",
            "location": "string",
            "salary": "string",
            "posted_days_ago": "integer",
            "_trace": {
                "source_url": "url",
                "fetched_at": "iso8601",
                "method": "string",
                "confidence": "0-100",
            },
        },
    }
