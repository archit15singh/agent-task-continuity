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

A second round found that delayed requests still applied when the receiver's generation lagged. A current-generation receiver rejected all three delayed requests. SQLite receiver crashes on either side of commit converged on one transactional effect and receipt in 6/6 trials. Eight additional live attempts on the frozen task produced zero verified fixes. A subsequent body edit passed the original checks and failed an expanded upstream oracle. The combined durable activation fixture converged across all 18 process-failure trials.

An authenticated receiver rejected current-generation requests carrying retired, missing, or other-task credentials. It confirmed one effect per operation in a further 18 fault trials. After an interrupted restore on each of the three repositories, the source predicate passed while a selected note was missing. A coordinator that persisted a fresh checkout destination recovered the full checkpoint in all three cases.

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

**Round 2 interventions.** The reasoning comparison used the same frozen Packaging checkpoint, OpenCode, fixed session title, local Qwen3 4B alias, 1,500-token model output cap, and 180-second worker deadline. A loopback relay set only the request's `reasoning_effort` field. The four attempts ran in default, none, none, default order with a fresh checkout each. We counted characters in the provider's reasoning and visible channels and graded workspace, task behavior, and process exit separately. The bounded receiver tested a different intervention. A single request received the same task, note, and original helper source. It returned one function for a guarded splice. The unchanged function served as a negative control. The upstream function with its companion regex inlined served as the positive control. Later diagnostics used six Boolean input-output cases and allowed at most one counterexample in an extra request. We separately tried feedback from the original helper and checked the feedback implementation with a scripted wrong-then-correct provider.

**Delayed acceptance and activation.** The reference service was paused after receiving a complete request and before applying the effect. We killed the client and advanced SQLite ownership. The receiver then ran under three conditions: operation-ID idempotency, a current generation check, or a generation check whose receiver remained one generation behind. A second experiment simulated an interruption after receiver activation and before local activation. It used the operator recovery key to repair the local generation and retry the same intent. The fixtures recorded delivery and application separately. A separate SQLite receiver fixture inserted effect and receipt rows in a single transaction and terminated its process before or after commit, before sending a response. We reopened the receiver database after death, then started a new process at the same endpoint and settled the intent.

**Human timing rehearsal.** The automated rehearsal measured capture, restart to workspace-ready, and restart to the first independently verified predicate. Each pinned repository ran a manual and managed restoration with the same candidate and note. The clean-parent control tried the same check with no restored change. The participant protocol calls for distinct matched tasks and counterbalanced order, with operator effort measured separately from runtime waiting. The reported rehearsal contains only scripted command timings.

**Round 3 format controls.** Qwen2.5-Coder 7B received the same recovered task, source excerpt, JSON object format, and output allowance in both arms. The code string contained either the whole function or just its body, with the original signature supplied at application time. We logged provider, JSON, signature, syntax, scope, and behavioral dispositions separately. We replayed a seed and expanded the behavioral oracle to every ABI list of length zero through three over ten fixed entries. The expected results came from the pinned upstream helper and remained outside the initial model prompts. We then tested one feedback request using the first disagreement.

**Combined durable activation.** A coordinator wrote the activation intent and successor credential to a protected fixture directory before advancing an authenticated receiver endpoint. The receiver stored its generation in SQLite and checked it in the same transaction as the simulated effect and receipt. A coordinator process terminated after the intent, receiver activation, worktree creation, or local takeover. A separate receiver process terminated before or after the effect commit. The harness restarted the receiver, replayed the intent, and delivered the archived old-generation request. The local API can adopt a detached linked worktree from the same repository after verifying its checkpoint fingerprint. It preserves mismatched or unrelated destinations during rejection.

**Worker authentication and incomplete restore.** Round 4 ran three matched credential control pairs and repeated the six interruption stages three times with worker authentication enabled. The managed client derives a bearer from the owner token, task, and generation using HMAC-SHA-256. The fixture's coordinator registers only the bearer hash with the next generation. The receiver verifies the bearer hash and the task-specific operation ID in the effect transaction. An independent restore experiment applied only the tracked path from each saved patch, using Git's path filter, then exited the coordinator. We ran the source predicate and checked the tracked and selected untracked bytes independently. The original recovery policy tried to adopt the partial checkout. The new policy persisted another destination and exited before restoring to it. After restarting both processes we checked authority, the restored fingerprint, and the preservation of the partial checkout. [Git apply documentation](https://git-scm.com/docs/git-apply)

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

In all three partial restores, the tracked source matched the upstream reference and its behavior predicate passed, but the selected note was missing. The original coordinator refused the checkout and left the local generation at 1. The revised coordinator saved a new destination and recovered from a second exit before that directory existed. After restart, the new checkout matched the saved fingerprint and passed all three grading checks. It reached generation 2 in each case. The original partial checkout retained its measured state. The injection exited between selected paths at a known boundary. Recovery after host power loss or an interruption inside a Git command remains unmeasured.

## 5. Design implications and limits

Git patch export is a strong baseline. The managed path earns its complexity when work has to survive an unattended interruption, a conflict over who owns the task, or uncertain publication. The replay unit in this prototype is a task checkpoint tied to an artifact. Agent sessions remain helpful as optional context. Qualify a replacement against a frozen task with a passing behavior check before relying on unattended recovery. The endpoint, generation budget, and setup requests can all change how much work fits inside the same deadline. Qualifying an output format requires both safe application and passing behavior. A narrow edit scope reduced the interaction but still left semantic validation essential.

The gateway owns the local credential check and its client protocol. Once a request is in flight, authority at application depends on the receiver's generation and when it was advanced. Direct shell and API writes outside it remain outside the fence. The black-box test used one host, a common Git object store, three Python repositories, selected file changes, and a loopback fixture with in-memory state. It exercised worker and publishing-client death while the provider survived. The separate Git follow-up covered local bare-repository pushes with a receiver paused after acceptance. It measured ref updates and does not establish provider-side fencing, hook effects beyond the instrumented update counter, or results on a hosted service. The SQLite receiver extension covers process restart for transactional effects. The original in-memory service and bare Git trials cover different receiver contracts. A hosted service and distributed consensus remain outside the evaluated system. The snapshot follows Git normalization, preserves selected files, and requires that the shared repository retain its base. The receipt describes the host and command, while dependency and tool versions beyond those explicitly pinned remain part of the operator's environment.

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

The [public repository](https://github.com/archit15singh/agent-task-continuity) includes both protocols, pinned cases, scripts, and receipts with source hashes. The [evidence index](https://github.com/archit15singh/agent-task-continuity/tree/main/evidence) records commands, model settings, test summaries, and failed attempts. The [research loop](https://github.com/archit15singh/agent-task-continuity/blob/main/docs/research-loop.md) records the hypotheses and ranked follow-ups.
