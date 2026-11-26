# Agent continuity follow-up

## Goal prompt

Find out which failure boundaries prevent a replacement agent from finishing work on a recovered checkout. Use the public pinned Packaging case, hold the handoff fixed, run the existing independent graders, and preserve receipts for every attempted arm. Use small controlled fixtures to isolate compaction and edit application. Update the paper and README only where the evidence changes the conclusion.

## Loop prompt

Read the latest receipts. Choose the cheapest experiment that distinguishes the strongest remaining explanations. Pin inputs and state the expected observation before running it. Run a negative control, then the experiment. Record failures, versions, timings, scope, and what the result cannot establish. Continue while the next experiment can resolve a material uncertainty within the authorized scope. Stop identical retries after a deterministic error.

## Frozen diagnostic protocol

- Use the existing pinned Packaging parent and graders. The two inputs in `evals/fixtures/packaging` are study-authored replacements for the ephemeral historical Codex inputs. The original run recorded hashes only. Grade the frozen reproduction and independent predicate on the clean parent and upstream positive reference before launching agents. Give the agents only the pinned parent and frozen handoff.
- Repeat the OpenCode reference and OpenCode with auto compaction disabled twice each, in enabled/disabled/disabled/enabled order, with the same local Qwen3 4B alias and 180-second worker deadline. Keep native tests, restored files, scope, independent predicate, carried repro, and worker exit separate. Stop early on a deterministic setup failure. This is a diagnostic case with no held-out inference.
- After the reference preflight, probe Codex with the same local model if its API can run it. Treat a transport mismatch as a setup result. A successful comparison would still vary harness prompts, tools, and protocol.
- Use scripted tool calls for Click, varying only exact `oldString` matching. For compaction, use a synthetic provider to vary the reported context usage and response completion. Scripted outcomes establish behavior at the boundaries under controlled input.

## Iteration after the scripted boundary tests

The truncated summary reproduced the live error label. Test whether a real summary request reaches the same finish condition by adding a loopback relay that records request type, provider finish reason, and usage. Give it one additional 180-second baseline attempt after the paired matrix. Do not run another inference job on the same provider during timed attempts.

Then try a minimal Codex Responses turn against the same local model. If it passes, apply the same frozen Packaging checkpoint in one exploratory Codex run. A Codex acceptance result requires its own passing smoke, matched checkpoint fingerprint, and the same out-of-band task gates.

## Independent Git publication probe

Use a disposable bare Git receiver as a second publication target. Hold the first push open in the receiver's post-receive hook after the new ref is visible. Kill the publishing client before it returns, verify the ref by independent readback, and replay the same candidate. A second control must reject a different candidate with the same expected-absent lease, leaving the first SHA intact. Repeat three times with fresh receivers. The probe measures Git ref convergence and changes recorded by post-receive. It does not test GitHub, remote fencing, or general exactly-once delivery.

## Iteration after the provider trace

The trace identified an auxiliary title request that ran concurrently with the first task request and consumed the same 1,500-token allowance. Test explicit titles against the scripted provider first. If supplying a title removes the tool-free startup request, add a single live traced attempt with a fixed title and the same checkpoint, provider and timeout. A reduction in calls verifies a mechanism on this setup. A single timed attempt is exploratory for latency and repair quality.

## Round 2 goal prompt

Separate wasted generation from task capability, and determine which component can enforce authority after takeover. Use the frozen Packaging checkpoint for diagnosis and the existing controlled service for delayed effects. Record the research question, prediction, controls, outcome, and limitations before deciding what to implement next. Keep the paper, evidence index, and runnable methods in sync.

## Round 2 loop prompt

1. Read the last receipt and name the decision the next experiment could change.
2. Specify a falsifiable hypothesis, one intervention, a negative control, and the success gates. Save the protocol before launching.
3. Execute the cheapest control, then run the predetermined arms. Preserve setup failures and incomplete attempts with their denominators.
4. Compare observations to the prediction and write the supported conclusion in the paper. Record the strongest surviving alternative and rank the next experiments by what each would resolve.
5. Continue on independent authorized experiments. Record dependencies for work that needs a human participant, an external receiver, or a capable model.

