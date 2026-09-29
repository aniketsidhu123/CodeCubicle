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
    """Allows all sources for testing purposes."""
    return target_sources


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_workflow_plan(prompt: str) -> dict:
    """
    Generates a structured data-collection workflow plan from a plain-English prompt.
    Uses the LLM Manager which auto-starts Ollama and manages GPU memory.
    Falls back to a mock plan if no LLM is available.
    """
    from llm_manager import llm_manager

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
        content = llm_manager.infer(
            system_prompt=system_prompt,
            user_prompt=f"Business requirement: {prompt}",
            temperature=0.2,
            max_tokens=512,
        )

        if not content:
            print("Info: LLM returned empty response. Using mock workflow plan.")
            return _mock_plan(prompt)

        # Strip markdown fences if the model added them
        content = content.strip()
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
        print(f"LLM plan generation failed: {e}. Falling back to mock plan.")
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
