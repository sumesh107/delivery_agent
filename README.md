
# Delivery Agent Orchestrator

## Overview

This project is an AI-powered orchestrator for delivery operations. It uses a Large Language Model (LLM) to interpret user queries, call APIs/tools, and return combined results. The orchestrator supports session memory, persistent storage, and context-aware responses.

---

## How It Works

### Main Workflow

1. **User Input:**  
   User sends a query (e.g., "What is the weather in Zurich and list sales orders").

2. **Session Handling:**  
   - Loads conversation history from the database (if enabled) or from in-memory storage.
   - Supports session survival across app restarts and multi-instance deployments.

3. **Agent Workflow (LangGraph):**  
   - The orchestrator uses a LangGraph agent workflow, which allows the LLM to decide if tool/API calls are needed.
   - The workflow consists of nodes and edges:
     - **Nodes:**  
       - `assistant`: The LLM agent that interprets queries and decides next steps.
       - `tools`: Executes tool/API calls (e.g., weather, sales orders).
       - `summarize_tools`: Cleans up and truncates tool outputs for clarity.
     - **Conditional Edges:**  
       - The LLM decides whether to call tools or respond directly.
     - **Edges:**  
       - After tool execution, results are summarized and looped back to the assistant for further processing or final response.

4. **LLM Call:**  
   - The LLM receives the system prompt and session history.
   - It decides whether to call tools or respond directly.

5. **Tool Calls:**  
   - If needed, the agent calls APIs/tools (weather, sales orders, etc.).
   - Tool responses are included in the output with role: "tool".

6. **Response Assembly:**  
   - Combines LLM and tool responses.
   - Serializes messages and returns a user-friendly answer.

---

## Agent Graph Workflow (LangGraph)

The agent workflow is built using LangGraph, which enables flexible, agentic flows:

- **Flow Diagram:**

  ```
  [assistant]
     ↓ (tools_condition)
     ├─→ [tools] → [summarize_tools] → [assistant] (loop)
     └─→ (finish/return response)
  ```

- **Nodes:**  
  - `assistant`: LLM agent, entry point.
  - `tools`: Executes tool/API calls.
  - `summarize_tools`: Truncates large tool outputs.

- **Conditional Edges:**  
  - The LLM decides if tools are needed; if yes, goes to `tools`, else responds.

- **Edges:**  
  - After `tools`, always goes to `summarize_tools`, then loops back to `assistant`.

---

## Persistent Session Storage

Sessions are stored in both an in-memory dictionary and a database (SQLite for development, PostgreSQL for production):

- **Features:**
  - Session survival across app restarts.
  - Conversation history for analytics.
  - Automatic cleanup of old sessions (7-day TTL).
  - Dual-write for backward compatibility.

- **Session Lifecycle:**
  1. User sends `/chat` request.
  2. Load session history from DB or Dict.
  3. Append new user message.
  4. Invoke agent workflow.
  5. Save updated session to Dict and DB.
  6. Return serialized messages to user.
  7. Cleanup expired sessions daily.

- **Database Schema:**
  - `SessionRecord`: Stores session metadata and expiration.
  - `MessageRecord`: Stores individual messages with roles, content, tool call IDs, and metadata.

---

## Directory Structure

- `app/orchestrator.py` – FastAPI app, main entry point, session handling, chat endpoint.
- `core/graph.py` – LangGraph agent workflow, system prompt, memory.
- `core/llm.py` – LLM instantiation and selection.
- `db/` – Database engine, models, repositories, cleanup tasks.
- `tools/odata_tools.py` – OData tool wrappers.
- `mcp_services/` – MCP client, weather server, weather helper.
- `cli/chat_cli.py` – Terminal chat client.
- `tests/` – Test suite.
- `server.js` – OData Node service.
- `requirements.txt` – Python dependencies.
- `README.md` – This file.

---

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run database migrations:
   ```bash
   alembic upgrade head
   ```
3. Run the orchestrator main app:
   - Start FastAPI app for chat endpoint:
     ```bash
     python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - Custom TTL (e.g., 3 days):
     ```bash
     SESSION_TTL_DAYS=3 python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - PostgreSQL production mode:
     ```bash
     DATABASE_URL=postgresql+asyncpg://user:pass@localhost/delivery_db \
       python -m uvicorn app.orchestrator:app --host 0.0.0.0 --port 8080
     ```
   - Disable persistence (in-memory only):
     ```bash
     DB_ENABLED=false python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - Enable SQL debugging:
     ```bash
     SQL_ECHO=true python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
