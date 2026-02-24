# Python Orchestrator

## Prerequisites
- Node OData server running on http://127.0.0.1:4004
- MCP weather server running on http://127.0.0.1:8000
- AI Core env vars set (AICORE_BASE_URL, AICORE_AUTH_URL, AICORE_CLIENT_ID, AICORE_CLIENT_SECRET)
- Optional: LLM_MODEL_NAME (defaults to gpt-5)
- Optional: LLM_DEPLOYMENT_ID to pin a specific deployment
- Optional: MCP_SERVERS_JSON for multiple MCP servers
- Optional: MCP_TRANSPORT=http and MCP_BASE_URL override
- Optional: ODATA_BASE_URL override

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
uvicorn orchestrator:app --host 127.0.0.1 --port 8080
```

## Start Services
```bash
node server.js
```

```bash
python mcp_weather_server.py
```

## One-Command Startup
```bash
bash run_all.sh
```

## Example
```bash
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","message":"What is the weather in Zurich and list sales orders"}'
```
