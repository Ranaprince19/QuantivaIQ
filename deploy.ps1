# Deploy QuantivaIQ stack locally using Docker Compose.
# Run this script from the repository root in PowerShell.

Write-Host "Starting PostgreSQL container..."
docker compose up -d postgres

Write-Host "Waiting for PostgreSQL to become ready..."
Start-Sleep -Seconds 15

Write-Host "Initializing database schema and seeding data..."
docker compose run --rm --profile setup setup

Write-Host "Starting the web dashboard and live simulation services..."
docker compose up -d web simulator

Write-Host "Deployment complete."
Write-Host "Open the web dashboard at http://localhost:8000"
Write-Host "Run Power BI Desktop and connect to PostgreSQL at localhost:5432 with DirectQuery mode."
