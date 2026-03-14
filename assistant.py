"""
JobTread AI Assistant — powered by Claude.

Usage:
    python assistant.py

Requires .env with:
    JOBTREAD_API_KEY=...
    ANTHROPIC_API_KEY=...
"""
import os
import json
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
import anthropic

from jobtread_client import JobTreadClient, GraphQLError

load_dotenv()

console = Console()

SYSTEM_PROMPT = """You are a helpful assistant for JobTread, a construction management platform.
You have access to the JobTread API via GraphQL and can:
- Query jobs, contacts, to-dos, tasks, budgets, expenses, documents, and more
- Create, update, and manage records in JobTread

When the user asks a question about their JobTread data or asks you to make changes,
you should use the `run_jobtread_query` tool to fetch or mutate data.

Guidelines:
- Always confirm destructive changes (deletions, status changes) before executing
- When listing items, show the most relevant fields (id, name, status, dates)
- For ambiguous requests, ask for clarification before acting
- Present data in a clean, readable format
- If a query fails, explain what went wrong and suggest alternatives

You have the full JobTread GraphQL schema available. Use proper GraphQL syntax.
"""


def build_tools(schema_summary: str) -> list:
    return [
        {
            "name": "run_jobtread_query",
            "description": (
                "Execute a GraphQL query or mutation against the JobTread API. "
                "Use this for all data retrieval and modifications. "
                f"\n\nAvailable schema summary:\n{schema_summary}"
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
                        "description": "Brief description of what this query does (shown to user)",
                    },
                },
                "required": ["query", "description"],
            },
        }
    ]


def summarize_schema(schema_data: dict) -> str:
    """Build a compact schema summary for the system prompt."""
    schema = schema_data.get("__schema", {})
    lines = []

    qt = schema.get("queryType", {})
    mt = schema.get("mutationType", {})

    if qt and qt.get("fields"):
        lines.append("## Available Queries")
        for f in qt["fields"]:
            desc = f.get("description", "")
            args = ", ".join(a["name"] for a in f.get("args", []))
            lines.append(f"- `{f['name']}({args})` — {desc}")

    if mt and mt.get("fields"):
        lines.append("\n## Available Mutations")
        for f in mt["fields"]:
            desc = f.get("description", "")
            args = ", ".join(a["name"] for a in f.get("args", []))
            lines.append(f"- `{f['name']}({args})` — {desc}")

    return "\n".join(lines) if lines else "Schema not available."


def run_assistant():
    api_key = os.getenv("JOBTREAD_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        console.print("[red]Error: JOBTREAD_API_KEY not set in .env[/red]")
        sys.exit(1)
    if not anthropic_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not set in .env[/red]")
        sys.exit(1)

    jt_client = JobTreadClient(api_key)
    ai_client = anthropic.Anthropic(api_key=anthropic_key)

    # Fetch schema on startup
    console.print("[dim]Connecting to JobTread API...[/dim]")
    try:
        schema_data = jt_client.get_top_level_fields()
        schema_summary = summarize_schema(schema_data)
        console.print("[green]Connected! Schema loaded.[/green]\n")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load schema: {e}[/yellow]")
        schema_summary = "Schema unavailable — use standard JobTread GraphQL types."

    tools = build_tools(schema_summary)
    conversation: list = []

    console.print(Panel(
        "[bold]JobTread Assistant[/bold]\n"
        "Ask me anything about your JobTread data, or ask me to make changes.\n"
        "Type [bold]quit[/bold] or [bold]exit[/bold] to stop.",
        style="blue"
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        conversation.append({"role": "user", "content": user_input})

        # Agentic loop
        while True:
            response = ai_client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=conversation,
            )

            # Collect text and tool uses from response
            assistant_content = response.content
            conversation.append({"role": "assistant", "content": assistant_content})

            # Print any text blocks
            for block in assistant_content:
                if block.type == "text" and block.text:
                    console.print(f"\n[bold green]Assistant:[/bold green]")
                    console.print(Markdown(block.text))

            # If no tool use, we're done
            if response.stop_reason != "tool_use":
                break

            # Process tool calls
            tool_results = []
            for block in assistant_content:
                if block.type != "tool_use":
                    continue

                tool_input = block.input
                query_desc = tool_input.get("description", "Running query...")
                console.print(f"\n[dim]> {query_desc}[/dim]")

                try:
                    result = jt_client.query(
                        tool_input["query"],
                        tool_input.get("variables"),
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


if __name__ == "__main__":
    run_assistant()
