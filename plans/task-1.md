# Task 1 Plan

## Goal

Build a CLI agent that accepts a question, optionally calls an OpenAI-compatible LLM, and prints valid JSON with `answer` and `tool_calls`.

## LLM provider and config

- Read `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` from environment variables.
- Load `.env.agent.secret` locally for convenience, but never hardcode secrets.
- Keep a deterministic fallback path so local development and tests do not fail when LLM credentials are unavailable.

## Agent structure

- Parse the first CLI argument as the user question.
- Load environment variables from local secret files.
- Build a result object with `answer` and `tool_calls`.
- Print exactly one JSON line to stdout.
- Send logs and debug output to stderr only.

## Error handling

- If the question is missing, return a valid JSON response instead of crashing.
- If the LLM is unavailable, fall back to a deterministic answer path.
- Keep network timeouts below the 60 second task limit.

## Test strategy

- Add one regression test that runs `agent.py` as a subprocess.
- Parse stdout as JSON.
- Verify `answer` exists and `tool_calls` exists as a list.
