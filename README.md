# AI-Powered Data Intelligence Platform

This is a monorepo containing the Next.js frontend and FastAPI backend for the AI-Powered Data Intelligence Platform.

## Project Structure

- `/backend`: Python FastAPI application, Celery workers, and Langchain AI orchestrator.
- `/frontend`: Next.js React application (App Router).

## Prerequisites for Collaborators

1. **Python 3.9+**
2. **Node.js 18+**
3. **Redis** (Must be running locally on `localhost:6379` or specify via `REDIS_URL` in backend `.env`)

## Setup Instructions

### Backend Setup

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create a copy of the environment template:
   ```bash
   cp .env.example .env
   ```
   Fill in your `OPENAI_API_KEY` in the `.env` file.
3. Run the setup script (Windows):
   ```cmd
   setup.bat
   ```
   Or manually (Mac/Linux):
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
5. In a separate terminal, start the Celery worker:
   ```bash
   celery -A worker.celery_app worker --loglevel=info
   ```

### Frontend Setup

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
