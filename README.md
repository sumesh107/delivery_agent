# Delivery Agent Orchestrator

## Overview
This project is an AI-powered orchestrator that uses a Large Language Model (LLM) to interpret user queries, call tools (APIs), and return combined results. It supports session memory and system prompts for context-aware responses.

### Main Flow
1. **User Input:** User sends a query (e.g., "What is the weather in Zurich and list sales orders").
2. **Orchestrator:** Receives the query, uses LangChain to decide which tools to call.
3. **System Prompt & Memory:** Prepends a system prompt and uses in-memory session memory.
4. **LLM Call:** Calls the correct LLM (e.g., GPT-5) with model-specific parameters.
5. **Tool Calls:** Invokes tools (e.g., weather, sales orders) as needed. Tool responses are included in the output with role: "tool".
6. **Response Assembly:** Combines LLM and tool responses, serializes messages, and returns a user-friendly answer.

### Directory Structure
- `orchestrator.py` – FastAPI app, main entry point
- `graph.py` – LangChain workflow, system prompt, memory
- `llm.py` – LLM instantiation and selection
- `weather.py` – Weather tool
- `odata_tools.py` – OData tool wrappers
- `server.js` – OData Node service
- `requirements.txt` – Python dependencies
- `README.md` – This file

### Tool Invocation
- When a tool is called, its output is included in the response with role: "tool". You can check for this role to confirm tool usage.

---

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run the orchestrator: `python -m uvicorn orchestrator:app --host 127.0.0.1 --port 8080`
3. Run services:
	- OData service: `node server.js`
	- MCP weather server: `python mcp_weather_server.py`
4. Test: `python test_orchestrator.py`

### One-Command Startup
- Start OData, MCP weather, and orchestrator together:
	`bash run_all.sh`

---

## Customization
- Add new tools by placing modules in the repo root.
- Edit the system prompt in `graph.py` as needed.

---

For questions or improvements, contact the maintainer.
