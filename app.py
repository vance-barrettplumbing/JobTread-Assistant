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
from jobtread_client import JobTreadClient, GraphQLError

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Globals initialised once at startup
# ---------------------------------------------------------------------------
_jt_client: JobTreadClient | None = None
_ai_client: anthropic.Anthropic | None = None
_schema_summary: str = ""
_tools: list = []

SYSTEM_PROMPT = """You are a helpful assistant for JobTread, a construction management platform.
You have access to the JobTread API via GraphQL and can:
- Query jobs, contacts, to-dos, tasks, budgets, expenses, documents, and more
- Create, update, and manage records in JobTread

When the user asks a question about their JobTread data or asks you to make changes,
use the `run_jobtread_query` tool to fetch or mutate data.

Guidelines:
- Always confirm destructive changes (deletions, status changes) before executing
- When listing items, show the most relevant fields (id, name, status, dates)
- For ambiguous requests, ask for clarification before acting
- Present data in a clean, readable format using markdown
- If a query fails, explain what went wrong and suggest alternatives
"""


def build_tools(schema_summary: str) -> list:
    return [
        {
            "name": "run_jobtread_query",
            "description": (
                "Execute a GraphQL query or mutation against the JobTread API. "
                "Use this for all data retrieval and modifications.\n\n"
                f"Available schema:\n{schema_summary}"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The GraphQL query or mutation string",
                    },
                    "variables": {
                        "type": "object",
                        "description": "Optional GraphQL variables",
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


def summarize_schema(schema_data: dict) -> str:
    schema = schema_data.get("__schema", {})
    lines = []
    qt = schema.get("queryType", {})
    mt = schema.get("mutationType", {})
    if qt and qt.get("fields"):
        lines.append("## Queries")
        for f in qt["fields"]:
            args = ", ".join(a["name"] for a in f.get("args", []))
            lines.append(f"- `{f['name']}({args})` — {f.get('description', '')}")
    if mt and mt.get("fields"):
        lines.append("\n## Mutations")
        for f in mt["fields"]:
            args = ", ".join(a["name"] for a in f.get("args", []))
            lines.append(f"- `{f['name']}({args})` — {f.get('description', '')}")
    return "\n".join(lines) if lines else "Schema unavailable."


def init_clients():
    global _jt_client, _ai_client, _schema_summary, _tools

    api_key = os.getenv("JOBTREAD_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or not anthropic_key:
        raise RuntimeError("JOBTREAD_API_KEY and ANTHROPIC_API_KEY must be set in .env")

    _jt_client = JobTreadClient(api_key)
    _ai_client = anthropic.Anthropic(api_key=anthropic_key)

    try:
        schema_data = _jt_client.get_top_level_fields()
        _schema_summary = summarize_schema(schema_data)
        print("✓ JobTread schema loaded")
    except Exception as e:
        _schema_summary = "Schema unavailable — use standard JobTread GraphQL types."
        print(f"⚠ Could not load schema: {e}")

    _tools = build_tools(_schema_summary)


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

    def generate():
        conversation = list(messages)

        while True:
            response = _ai_client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=_tools,
                messages=conversation,
            )

            assistant_content = response.content
            conversation.append({"role": "assistant", "content": assistant_content})

            # Stream text blocks to the client
            for block in assistant_content:
                if block.type == "text" and block.text:
                    yield f"data: {json.dumps({'type': 'text', 'content': block.text})}\n\n"

            if response.stop_reason != "tool_use":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            # Execute tool calls
            tool_results = []
            for block in assistant_content:
                if block.type != "tool_use":
                    continue

                desc = block.input.get("description", "Running query…")
                yield f"data: {json.dumps({'type': 'tool_call', 'description': desc})}\n\n"

                try:
                    result = _jt_client.query(
                        block.input["query"],
                        block.input.get("variables"),
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
                except GraphQLError as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"GraphQL Error: {e}",
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
    """Hit http://localhost:5000/debug to see the raw API response."""
    import requests as req
    api_key = os.getenv("JOBTREAD_API_KEY")
    url = os.getenv("JOBTREAD_API_URL", "https://api.jobtread.com/pave")
    try:
        r = req.post(
            url,
            json={"query": "{ __typename }"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=10,
        )
        return jsonify({
            "url": url,
            "status_code": r.status_code,
            "response_headers": dict(r.headers),
            "body": r.text,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_clients()
    print("\n🚀 JobTread Assistant running at http://0.0.0.0:5000")
    print("   Open in browser or share your local IP with your phone\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