### H1 · Provider reasoning and completion

The ordinary generation cap was reached even with a fixed title. Test whether an explicit provider request to disable reasoning reduces the reasoning output observed on the stream and increases passing edits within 180 seconds. Use OpenCode, the same local Qwen3 4B alias, fixed title, auto compaction on, and one shared Packaging checkpoint. Set `reasoning_effort=none` only on the intervention arm. Order is default, none, none, default. Two repetitions are diagnostic. Grade exit, change scope, restored files, independent predicate, carried reproduction, and native tests separately. Report reasoning characters and visible content characters as stream observations. They are not token counts. The ledger fingerprint must match across arms and the clean and upstream grading controls must pass.

### H2 · Delayed acceptance after takeover

Hold the first publication at a loopback receiver after it has received the request and before it applies the effect. Kill the publishing client, complete takeover, and release the held request. Compare an idempotent receiver that accepts by operation ID with one that checks a monotonic generation at the effect boundary. Advance the generation through the test coordinator before release. Run three trials per arm. Verify the stale client fails locally, the effect count before recovery, and convergence after the replacement retries. A receiver that fences correctly rejects the old generation and still permits the replacement to settle the same reserved intent.

### H3 · Human restart cost

Measure capture effort, time to first verified useful action, and active operator time against competent manual Git and a concise brief. Use distinct matched tasks, paired within participants, with order counterbalanced. Record abandonments and idle/backend time separately. A mechanical rehearsal can validate timing and completeness gates. Human outcomes require an actual participant.

### H2b · Lagging receiver generation

The first acceptance experiment shows a difference when the receiver is advanced before release. Add a negative control that keeps generation 1 at the fenced receiver until after the delayed request is processed. SQLite still completes takeover first. Three lagged trials should accept the old request while the receiver remains on generation 1. This tests the transfer-to-receiver gap separately from implementing the equality check.

### H3 rehearsal

On Click, Packaging, and attrs, seed a tracked change and a concise note. Record capture, restore, first predicate, and end-to-end time for matched manual and managed restores, with a fresh worktree per attempt. A negative control restores the clean base, runs the same predicate, and must record no first verified action. All timings in these receipts are scripted command wall time.

### H4 · Bounded one-function receiver

Test whether the same 4B model can solve the frozen Packaging task with a shorter interaction. Give one request the objective, frozen note, and existing helper source. Request only a replacement for that helper, apply it through a syntax-checked splice, and grade in the recovered worktree. The scope is fixed before inference. Validate the splicer on the unchanged function and the function from the upstream fix with its companion regex inlined. The model receives only the original helper. This is a one-attempt feasibility test of a task-specific receiver with preselected source. It changes both the context and the editing mechanism relative to a general coding agent.

### H5 · Recovery after receiver-first activation

Advance the fenced receiver to generation 2, then interrupt the activation sequence before writing the local takeover. Keep the original request held. The still-valid local generation-1 owner should receive an HTTP 412 from the receiver and leave the operation unknown. Recover the local owner with the operator recovery key, release the original request, and retry the same intent under generation 2. Repeat three times. This simulates the interrupted coordination state and kills the publishing client for real. The experiment addresses convergence with a compatible receiver and access to its generation and the recovery key.

### H1 follow-up · Channel labels and answer quality

The first arithmetic smoke moved hundreds of characters from the reasoning stream to ordinary content and still hit the cap. Repeat the identical two-request smoke with checks for an exact answer and literal think tags. These are observable output properties. A missing tag cannot reveal how the model used its generation budget.

### H6 · Receiver death before or after commit

Use a loopback receiver that writes a simulated effect row and a receipt in one SQLite transaction. Kill the receiver process immediately before or after that commit, before any acknowledgment. Restart a new process at the same endpoint. The before-commit condition should expose zero effects and zero receipts after death. The after-commit condition should expose one of each. In both conditions a replacement must reconcile to one durable effect and one matching receipt. Repeat three times per condition with separate receiver databases. This exercises a transactional stand-in for an effect that shares the receiver's database.

### H4b · Coding-tuned local comparison

