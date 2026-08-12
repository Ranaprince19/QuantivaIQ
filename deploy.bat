@echo off
REM QuantivaIQ Windows deployment helper
echo Starting PostgreSQL container...
docker compose up -d postgres

echo Waiting for PostgreSQL to become ready...
timeout /t 15 /nobreak >nul

echo Initializing database schema and seeding data...
docker compose run --rm --profile setup setup

echo Starting the web dashboard and live simulator...
docker compose up -d web simulator

echo Deployment complete.
echo Open the web dashboard at http://localhost:8000
pause
