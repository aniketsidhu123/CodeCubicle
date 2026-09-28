# Tracelight — AI Data Intelligence Platform

## Quick Start

You need **two terminals** — one for the backend, one for the frontend.

---

## Terminal 1 — Backend (FastAPI)

```bash
cd backend

# First time only: install dependencies
pip install fastapi uvicorn sqlalchemy pydantic

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at → **http://localhost:8000**  
API docs at → **http://localhost:8000/docs**

---

## Terminal 2 — Frontend (Next.js)

```bash
cd frontend

# First time only: install dependencies
npm install

# Run the dev server
npm run dev
```

Frontend runs at → **http://localhost:3000**

---

## That's it — open http://localhost:3000 in your browser

By default, the app runs in **demo mode** to give you an instant preview without actual web scraping. 

---

## ⚡ Enable True Agentic Scraping (Local GPU)

You can run the true end-to-end AI scraper **locally on your GPU** using Ollama. No cloud APIs, no Redis, and no Celery required!

### 1. Start Ollama
Download and install [Ollama](https://ollama.com/), then pull a model:
```bash
ollama pull llama3.2
```

### 2. Enable Real Scraping
In the `backend` folder, copy `.env.example` to `.env` and make sure these lines are set:
```env
# Enable true background scraping
REAL_SCRAPING=true

# Point to your local Ollama
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3.2
```

### 3. Restart the backend
The next time you click "Collect data", the system will actually visit the URLs, download the HTML, and feed it through your local Llama 3.2 model to extract the structured data perfectly.

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET`  | `/` | Health check |
| `POST` | `/api/tasks` | Submit a new data collection prompt |
| `GET`  | `/api/tasks` | List all past runs |
| `GET`  | `/api/tasks/{id}` | Full task details + records |
| `GET`  | `/api/tasks/{id}/status` | Lightweight status poll |
| `GET`  | `/docs` | Interactive Swagger UI |
