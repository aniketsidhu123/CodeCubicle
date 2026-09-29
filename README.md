# Tracelight — AI Data Intelligence Platform

An end-to-end AI-powered data intelligence scraper built for Windows with local GPU acceleration using Hugging Face Transformers.

## 🚀 Quick Start (Windows)

We have provided automated batch scripts to handle environment setup, GPU dependencies, and Hugging Face model downloads.

1. **Run Setup**:
   ```cmd
   .\setup.bat
   ```
   *This will install Python packages, Next.js dependencies, PyTorch with CUDA, and pre-download the LLM weights into the local `backend/models` folder.*

2. **Run Application**:
   ```cmd
   .\run.bat
   ```
   *This launches the backend on `http://localhost:8000` and the frontend on `http://localhost:3000` in separate windows.*

---

## ⚡ Zero-Dependency GPU AI Scraping

This platform features a **Custom LLM Manager** that natively loads Hugging Face models into VRAM using PyTorch and `transformers`. 

When you click **Collect data** on the frontend:
1. The backend natively loads the Hugging Face model (e.g., Qwen 2.5) into VRAM.
2. The agent uses `Playwright` headless Chromium to silently visit job boards and bypass basic anti-bot systems by waiting for modern JS to fully load.
3. The raw HTML is securely chunked and evaluated locally on your GPU.
4. The GPU rips through the HTML and streams extracted JSON records back to the UI, reporting granular progress (e.g., `Scraping careers.nimbus.dev (1/22)`).
5. Data is strictly validated and deduplicated based on role, company, and location.
6. After 2 minutes of inactivity, the custom LLM manager automatically cleans the AI model out of your VRAM so your laptop stays fast.

### Environment Setup
The system works locally out-of-the-box. Ensure your `backend/.env` file has real scraping enabled:

```env
# Enable true background scraping
REAL_SCRAPING=true

# Keep Hugging Face models locally in this project
HF_HOME=./models

# Model Configuration
LOCAL_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
LLM_USE_GPU=true
```

---

## 🛠 Features
- **Natural Language Parsing**: Ask for data like "Senior Data Engineer roles in Bengaluru".
- **Dynamic Task Management**: Cancel, Retry, or Delete tasks on the fly from the frontend.
- **Persistent History**: All past runs are logged and accessible via the sidebar.
- **Data Export**: Export validated datasets directly to **CSV** or **JSON** files.
- **Record Tracing**: Inspect individual records to see extraction confidence and origin URLs.

---

## API Endpoints

| Method   | URL | Description |
|----------|-----|-------------|
| `POST`   | `/api/tasks` | Submit a new data collection prompt |
| `GET`    | `/api/tasks` | List all past runs |
| `GET`    | `/api/tasks/{id}` | Full task details + records |
| `GET`    | `/api/tasks/{id}/status` | Lightweight status poll |
| `POST`   | `/api/tasks/{id}/cancel` | Cancel an ongoing scraping task |
| `POST`   | `/api/tasks/{id}/retry` | Retry a failed scraping task |
| `DELETE` | `/api/tasks/{id}` | Delete a specific task and its records |
| `DELETE` | `/api/tasks` | Purge all tasks in the database |
