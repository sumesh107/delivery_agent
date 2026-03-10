#!/bin/bash
# Start all services for the Delivery Agent Orchestrator

set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Using virtual environment: $(which python)"
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Delivery Agent Services...${NC}"

# Disable DB by default for simpler testing (enable with DB_ENABLED=true)
export DB_ENABLED="${DB_ENABLED:-false}"

# Enable debug mode by default to see detailed logs
export ORCH_DEBUG="${ORCH_DEBUG:-1}"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start OData service (Node.js)
echo -e "${GREEN}[1/3] Starting OData service on port 4004...${NC}"
node server.js &
ODATA_PID=$!

# Wait a moment for OData to start
sleep 2

# Start MCP Weather server (Python)
echo -e "${GREEN}[2/3] Starting MCP Weather service on port 8000...${NC}"
python -m mcp_services.weather_server &
MCP_PID=$!

# Wait a moment for MCP to start
sleep 2

# Start Orchestrator (FastAPI)
echo -e "${GREEN}[3/3] Starting Orchestrator on port 8080...${NC}"
uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080 &
ORCH_PID=$!

echo -e "\n${GREEN}✓ All services started!${NC}"
echo -e "  - OData:        http://127.0.0.1:4004/odata/v4"
echo -e "  - MCP Weather:  http://127.0.0.1:8000"
echo -e "  - Orchestrator: http://127.0.0.1:8080"
echo -e "  - Chat UI:      http://127.0.0.1:8080/chat-ui"
echo -e "  - Health Check: http://127.0.0.1:8080/health"
if [ "$DB_ENABLED" = "false" ]; then
    echo -e "  - Database:     ${YELLOW}DISABLED${NC} (in-memory sessions only)"
    echo -e "                  ${YELLOW}Use: DB_ENABLED=true bash run_all.sh to enable${NC}"
fi
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for all background processes
wait
