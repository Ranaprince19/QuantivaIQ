@echo off
REM =========================================================
REM  QuantivaIQ India Dashboard - One-Click Local Runner
REM  Double-click this file (or run it from a terminal) and
REM  it will set up everything and open 2 windows for you:
REM    1) The live data simulator
REM    2) The web dashboard
REM  Then open http://localhost:8000 in your browser.
REM =========================================================

cd /d "%~dp0"

echo.
echo ============================================
echo  Step 1/5: Checking virtual environment...
echo ============================================
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists, skipping creation.
)

call venv\Scripts\activate.bat

echo.
echo ============================================
echo  Step 2/5: Installing dependencies...
echo  (This may take a few minutes the first time)
echo ============================================
python -m pip install --upgrade pip >nul
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo.
    echo Full install failed - trying a minimal install instead...
    python -m pip install Flask pandas numpy sqlalchemy psycopg2-binary python-dotenv requests scikit-learn scipy statsmodels faker schedule matplotlib seaborn
)

echo.
echo ============================================
echo  Step 3/5: Setting up the database...
echo ============================================
python python\db_setup.py

echo.
echo ============================================
echo  Step 4/5: Seeding Indian sample data...
echo  (This can take a few minutes for the full
echo   default 50,000 orders. Please wait...)
echo ============================================
python python\etl_pipeline.py

echo.
echo ============================================
echo  Step 5/5: Launching live simulator + dashboard...
echo ============================================
start "QuantivaIQ - Live Simulator" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python python\live_data_generator.py"

timeout /t 3 /nobreak >nul

start "QuantivaIQ - Web Dashboard" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python -m python.web_dashboard"

timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo  All set! Opening your browser now...
echo  If it doesn't open automatically, go to:
echo  http://localhost:8000
echo ============================================
start http://localhost:8000

echo.
echo This window can stay open or be closed - the
echo other 2 windows (Simulator and Dashboard) are
echo what keep everything running. Close THOSE
echo windows if you want to stop the app.
echo.
pause