Reuse the bounded receiver, prompt, checkpoint, output allowance, and graders with Qwen2.5-Coder 7B. Give it one attempt after the Qwen3 4B tests. The outcome decides whether there is a local configuration worth replicating on new tasks. This diagnostic changes the model family and size together and gives no model ranking. [Model card](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)

### H7 · One behavioral counterexample

The coding-tuned receiver applied a scoped function and failed both change checks, so use a single feedback turn. Repeat its initial bounded request. If a candidate applies and fails, test the helper against a fixed six-input behavior matrix and send only the first failing input, expected boolean, and observed boolean with the candidate function. Regrade with the original checks and all six cases. Stop after at most one feedback request. This is adaptive repair on a diagnostic task. The first and final outcomes are both retained, and any new pass still requires held-out replication.

### H8 · Seeded feedback feasibility

The adaptive repeat produced an output that the splice guard rejected, so it gave no feedback trial. Isolate the second turn with the original helper as a verified failing seed. Supply the same first failing example and request one correction from the coding-tuned model. Retain this receipt separately from the adaptive run. If the candidate applies, compare all six helper behaviors and both existing change-specific checks. This isolates whether the feedback prompt can produce a valid repair from a known source state.

## Round 2 results and next hypotheses

- H1 changed the reported output channels. Both settings produced zero verified fixes. The provider advertised thinking enabled as its sole supported value. Future reasoning experiments should qualify a demonstrated ability to switch modes before running repository tasks.
- H2 and H5 isolated the local transfer-to-receiver gap and the temporary unavailability when the receiver advances first. H6 established the distinct effect-and-receipt commit boundary in SQLite. The next implementation hypothesis is that a durable, authenticated receiver generation can be combined with durable operation receipts and an interrupted activation record. Fault each boundary under process restart.
- H3 validated the timing measurements on three public repositories. Participant observations are the next requirement for conclusions about operator effort.
- H4, H7, and H8 separated output length, guard rejection, and behavioral failure. A scripted wrong-then-correct pair confirmed that a real counterexample reaches the second request and the same verifier can pass its replacement. Qualify a typed body or patch format on new tasks before broader model comparisons.

| Rank | Next experiment | Decision it would change |
|---:|---|---|
| 1 | Hold the edit region fixed and compare a typed function body with a whole function, tracking the specific guard boundary on each attempt | Whether a smaller edit contract reduces rejection without sacrificing correctness |
| 2 | Persist receiver epochs and activation intent, then repeat old-request delivery and restart at each transition | Whether remote authority survives interrupted activation and receiver restart together |
| 3 | Choose new held-out repository tasks and repeat only receivers that first pass a fixed qualification case | Whether verified continuation generalizes beyond Packaging |
| 4 | Run the paired restart protocol with actual operators | Whether managed recovery saves human active time after accounting for capture and review |
| 5 | Exercise a cooperating hosted receiver with independent readback | Which external guarantees hold outside the loopback and bare-Git fixtures |

## Round 3 goal prompt

Measure whether restricting the model to a replacement function body improves edit acceptance and correctness on the frozen Packaging task. Combine durable receiver ownership with durable effect receipts and test recovery across both processes. Preserve results that contradict the hypotheses. Update the paper and promote only claims supported by independent checks.

## Round 3 loop prompt

Read the previous result. Pick a boundary where competing explanations predict different outcomes. Freeze inputs, state the expected observation, and run the negative and positive controls before inference or fault injection. Record request disposition, action application, and final correctness separately. Repeat the smallest test that resolves remaining uncertainty, then publish the receipts and rank the next questions.

### H9 · Body-only edit contract

Keep the task, original helper, checkpoint, provider, output budget, guard, and graders fixed. Ask for JSON with a single code string in both arms. One string contains the whole helper and the other contains only its body. For the body, the receiver supplies the original signature. Predict fewer signature rejections and no loss of behavioral correctness. Run whole, body, body, whole with paired seeds 31 and 32. A scripted wrong-signature control must fail independently of syntax. Use the unchanged and upstream-equivalent helpers as behavioral controls. Treat this as a one-task diagnostic.

### H10 · Durable activation and effects

