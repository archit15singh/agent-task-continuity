# Implementation plan

Scope is ranks 1–11 from the original build ranking. The first release is a local Python CLI with a SQLite task store, Git-backed workspace snapshots, and a loopback HTTP publishing adapter for a controlled service.

| Phase | Ranks | Deliverable and completion evidence |
|---|---|---|
| 1. Planned handoff | 1–4 | Create a task, checkpoint tracked and explicitly selected untracked changes, inspect drift, then restore and launch a replacement from a detached workspace. Verify content and prompt through the CLI. |
| 2. Study harness | 5–6 | Freeze public upstream revisions, controls, grading, and stop conditions before running the comparative cases. Exercise the negative control before collecting comparative evidence. |
| 3. Recovery and publication | 7–11 | Run a bounded worker, handle abnormal exits and timeouts, restore from the last durable checkpoint, fence stale owners at checkpoint and publishing boundaries, and reconcile a provider write after acknowledgment loss. Bind test results to the exact selected workspace content. |
| 4. Evaluation and publication | 1–11 | Run deterministic scenario evaluations across public upstream worktrees, run a live Codex-to-OpenCode handoff, and publish the paper, protocols, results, receipts, and an evidence-driven README. |

## Design choices

- Git supplies the base and patch semantics. Worktree bytes after restore are the guarantee. Staging, ignored files, Git submodules, active shells, and session internals are outside the file snapshot contract.
- Every attempt works in its own checkout except the explicitly user-managed initial workspace. Updating SQLite ownership and accepting a checkpoint are atomic within SQLite. Immutable patch bytes are committed in that same transaction.
- Stable operation IDs, a provider-side idempotency contract, and provider lookup cover acknowledgment loss. Only the managed route participates in fencing. Runtime sandboxing, external authorization, and public write credentials belong to the operator.
- State is local. A worker timeout is a supervisor decision. Local snapshots establish a bounded recovery point, and an agent must checkpoint during its work to make newer edits recoverable.
- Use real open-source code and read-only upstream access. External writes during the study go to a controlled loopback service. The public study repository is the publication destination.
