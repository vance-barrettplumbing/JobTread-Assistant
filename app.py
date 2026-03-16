"""
JobTread AI Assistant — Flask web app.

Run with:  python app.py
Then open: http://localhost:5000  (or your local IP from phone)
"""
import os
import json
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from dotenv import load_dotenv
import anthropic
from jobtread_client import JobTreadClient, PaveError

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Globals initialised once at startup
# ---------------------------------------------------------------------------
_jt_client: JobTreadClient | None = None
_ai_client: anthropic.Anthropic | None = None
_org_id: str = ""
_org_name: str = ""
_tools: list = []

SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant for JobTread, a construction management platform.
You can query and modify any data in JobTread using the `run_jobtread_query` tool.

## Organization
- Organization name: {org_name}
- Organization ID: {org_id}  ← use this for all queries requiring organizationId

## Pave Query Language
JobTread uses a JSON-based query language called Pave (NOT GraphQL strings).

**Field selection** — return a field by setting it to `{{}}`:
```json
{{"organization": {{"$": {{"id": "{org_id}"}}, "id": {{}}, "name": {{}}}}}}
```

**Inputs** — pass arguments under `$` at the same level as the fields you want:
```json
{{"job": {{"$": {{"id": "JOB_ID"}}, "id": {{}}, "name": {{}}, "number": {{}}}}}}
```

**Nested/connection fields** — query sub-objects the same way:
```json
{{"organization": {{
  "$": {{"id": "{org_id}"}},
  "jobs": {{
    "nextPage": {{}},
    "nodes": {{"id": {{}}, "name": {{}}, "number": {{}}, "closedOn": {{}}}}
  }}
}}}}
```

**Pagination** — add `size` and `page` to `$`, query `nextPage`:
```json
{{"$": {{"size": 20, "page": null}}, "nodes": {{"id": {{}}, "name": {{}}}}}}
```

**Filtering** — use `where` in `$`:
```json
{{"$": {{"where": [["status", "=", "active"]]}}, "nodes": {{"id": {{}}, "name": {{}}}}}}
```

**Sorting**:
```json
{{"$": {{"sortBy": [{{"field": "name"}}]}}, "nodes": {{"id": {{}}, "name": {{}}}}}}
```

## Key Operations
- `organization($: {{id}})` — org data; has `.jobs`, `.accounts`, `.contacts`, `.documents`, `.tasks`, `.locations`, `.customFields`, etc.
- `job($: {{id}})` — single job; has `.documents`, `.tasks`, `.costItems`, `.comments`, `.files`, etc.
- `account($: {{id}})` — customer/vendor
- `contact($: {{id}})` — contact person
- `task($: {{id}})` — task or to-do
- `document($: {{id}})` — invoice, order, bid, etc.
- `createJob`, `updateJob`, `deleteJob`
- `createTask`, `updateTask`, `deleteTask`
- `createAccount`, `updateAccount`, `deleteAccount`
- `createContact`, `updateContact`, `deleteContact`
- `createDocument`, `updateDocument`
- `createComment`, `updateComment`
- `currentGrant` — who is authenticated

## Rules
- Always include `id: {{}}` for every object you request (required by the API)
- Confirm before any destructive action (delete, status change)
- Present results in clean markdown
- For to-dos, use `tasks` with `isToDo: true` filter
"""


def build_tools(org_id: str) -> list:
    return [
        {
            "name": "run_jobtread_query",
            "description": (
                "Execute a Pave query or mutation against the JobTread API. "
                "Pass a JSON object (not a GraphQL string) as the query. "
                "The grantKey is injected automatically — do not include it. "
                f"Organization ID is: {org_id}"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "object",
                        "description": (
                            "The Pave query as a JSON object. Example: "
                            '{"organization": {"$": {"id": "ORG_ID"}, "id": {}, "name": {}}}'
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this query does",
                    },
                },
                "required": ["query", "description"],
            },
        }
    ]


def init_clients():
    global _jt_client, _ai_client, _org_id, _org_name, _tools

    grant_key = os.getenv("JOBTREAD_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not grant_key or not anthropic_key:
        raise RuntimeError("JOBTREAD_API_KEY and ANTHROPIC_API_KEY must be set in .env")

    _jt_client = JobTreadClient(grant_key)
    _ai_client = anthropic.Anthropic(api_key=anthropic_key)

    # Discover org ID from the grant
    try:
        result = _jt_client.get_current_grant()
        memberships = (
            result.get("currentGrant", {})
                  .get("user", {})
                  .get("memberships", {})
                  .get("nodes", [])
        )
        if memberships:
            org = memberships[0].get("organization", {})
            _org_id = org.get("id", "")
            _org_name = org.get("name", "")
            print(f"✓ Connected to JobTread org: {_org_name} ({_org_id})")
        else:
            print("⚠ No organization memberships found on this grant")
    except Exception as e:
        print(f"⚠ Could not fetch org info: {e}")

    _tools = build_tools(_org_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])

    system = SYSTEM_PROMPT_TEMPLATE.format(org_id=_org_id, org_name=_org_name)

    def generate():
        conversation = list(messages)

        while True:
            response = _ai_client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=system,
                tools=_tools,
                messages=conversation,
            )

            assistant_content = response.content
            conversation.append({"role": "assistant", "content": assistant_content})

            for block in assistant_content:
                if block.type == "text" and block.text:
                    yield f"data: {json.dumps({'type': 'text', 'content': block.text})}\n\n"

            if response.stop_reason != "tool_use":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            tool_results = []
            for block in assistant_content:
                if block.type != "tool_use":
                    continue

                desc = block.input.get("description", "Running query…")
                yield f"data: {json.dumps({'type': 'tool_call', 'description': desc})}\n\n"

                try:
                    result = _jt_client.query(block.input["query"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
                except PaveError as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Pave Error: {e}",
                        "is_error": True,
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

            conversation.append({"role": "user", "content": tool_results})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/debug")
def debug():
    """Raw API test — open http://localhost:5000/debug"""
    try:
        result = _jt_client.get_current_grant()
        return jsonify({"ok": True, "org_id": _org_id, "org_name": _org_name, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_clients()
    print(f"\n🚀 JobTread Assistant running at http://0.0.0.0:5000")
    print(f"   Org: {_org_name} ({_org_id})\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
