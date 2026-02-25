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

---

## Persistent Session Storage

The orchestrator now supports **persistent session storage** using SQLite (development) and PostgreSQL (production-ready). All conversations are saved to a database, enabling:

- Session survival across app restarts
- Conversation history for analytics
- Multi-instance deployment support
- Automatic cleanup of old sessions (7-day TTL)
- Backward compatibility (dual-write to Dict + DB)

### Database Configuration

Set environment variables as needed:

```
DATABASE_URL=sqlite+aiosqlite:///./sessions.db  # Default
SESSION_TTL_DAYS=7                              # Session lifespan
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
- `orchestrator.py` – FastAPI app, main entry point
- `graph.py` – LangChain workflow, system prompt, memory
- `llm.py` – LLM instantiation and selection
- `weather.py` – Weather tool
- `odata_tools.py` – OData tool wrappers
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
     python -m uvicorn orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - Custom TTL (e.g., 3 days):
     ```bash
     SESSION_TTL_DAYS=3 python -m uvicorn orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - PostgreSQL production mode:
     ```bash
     DATABASE_URL=postgresql+asyncpg://user:pass@localhost/delivery_db \
       python -m uvicorn orchestrator:app --host 0.0.0.0 --port 8080
     ```
   - Disable persistence (in-memory only):
     ```bash
     DB_ENABLED=false python -m uvicorn orchestrator:app --host 127.0.0.1 --port 8080
     ```
   - Enable SQL debugging:
     ```bash
     SQL_ECHO=true python -m uvicorn orchestrator:app --host 127.0.0.1 --port 8080
     ```
4. Run services:
   - OData service: `node server.js`
   - MCP weather server: `python mcp_weather_server.py`
5. Test: `python test_orchestrator.py`

### One-Command Startup
- Start OData, MCP weather, and orchestrator together:
  ```bash
  bash run_all.sh
  ```

---

## Customization
- Add new tools by placing modules in the repo root.
- Edit the system prompt in `graph.py` as needed.

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