4. Run services:
   - OData service: `node server.js`
   - MCP weather server: `python -m mcp_services.weather_server`
5. Test:
   ```bash
   python tests/test_orchestrator.py
   ```

### One-Command Startup

Start OData, MCP weather, and orchestrator together:
```bash
bash run_all.sh
```

---

## Customization

- Add new tools by placing modules in `tools/` or `mcp_services/`.
- Edit the system prompt in `core/graph.py` as needed.

---

## Health Check

To verify database connectivity:
```bash
curl http://localhost:8080/health
# Response:
# {
#   "status": "ok",
#   "database": "connected"
# }
```

---

## Contact

For questions or improvements, contact the maintainer.
DB_ENABLED=true                                 # Enable/disable persistence
SQL_ECHO=false                                  # Debug SQL queries
```

### Database Schema

- **SessionRecord**: Stores session metadata and expiration
- **MessageRecord**: Stores individual messages with roles, content, tool call IDs, and metadata

### Session Lifecycle

```
User sends /chat request
    ↓
Load Phase:
  1. Check if DB enabled
  2. Load messages from DB (or create new session)
  3. Fallback to in-memory Dict if DB unavailable
    ↓
Process Phase:
  4. Append user message
  5. Invoke LLM workflow
  6. Get updated message list
    ↓
Dual-Write Phase:
  7. Save to sessions Dict (backward compatibility)
  8. Save to DB (persistence)
  9. Reset session TTL (keep alive for 7 more days)
    ↓
Response Phase:
  10. Serialize messages to JSON
  11. Return to user
    ↓
Cleanup (Daily @ 2 AM via scheduler):
  12. Find all sessions where expires_at < now
  13. Delete expired sessions
  14. Log count
```

### Backward Compatibility

- Dual-write: All messages are written to both Dict and DB
- Fallback: If DB fails, session continues in Dict
- Optional disabling: Set `DB_ENABLED=false` for in-memory only

---

## Directory Structure
- `app/orchestrator.py` – FastAPI app, main entry point
- `core/graph.py` – LangChain workflow, system prompt, memory
- `core/llm.py` – LLM instantiation and selection
- `db/` – Database engine, models, repositories, cleanup tasks
- `tools/odata_tools.py` – OData tool wrappers
- `mcp_services/` – MCP client, weather server, weather helper
- `cli/chat_cli.py` – Terminal chat client
- `tests/` – Test suite
- `server.js` – OData Node service
- `requirements.txt` – Python dependencies
- `README.md` – This file

---

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run database migrations: `alembic upgrade head`
3. Run the orchestrator main app:
   - Start FastAPI app for chat endpoint:
     ```bash
     python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - Custom TTL (e.g., 3 days):
     ```bash
    SESSION_TTL_DAYS=3 python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - PostgreSQL production mode:
     ```bash
     DATABASE_URL=postgresql+asyncpg://user:pass@localhost/delivery_db \
       python -m uvicorn app.orchestrator:app --host 0.0.0.0 --port 8080
     ```
   - Disable persistence (in-memory only):
     ```bash
    DB_ENABLED=false python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - Enable SQL debugging:
     ```bash
    SQL_ECHO=true python -m uvicorn app.orchestrator:app --host 127.0.0.1 --port 8080
     ```
4. Run services:
   - OData service: `node server.js`
  - MCP weather server: `python -m mcp_services.weather_server`
5. Test: `python tests/test_orchestrator.py`

### One-Command Startup
- Start OData, MCP weather, and orchestrator together:
  ```bash
  bash run_all.sh
  ```

---

## Customization
- Add new tools by placing modules in `tools/` or `mcp_services/`.
- Edit the system prompt in `core/graph.py` as needed.

---

## Health Check
To verify database connectivity:

```bash
curl http://localhost:8080/health
# Response:
# {
#   "status": "ok",
#   "database": "connected"
# }
```

---

For questions or improvements, contact the maintainer.
