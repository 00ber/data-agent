# API Design Plan

## Context

The current API (`apps/web/backend/main.py`, ~220 LOC) is a thin HTTP layer
over the old `AgentSession`. It has 13 routes, many tied to the old agent's
concepts — clarification loops, workspace scanning, memo generation, and a
queue+thread bridge to make a sync iterator async.

The new agent is async-native and exposes one interface:
`run(session, message) → AsyncIterator[Event]`. The API becomes even thinner.

## Design Decisions (settled)

1. **Two files.** `api/main.py` (routes) and `api/sessions.py` (session
   manager). No reason for more.

2. **SSE for streaming.** The agent yields Events. The API wraps them in
   SSE. No WebSockets — SSE is simpler, auto-reconnects, and the
   communication is one-directional (server → client). The client sends
   messages via POST.

3. **No queue+thread bridge.** The old API ran a sync iterator in a thread
   and bridged it to async via a queue. The new agent's `run()` is an async
   generator. SSE wraps it directly.

4. **Datasets are an API concern.** The sample dataset catalog (`SAMPLE_DATASETS`,
   `get_dataset_paths`) belongs in the API layer, not the agent. The agent
   only knows about Sessions and DataFrames. The API handles file discovery,
   upload mechanics, and dataset routing.

5. **Session manager stores Sessions.** The manager creates `Session` objects
   (from the agent library), stores them by ID, and retrieves them. No
   `AgentSession` god-class — just the `Session` dataclass.

6. **Suggestions are a separate endpoint.** LLM-generated suggestions based
   on loaded tables. Called after data load and after each analysis completes.
   This is a lightweight LLM call, not a full agent run.

## Routes

```
GET  /health                                    → { status: "ok" }

GET  /api/datasets                              → dataset catalog
POST /api/sessions                              → create session
POST /api/sessions/{id}/upload                  → upload files
POST /api/sessions/{id}/load-sample/{dataset}   → load sample dataset
GET  /api/sessions/{id}/tables                  → table metadata
POST /api/sessions/{id}/suggestions             → LLM-generated suggestions
POST /api/sessions/{id}/ask                     → SSE stream of events
GET  /api/sessions/{id}/artifacts/{artifact_id} → single artifact data
```

8 routes total (down from 13).

### Route Details

#### `GET /api/datasets`

Returns the sample dataset catalog for onboarding cards.

```json
[
  {
    "id": "ecommerce",
    "name": "E-Commerce Sales",
    "description": "8K customers, 30K orders across 500 products with returns",
    "icon": "shopping-cart",
    "tables": 5,
    "preview": "customers, orders, order_items, products, returns"
  }
]
```

No session required. Static data.

#### `POST /api/sessions`

Creates a session, returns the ID.

```json
// Request (all optional)
{ "model": "gpt-4o", "temperature": 0.0 }

// Response
{ "session_id": "a1b2c3d4e5f6" }
```

#### `POST /api/sessions/{id}/upload`

Multipart file upload. Accepts CSV, XLSX, Parquet. Calls `load_file()` for
each file, adds to `session.tables`.

```json
// Response
{
  "tables": [
    { "name": "sales", "rows": 12847, "columns": 14 },
    { "name": "returns", "rows": 423, "columns": 6 }
  ]
}
```

#### `POST /api/sessions/{id}/load-sample/{dataset_id}`

Loads a sample dataset by ID. Resolves file paths, calls `load_file()` for
each, adds to `session.tables`.

Same response shape as upload.

#### `GET /api/sessions/{id}/tables`

Returns metadata for all loaded tables. Used by the data bar and data panel.

```json
{
  "tables": [
    {
      "name": "sales",
      "rows": 12847,
      "columns": [
        { "name": "date", "dtype": "datetime64[ns]" },
        { "name": "customer_id", "dtype": "int64" },
        { "name": "revenue", "dtype": "float64" }
      ]
    }
  ]
}
```

#### `POST /api/sessions/{id}/suggestions`

Generates LLM suggestions based on loaded table schemas. Lightweight —
single LLM call with table descriptions, returns 3-5 natural language
questions.

```json
// Response
{
  "suggestions": [
    "Revenue trends by quarter",
    "Top customers by lifetime value",
    "Product category performance comparison"
  ]
}
```

