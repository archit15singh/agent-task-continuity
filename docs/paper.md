---
title: "Recovering Coding-Agent Work Across Runtime Boundaries"
subtitle: "A local Git and SQLite prototype evaluated on three open-source projects"
date: "November 26, 2026"
geometry: margin=0.82in
fontsize: 11pt
colorlinks: true
---

## Abstract

Conversation history can explain a coding task. Recovery also requires a restorable workspace, evidence tied to the artifact, and a way to resolve external actions whose outcome is uncertain. We built a local CLI that stores a task independently of its worker, preserves selected Git workspace changes, fences writes at managed boundaries, and reconciles a controlled publishing service by operation ID. On pinned changes in Click, Packaging, and attrs, both a manual Git bundle and managed continuation restored the selected files in 3/3 cases. A brief-only transport control restored them in 0/3. Across six managed publication trials spanning two fault modes, the provider applied one effect per operation and the replacement confirmed every outcome. The original three Codex-to-OpenCode runs timed out. A replay found sustained local inference and a stale working-directory environment. After fixing the workspace launch, a stronger local Qwen3.5 9B model restored both inputs in all three cases and still passed 0/3 within 180 seconds. The original corrected 4B Packaging failure reached the summary output limit. A frozen Packaging rerun completed 0/2 with auto compaction enabled and 0/2 with it disabled. An exploratory Codex-to-Codex comparison completed the Click change. A separate bare-Git experiment recovered the exact intended ref in 3/3 interrupted pushes with one receiver update per trial. The strongest result concerns recoverable task state and controlled side effects. We report runtime completion and deterministic transport as separate outcomes.

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

