---
title: "Recovering Coding-Agent Work Across Runtime Boundaries"
subtitle: "A local Git and SQLite prototype evaluated on three open-source projects"
date: "November 26, 2026"
geometry: margin=0.82in
fontsize: 11pt
colorlinks: true
---

## Abstract

Conversation history can explain a coding task. Recovery also requires a restorable workspace, evidence tied to the artifact, and a way to resolve external actions whose outcome is uncertain. We built a local CLI that stores a task independently of its worker, preserves selected Git workspace changes, fences writes at managed boundaries, and reconciles a controlled publishing service by operation ID. On pinned changes in Click, Packaging, and attrs, both a manual Git bundle and managed continuation restored the selected files in 3/3 cases. A brief-only transport control restored them in 0/3. Across six managed publication trials spanning two fault modes, the provider applied one effect per operation and the replacement confirmed every outcome. Three live Codex-to-OpenCode handoffs preserved their inputs, but the local replacement timed out in every case. An exploratory Codex-to-Codex comparison completed the Click change. The strongest result concerns recoverable task state and controlled side effects. We report runtime completion and deterministic transport as separate outcomes.

## 1. Motivation and questions

A coding worker can disappear after changing files, while waiting for a decision, or after sending a request whose acknowledgment is lost. A saved conversation helps another worker understand prior reasoning. Git and the external provider still carry facts that must be checked before the replacement can act. We asked three questions.

1. Can a managed checkpoint restore the selected work as faithfully as an explicit Git patch plus copied files?
2. Can a fresh owner recover a checkpoint after process death, reject a retired owner at a managed boundary, and reconcile an uncertain external write?
3. Can a real replacement runtime finish a graded change using the restored artifacts?

The evaluation plan distinguished these questions before running the comparison. The project implements the top 11 ranked ideas as one vertical slice. The CLI covers cross-agent continuation, snapshots, a task manifest, and inspection. The study covers fault injection and a comparison harness. The execution path covers replacement supervision, an action ledger, ownership fencing, revision-bound verification, and managed publishing.

## 2. System

A *task* has an objective, a current workspace, an owner generation, and a pointer to its latest checkpoint. An immutable checkpoint stores the Git base commit, a binary patch, the selected untracked paths, and a continuation note. Capture uses an alternate Git index. Restore applies the patch in a detached worktree and rechecks the fingerprint before transferring ownership. A checkpoint write and an owner change each compare current state inside a SQLite transaction. Retired workers can still write to their own local checkout. The managed checkpoint and publishing paths reject the retired credential.

The JSON manifest carries the objective, constraints, decisions, remaining actions, acceptance criteria, evidence, and operation status. An optional binary patch makes the workspace artifact transferable to another checkout with the same base.

A verifier runs the operator's command in a disposable checkout of the saved artifact. The receipt records the artifact fingerprint, command, exit status, output hash, and basic host details. Inspection marks evidence stale when the selected workspace contents change. The publish command requires a passing receipt for the snapshot it names.

The gateway reserves a stable operation ID and immutable payload before sending a request. On acknowledgment loss, the next owner can query the provider by ID. The reference provider returns the original receipt for an identical operation and rejects payload changes under that key. The authority check and request initiation share a local transaction. An already-started request can survive a worker's death. Provider idempotency and lookup address that separate failure mode.

## 3. Methods

