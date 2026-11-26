---
title: "Recovering Coding-Agent Work Across Runtime Boundaries"
subtitle: "The Worktree Ledger prototype evaluated on three open-source projects"
date: "November 26, 2026"
geometry: margin=0.82in
fontsize: 11pt
colorlinks: true
---

## Abstract

Conversation history can explain a coding task. Recovery also requires a restorable workspace, evidence tied to the artifact, and a way to resolve external actions whose outcome is uncertain. We built Worktree Ledger, a local CLI that stores a task independently of its worker, preserves selected Git workspace changes, fences writes at managed boundaries, and reconciles a controlled publishing service by operation ID. On pinned changes in Click, Packaging, and attrs, both a manual Git bundle and managed continuation restored the selected files in 3/3 cases. A brief-only transport control restored them in 0/3. Across six managed publication trials spanning two fault modes, the provider applied one effect per operation and the replacement confirmed every outcome. The original three Codex-to-OpenCode runs timed out. A replay found sustained local inference and a stale working-directory environment. After fixing the workspace launch, a stronger local Qwen3.5 9B model restored both inputs in all three cases and still passed 0/3 within 180 seconds. The original corrected 4B Packaging failure reached the summary output limit. A frozen Packaging rerun completed 0/2 with auto compaction enabled and 0/2 with it disabled. An exploratory Codex-to-Codex comparison completed the Click change. A separate bare-Git experiment recovered the exact intended ref in 3/3 interrupted pushes with one receiver update per trial. The strongest result concerns recoverable task state and controlled side effects. We report runtime completion and deterministic transport as separate outcomes.

A second round found that delayed requests still applied when the receiver's generation lagged. A current-generation receiver rejected all three delayed requests. SQLite receiver crashes on either side of commit converged on one transactional effect and receipt in 6/6 trials. Eight additional live attempts on the frozen task produced zero verified fixes. A subsequent body edit passed the original checks and failed an expanded upstream oracle. The combined durable activation fixture converged across all 18 process-failure trials.

An authenticated receiver rejected current-generation requests carrying retired, missing, or other-task credentials. It confirmed one effect per operation in a further 18 fault trials. After an interrupted restore on each of the three repositories, the source predicate passed while a selected note was missing. A coordinator that persisted a fresh checkout destination recovered the full checkpoint in all three cases.

A paired pilot on three new historical tasks restored identical checkpoints in all six fresh Codex and OpenCode attempts with the same local model. None changed the source. Three deliberately incomplete repairs passed their carried reproduction and parent native checks, while reference-derived behavior probes rejected all three and accepted three equivalent implementations. Three native Git process kills left partial output on disk. Each incomplete checkout was refused and a fresh restore reproduced the checkpoint.

On those same three tasks a signed-in Codex configuration passed the independent graders in six of six attempts over two series. A local read cap reduced some input sizes and produced no verified fix. The hosted GitHub receiver preserved the intended ref across three publisher failures. An authenticated fixture running as a separate container on a hosted VM converged in nine faults.

## 1. Motivation and questions

A coding worker can disappear after changing files, while waiting for a decision, or after sending a request whose acknowledgment is lost. A saved conversation helps another worker understand prior reasoning. Git and the external provider still carry facts that must be checked before the replacement can act. We asked three questions.

1. Can a managed checkpoint restore the selected work as faithfully as an explicit Git patch plus copied files?
2. Can a fresh owner recover a checkpoint after process death, reject a retired owner at a managed boundary, and reconcile an uncertain external write?
3. Can a real replacement runtime finish a graded change using the restored artifacts?

The project implements 11 ideas as one prototype. The CLI covers cross-agent continuation, snapshots, a task manifest, and inspection. The execution path covers replacement supervision, an action ledger, ownership fencing, revision-bound verification, and managed publishing. Table 1 states the predictions and how the study evaluated them. Appendix A traces the numbered follow-up hypotheses to results and receipts.

| Question | Prediction or feasibility criterion | Primary observation |
|:---|:---|:---|
| RQ1 · Transport | Managed recovery and manual Git should recover the same selected artifact. A brief alone should leave the clean checkout unchanged. | Exact tracked and selected untracked bytes, plus an independent behavior check, per case (§4.1). |
| RQ2 · Recovery | After a controlled interruption, a successor should recover the saved revision, fences should refuse stale authority, and a cooperating receiver should produce one effect per reserved operation. | Checkpoint match, receiver acceptance and independently observed effects and receipts per fault trial (§§4.1, 4.8, 4.10, 4.14–4.15, 4.17, 4.21). |
| RQ3 · Live feasibility | A fresh replacement may finish under the stated deadline. A pass requires the preserved artifact, a scoped edit, and passing behavioral checks. | Verified completions and observed failure stages per worker attempt (§§4.2–4.7, 4.11–4.13, 4.16, 4.18–4.20). |

Table 1. Study questions and criteria.

## 2. System

A *task* has an objective, a current workspace, an owner generation, and a pointer to its latest checkpoint. An immutable checkpoint stores the Git base commit, a binary patch, the selected untracked paths, and a continuation note. Capture uses an alternate Git index. Restore applies the patch in a detached worktree and rechecks the fingerprint before transferring ownership. A checkpoint write and an owner change each compare current state inside a SQLite transaction. Retired workers can still write to their own local checkout. The managed checkpoint and publishing paths reject the retired credential.

The JSON manifest carries the objective, constraints, decisions, remaining actions, acceptance criteria, evidence, and operation status. An optional binary patch makes the workspace artifact transferable to another checkout with the same base.

A verifier runs the operator's command in a disposable checkout of the saved artifact. The receipt records the artifact fingerprint, command, exit status, output hash, and basic host details. Inspection marks evidence stale when the selected workspace contents change. The publish command requires a passing receipt for the snapshot it names.

The gateway reserves a stable operation ID and immutable payload before sending a request. On acknowledgment loss, the next owner can query the provider by ID. The reference provider returns the original receipt for an identical operation and rejects payload changes under that key. The authority check and request initiation share a local transaction. An already-started request can survive a worker's death. Provider idempotency and lookup address that separate failure mode.

