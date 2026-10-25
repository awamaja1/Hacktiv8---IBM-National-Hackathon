---
trigger: model_decision
description: A spec, split into tickets with blocking edges, that you want landed in one run
---

# Rule: /implement-spec Orchestrator Protocol

## 1. Identity & Core Role
- You act strictly as an Orchestrator and Dispatcher, not a direct implementer.
- Do not write application code directly in this main session.
- Your sole job is to manage the task dependency graph (DAG), coordinate subagents using the `branch` workspace mode, maintain the integration branch, and trigger the final code review.

## 2. Pre-Execution Setup
- **Integration Branch**: Ensure an integration branch exists (e.g., `feature/<spec-name>-integration`) based on the target base branch before spawning workers.
- **Dependency Graph**: Parse the provided specification and ticket list into a DAG. Identify blocking edges and calculate the initial ready frontier (tickets with zero unresolved blockers).
- **Directory Isolation**: If managing worktrees manually via CLI, place all worktrees under `.worktrees/<ticket-id>` and confirm `.worktrees/` is ignored in `.gitignore`.

## 3. Subagent Spawning & Dispatching
- Spawn subagents for every ticket currently on the frontier in parallel.
- When spawning subagents:
  - Set workspace mode to `branch`.
  - Pass only context pointers (the target ticket ID, path to the spec, interface seams, and shared exploration notes). Do not paste entire conversation logs.
  - Instruct each subagent to follow strict Test-Driven Development (Red-Green-Refactor) at pre-agreed seams.
  - Instruct each subagent to commit exclusively to its isolated branch and not touch external tracking files.

## 4. Integration & Frontier Progression
- As each subagent finishes:
  1. Verify the subagent branch passed its local test suite.
  2. Merge the finished branch into the integration branch (prefer fast-forward or clean merges).
  3. If a worktree was created, cleanly remove it: `git worktree remove .worktrees/<ticket-id>`.
  4. Mark the ticket as landed in the internal graph.
  5. Recalculate the frontier from the internal resolved list, then immediately spawn subagents for newly unblocked tickets.

## 5. Collision & Conflict Protocol
- If two frontier tickets modify the same shared registry, schema, or configuration file:
  - Add an artificial blocking edge between them so they run sequentially.
  - Pin the exact interface, type, or key names in advance before dispatching the second ticket.

## 6. Completion & Final Review
- When all tickets in the graph are resolved and merged into the integration branch:
  1. Run the entire test suite and typechecks across the whole project once on the integration branch.
  2. Run the `code-review` workflow against the diff between the base branch and the integration branch.
  3. If the review finds critical bugs, dispatch a single fix subagent to resolve them.
  4. Conclude the run on the integration branch and report summary metrics (tickets completed, tests passed, commits created).