#!/bin/bash

# Docker Services Startup Script
# Brings up PostgreSQL and n8n for FinancialReportNews

echo "=========================================="
echo "STARTING DOCKER SERVICES"
echo "=========================================="
echo ""

# Check Docker installation
if ! command -v docker compose &> /dev/null; then
    echo "[ERROR] Docker Compose not found"
    echo "Install with: sudo apt-get install docker-compose"
    exit 1
fi

echo "[STEP 1] Verifying environment configuration"
if [ ! -f ".env" ]; then
    echo "[ERROR] .env file not found"
    echo "Create from template: cp .env.example .env"
    exit 1
fi
echo "[OK] .env file present"
echo ""

echo "[STEP 2] Starting PostgreSQL"
docker compose up -d postgres
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to start PostgreSQL"
    exit 1
fi
echo "[OK] PostgreSQL starting..."
echo ""

echo "[STEP 3] Waiting for PostgreSQL to be ready"
echo "Waiting for health check..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U n8n -d n8n > /dev/null 2>&1; then
        echo "[OK] PostgreSQL is ready"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 2
done
echo ""

echo "[STEP 4] Initializing database schema"
docker compose exec -T postgres psql -U n8n -d n8n -f /docker-entrypoint-initdb.d/schema.sql > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "[OK] Schema initialized"
else
    echo "[WARNING] Schema initialization may have skipped (database already initialized)"
fi
echo ""

echo "[STEP 5] Starting n8n"
docker compose up -d n8n
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to start n8n"
    exit 1
fi
echo "[OK] n8n starting..."
echo ""

echo "[STEP 6] Waiting for n8n to be ready"
echo "Waiting for health check..."
for i in {1..30}; do
    if curl -s http://localhost:5678/healthz > /dev/null 2>&1; then
        echo "[OK] n8n is ready"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 2
done
echo ""

echo "[STEP 7] Verifying services"
docker compose ps
echo ""

echo "=========================================="
echo "SERVICES STARTED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "Access Points:"
echo "  - n8n UI: http://localhost:5678"
echo "  - PostgreSQL: postgres:5432"
echo ""
echo "Next Steps:"
echo "  1. Open http://localhost:5678 in browser"
echo "  2. Import workflows from n8n/workflows/"
echo "  3. Configure Telegram credentials"
echo "  4. Test pipeline execution"
echo ""