#### `POST /api/sessions/{id}/ask`

The main endpoint. Streams agent events via SSE.

```json
// Request
{ "message": "Revenue trends by quarter" }
```

SSE stream:

```
event: thinking
data: {"text": "I'll group revenue by quarter..."}

event: code
data: {"text": "quarterly = group_by(sales, \"quarter\", \"revenue\", \"sum\")..."}

event: artifact
data: {"id": "art_001", "kind": "table", "title": "sum(revenue) by quarter", "data": {...}}

event: artifact
data: {"id": "art_002", "kind": "chart", "title": "Revenue by Quarter", "data": {...}}

event: answer
data: {"text": "Revenue grew steadily across 2024..."}
```

Each SSE event maps directly to an agent `Event`. The `event:` field is
`Event.kind`, the `data:` field is `json.dumps(Event.data)`.

On error:

```
event: error
data: {"text": "Column 'revnue' not found in table 'sales'. Available: date, customer_id, revenue, ..."}
```

The client can cancel by closing the connection.

#### `GET /api/sessions/{id}/artifacts/{artifact_id}`

Returns the full data for a single artifact. Used for:
- Full-screen overlay (needs full-resolution chart data)
- Download (CSV for tables, PNG for charts)
- "View underlying data" (chart → its source table)

```json
{
  "id": "art_002",
  "kind": "chart",
  "title": "Revenue by Quarter",
  "data": {
    "chart_type": "line",
    "x": ["Q1", "Q2", "Q3", "Q4"],
    "y": [1000000, 1200000, 2100000, 2300000],
    "x_label": "quarter",
    "y_label": "revenue"
  },
  "source_table": {
    "columns": ["quarter", "revenue"],
    "rows": [["Q1", 1000000], ["Q2", 1200000], ...]
  }
}
```

## What Gets Deleted

| Old Route | Reason |
|---|---|
| `POST /investigate` | Replaced by `POST /ask` |
| `POST /clarify` | No clarification loop in new agent |
| `POST /scan` | No workspace scanning concept |
| `POST /memo` | LLM synthesizes via `final_answer` |
| `GET /artifacts` (list all) | Not needed — artifacts arrive via SSE events |

The queue+thread bridge (`_iter_to_queue`, `_SENTINEL`, `threading.Event`)
is deleted. The new agent is async-native.

## File Structure

```
api/
├── main.py         # App, middleware, routes, SSE streaming
├── sessions.py     # SessionManager (create/get/destroy)
└── datasets.py     # SAMPLE_DATASETS, get_dataset_paths
```

`datasets.py` moves from `src/analytics_agent/datasets.py` to `api/datasets.py`.
The sample dataset catalog is a routing concern — the agent doesn't know
about dataset IDs or file paths on disk. It only knows about Sessions with
DataFrames.

## SSE Implementation

```python
@app.post("/api/sessions/{session_id}/ask")
async def ask(session_id: str, body: AskRequest):
    session = _get_session(session_id)

    async def stream():
        async for event in run(session, body.message):
            yield {
                "event": event.kind,
                "data": json.dumps(event.data),
            }

    return EventSourceResponse(stream())
```

That's it. No queue. No thread. No sentinel. The agent is async, SSE wraps
it directly.

## Artifact Data Flow

Artifacts flow through two paths:

**1. During streaming (via SSE):**
Agent emits `Event("artifact", {...})` → SSE delivers to client → UI renders
inline. The artifact data in the SSE event is sufficient for inline display
(chart config, table preview, stat value).

**2. On demand (via REST):**
Client requests `GET /artifacts/{id}` → API reads from `session.artifacts` →
returns full data including source table. Used for full-screen overlay,
download, and "view underlying data".

The SSE artifact event carries enough data for inline rendering. The REST
endpoint provides the full-resolution version when the user drills in.

## What This Plan Does NOT Cover

- **Authentication / multi-user** — production concern, not architectural.
- **Rate limiting** — production concern.
- **Persistent session storage** — in-memory for now. Add persistence later.
- **WebSocket alternative** — SSE is sufficient. Revisit only if bi-directional
  streaming is needed.
