from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_agent(question: str, extra_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    env.pop("LLM_API_KEY", None)
    env.pop("LLM_API_BASE", None)
    env.pop("LLM_MODEL", None)
    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        [sys.executable, "agent.py", question],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def test_agent_returns_answer_and_tool_calls() -> None:
    data = run_agent("What does REST stand for?")
    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)


def test_agent_reads_wiki_for_merge_conflicts() -> None:
    data = run_agent("How do you resolve a merge conflict?")
    tools = {call["tool"] for call in data["tool_calls"]}
    assert "read_file" in tools
    assert "wiki/git-workflow.md" in data["source"]


def test_agent_lists_wiki_files() -> None:
    data = run_agent("What files are in the wiki?")
    tools = {call["tool"] for call in data["tool_calls"]}
    assert "list_files" in tools
    assert "wiki" in data["answer"].lower()


def test_agent_reads_source_for_framework_question() -> None:
    data = run_agent("What framework does the backend use?")
    tools = {call["tool"] for call in data["tool_calls"]}
    assert "read_file" in tools
    assert "fastapi" in data["answer"].lower()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/items/":
            body = json.dumps([{"id": 1}, {"id": 2}, {"id": 3}]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def test_agent_uses_query_api_for_item_count() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        data = run_agent(
            "How many items are in the database?",
            extra_env={
                "AGENT_API_BASE_URL": f"http://127.0.0.1:{server.server_port}",
                "LMS_API_KEY": "test-key",
            },
        )
    finally:
        server.shutdown()
        thread.join()

    tools = {call["tool"] for call in data["tool_calls"]}
    assert "query_api" in tools
    assert "3" in data["answer"]
