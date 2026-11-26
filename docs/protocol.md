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
- Hosted free OpenCode smoke calls returned HTTP 429. The live development run used local Qwen3 4B under Ollama. For held-out runs, the replacement uses the same weights with a 16,384-token server context and a 1,500-token per-call generation cap, plus a prompt-level `/no_think` hint. The handoff directs the replacement to the relevant source region first. Case targets, graders, one-attempt policy, and 180-second worker limit remain fixed.
- One exploratory Codex-to-Codex trial reruns the development case as a same-runtime comparison. It helps isolate whether the handoff and grading path can complete a live task when the replacement model changes. It uses the same case predicates and time limit. Report its task outcome separately from cross-runtime success.
- The final mechanical rerun also checks the public task manifest. It decodes the optional Git patch, recomputes the checkpoint fingerprint, and checks that the named continuation step survived export. This additive gate leaves the original transport and fault predicates unchanged.

## Follow-up on OpenCode timeouts

Keep the pinned parents, Codex source model, workspace selection, graders, and 180-second limit. Reproduce the historical held-out configuration on Packaging with Qwen3 4B, its 16,384-token context, 1,500-token generation cap, and the original prompt hint. Collect OpenCode step and tool timing and Ollama request durations. A request active when the supervisor fires is evidence of time spent waiting for inference. A run that spends the budget between requests or on denied tools would support a different diagnosis.

For the stronger-model rerun, test hosted free availability using a trivial prompt. If the free endpoints return a quota error, run Qwen3.5 9B locally. Use a short synthetic file-edit smoke probe to validate the model route and tool permissions. Run each of the original three repository cases once for the primary comparison. Report each result against the same 180-second gate. If that gate still cuts off an active replacement, a separately labeled confirmation may allow more time on a failed case. The already-seen repositories measure feasibility and failure modes. They provide no independent estimate of model quality.
