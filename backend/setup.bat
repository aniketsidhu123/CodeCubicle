@echo off
echo Setting up Python virtual environment...
python -m venv venv
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Setup complete! To run the server, use: uvicorn main:app --reload
