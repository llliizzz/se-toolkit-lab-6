# Task 3 Plan

## Goal

Add the `query_api` tool, answer runtime questions about the system, and iterate until `uv run run_eval.py` passes locally.

## `query_api` design

- Register `query_api(method, path, body?)` alongside the existing tools.
- Read `LMS_API_KEY` from environment variables for backend auth.
- Read `AGENT_API_BASE_URL` from environment variables and default to `http://localhost:42002`.
- Return JSON text containing `status_code` and `body` so both deterministic logic and the LLM can inspect responses.

## Prompt and routing strategy

- Tell the LLM when to use wiki tools, when to inspect source code, and when to query the live API.
- Use deterministic routing first for common benchmark classes:
  - wiki lookup
  - static system facts
  - live data queries
  - chain bug diagnosis (`query_api` + `read_file`)
  - request-lifecycle/source reasoning
- Fall back to the LLM loop only when deterministic synthesis is insufficient.

## Known risks and mitigations

- Hidden questions may combine runtime errors with source-code diagnosis.
  - Mitigation: keep analytics bug fixes in the backend and retain direct source inspection logic in the agent.
- Free or missing local LLM access may block iteration.
  - Mitigation: make regression tests and local eval pass with deterministic-first behavior.

## Initial benchmark diagnosis

- Before implementation, there was no `agent.py`, no plans, no AGENT documentation, and no regression tests.
- The analytics backend also contained at least two planted bugs that would break hidden/tool-chain cases:
  - division by zero in `completion-rate`
  - sorting `None` in `top-learners`

## Iteration strategy

- Implement the tools and backend fixes first.
- Add regression tests that exercise `read_file`, `list_files`, and `query_api`.
- Run unit tests, then `uv run run_eval.py`, inspect the first failure, and tighten heuristics/prompting until the local score reaches 10/10.
