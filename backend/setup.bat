@echo off
echo ===========================================
echo Tracelight Setup for Windows (Hugging Face)
echo ===========================================

echo.
echo [1/4] Setting up environment variables...
if not exist ".env" (
    echo Copying .env.example to .env...
    copy .env.example .env
) else (
    echo .env already exists, skipping.
)

echo.
echo [2/4] Setting up Backend...
echo Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate

echo Installing backend dependencies...
pip install -r requirements.txt

echo Installing PyTorch with CUDA acceleration (this overrides the CPU-only torch)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall --no-deps

echo Installing Playwright browser (Chromium)...
python -m playwright install chromium

echo.
echo [3/4] Initializing Hugging Face Model...
echo Downloading the AI model from Hugging Face into the local cache...
set HF_HOME=%cd%\models
python -c "import llm_manager; llm_manager.llm_manager.ensure_model()" || echo WARNING: Could not pull AI model automatically.

echo.
echo [4/4] Setting up Frontend...
cd ../frontend
call npm install
cd ../backend

echo.
echo ===========================================
echo Setup complete! 
echo ===========================================
echo To run the full application, open TWO terminals:
echo.
echo Terminal 1 (Backend):
echo   cd backend
echo   call venv\Scripts\activate
echo   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
echo.
echo Terminal 2 (Frontend):
echo   cd frontend
echo   npm run dev
echo ===========================================
