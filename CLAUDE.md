# SAP AI Documentation Assistant — Frontend

Streamlit chatbot UI for querying SAP AI documentation. Talks to a FastAPI backend that uses GPT-4o with tool calling to search a vector knowledge base.

## File Structure

```
app.py                  # Main chat page — all UI rendering, CSS, helpers
api_client.py           # Pure HTTP client (no Streamlit imports) — testable standalone
config.py               # Constants: endpoints, service metadata, colors, suggested questions
pages/
  1_Knowledge_Base.py   # KB management page — browse, add, edit, delete entries
.streamlit/config.toml  # SAP Fiori-themed Streamlit configuration
manifest.yml            # Cloud Foundry deployment descriptor
requirements.txt        # streamlit>=1.29, requests>=2.28
API_REFERENCE.md        # Full backend API docs (endpoint specs, request/response shapes)
```

## Architecture

- **`api_client.py`** — Pure HTTP. No `import streamlit`. Every function raises `APIError` on failure. Intentionally decoupled so it can be unit-tested without Streamlit.
- **`config.py`** — All constants in one place: endpoint URLs, timeouts, service display names, badge colors, client-side entity types, suggested questions.
- **`app.py`** — UI only. Imports from `api_client` and `config`. Defines all helper functions before any `st.sidebar` / main-area rendering (Streamlit executes top-to-bottom).
- **`pages/`** — Streamlit multi-page app. Each file is an independent page with its own `set_page_config`.

## Running Locally

**Backend first** (separate repo at `../gen-ai-sap-helper-app`):
```bash
cd ../gen-ai-sap-helper-app && uvicorn app.main:app --reload
```

**Then the UI:**
```bash
streamlit run app.py
```

The UI defaults to `http://localhost:8000` for the backend. Override with:
```bash
API_BASE_URL=https://my-backend.example.com streamlit run app.py
```

## Deployment

Cloud Foundry via `cf push`. The `manifest.yml` targets the **ap10** landscape:
- Python 3.11, `python_buildpack`
- 256 MB memory, 1 GB disk
- `API_BASE_URL` set to production backend URL in `manifest.yml` → `env`

## Backend API (Summary)

See `API_REFERENCE.md` for full details. Key endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Status, service name, version |
| `/api/v1/kb/services` | GET | List services with doc counts |
| `/api/v1/ask` | POST | Ask a question → answer, confidence, services, links, pipeline |
| `/api/v1/kb/entries` | GET/POST | List or create KB entries |
| `/api/v1/kb/entries/{id}` | PUT/DELETE | Update or delete a KB entry |

## Streamlit Conventions

- **Top-to-bottom rule**: Define all helper functions _before_ any sidebar/main-area code that calls them.
- **`st.chat_input`** must be at top level, never inside conditionals.
- **`html.escape()`** all user/API text rendered with `unsafe_allow_html=True`.
- **Unique `key` params** on every widget, especially inside loops (e.g., `key=f"edit_{entry['id']}"`).
- **`@st.cache_data(ttl=300)`** for API data shared across reruns.
- **Multiple `with st.sidebar:` blocks** are additive — they append to the same sidebar.
- **`@st.dialog`** decorator for modal CRUD dialogs (see `pages/1_Knowledge_Base.py`).
- **CSS is inline** in `st.markdown(unsafe_allow_html=True)` blocks — no external CSS files.
- **Masking rendering**: SAP DPI tokens get red styling (`.masked-token`), client-side tokens (e.g., NRIC) get amber styling (`.masked-token-custom`). The `CLIENT_SIDE_ENTITIES` set in config controls which get amber.

## Key Constants (config.py)

- `API_BASE_URL` — env var, defaults to `http://localhost:8000`
- `REQUEST_TIMEOUT` — 30 seconds
- `MAX_QUESTION_LENGTH` — 2000 characters
- `SERVICE_DISPLAY` — fallback display names when API is offline
- `SERVICE_COLORS` — hex colors for service badges
- `CLIENT_SIDE_ENTITIES` — entity types masked client-side (currently `{"NRIC"}`)
- `SUGGESTED_QUESTIONS` — 4 starter questions shown on empty chat

## Code Style

- **Commits**: imperative mood, short (~50 chars), no conventional-commits prefix
- **Python**: 3.11, no linter config in repo
- **No type-checking config** — type hints used informally
- **Section separators**: `# ---` comment blocks to divide logical sections in `.py` files