Write activation intent durably before advancing the receiver. Authenticate the receiver's generation update using a separate coordinator credential. Persist the receiver generation across process restart and check it in the same transaction that applies effects and stores receipts. Exercise process death after writing the intent, after advancing the receiver, after local transfer, and before or after the receiver effect commit. After reopening both stores, replay the activation intent and test delayed generation-1 delivery. Predict a stale rejection after recovered activation and exactly one final effect. A generation header in this loopback fixture is a trusted-client assertion. The coordinator credential protects activation only.

### H11 · Oracle expansion and repetition

The first four edit-contract trials accepted one candidate per arm; only the body candidate passed. Repeat seed 32 and add seed 33 in whole/body/body/whole order on fresh checkouts. Compare accepted candidates to the pinned upstream helper over all ABI lists of length zero to three drawn from ten fixed entries. Keep the oracle cases out of both prompts. Count behavior differences separately from guard rejections. This expands verification on the same task; it is not a cross-repository generalization test.

### H12 · Interrupted worktree preparation

The first activation matrix interrupted the coordinator on either side of ownership commit. Add the earlier boundary after successful Git restoration and before local authority changes. Resume with the same staged token and prepared path. The takeover should adopt only a verified linked worktree from the same repository and keep the generation monotonic. A mismatched or unrelated path must be rejected and preserved.

### H13 · Exact-request repeatability

Seed 32 produced different grades across rounds. Forward and record the requested seed explicitly and run the identical body request three times. Keep the expanded oracle and compare response hashes as well as verified behavior. A match within this series establishes observed repeatability for this run; a difference establishes that the request seed alone was insufficient to reproduce the output on this setup.

### H14 · Counterexample from the expanded oracle

The repeated body candidate was byte-identical to the initial apparent pass. Produce it again with seed 32, then give the model that candidate and the first minimal mismatch from the ordered upstream-oracle inputs. Test one correction with the same body contract and output allowance. Recheck the original gates and all 1,111 inputs. Record whether the sample was actually repaired and whether other differences remain. A successful correction would still only qualify the receiver on this diagnostic case.

### H15 · Normalize a redundant function wrapper

The counterexample correction returned a nested-function rejection under the body contract. Repeat that exact request with one normalizer. If the body fails because it contains a function definition, accept a complete wrapper only when it independently passes the existing whole-function guard, including the original signature and scoped AST. Keep the input, expected response, and oracle unchanged. Reject arbitrary nested definitions and score any normalized candidate against all behaviors.

## Round 3 results and next hypotheses

The requested seed was present at the relay, and the body output matched byte-for-byte across the repeat series and the initial success. The change in disposition came from adding a broader grader. The single counterexample correction returned a function wrapper. Normalization accepted the same response but yielded the unchanged candidate and the same 123 disagreements.

The combined durable fixture converged in all 18 trials after testing six interruption points. The prepared checkout was adopted in three more specific trials without advancing past generation 2. The regression test confirms unrelated and changed destinations are preserved.

| Rank | Next experiment | Decision it would change |
|---:|---|---|
| 1 | Predeclare broader hidden behavior oracles on new repository tasks before qualifying a replacement | Whether scoped edits succeed beyond a small task-specific check set |
| 2 | Bind each remotely submitted generation to a per-task credential, then repeat delayed delivery and receiver restart | Whether the trusted loopback generation assertion can become an authenticated worker contract |
| 3 | Stop Git restoration midway through applying a multi-file patch | Whether the coordinator can safely distinguish a verified prepared checkout from an incomplete one and resume it |
| 4 | Run the paired restart protocol with operators | Whether managed recovery changes human active time |

## Round 4 goal prompt

Determine whether a receiver can enforce task ownership using a credential bound to the active generation, and whether a replacement can recover when a process dies with only part of a multi-file checkpoint applied. Run the restore experiment on the three pinned public repositories and publish both controls and failures.

## Round 4 loop prompt

Freeze the checkpoints and interruption points. Run the controls, inject a process exit, reopen both stores, and independently count recovery, rejected writes, and effects. Compare the committed checkout to the captured fingerprint. Retain the incomplete attempt so a recovery rule can be audited. Report any behavior this design leaves untested, then rank the next questions.