We used historical source changes in [Click](https://github.com/pallets/click/commit/fdb65f4809719580436acb067410cec64433e5de), [Packaging](https://github.com/pypa/packaging/commit/cf2cdf099375f7e208168cd2d8880699aeef0583), and [attrs](https://github.com/python-attrs/attrs/commit/319c53cc178afe980362c1bd59d8109019e344bd). Click was the development case. Packaging and attrs were held out from development execution. The graders were authored with access to the public reference diffs. The case manifest pins parents and references. Native checks ran with Python 3.13.18, Apple Git 2.54.0, and pinned Python dependencies on one arm64 macOS host.

**Transport.** We applied only the upstream implementation-file diff to the historical parent, then added a selected untracked note. The brief-only control received the same objective and note text but started in a clean worktree. The manual arm exported a binary Git patch and copied the selected file. The managed arm saved a checkpoint, killed the initial worker, and restored into a new checkout. We graded both files byte-for-byte and ran an independent case predicate. The brief-only arm controls for transporting information while leaving out the artifact. It received no reconstruction worker.

**Faults.** We killed the worker after it wrote an edit beyond the checkpoint boundary. We checked recovered files, retired-owner rejection, and stale verification detection. In one publication scenario the provider accepted the operation and dropped its response. In the second, added as an explicitly recorded extension, the fixture killed the client after provider acceptance and before a receipt could commit locally. Each recovery counted provider writes and applied effects independently of SQLite state.

**Live feasibility.** A headless Codex worker received a scoped task and wrote a failing reproduction plus handoff note. It received the public parent revision and no reference patch. The secondary worker ran through the shipping continuation CLI using headless OpenCode with local Qwen3 4B. It could edit the named implementation file. An out-of-band grader checked artifact preservation, independent behavior, the source reproduction, and the upstream native test module. Each stage had a 180-second limit. Hosted OpenCode free-model probes returned HTTP 429. The local development run and held-out model settings are recorded separately.

## 4. Results

### 4.1 Transport and recovery

| Project | Brief only | Manual Git | Managed restore | Upstream test module |
|---|---:|---:|---:|---|
| Click | Fail | Pass | Pass | 52 passed, 1 skipped |
| Packaging | Fail | Pass | Pass | 238 passed |
| attrs | Fail | Pass | Pass | 53 passed |

A transport pass required matching tracked bytes, matching selected untracked bytes, and a positive source predicate. Manual Git and managed handoff tied on this measure. The measured wall times include grading and different steps. The median was 0.094 seconds for the scripted manual arm and 0.573 seconds for the managed arm, which also launched a worker, killed it, and ran a replacement. These timings describe the scripted procedures. Estimating operator effort or speedup requires a separate comparison.

All 39 original managed fault predicates passed across the three projects. The retired owner was rejected at checkpoint and publication boundaries in all three. In the two publication fault modes, the replacement confirmed the outcome in 6/6 scenarios. The provider observed one PUT and one effect per scenario. The worker's edit made after the last checkpoint was lost in 3/3 cases, as expected at the documented recovery boundary. The versioned manifest exported matching snapshot fingerprints in all three projects. Six product tests separately covered binary capture, concurrent takeover, recovery-key rotation, publication, manifest export, and out-of-worktree file selection.

The first held-out run reached the transport and fault checks. Packaging's native suite stopped during collection because the test environment lacked `pretend`. We pinned the dependency, retained the failed receipt, and reran the same cases. The final native modules reported 343 passes and one skip in total.

### 4.2 Live feasibility

| Project and arm | Source stage | Replacement | Restored inputs | Task result |
|---|---:|---:|---|---|
| Click · Codex to OpenCode | 27.6 s | 180.0 s | Both files | Timeout |
| Packaging · Codex to OpenCode | 30.6 s | 180.0 s | Both files | Timeout |
| attrs · Codex to OpenCode | 28.5 s | 180.0 s | Both files | Timeout |
| Click · Codex to Codex | 38.5 s | 26.2 s | Both files | Passed |

The three OpenCode runs recovered a reproduction that failed with an assertion on the original revision and preserved the handoff note byte-for-byte. During the two held-out runs, OpenCode emitted four and two tool-use events, respectively. Neither run produced a passing implementation before timeout. Native baseline tests still passed because the independent predicate and the carried reproduction targeted the behavior missing from the historical source.

The exploratory same-runtime Click trial preserved both files, edited only the intended implementation file, passed the independent predicate, made the carried reproduction pass, and finished the native test module with 52 passes and one skip. This establishes that the same handoff and grading procedure can complete a live task with another session. The experimental arms differ in runtime and model, and we cannot attribute the difference to either in isolation.

## 5. Design implications and limits

Git patch export is a strong baseline. The managed path earns its complexity when work has to survive an unattended interruption, a conflict over who owns the task, or uncertain publication. The replay unit in this prototype is a task checkpoint tied to an artifact. Agent sessions remain helpful as optional context.

The gateway makes the guarantee observable because it owns the credential check and protocol. Direct shell and API writes outside it remain outside the fence. The black-box test used one host, a common Git object store, three Python repositories, selected file changes, and a loopback fixture with in-memory state. It exercised worker and publishing-client death while the provider survived. Durable provider restart, remote hostile workers, source-control pushes, and distributed consensus were outside the reported scenarios. The snapshot follows Git normalization, preserves selected files, and requires that the shared repository retain its base. The receipt describes the host and command, while dependency and tool versions beyond those explicitly pinned remain part of the operator's environment.

Historical public changes can appear in model training data. The live sample is small and mixes a hosted source model with a local replacement. The study used one attempt per live case and changed local context and generation bounds after the development pilot. These results establish observed feasibility and failure modes under the recorded conditions. Comparative model quality, productivity, and broad framework rankings remain outside the conclusions.

## 6. Related work

Temporal documents the failure mode where an activity completes externally before its worker can report completion and recommends idempotent activities. OpenAI Symphony organizes work around an issue and its workspace, and its specification lists persistence of retry and session metadata as a recommended extension. Cross Agent Handoff records project-level checkpoints across runtimes and describes its writer lock as advisory. ACP covers client-agent session operations. A2A defines agent task and artifact exchange. Their contracts address useful layers of the system. This prototype evaluates the surrounding workspace, authority, and side-effect recovery directly.

1. [Temporal documentation, Activity Definition](https://docs.temporal.io/activity-definition)
2. [OpenAI Symphony specification](https://github.com/openai/symphony/blob/main/SPEC.md)
3. [Cross Agent Handoff](https://github.com/kristianrolando/cross-agent-handoff)
4. [Agent Client Protocol, Session Setup](https://agentclientprotocol.com/protocol/v1/session-setup)
5. [Agent2Agent Protocol specification](https://a2a-protocol.org/latest/specification/)

## Reproducibility

The [public repository](https://github.com/archit15singh/agent-task-continuity) contains the frozen protocol, case manifest, CLI, scripts, and receipts. The final mechanical run used candidate `c2f94ba`. The held-out live run used `b4ce25b`. See the repository's evidence index for exact commands, model settings, test summaries, and the first held-out run's collection failure.
