# Evaluation protocol

## Decisions

1. Does a managed handoff restore the same selected work as an experienced operator exporting a patch plus selected files, with less manual state assembly?
2. Can a replacement recover an acknowledged checkpoint after a worker dies, adopt an external write whose acknowledgment was lost, and prevent a retired worker from using the managed write path?
3. Does a live cross-runtime handoff complete a real, graded task? This is a feasibility check. Models and sample size do not support a performance comparison.

## Frozen design

The case manifest pins the upstream parent and reference revisions. Click is the development case. Packaging and attrs are held out from product implementation and development execution. Case requirements and graders were authored with access to public reference changes. Public repository history may be present in model training data. Candidate worktrees in the live arm fetch just the parent and receive no reference patch or grader.

### Recovery comparison

For each case the runner stages the exact historical implementation-file diff (excluding upstream tests and docs) as working-tree edits. It also generates a selected untracked note with a distinct ID. The same input is used for all arms, in fresh isolated worktrees.

- **Brief only** receives the objective and note text in a separate message and starts in a fresh checkout. It is the negative transport control. The control receives no reconstruction agent.
- **Manual Git** receives the same brief plus an operator-exported binary patch and an explicit copy of the untracked file.
- **Managed** receives the same brief via the tool, plus a checkpoint. It is restored after an initial worker writes a late change and receives SIGKILL, then a replacement runs the case grader.

All arms are graded by file SHA-256 and a case-specific source predicate. The source predicates cover context settings in Click, free-threaded ABI selection in Packaging, and preservation of mapping output plus avoidance of redundant class probes in attrs. Untracked data and tracked content are graded separately. The managed arm also checks its selected snapshot digest, stale checkpoint rejection, verification ties, loss of acknowledgment, provider receipt recovery, remote application count, stale publish rejection, and changed-artifact rejection. The provider is a separate HTTP boundary with an in-memory idempotency ledger. Each scenario is run once per report, with no replacement quality retries.

### Live feasibility

Use Codex headless for a scoped first stage that writes a reproduction and a handoff note in the source workspace. Use OpenCode headless as the first choice for the replacement and a free local model if available. The replacement receives the task objective and the checkpoint note, with restored files. It may edit the named implementation file. Codex headless is the availability fallback and is reported as same-runtime, not cross-runtime, if used. Grade the final artifact out of band with the same case predicate and verify the source reproduction survived. Use Click as a development run, then one Packaging and one attrs run. One source and one replacement attempt per case after the protocol is frozen. Adapter smoke probes may retry without exposing any case. Each worker is capped at 180 seconds. No paid API budget is committed.

### Gates

Before comparative execution run unit tests, the Click dry run, and a wrong-revision evidence check. Treat a negative-control pass, baseline or managed integrity failure, duplicate provider application, or accepted stale write as an engineering failure. A live failure stays in the results. Publish counts, failures, environment, case revisions, test receipts, and elapsed times. Timings are descriptive and mix different workflow steps. For the live feasibility arm, a complete pass requires two distinct runtime invocations, a preserved reproduction, and a positive grader.

## Recorded amendments

- The first held-out mechanical run reached all source and fault gates. Packaging's native suite failed during collection because its `pretend` dependency was missing. The original receipt is retained. The pinned dependency was added and the same cases and grading rules rerun.
- An additional fault probe kills the publishing client after the provider commits but before the client can record a result. This supplements the frozen comparison by exercising a durable `reserved` intent with the original process gone. It is reported separately from the original gates.