## 3. Methods

**Design and provenance.** This is an engineering evaluation of a prototype. It combines deterministic mechanism tests, instrumented fault scenarios, and exploratory live pilots. The initial protocol and case manifest were committed before the first comparative runs. The research loop records later predictions, diagnostic extensions, and findings. Plans added after earlier outcomes informed subsequent runs and carry exploratory status here. Round 4 and the main Round 5 matrix have separately identifiable pre-run commits. The study had no external preregistration or independent evaluator. [Initial protocol revision](https://github.com/archit15singh/worktree-ledger/commit/7cc54b5) · [Round 4 plan](https://github.com/archit15singh/worktree-ledger/commit/2a427e3) · [Round 5 plan](https://github.com/archit15singh/worktree-ledger/commit/d630a70)

**Units and analysis.** A transport case is one historical change and selected note across three arms. A fault trial is one isolated scenario, starting from a fresh fixture and graded at its stated boundary. A live attempt is one worker invocation on a case under a named configuration. Paired attempts on a checkpoint share a task. Multiple provider requests and individual oracle inputs are observations within attempts, so they do not increase the task sample. We report counts with denominators, observed timings, and exact receipt and fingerprint checks. Deliberately selected tasks, single-attempt arms, and shared inputs limit the analysis to descriptive outcomes.

**Outcome definitions.** Transport success requires exact selected artifacts and the independent case predicate in the mechanical comparison. Fault success requires the expected rejection or recovery and an independently observed effect or receipt count where relevant. A verified live edit requires passing the carried reproduction and independent behavior checks, passing the specified native checks, preserving the handoff files, and remaining within edit scope. The initial live feasibility protocol also requires a successful worker exit. Round 5 reports worker disposition independently of verified artifact state. A timeout, clean exit with no edit, invalid tool response, and applied but incorrect edit remain distinct recorded outcomes.

We used historical source changes in Click, Packaging, and attrs. Case selection favored scoped fixes with a clear parent, an upstream reference, and targeted native test modules. Click was the development case. Packaging and attrs were held out from development execution. The graders were authored with access to the public reference diffs. The case manifest pins parents and references. Native checks ran with Python 3.13.18, Apple Git 2.54.0, and pinned Python dependencies on one arm64 macOS host. [Click](https://github.com/pallets/click/commit/fdb65f4809719580436acb067410cec64433e5de) · [Packaging](https://github.com/pypa/packaging/commit/cf2cdf099375f7e208168cd2d8880699aeef0583) · [attrs](https://github.com/python-attrs/attrs/commit/319c53cc178afe980362c1bd59d8109019e344bd)

**Transport.** We applied only the upstream implementation-file diff to the historical parent, then added a selected untracked note. The brief-only control received the same objective and note text but started in a clean worktree. The manual arm exported a binary Git patch and copied the selected file. The managed arm saved a checkpoint, killed the initial worker, and restored into a new checkout. We graded both files byte-for-byte and ran an independent case predicate. The brief-only arm controls for transporting information while leaving out the artifact. It received no reconstruction worker.

**Faults.** We killed the worker after it wrote an edit beyond the checkpoint boundary. We checked recovered files, retired-owner rejection, and stale verification detection. In one publication scenario the provider accepted the operation and dropped its response. In the second, added as an explicitly recorded extension, the fixture killed the client after provider acceptance and before a receipt could commit locally. Each recovery counted provider writes and applied effects independently of SQLite state. An independent follow-up exercised a standard bare Git receiver. It held the push open after the ref became visible, killed the local push process group before the command returned, and checked the ref through a separate Git request. A matching SHA and a different SHA were then pushed with the same expected-absent lease. [Git push reference](https://git-scm.com/docs/git-push)

**Live feasibility.** A headless Codex worker received a scoped task and wrote a failing reproduction plus handoff note. It received the public parent revision and no reference patch. The secondary worker ran through the shipping continuation CLI using headless OpenCode. The original run used local Qwen3 4B. It could edit the named implementation file. An out-of-band grader checked artifact preservation, independent behavior, the source reproduction, and the upstream native test module. Each stage had a 180-second limit. The follow-up kept the pinned inputs, graders, and 180-second budget. Three hosted free-model probes returned HTTP 429. We used local Qwen3.5 9B with explicit reasoning-off at the Ollama API and kept the original held-out context and generation caps. Codex regenerated the two handoff files on each run. [Qwen3.5 9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) · [Ollama API](https://docs.ollama.com/api/openai-compatibility)

**Frozen diagnostic.** We fixed the Packaging parent, task brief, and reproduction, with no prior agent session needed. The frozen handoff used a study-authored note and reproduction. Historical Codex inputs were ephemeral and only their hashes were retained. The clean parent had to fail both change-specific checks, and the public upstream fix had to pass them. Both had to pass the native test module. The diagnostic used enabled, disabled, disabled, enabled order with two attempts per setting, identical checkpoint fingerprints, the same local Qwen3 4B variant, and a 180-second worker deadline. Separately, a scripted provider varied exact match text, reported token use, and the summary finish condition. The packaged tools preserve provider categories and artifact hashes. [Follow-up protocol](https://github.com/archit15singh/worktree-ledger/blob/main/docs/research-loop.md)

**Round 2 interventions.** The reasoning comparison used the same frozen Packaging checkpoint, OpenCode, fixed session title, local Qwen3 4B alias, 1,500-token model output cap, and 180-second worker deadline. A loopback relay set only the request's `reasoning_effort` field. The four attempts ran in default, none, none, default order with a fresh checkout each. We counted characters in the provider's reasoning and visible channels and graded workspace, task behavior, and process exit separately. The bounded receiver tested a different intervention. A single request received the same task, note, and original helper source. It returned one function for a guarded splice. The unchanged function served as a negative control. The upstream function with its companion regex inlined served as the positive control. Later diagnostics used six Boolean input-output cases and allowed at most one counterexample in an extra request. We separately tried feedback from the original helper and checked the feedback implementation with a scripted wrong-then-correct provider.

**Delayed acceptance and activation.** The reference service was paused after receiving a complete request and before applying the effect. We killed the client and advanced SQLite ownership. The receiver then ran under three conditions: operation-ID idempotency, a current generation check, or a generation check whose receiver remained one generation behind. A second experiment simulated an interruption after receiver activation and before local activation. It used the operator recovery key to repair the local generation and retry the same intent. The fixtures recorded delivery and application separately. A separate SQLite receiver fixture inserted effect and receipt rows in a single transaction and terminated its process before or after commit, before sending a response. We reopened the receiver database after death, then started a new process at the same endpoint and settled the intent.

**Human timing rehearsal.** The automated rehearsal measured capture, restart to workspace-ready, and restart to the first independently verified predicate. Each pinned repository ran a manual and managed restoration with the same candidate and note. The clean-parent control tried the same check with no restored change. The participant protocol calls for distinct matched tasks and counterbalanced order, with operator effort measured separately from runtime waiting. The reported rehearsal contains only scripted command timings.

**Round 3 format controls.** Qwen2.5-Coder 7B received the same recovered task, source excerpt, JSON object format, and output allowance in both arms. The code string contained either the whole function or just its body, with the original signature supplied at application time. We logged provider, JSON, signature, syntax, scope, and behavioral dispositions separately. We replayed a seed and expanded the behavioral oracle to every ABI list of length zero through three over ten fixed entries. The expected results came from the pinned upstream helper and remained outside the initial model prompts. We then tested one feedback request using the first disagreement.

**Combined durable activation.** A coordinator wrote the activation intent and successor credential to a protected fixture directory before advancing an authenticated receiver endpoint. The receiver stored its generation in SQLite and checked it in the same transaction as the simulated effect and receipt. A coordinator process terminated after the intent, receiver activation, worktree creation, or local takeover. A separate receiver process terminated before or after the effect commit. The harness restarted the receiver, replayed the intent, and delivered the archived old-generation request. The local API can adopt a detached linked worktree from the same repository after verifying its checkpoint fingerprint. It preserves mismatched or unrelated destinations during rejection.

**Worker authentication and incomplete restore.** Round 4 ran three matched credential control pairs and repeated the six interruption stages three times with worker authentication enabled. The managed client derives a bearer from the owner token, task, and generation using HMAC-SHA-256. The fixture's coordinator registers only the bearer hash with the next generation. The receiver verifies the bearer hash and the task-specific operation ID in the effect transaction. An independent restore experiment applied only the tracked path from each saved patch, using Git's path filter, then exited the coordinator. We ran the source predicate and checked the tracked and selected untracked bytes independently. The original recovery policy tried to adopt the partial checkout. The new policy persisted another destination and exited before restoring to it. After restarting both processes we checked authority, the restored fingerprint, and the preservation of the partial checkout. [Git apply documentation](https://git-scm.com/docs/git-apply)

**Paired replacement on new tasks.** The fifth round froze three public changes and a study-authored checkpoint for each. Both fresh runtimes received the same brief, visible reproduction, and checkout fingerprint. The historical parent and upstream reference calibrated the visible reproduction and an out-of-band oracle. The oracle covers Click command and option formatting across help variants and terminal widths, Packaging marker and requirement round-trips plus unrepresentable delimiter combinations, and attrs direct invocation, construction, and assignment across converter shapes. The upstream reference supplied expected outputs. A deliberately incomplete repair on each parent served as a second negative control. Codex and OpenCode used the same local Qwen3 8B model with a 16,384-token context configuration, 2,048 configured output tokens per request, and 180 seconds per attempt. We ran one attempt per arm per task, reversed the order for Packaging, and kept the model warm. The runtimes used different provider endpoints and tools. This fixture starts at a saved checkpoint, without a source-worker session or transcript. [Click change](https://github.com/pallets/click/pull/3509) · [Packaging change](https://github.com/pypa/packaging/pull/1213) · [attrs change](https://github.com/python-attrs/attrs/pull/1328)

**Native Git interruption.** A byte-preserving, repository-local filter paused a single `git apply` when it reached the binary path. We waited until a text edit was visible and the filter had received the expected binary bytes, then killed Git's process group. We compared each path before and after the kill, attempted prepared takeover, and retried into a fresh worktree. The experiment used three disposable repositories with the same text edit, binary edit, deletion, and selected note. [Git filter documentation](https://git-scm.com/docs/gitattributes)

### 3.1 Protocol deviations and reporting scope

| Event | Disposition |
|:---|:---|
| Packaging's first native test run could not collect because `pretend` was missing. | Preserved the failed receipt, pinned the dependency, and reran with the same gates. [First held-out run](../evidence/mechanical-held-out-first.json) |
| Hosted free-model probes were rate limited, and local generation settings changed after the Click pilot. | Reported the development and held-out configurations separately. The 9B follow-up used a new model and regenerated Codex artifacts. [Provider probe](../evidence/opencode-provider-timing.json) |
| The pre-fix 9B batch inherited a stale `PWD`. | Retained for diagnosis and excluded from the model comparison. Only the corrected batch contributes to its denominator. [Pre-fix batch](../evidence/opencode-9b-pre-fix.json) · [Corrected batch](../evidence/opencode-9b-rerun.json) |
| A separate same-runtime Click attempt, extra fault trials, and later model interventions were added. | Reported under their own labels and denominators. They use earlier evidence to select diagnostic questions. [Follow-up protocol](research-loop.md) |
| Round 5 used study-authored artifacts and did not run a live source-worker phase. | The paired result measures two fresh replacements from the same saved input. It gives no comparison of transcript resumption or source-worker handoff quality. [Paired receipt](../evidence/paired-continuation.json) |

## 4. Results

### 4.1 Transport and recovery

A transport pass required matching tracked bytes, matching selected untracked bytes, and a positive source predicate.

| Project | Brief only | Manual Git | Managed restore | Upstream test module |
|---|---:|---:|---:|---|
| Click | Fail | Pass | Pass | 52 passed, 1 skipped |
| Packaging | Fail | Pass | Pass | 238 passed |
| attrs | Fail | Pass | Pass | 53 passed |

Manual Git and managed handoff tied on this measure. The measured wall times include grading and different steps. The median was 0.094 seconds for the scripted manual arm and 0.573 seconds for the managed arm, which also launched a worker, killed it, and ran a replacement. These timings describe the scripted procedures. Estimating operator effort or speedup requires a separate comparison.

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

### 4.8 Delayed effects and receiver activation

All nine trials rejected the old owner's new local command. The receiver nevertheless applied the already-sent request after local takeover in all six idempotency-only or lagged-generation trials. When the receiver had advanced before release, it rejected the old request in all three trials. Each replacement converged on one applied effect.

| Receiver condition | Delayed old-owner effects | Replacement confirmed | Final effects per trial |
|---|---:|---:|---:|
| Operation-ID idempotency | 3/3 | 3/3 | 1 |
| Current generation check | 0/3 | 3/3 | 1 |
| Lagging generation check | 3/3 | 3/3 | 1 |

In the three receiver-first interruption trials, the receiver returned HTTP 412 while the local owner remained on generation 1. The caller recorded an unknown operation. Recovering the local owner with the operator key advanced it to generation 2. The held generation-1 request was rejected, and the successor confirmed the reserved intent with one receiver effect in every trial.

These results distinguish three guarantees: operation-ID deduplication, local ownership, and receiver-side authority at the moment of application. The fixture coordinator advances the in-memory receiver explicitly. The HTTP generation header is a signal for a cooperating service. A distributed deployment would need authenticated generations, durable receiver state, and a recovery path for interruption between activation steps. [Chubby, §2.4](https://static.usenix.org/event/osdi06/tech/full_papers/burrows/burrows.pdf)

### 4.9 Restart timing rehearsal

Both restore paths produced a verified action in 3/3 scripted runs. All three clean controls failed the predicate and recorded no verified action. The median restart-to-verified-action durations were 83 ms for the manual script and 187 ms for the managed script. These wall times cover a scripted restore and a fixed check on an already-prepared candidate. The operator-active-time field is empty in the receipts. A human comparison remains a separate experiment.

### 4.10 Durable receiver restart

Across three process deaths before commit, independent readback found zero effect rows and zero receipt rows. Across three deaths after commit, it found one of each. The original client recorded an unknown outcome in all six. A replacement reached confirmed status after the receiver restarted in 6/6 trials, with one effect and one receipt in every database. This result covers a simulated effect whose state shares the receiver transaction. An external action with a separate commit boundary needs its own receipt or readback contract. [RIFL, durable RPC completion records](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf)

### 4.11 Reasoning request setting and the output cap

All four fixed-title Packaging runs restored the same checkpoint and left the source unchanged. With the default setting, six of seven provider requests finished at the output cap. That includes a compaction summary that ended with `length` at 1,500 tokens and produced `compaction.failed`. Under `reasoning_effort=none`, the two runs made fourteen requests, four ended at the cap, and OpenCode recorded seven tool events across the two runs. Both reached the deadline. Neither setting produced a repair.

| Request setting | Reasoning characters | Visible characters | Requests at cap | Verified fixes |
|---|---:|---:|---:|---:|
| Default | 43,008 | 0 | 6/7 | 0/2 |
| `none` | 0 | 52,060 | 4/14 | 0/2 |

Ollama advertised only `true` as a supported thinking value for the measured alias. The observed stream labels changed under the requested setting. The comparison leaves the underlying generation behavior unresolved. Both short arithmetic smokes reached their 64-token cap in both settings. In the follow-up, neither arm returned the exact answer or a literal think tag in visible content. [Ollama thinking documentation](https://docs.ollama.com/capabilities/thinking)

### 4.12 Bounded replacement of one helper

The unchanged-function control failed both change checks. The spliced upstream helper passed both change checks and the native suite. In the single Qwen3 4B attempt, the provider returned `length` after 31.3 seconds with 6,172 visible characters. The candidate did not parse as Python. The receiver left the source unchanged and both change checks failed.

Qwen2.5-Coder 7B returned a scoped function in 4.7 seconds. The guard accepted it and the 238 native tests passed. The independent predicate and carried reproduction both failed. With the same first prompt, the adaptive repeat produced a candidate the guard rejected, so the second request did not run. An independent seeded trial sent the original helper with one failing input, `["none", "cp316t"]`, and the expected Boolean. The guard also rejected that response. The live receipts keep the exception class and response hash. They do not resolve the precise guard rule involved in those two rejections.

The scripted wrong-then-correct provider reached the feedback step, sent one counterexample, and passed six helper behaviors, both change checks, and the native suite after repair. That control validates the path through the evaluator. The two model families received one diagnostic task with a preselected helper. These attempts support conclusions about the observed failure stages only. [Qwen2.5-Coder 7B model card](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)

### 4.13 Function-body contract and expanded verification

In the first four trials the guard applied one edit per arm. The body edit passed the two change checks, six helper behaviors, and native suite. The whole-function edit failed both change checks. The other whole-function response failed Python parsing. The other body response failed the supported edit shape. A scripted invalid-signature function was rejected before application. The whole-function live failures were never attributed to a changed signature.

The next four trials repeated seed 32 and added seed 33. For seed 32, both the response hash and source hash matched each corresponding initial edit. The whole-function candidate disagreed with upstream on 279 of 1,111 inputs and the body candidate disagreed on 123. The two seed-33 responses reached separate guard failures. In three additional exact body requests the relay forwarded seed 32. All three returned the same bytes and the same 123 disagreements. The initial pass therefore reflects coverage of the original checks. The broader oracle rejected the same candidate.

The first disagreement was the single generic entry `["other"]`. The candidate returned true, while upstream returned false. A counterexample request returned a nested function under the body contract and was rejected. Replaying the exact response with wrapper normalization passed the existing whole-function guard. Both the resulting source hash and all 123 disagreements remained identical. This separates recovering a valid edit shape from correcting the behavior.

### 4.14 Durable activation across receiver and worktree restart

All 18 trials in the final fixture converged on local and receiver generation 2. All 18 denied the delayed generation-1 request and ended with one confirmed effect and one receipt. The receiver denied an unauthenticated activation in each trial. The worktree-only fault left local generation 1, receiver generation 2, and a prepared checkout. Replay adopted the verified checkout in all three trials for that fault. The regression checks also exercised unrelated destinations, a changed tracked file, a stale checkpoint intent, and reuse of the old token.

The first three ownership stages exhibit different durable states. Death after persisting intent preserves generations `(1, 1)`. Death after receiver advancement yields `(1, 2)`, with local authority temporarily unable to publish. Death after local transfer yields `(2, 2)`, even if the coordinator has yet to mark completion. The worktree-only fault also yields `(1, 2)`. The fixture coordinator resumes using the recorded successor credential and does not rotate the generation again once that credential is active. Worker generations are trusted assertions in the loopback protocol. This tests process death at known boundaries using a simulated transactional effect, with receiver authentication established only for generation administration.

### 4.15 Worker authentication and partial workspace recovery

Each of the following outcomes occurred in all three trials per receiver mode, after restarting the receiver against its persisted database.

| Request | Header only | Authenticated |
|:-------------------------------------------------------|------------:|--------------:|
| Retired credential and retired generation | 412 | 412 |
| Retired, missing, or other-task credential and current generation | 201 | 403 |
| Valid worker credential with an operation ID derived for another task | 201 | 400 |
| New publication by the active worker | 201 | 201 |
| Repeat of the active worker's publication | 200 | 200 |
| Repeated activation with a different worker binding | 200 | 409 |

An identical activation retry returned HTTP 200 in both modes. The authenticated arm wrote one effect and one receipt per control trial, compared with five in the header-only arm. With authentication enabled, all 18 crash trials reached local and receiver generation 2, rejected the retired generation, and confirmed one effect and one receipt. Receipt lookup remains open within the loopback fixture. The experiment did not vary network trust or test replay of a stolen active bearer.

In all three partial restores, the tracked source matched the upstream reference and its behavior predicate passed, but the selected note was missing. The original coordinator refused the checkout and left the local generation at 1. The revised coordinator saved a new destination and recovered from a second exit before that directory existed. After restart, the new checkout matched the saved fingerprint and passed all three grading checks. It reached generation 2 in each case. The original partial checkout retained its measured state. This injection exited between selected paths. Section 4.17 separately injects process death inside Git.

### 4.16 Calibration and partial repair controls

All three historical parents passed the targeted native modules and failed the carried reproduction. All three reference revisions passed both. The parent outputs differed from the reference on 16 of 45 Click probes, 50 of 165 Packaging probes, and 31 of 37 attrs probes. Every deliberate partial repair passed the carried reproduction and the parent native modules. The probes still rejected the option-only Click change on 12 inputs, the incomplete quoting guard on one input, and the narrow attrs assignment fix on 29 inputs. Three reference variants with different control flow passed their tests and matched all frozen outputs. These controls establish incremental detection over the visible checks and acceptance of the sampled alternate implementations.

### 4.17 Native Git process death

The text edit and deletion were already visible when Git stopped in all three trials. The binary file was empty and the selected note was absent. The partially applied tree remained unchanged after SIGKILL. Prepared takeover refused it and kept local generation 1. Taking over into a fresh checkout recovered all four path dispositions and the checkpoint fingerprint in 3/3, at generation 2. The filter supplies a deterministic fault location on this Git version. These trials cover a local `git apply` process death under instrumentation. The frequency of partial states on ordinary restores and recovery after a host restart remain unmeasured.

### 4.18 Paired live replacements

| Case | Codex | OpenCode | Verified |
|:---------------------------|:----------------|:----------------|----------:|
| Click help formatting | Deadline | Deadline | 0/2 |
| Packaging marker quotes | Exit 0 in 65.1 s | Exit 0 in 74.3 s | 0/2 |
| attrs converter adapter | Exit 0 in 90.4 s | Deadline | 0/2 |

All six attempts began at the intended checkpoint and preserved both carried files. Every source remained unchanged, every carried reproduction still failed, and every parent native module still passed. Within each pair the prompt and checkpoint hashes matched. No model-generated edit reached the broader oracle as a candidate. The scripted tool control reached the workspace and returned tool results on both runtimes, establishing that a known-good response can operate under these settings.

The OpenCode Click and attrs runs each started with a completion that used 2,048 tokens, terminated with a length disposition, and returned reasoning content only. OpenCode's clean Packaging exit followed one reasoning-only completion with a stop disposition. Codex reported a completed provider response with exactly 2,048 output tokens on attrs. The relay counts reasoning and visible characters on Chat Completions. The Responses receipts record completion events and token usage. This pilot cannot rank the runtimes or attribute the failures to a single difference in the two paths.

### 4.19 API-level reasoning control

The Qwen3 8B alias advertised both Boolean thinking settings. On the same arithmetic prompt at a 32-token allowance, the defaults across native chat, Chat Completions, and Responses each returned 130 reasoning characters and no visible answer. The documented API-level off requests each returned the exact answer in three tokens, with no reasoning content or literal think tags. The default Responses request reported completion and zero reasoning tokens in its usage breakdown while including a reasoning item. The item and its content provided the direct observation for this check. [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking) · [Ollama compatibility endpoints](https://docs.ollama.com/api/openai-compatibility)

On the identical Click checkpoint and prompt, OpenCode with API-level off made a read call in its first completion, which used 23 output tokens and 3.1 seconds. The follow-up request grew to 8,194 input tokens, returned 5,307 characters of text, and issued no edit. OpenCode exited in 65.1 seconds with the original 16 behavior disagreements. The single comparison changes the setting on the wire and observes different behavior on this task. Its timing provides one diagnostic observation.

The Responses off repeat used the original Codex Click prompt and checkpoint, for which the default attempt timed out. Codex exited in 137.5 seconds. Its fourth request had 10,265 input tokens and consumed all 2,048 configured output tokens while the provider reported completion. The source remained unchanged and all 16 disagreements remained. A second endpoint smoke before this repeat again returned the exact answer on all three off arms. One default reasoning string changed in length despite the zero-temperature request. These observations qualify a provider setting and motivate smaller context reads. They establish no verified completion improvement.

### 4.20 Read limits, scoped edits, and receiver qualification

Round 6 used the Round 5 Click checkpoint, OpenCode, Qwen3 8B, reasoning-off on the wire, and a 180-second deadline. Two attempts per arm ran in default, capped, capped, default order. The capped relay shortened each oversized read observation to 4,096 characters. Both default attempts peaked at 8,194 input tokens and left the source unchanged. Capped attempts peaked at 5,127 and 8,745 tokens. Repeated interactions can still grow the request because they accumulate new observations. One capped attempt applied a source edit and disagreed on 24/45 probes, compared with 16/45 on the parent. Both arms finished 0/2 verified. [Capped reads](../evidence/capped-reads.json)

The two-block JSON qualification then withheld the full tool loop and supplied only the relevant Click fragments. The original guard refused both responses because the command fragment occurred twice. We narrowed the anchor to its class and method and verified that the upstream edit passed. The exact replay produced the same response hash and left both blocks unchanged. An explicit request to change both blocks produced a scoped edit that reduced independent disagreements to 4/45. It still failed the full grade. [Initial JSON trial](../evidence/scoped-click.json) · [Guard correction and replay](../evidence/scoped-click-replay.json)

Separately, a configured Codex session using requested model `gpt-6.2-sol` received the same three frozen tasks and the same task deadline and graders. Each initial attempt preserved both artifacts, stayed within file scope, passed its reproduction and native modules, and passed every independent probe. A separately planned repeat passed all three again, giving 6/6 attempts on three tasks. Across the two series, verified attempts took 32.0–40.6 seconds. Prompts and checkpoint hashes match the prior paired study. The changed model and provider distinguish this qualification from the local comparison. Two observations per task provide a repeatability check, with no population-level estimate. [Initial qualification](../evidence/receiver-qualification.json) · [Repeat qualification](../evidence/receiver-qualification-repeat.json)

### 4.21 Hosted publication recovery

In three trials using the public GitHub repository, a publisher issued an expected-absent lease for a unique ref. Independent readback observed the intended SHA while the worker still lived. The worker was killed after its Git child returned and before a durable acknowledgment. Replaying the same SHA converged, and a different SHA using the old lease was rejected in 3/3. We removed each test ref with a matching lease and verified its absence. This test observes the final GitHub ref and published command dispositions. It does not count GitHub's internal effects or authenticate prototype task generations. [Hosted Git receipts](../evidence/hosted-git.json)

The authenticated receiver fixture ran in a distinct Docker network namespace on a GitHub-hosted Linux VM. The client reached it through a forwarded port. The first setup failed because the Docker port accepted TCP before the receiver was ready. An HTTP readback replaced the TCP readiness check. The corrected run interrupted coordinator activation and receiver transactions on both sides of commit, with three trials per stage. In all nine trials the receiver rejected the stale generation and the retired task credential under the current generation. Recovery confirmed one effect and receipt. Client, receiver and the bind-mounted durable volume share the hosted VM. This tests service restart on hosted infrastructure. Separate-host failover and production external effects remain unmeasured. [Initial workflow](https://github.com/archit15singh/worktree-ledger/actions/runs/45812722995) · [Successful workflow](https://github.com/archit15singh/worktree-ledger/actions/runs/45812920668) · [Hosted receiver receipts](../evidence/hosted-receiver.json)

### 4.22 Operator pilot instrument

Two rehearsed sequences exercised the manual and managed procedures, phase markers, independent grader, and receipt export. Each produced two verified recoveries. The rehearsals report phase elapsed time without participant observations. The pilot measures recovery and verification of a prepared candidate. A comparison of human performance requires participant data across counterbalanced assignments. [Operator guide](operator-pilot.md) · [First rehearsal](../evidence/operator-pilot-rehearsal.json) · [Reversed order](../evidence/operator-pilot-reversed.json)

## 5. Discussion and threats to validity

The strongest engineering result is that a replacement can recover the selected artifact and settle a reserved effect after controlled failures. Manual Git matched managed recovery on the transport gate. The managed prototype adds an ownership check, evidence binding, and publication readback around that transport. The study qualified one configured receiver on a small frozen set. It did not estimate a completion advantage from managed handoff or a change in operator time.

**Construct validity.** A checkpoint fingerprint covers selected Git-normalized content. It leaves out ignored files, staging state, and live runtime state. A green upstream suite or process exit does not establish task correctness. The study uses a carried reproduction and independent behavior checks to narrow that gap. The expanded checks still sample specified behavior and could reject a legitimate output outside the sampled equivalent implementations. For publication, a fixture receipt and a Git ref update observe different kinds of effects.

**Internal validity.** The original live arms used different model and harness configurations. Early runs had stale workspace context. The paired round held checkpoint, prompt, and model constant, while tool surfaces and wire endpoints still differed. Launch order was reversed only for the middle case. Some probes change one setting on the wire, but stochastic outputs and one attempt per arm leave alternative explanations for the observed elapsed times. The research team authored the cases, graders, and reference-derived checks.

**Conclusion validity.** The analysis describes measured attempts and does not estimate population effects. Repeated fault trials probe named states of the same mechanism. Provider calls and oracle inputs share attempts and cannot serve as independent task replicates. A failure to solve within 180 seconds shows failure under that deadline. Experiments did not estimate how often a different model or a longer run would succeed.

**External validity.** We used six historically selected changes across three Python libraries, local testing on one macOS host, pinned model configurations, and deliberately targeted failures. Public reference changes may occur in training data. The fixture receiver shares one SQLite transaction between an effect and its receipt. The bare-Git experiment exercises a local conditional ref update. The hosted experiments cover Git ref state and simulated effects across a container restart. Cross-host failover, independent production effects, disk or power loss, and writes outside the managed route remain outside the evidence. The human protocol was rehearsed using scripts and collected no participant data.

## 6. Related work

Temporal documents the failure mode where an activity completes externally before its worker can report completion and recommends idempotent activities. OpenAI Symphony organizes work around an issue and its workspace, and its specification lists persistence of retry and session metadata as a recommended extension. Cross Agent Handoff records project-level checkpoints across runtimes and describes its writer lock as advisory. ACP covers client-agent session operations. A2A defines agent task and artifact exchange. Their contracts address useful layers of the system. This prototype evaluates the surrounding workspace, authority, and side-effect recovery directly.

Qi and colleagues found that weak validation proxies, including exit-code checks, accepted patches that produced incorrect outputs. STING later used deliberately defective variants to test regression-suite coverage and behavior-preserving variants to screen for overfitting to the reference implementation. Our partial-repair and alternate-implementation controls sample both checks with one deliberately incomplete variant and one equivalent reference rewrite per task. [Qi et al.](https://people.csail.mit.edu/rinard/paper/issta15.pdf) · [STING preprint](https://arxiv.org/html/2604.01518v1)

1. [Temporal documentation, Activity Definition](https://docs.temporal.io/activity-definition)
2. [OpenAI Symphony specification](https://github.com/openai/symphony/blob/main/SPEC.md)
3. [Cross Agent Handoff](https://github.com/kristianrolando/cross-agent-handoff)
4. [Agent Client Protocol, Session Setup](https://agentclientprotocol.com/protocol/v1/session-setup)
5. [Agent2Agent Protocol specification](https://a2a-protocol.org/latest/specification/)
6. [Handoff Debt, evaluating frozen intermediate checkouts](https://arxiv.org/html/2606.02875v1)
7. [Compact-Bench, evaluating task quality after compaction](https://arxiv.org/html/2610.31710v1)
8. [RIFL, durable RPC completion records](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf)

## Reproducibility

The [public repository](https://github.com/archit15singh/worktree-ledger) includes both protocols, pinned cases, scripts, and receipts with source hashes. The [evidence index](https://github.com/archit15singh/worktree-ledger/tree/main/evidence) records commands, model settings, test summaries, and failed attempts. The [research loop](https://github.com/archit15singh/worktree-ledger/blob/main/docs/research-loop.md) records the hypotheses and ranked follow-ups.

Run `python -m evals.audit_evidence` from a full Git clone to check selected receipt-derived headline results, archived source hashes, local links, and hypothesis coverage. This reads existing records and does not invoke a model. The artifact guide separates this audit from deterministic and live reruns. Study-authored fixtures are public. Many historical receipts publish hashes and derived measurements instead of full transcripts and generated patches. This permits consistency checks and leaves full regrading dependent on access to the original bytes. [Artifact guide](../evidence/README.md) · [Fresh-clone verification receipt](../evidence/reporting-verification.json)

The study used public revisions and disposable local receivers. It collected no human participant data. Public receipts omit runtime logs containing local paths or tool data and credentials generated for fixture runs. A public Git commit provides a versioned source snapshot. The package has not undergone third-party artifact evaluation or permanent archival deposit. The [reporting audit](reporting-audit.md) records the standards applied and the remaining gaps.

## Appendix A. Hypotheses, outcomes, and receipts

The predictions below are summarized from the [initial protocol](protocol.md) and [follow-up log](research-loop.md). Each row links to the observations on which its disposition depends. The first table also includes the initial research questions and unnumbered first-round diagnostics. Counts belong to their named scenarios, and overlapping follow-ups on the same task are kept separate.

### Initial evaluation and Round 1

| Question or diagnostic | Reported outcome | Evidence |
|:----------------------------|:--------------------------------------------|:-------------------|
| RQ1 · Transport parity | Manual Git and managed 3/3 each. Brief-only 0/3. §4.1. | [Mechanical matrix](../evidence/mechanical-final.json) |
| RQ2 · Worker and client death | 39 fault predicates passed. Six publications confirmed with one effect each. §4.1. | [Mechanical matrix](../evidence/mechanical-final.json) |
| RQ3 · Cross-runtime feasibility | Original OpenCode 0/3. Corrected 9B 0/3. Exploratory Codex-to-Codex 1/1. §§4.2–4.4. | [Development](../evidence/live-development.json) · [Held-out](../evidence/live-held-out.json) · [9B](../evidence/opencode-9b-rerun.json) · [Codex](../evidence/live-same-runtime.json) |
| Correct workspace and locate the timeout | Matching `PWD` fixed checkout selection. Inference occupied about 177 of 180 seconds in the original replay. §4.3. | [Workspace](../evidence/opencode-workspace-probe.json) · [Timing](../evidence/opencode-provider-timing.json) |
| Isolate edit and compaction boundaries | Exact match applied. A truncated scripted summary reproduced the observed compaction error. Enabled and disabled live arms each finished 0/2. §§4.5–4.6. | [Scripted controls](../evidence/opencode-boundaries.json) · [Historical summary](../evidence/opencode-historical-compaction.json) · [Live pairs](../evidence/packaging-frozen.json) |
| Isolate startup and same-model harness effects | A fixed title removed the auxiliary request. The fixed-title run and local Codex probe left source unchanged. §4.7. | [Trace](../evidence/packaging-provider-trace.json) · [Fixed title](../evidence/packaging-fixed-title.json) · [Local Codex](../evidence/codex-local-provider.json) |
| Conditional Git push recovery | 3/3 intended refs observed, one update each after retry. §4.1. | [Bare-Git trials](../evidence/git-publication.json) |

### Rounds 2 and 3

| Hypothesis and prediction | Reported outcome | Evidence |
|:----------------------------|:--------------------------------------------|:-------------------|
| H1 · Request-level reasoning off improves completion | Channels changed and 0/2 fixes per arm. Smoke probe failed to qualify off. §4.11. | [Matrix](../evidence/packaging-reasoning-matrix.json) · [Smoke](../evidence/reasoning-channel-check.json) |
| H2 · A current receiver rejects delayed old writes | Current denied 3/3. H2b lagged and idempotency-only accepted 3/3 each. §4.8. | [Delayed delivery](../evidence/delayed-publication.json) |
| H3 · Managed recovery changes human restart cost | Human hypothesis untested. Scripted rehearsal completed both arms and validated timing fields. §4.9. | [Rehearsal](../evidence/handoff-timing-rehearsal.json) |
| H4 · A bounded function response can repair the task | 4B failed to parse. H4b 7B applied and failed both change checks. §4.12. | [4B](../evidence/packaging-bounded-receiver.json) · [7B](../evidence/packaging-bounded-coder.json) |
| H5 · Recover a receiver-first transfer | 3/3 recovered with the operator key and one effect, following a temporary refusal. §4.8. | [Receiver first](../evidence/receiver-first-activation.json) |
| H6 · Reopen an interrupted effect transaction | 6/6 converged after failure on either side of commit. §4.10. | [Receiver restart](../evidence/receiver-restart.json) |
| H7 · Counterexample enables a second repair | Live guard rejected the first response. Scripted correction passed. §4.12. | [Adaptive](../evidence/packaging-bounded-feedback.json) · [Scripted](../evidence/packaging-feedback-scripted.json) |
| H8 · Feedback from a known failing seed yields a repair | The candidate was rejected by the guard. §4.12. | [Seeded trial](../evidence/packaging-bounded-seeded-feedback.json) |
| H9 · Body-only improves application or correctness | One edit applied per arm. Body passed only the initial grader. §4.13. | [Contract comparison](../evidence/packaging-body-contract.json) |
| H10 · Durable activation and effects survive restart | Five initial fault points. Extended matrix converged in 18/18. §4.14. | [Original](../evidence/durable-activation.json) · [Extended](../evidence/prepared-activation.json) |
| H11 · Expanded checks expose missed behavior | Whole edit differed on 279/1,111 and body on 123/1,111. §4.13. | [Expanded oracle](../evidence/packaging-body-oracle.json) |
| H12 · Reopen a fully prepared checkout | 3/3 matching detached worktrees were adopted. §4.14. | [Prepared activation](../evidence/prepared-activation.json) |
| H13 · Identical requests reproduce the candidate | Three seed-32 repeats matched response, source, and grade. §4.13. | [Exact repeat](../evidence/packaging-body-repeat.json) |
| H14 · Expanded-oracle feedback repairs the error | Guard rejected a nested function wrapper. §4.13. | [Refinement](../evidence/packaging-body-refinement.json) |
| H15 · Normalize a redundant wrapper | Normalization admitted the same candidate with 123 mismatches. §4.13. | [Wrapper refinement](../evidence/packaging-wrapper-refinement.json) |

| Rounds 4–5 hypotheses | Reported outcome | Evidence |
|:----------------------------|:--------------------------------------------|:-------------------|
| H16 · Authenticate ownership at effect time | Credential controls rejected wrong authority, and 18/18 faults converged. §4.15. | [Authenticated recovery](../evidence/authenticated-recovery.json) |
| H17 · Recover an incomplete checkout with a fresh path | 3/3 replaced the incomplete snapshot after a second exit. §4.15. | [Authenticated recovery](../evidence/authenticated-recovery.json) |
| H18 · Paired live continuation | All six restored the intended artifact. 0/6 verified edits. §4.18. | [Paired attempts](../evidence/paired-continuation.json) |
| H19 · Broader probes reject partial repairs | Rejected 3/3 despite visible and native passes. §4.16. | [Negative controls](../evidence/paired-oracle-controls.json) |
| H20 · Scripted tool round trip | 2/2 applied an edit and returned its tool result. §4.18. | [Tool controls](../evidence/paired-tool-control.json) |
| H21 · Kill Git mid-apply | 3/3 refused partial output and recovered a fresh checkpoint. §4.17. | [Native Git crash](../evidence/git-restore-crash.json) |
| H22 · Qualify reasoning off | Three endpoints gave exact answers with reasoning off on both smoke passes. §4.19. | [First smoke](../evidence/paired-reasoning-control.json) · [Repeat](../evidence/paired-reasoning-repeat.json) |
| H23 · OpenCode Click with off | Earlier clean exit in 65.1 s, source unchanged. §4.19. | [OpenCode follow-up](../evidence/paired-click-reasoning-off.json) |
| H24 · Accept equivalent reference variants | All three alternates matched all 247 probes. §4.16. | [Positive controls](../evidence/paired-alternate-controls.json) |
| H25 · Codex Click with off | Earlier clean exit in 137.5 s, source unchanged. §4.19. | [Codex follow-up](../evidence/paired-codex-click-reasoning-off.json) |

| Round 6 hypotheses | Reported outcome | Evidence |
|:----------------------------|:--------------------------------------------|:-------------------|
| H26 · Cap tool read observations | 0/2 verified per arm. One capped edit failed on 24/45 probes. §4.20. | [Capped reads](../evidence/capped-reads.json) |
| H27 · Hosted Git ref recovery | 3/3 retained the intended SHA and rejected the delayed conflict. §4.21. | [Hosted ref trials](../evidence/hosted-git.json) |
| H28 · Human handoff effort | Instrument qualified in two scripted sequences. Participant comparison pending. §4.22. | [Rehearsal](../evidence/operator-pilot-rehearsal.json) |
| H29 · Hosted authenticated receiver | 9/9 converged at one confirmed effect and receipt. §4.21. | [Hosted container trials](../evidence/hosted-receiver.json) |
| H30 · Qualify configured Codex | 3/3 initially passed all frozen grading gates. §4.20. | [Qualification](../evidence/receiver-qualification.json) |
| H31 · Scope a replacement to two blocks | Initial guard rejected both responses due to a duplicate anchor. §4.20. | [Initial trial](../evidence/scoped-click.json) |
| H32 · Requalify and replay the guard | Reference control passed. Exact replay was unchanged. Explicit prompt edit missed 4/45. §4.20. | [Corrected replay](../evidence/scoped-click-replay.json) |
| H33 · Repeat receiver qualification | 3/3 repeated the initial successes on the same tasks. §4.20. | [Repeat](../evidence/receiver-qualification-repeat.json) |
