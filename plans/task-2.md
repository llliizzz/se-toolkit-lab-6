# Task 2 Plan

## Goal

Upgrade the CLI into a documentation agent with `read_file` and `list_files`, a tool loop, and `source` references to wiki sections.

## Tool schemas

- Define `read_file(path)` and `list_files(path)` as OpenAI-compatible function schemas.
- Restrict both tools to paths inside the repository root.
- Return readable error strings for missing files, bad directories, and traversal attempts.

## Agent loop

- Send the user question, system prompt, and tool schemas to the model.
- If the model emits tool calls, execute them and append `tool` messages.
- Stop when the model emits a final answer or when the tool-call cap is reached.

## Deterministic support

- Add a repository-side retrieval path for wiki questions.
- Start with `list_files("wiki")`, then read the most relevant markdown files.
- Extract the most relevant heading and convert it into a `path#anchor` source reference.

## Test strategy

- Add subprocess tests for a wiki question about merge conflicts and a directory-discovery question about the `wiki/` folder.
- Verify the JSON structure, `source`, and presence of `read_file` or `list_files` in `tool_calls`.