### H16 · Worker-authenticated publication

Compare the existing header-only receiver against one that also checks a task-scoped bearer bound to the active generation. After activating and reopening the receiver, send a generation-1 request and then a generation-2 request carrying the retired credential. Send the same generation-2 request without a credential. The header-only control should accept both current-number requests. The authenticated receiver should reject both and accept the active credential. Retry activation with matching and conflicting bindings. Re-run the original six failure stages, three trials each. Require one final effect and receipt per operation.

### H17 · Incomplete checkout recovery

Reuse the pinned Click, Packaging, and attrs implementation diffs. Capture each source change with a selected untracked note. In a disposable linked checkout apply only the tracked implementation patch and exit the coordinator before the note is applied. The existing coordinator should fail verification and leave ownership unchanged. With recovery enabled it should retain the incomplete checkout, commit a fresh destination to the intent before restoring, and converge on a verified snapshot at generation 2. Also interrupt after committing the fresh path and verify a subsequent restart can finish. Treat the selected-file split as a controlled process-boundary injection rather than a random fault inside Git.

## Round 4 results and next hypotheses

H16 passed within the loopback fixture. All three current-generation attempts per credential class succeeded under header-only checking. With worker authentication, all attempts using the retired credential, no credential, or a credential bound to the other task were refused. A different binding could not replace a binding on a repeated activation. Exploratory checks also found that a valid credential could no longer submit an operation under an ID derived for a different task. The 18 authenticated fault trials each converged on one effect and one receipt.

H17 passed on Click, Packaging, and attrs. The tracked source and the source predicate passed before recovery even though the selected note was missing in all three. The fingerprint precondition caught the missing file. Retrying into a newly recorded path recovered the complete snapshot after a second process exit. The abandoned worktree retained its measured contents.

| Rank | Next experiment | Decision it would change |
|---:|---|---|
| 1 | Freeze independent behavior oracles for new repository tasks before running the same-runtime and cross-runtime replacements on matched checkpoints | Whether new replacement failures come from transfer quality, runtime ability, or what the grader measures |
| 2 | Interrupt the Git child process during checkout and during patch writes, including regular files, binary data, and deletions | Which real Git crash states require quarantine, retry, or operator repair |
| 3 | Publish to a cooperating hosted receiver and independently read back effects after disconnects | Which loopback guarantees survive a network and a separate service boundary |
| 4 | Run the paired restart protocol with real operators | Whether managed recovery saves operator time after capture and verification |

[Round 4 receipts](../evidence/authenticated-recovery.json)

## Round 5 goal prompt

Measure completion on three new historical changes with matched fresh Codex and OpenCode replacements and the same locally hosted model. Freeze the brief, visible reproduction, scope, and broader behavior probes first. Keep restoration, tool execution, native tests, and verified behavior separate.

## Round 5 loop prompt

Pin the historical parent and reference. Grade both before launching a worker. Freeze the checkpoint and expected probe outputs. Run one bounded attempt per runtime per task, reversing launch order on the middle case. Archive dispositions and differences for every attempt. If the two runtimes fail at different boundaries, qualify that boundary separately before changing model or prompt budget.

### H18 · Paired continuation and independent verification

Use the Click deprecated-help formatting change, Packaging marker quoting change, and attrs converter adapter change. The study author supplies a fixed brief and a narrow reproduction to both fresh runtimes. This controls the artifact and omits any live source-phase or transcript resumption. Require the parent to fail the visible reproduction and differ on at least one hidden probe, and require the reference to pass the reproduction and native test modules. The reference supplies the hidden outputs. Each runtime receives the historical parent without Git history, the same checkpoint and brief, 180 seconds, and the same Qwen3 8B alias via the installed Ollama service. Cap its model context at 16,384 and configured generation at 2,048 tokens per request. Run serially in Codex/OpenCode order for Click and attrs and OpenCode/Codex order for Packaging with no replacement retries. Both replacements should recover the exact same selected bytes. Compare successful visible reproductions with the broader probes, native checks, and edit scope. Report this as a pilot on one model and three tasks. Endpoint and tool-surface differences are part of the runtime configuration.