**Faults.** We killed the worker after it wrote an edit beyond the checkpoint boundary. We checked recovered files, retired-owner rejection, and stale verification detection. In one publication scenario the provider accepted the operation and dropped its response. In the second, added as an explicitly recorded extension, the fixture killed the client after provider acceptance and before a receipt could commit locally. Each recovery counted provider writes and applied effects independently of SQLite state. An independent follow-up exercised a standard bare Git receiver. It held the push open after the ref became visible, killed the local push process group before the command returned, and checked the ref through a separate Git request. A matching SHA and a different SHA were then pushed with the same expected-absent lease. [Git push reference](https://git-scm.com/docs/git-push)

**Live feasibility.** A headless Codex worker received a scoped task and wrote a failing reproduction plus handoff note. It received the public parent revision and no reference patch. The secondary worker ran through the shipping continuation CLI using headless OpenCode. The original run used local Qwen3 4B. It could edit the named implementation file. An out-of-band grader checked artifact preservation, independent behavior, the source reproduction, and the upstream native test module. Each stage had a 180-second limit. The follow-up kept the pinned inputs, graders, and 180-second budget. Three hosted free-model probes returned HTTP 429. We used local Qwen3.5 9B with explicit reasoning-off at the Ollama API and kept the original held-out context and generation caps. Codex regenerated the two handoff files on each run. [Qwen3.5 9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) · [Ollama API](https://docs.ollama.com/api/openai-compatibility)

**Frozen diagnostic.** We fixed the Packaging parent, task brief, and reproduction, with no prior agent session needed. The frozen handoff used a study-authored note and reproduction. Historical Codex inputs were ephemeral and only their hashes were retained. The clean parent had to fail both change-specific checks, and the public upstream fix had to pass them. Both had to pass the native test module. The diagnostic used enabled, disabled, disabled, enabled order with two attempts per setting, identical checkpoint fingerprints, the same local Qwen3 4B variant, and a 180-second worker deadline. Separately, a scripted provider varied exact match text, reported token use, and the summary finish condition. The packaged tools preserve provider categories and artifact hashes. [Follow-up protocol](https://github.com/archit15singh/agent-task-continuity/blob/main/docs/research-loop.md)

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

In 3/3 independent bare-Git trials, the receiver exposed the intended ref while the original push command was still pending. After SIGKILL, the same-SHA replay reported up to date, the different-SHA push was rejected as stale, and independent readback confirmed the original SHA. The receiver logged one ref update per trial. This measures convergence for conditional Git ref creation and whether the receiver logged another ref update.

### 4.2 Live feasibility

| Project and arm | Source stage | Replacement | Restored inputs | Task result |
|---|---:|---:|---|---|
| Click · Codex to OpenCode | 27.6 s | 180.0 s | Both files | Timeout |
| Packaging · Codex to OpenCode | 30.6 s | 180.0 s | Both files | Timeout |
| attrs · Codex to OpenCode | 28.5 s | 180.0 s | Both files | Timeout |
| Click · Codex to Codex | 38.5 s | 26.2 s | Both files | Passed |

The three OpenCode runs recovered a reproduction that failed with an assertion on the original revision and preserved the handoff note byte-for-byte. During the two held-out runs, OpenCode emitted four and two tool-use events, respectively. Neither run produced a passing implementation before timeout. Native baseline tests still passed because the independent predicate and the carried reproduction targeted the behavior missing from the historical source.

The exploratory same-runtime Click trial preserved both files, edited only the intended implementation file, passed the independent predicate, made the carried reproduction pass, and finished the native test module with 52 passes and one skip. This establishes that the same handoff and grading procedure can complete a live task with another session. The experimental arms differ in runtime and model, and we cannot attribute the difference to either in isolation.

### 4.3 Why the original OpenCode workers timed out

The Packaging replay reached the 180-second deadline with both handoff files intact and no edit. Ollama's five requests covered approximately 177 seconds, with overlap. Its first two logged generations reached the 1,500-token cap, and it logged cancellation of the final request at the deadline. OpenCode reported one failed read and one successful glob. This places most of the observed delay in provider work and shows that the worker spent steps searching before it reached an edit.

A separate workspace probe identified a launch defect. The subprocess cwd was the restored checkout, while inherited `PWD` still named the study checkout. OpenCode's main request used that stale path. With identical process cwd, setting `PWD` to the workspace or removing it made the request name the correct checkout. The first Qwen3.5 9B file-edit smoke actually searched the wrong checkout. That smoke and the first 9B batch are diagnostic evidence. We synchronized cwd and `PWD` in the runner and added a regression test. With only the workspace fix and a fresh Codex handoff, the 4B Packaging control completed a read, then exited after 142.6 seconds with OpenCode error `compaction.failed`, before any edit. This confirms a separate failure after the workspace correction. The persisted OpenCode record reports that the summary reached the output token limit and records 1,500 summary tokens. We matched it to the existing receipt by run window, workspace pattern, runtime version, error category, and the preceding assistant output counts of 1,500 and 1,139 tokens. This diagnosis applies to the corrected 4B control.

### 4.4 Stronger free-model rerun

The 9B model passed a real synthetic file edit in 8.9 seconds after the workspace fix. In the repository rerun, all three upstream test modules passed at the deadline. The change-specific checks independently assessed the files left behind by each worker.

| Project | Codex source | 9B replacement | Artifact at cutoff | Task result |
|---|---:|---:|---|---|
| Click | 29.2 s | 180.2 s | No scoped edit | Timeout |
| Packaging | 26.4 s | 180.1 s | No scoped edit | Timeout |
| attrs | 32.4 s | 180.0 s | Scoped edit, grade failed | Timeout |

All six handoff files were preserved. The independent predicates and carried reproductions rejected all three candidates. The scoped attrs change still failed both change-specific checks. Click reached its target file but the edit tool rejected both attempts because their match text differed from the file. Packaging eventually read the target but made no edit. Its trace also shows wasted lookups and unavailable tool calls.

The rerun demonstrates that the workspace fix restored usable file access. It also shows that the stronger local configuration did not meet the task-completion deadline under the tested settings. The results compare whole configurations, with regenerated handoff notes and a single attempt per case.

### 4.5 Isolating edit application and summary completion

The scripted Click experiment sent one edit with a nonexistent match string and one with exact text from the pinned file. The tool rejected the first and applied exactly the expected bytes for the second. Both processes exited successfully and both failed the change-specific predicate because the prescribed edit only inserted a comment. Process exit, successful edit application, and verified behavior are separate measurements.

The synthetic compaction fixture used a short synthetic file and a 16,384-token model window. With a response reporting 200 input tokens, the tool completed and the agent continued without compaction. With 16,000 reported input tokens and compaction disabled, the tool and continuation also completed. With compaction enabled at the same usage, a completed structured summary appeared in the first subsequent model request. An HTTP 400 from the summary request produced `provider.invalid-request`. A summary stream with the same content and `finish_reason=length` produced `compaction.failed` and did not proceed to a new task request. The scripted failure agrees with the detailed error in the persisted historical session. [OpenCode compaction documentation](https://opencode.ai/docs/compaction)

### 4.6 Repeated frozen Packaging comparison

The clean parent failed both change-specific checks and passed 238 native tests. The upstream fix passed both change-specific checks and 240 native tests. The four workers received the same checkpoint fingerprint. All preserved both inputs and passed 238 native tests. None changed the intended source file or passed either change-specific check.

| Auto compaction | Attempts | Worker outcomes | Verified completions |
|---|---:|---|---:|
| Enabled | 2 | One timeout, one `output-limit` exit at 146.3 s | 0/2 |
| Disabled | 2 | Two timeouts | 0/2 |

The enabled timeout had one completed summary and one interrupted compaction in the persisted session. The other enabled attempt hit the ordinary output limit without a compaction record. Disabling automatic compaction avoided the summary path in both observed off attempts and yielded zero verified fixes. The small paired test varies one runtime setting on one repository task. It uses no fixed random seed and cannot estimate the setting's effect on completion rate or rank harnesses.

### 4.7 Provider trace and same-model runtime probe

An additional traced OpenCode run restored the identical checkpoint. The relay observed four successful HTTP responses, all with `finish_reason=length` and exactly 1,500 output tokens. Three belonged to the task loop. The other was an auxiliary startup request without tools that overlapped the first task request and lasted 33.4 seconds. No summary request was observed. OpenCode exited in 151.4 seconds with `output-limit`, and the task received no edit. This is distinct from truncating the compaction summary.

A scripted control showed that supplying `--title` removed that tool-free startup request. In an exploratory fixed-title live run, the relay confirmed its absence. Two ordinary requests reached the output cap. A later compaction summary completed with 1,314 tokens and the task issued further tool requests. The worker reached the 180-second deadline without an edit. This isolates one source of avoidable provider work. The exploratory pair does not give a stable estimate of time saved or task quality.

Codex 0.170.0 completed a minimal smoke turn through the same local Ollama model in 11.6 seconds. The frozen Packaging probe used the same checkpoint and ended in 42.7 seconds. Ollama's Responses endpoint emitted `response.completed` with 1,500 output tokens. Codex exited zero. The independent graders rejected the unchanged source. This probe uses the same model and provider and still varies the HTTP endpoint, tool schemas, and harness instructions. Neither a successful process exit nor a completed provider response established a passing repair. [Ollama compatibility documentation](https://docs.ollama.com/api/openai-compatibility)

## 5. Design implications and limits

Git patch export is a strong baseline. The managed path earns its complexity when work has to survive an unattended interruption, a conflict over who owns the task, or uncertain publication. The replay unit in this prototype is a task checkpoint tied to an artifact. Agent sessions remain helpful as optional context. Qualify a replacement against a frozen task with a passing behavior check before relying on unattended recovery. The endpoint, generation budget, and setup requests can all change how much work fits inside the same deadline.

The gateway makes the guarantee observable because it owns the credential check and protocol. Direct shell and API writes outside it remain outside the fence. The black-box test used one host, a common Git object store, three Python repositories, selected file changes, and a loopback fixture with in-memory state. It exercised worker and publishing-client death while the provider survived. The separate Git follow-up covered local bare-repository pushes with a receiver paused after acceptance. It measured ref updates and does not establish provider-side fencing, hook effects beyond the instrumented update counter, or results on a hosted service. Durable provider restart and distributed consensus remain untested. The snapshot follows Git normalization, preserves selected files, and requires that the shared repository retain its base. The receipt describes the host and command, while dependency and tool versions beyond those explicitly pinned remain part of the operator's environment.

Historical public changes can appear in model training data. The live sample is small and mixes a hosted source model with a local replacement. The original study used one attempt per live case and changed local context and generation bounds after the development pilot. The follow-up revisited the same cases and changed the replacement model and reasoning control together. Results describe the tested launch and model configuration. These results establish observed feasibility and failure modes under the recorded conditions. Comparative model quality, productivity, and broad framework rankings remain outside the conclusions.

## 6. Related work

Temporal documents the failure mode where an activity completes externally before its worker can report completion and recommends idempotent activities. OpenAI Symphony organizes work around an issue and its workspace, and its specification lists persistence of retry and session metadata as a recommended extension. Cross Agent Handoff records project-level checkpoints across runtimes and describes its writer lock as advisory. ACP covers client-agent session operations. A2A defines agent task and artifact exchange. Their contracts address useful layers of the system. This prototype evaluates the surrounding workspace, authority, and side-effect recovery directly.

1. [Temporal documentation, Activity Definition](https://docs.temporal.io/activity-definition)
2. [OpenAI Symphony specification](https://github.com/openai/symphony/blob/main/SPEC.md)
3. [Cross Agent Handoff](https://github.com/kristianrolando/cross-agent-handoff)
4. [Agent Client Protocol, Session Setup](https://agentclientprotocol.com/protocol/v1/session-setup)
5. [Agent2Agent Protocol specification](https://a2a-protocol.org/latest/specification/)
6. [Handoff Debt, evaluating frozen intermediate checkouts](https://arxiv.org/html/2606.02875v1)
7. [Compact-Bench, evaluating task quality after compaction](https://arxiv.org/html/2610.31710v1)
8. [RIFL, durable RPC completion records](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf)

## Reproducibility

The [public repository](https://github.com/archit15singh/agent-task-continuity) contains the frozen protocol, case manifest, CLI, scripts, and receipts. The frozen follow-up records the evaluation script hash. The paired runner is archived at `1d046de`, the request trace and Codex probe at `857cc17`, and the fixed-title runner at `584df15`. The final mechanical run used candidate `c2f94ba`. The original held-out live run used `b4ce25b`. The corrected rerun and the mechanical regression used `24ac9a9`. See the repository's evidence index for exact commands, model settings, test summaries, and the first held-out run's collection failure.
