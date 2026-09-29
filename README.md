# Tracelight — AI Data Intelligence Platform

An end-to-end AI-powered data intelligence scraper built for Windows with local GPU acceleration.

## 🚀 Quick Start

You need **two terminals** — one for the backend, one for the frontend.

---

### Terminal 1 — Backend (FastAPI + GPU inference)

```bash
cd backend

# 1. Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic requests playwright

# 2. Install Playwright browser for true JS-rendering and anti-bot bypass
python -m playwright install chromium

# 3. Run the backend server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at → **http://localhost:8000**  
API docs at → **http://localhost:8000/docs**

---

### Terminal 2 — Frontend (Next.js)

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Run the dev server
npm run dev
```

Frontend runs at → **http://localhost:3000**

---

## ⚡ Zero-Dependency GPU AI Scraping

This platform features a **Custom LLM Manager** that automatically handles your local AI inference without requiring you to manually start applications!

When you click **Collect data** on the frontend:
1. The backend automatically boots up `Ollama` in the background.
2. The agent uses `Playwright` headless Chromium to silently visit job boards and bypass basic anti-bot systems by waiting for React/Angular JS to fully load.
3. The raw HTML is securely chunked and passed into your local GPU's VRAM (via Llama 3.2).
4. The GPU rips through the HTML and streams extracted JSON records back to the UI.
5. After a few minutes of inactivity, the custom LLM manager automatically cleans the AI model out of your VRAM so your laptop stays fast.

Ensure your NVIDIA drivers are up to date to enjoy full CUDA hardware acceleration.

### Environment Setup
The system works fully locally out-of-the-box. Ensure your `backend/.env` file looks like this:

```env
# Enable true background scraping
REAL_SCRAPING=true

# Ollama Auto-Manager
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3.2
LLM_USE_GPU=true
```

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/api/tasks` | Submit a new data collection prompt |
| `GET`  | `/api/tasks` | List all past runs |
| `GET`  | `/api/tasks/{id}` | Full task details + records |
| `GET`  | `/api/tasks/{id}/status` | Lightweight status poll |
