# AI-Powered Data Intelligence Platform

## System Prompt for the Core AI Orchestrator

> "You are the core intelligence engine for an AI-Powered Data Intelligence Platform. Your primary objective is to receive business requirements described in plain English and translate them into actionable data collection workflows. 
>
> Upon receiving a user prompt, you must:
> 1. Parse the natural language to understand the specific data requirements (e.g., job openings, sales leads, market data).
> 2. Dynamically design a step-by-step data-collection workflow tailored to the request.
> 3. Identify and generate search strategies for permitted, relevant web sources.
> 4. Define the JSON schema for how the resulting data should be structured, cleaned, validated, and deduplicated.
> 5. Ensure every data point you return includes metadata linking it to a traceable source.
>
> Return a JSON object containing the execution plan, the list of target sources, and the required data schema."

---

## End-to-End Implementation Plan

Based on the requirements outlined in the problem statement, this implementation plan covers the entire lifecycle to build the product from scratch, turning a natural-language requirement into a clean, structured dataset with a managed workflow.

### Phase 1: Architecture & Database Design
*   **Tech Stack Selection**: Use a JavaScript framework (like Next.js or React) for the frontend dashboard and Python (FastAPI or Django) for the backend, as Python provides robust libraries for AI orchestration (LangChain, LlamaIndex) and web scraping (Scrapy, Playwright).
*   **Database Modeling**: Set up a relational database (like PostgreSQL) to track users, prompts, workflow states, and data schemas. Ensure you design tables specifically to maintain workflow and dataset history.
*   **Job Queue System**: Implement a message broker (like Redis + Celery) to handle long-running collection tasks, allowing the system to execute tasks in the background while users monitor their progress.

### Phase 2: AI Orchestration & Workflow Engine
*   **Prompt Parsing**: Integrate an LLM (e.g., GPT-4 or Claude 3) configured to understand data requirements from natural-language prompts.
*   **Dynamic Planner**: Build a microservice where the AI dynamically designs and executes data-collection workflows based on the parsed intent rather than relying on hardcoded, separate scrapers.
*   **Source Verification**: Create a validation layer that checks the AI's proposed scraping targets against an allowlist of permitted sources to ensure compliance and ethical scraping.

### Phase 3: Data Collection & Processing Pipeline
*   **Agentic Scraping Layer**: Deploy web scraping agents capable of executing the AI-generated workflows to collect and process information from multiple sources.
*   **Data Processing Pipeline**: Build a transformation layer that takes raw HTML/JSON responses and uses AI or programmatic rules to clean, structure, validate, and deduplicate results.
*   **Traceability Mapping**: Ensure the pipeline tags every structured entity with its origin URL and timestamp to provide source-backed, traceable data.

### Phase 4: Interactive Dashboard (Frontend)
*   **Prompt Interface**: Create a simple search-like interface where users can describe what they need in plain English.
*   **Task Management**: Build a view that allows users to monitor and manage collection tasks in real-time, displaying progress states (e.g., "Planning", "Scraping", "Processing").
*   **Results & Analytics**: Develop an interactive dashboard to present results in a centralized view. Allow users to explore results and inspect sources.
*   **Data Tools**: Add table functionalities allowing users to search, filter, and export collected data. Ensure the UI lets users revisit previous workflows to see historical data.