# Evidence and reproduction

Each receipt identifies the candidate or harness revision, the pinned upstream input, and the checks that ran. Source and output hashes let a reproducer compare byte-level evidence. Raw live runtime logs can contain local paths and interleaved tool data. The public receipts carry event counts, dispositions, durations, hashes, and test summaries.

| Receipt | What it records |
|---|---|
| [Smoke and unit checks](smoke-and-unit.json) | Package installation, CLI, unit checks, hosted OpenCode rate limits, and local runtime probes. |
| [Mechanical development](mechanical-development.json) | Click dry run on the initial frozen harness. |
| [First held-out mechanical run](mechanical-held-out-first.json) | Packaging and attrs. Packaging's native suite failed at collection with `ModuleNotFoundError: No module named 'pretend'`. The transport and fault predicates completed. |
| [Mechanical matrix before manifest export](mechanical-before-manifest.json) | Clean native rerun and first publication-client SIGKILL results. |
| [Final mechanical matrix](mechanical-final.json) | All three repos with the dependency pinned. Includes the publication-client SIGKILL probe and public manifest round-trip. |
| [Live development](live-development.json) | First Codex-to-OpenCode attempt on Click. The reproduction and note survived. The replacement hit the preregistered time limit. |
| [Same-runtime live comparison](live-same-runtime.json) | Exploratory Codex-to-Codex Click run. All task gates passed. The cross-runtime flag remains false by definition. |
| [Live held-out](live-held-out.json) | One Codex-to-OpenCode attempt on each held-out case. Both recovered the checkpoint files and reached the time limit without a passing edit. |

The original live runner recorded Git HEAD when writing the receipt. The Click pilot began and launched the replacement under `7cc54b5` and finished after `0f56e74` was committed. Both revisions are recorded in its receipt. The held-out run began and both replacements launched under `b4ce25b`. It finished after `c2f94ba` was committed. Both revisions are recorded in its receipt.

## Reproduce

From the repository root, follow the environment setup in the [README](../README.md). Run the development and held-out arms separately to keep their reports separate, or use `--set all` for the final mechanical matrix.

For the live held-out configuration, make the local Ollama registry available to OpenCode and create a bounded model variant. The recorded run used Qwen3 4B Q4_K_M. The Ollama base manifest digest was `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`; the derived manifest was `48c0fc34e0759fbccf94c03a62321d814d851e14368b1a4ad3c97da6f1012109`. Model registry tags and provider aliases can change.

```sh
ollama pull qwen3:4b
printf '%s\n' 'FROM qwen3:4b' 'PARAMETER num_ctx 16384' \
  'PARAMETER num_predict 1500' > /tmp/continuity-model
ollama create continuity-qwen3:4b -f /tmp/continuity-model

.venv/bin/python -m evals.live --set held-out \
  --model continuity-local/continuity-qwen3:4b \
  --local-endpoint http://127.0.0.1:11434/v1 \
  --local-no-think --output /tmp/continuity-live-held-out.json
```

The live arm needs authenticated Codex CLI access, OpenCode, and the local model. It reads only the selected public project at its pinned parent and supplies the prompts in [the live runner](../evals/live.py). It downloads no upstream candidate patch. The reference and parent SHAs are in [the case manifest](../evals/cases.json).

## OpenCode timeout follow-up

- [Qwen3 4B Packaging replay](opencode-4b-replay.json) records the original configuration with added step and tool timing.
- [Ollama timing and availability probes](opencode-provider-timing.json) record the overlapping local request windows, the canceled request, the hosted free-model quota errors, and a synthetic check of the reasoning parameter.
- [Workspace probe](opencode-workspace-probe.json) compares the checkout named in OpenCode's project prompt under inherited, matched, and unset `PWD`.

To reproduce the original Packaging replay, use the original 4B variant above and add `--case packaging` to the held-out command. A current checkout includes the workspace fix. The historical launcher is at `96f0e6c`; run it only from a disposable study checkout for the pre-fix diagnostic. Ollama's server logs provide request durations and generation counts. The live receipt supplies OpenCode step timing and grading.

The corrected comparison uses Qwen3.5 9B through Ollama 0.40.6 with its MLX runner. The base manifest digest was `d63f830f28d515fefea546f213fca7a75e9dd5176ef51a6deabc952d1c99a911` and the bounded alias digest was `5cb0679029eb4c3e13d020bec7e3489e973b47dd948456155e0d5c6c04695598`. [Qwen3.5 9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) · [Ollama reasoning control](https://docs.ollama.com/api/openai-compatibility#v1chatcompletions)

```sh
ollama pull qwen3.5:9b
printf '%s\n' 'FROM qwen3.5:9b' 'PARAMETER num_ctx 16384' \
  'PARAMETER num_predict 1500' > /tmp/continuity-model-9b
ollama create continuity-qwen35:9b -f /tmp/continuity-model-9b

.venv/bin/python -m evals.live --set all \
  --model continuity-local/continuity-qwen35:9b \
  --local-endpoint http://127.0.0.1:11434/v1 \
  --local-no-think --local-reasoning-effort none \
  --output /tmp/continuity-opencode-9b.json
```

[The pre-fix 9B batch](opencode-9b-pre-fix.json) is retained as a workspace diagnostic. [The mechanical regression rerun](mechanical-workspace-fix.json) records passes across Click, Packaging, and attrs after the launch fix.

[The corrected Qwen3.5 9B matrix](opencode-9b-rerun.json) preserves all three deadline failures and their out-of-band grades. [The sanitized Click and Packaging tool traces](opencode-9b-tool-errors.json) record the edit and lookup error categories.

[The corrected 4B Packaging control](opencode-4b-workspace-fix.json) completed a read, then exited in 142.6 seconds with `compaction.failed` before a scoped edit.


## Frozen Packaging and boundary diagnostics

The [follow-up protocol](../docs/research-loop.md) records controls, expected outcomes, and the order of the runs. The frozen note and failing reproduction live in [the fixtures directory](../evals/fixtures/packaging). The oracle checkout contains the upstream fix and is used only for grading controls.

```sh
.venv/bin/python -m evals.frozen --dry-run --output /tmp/frozen-dry.json
.venv/bin/python -m evals.opencode_boundary --output /tmp/opencode-boundaries.json
.venv/bin/python -m evals.git_publication --output /tmp/git-publication.json
```

[The scripted OpenCode receipt](opencode-boundaries.json) reports the edit match outcomes and compaction request sequence under controlled provider responses. [The Git publication receipt](git-publication.json) records three separate bare-repository trials. The Git experiment uses the local Git executable and does not contact GitHub.

[The frozen Packaging receipt](packaging-frozen.json) holds the four repeated live arms and their controls. All four use the same snapshot fingerprint. The Qwen3 4B base and bounded model digests match the values in the reproduction instructions above. Ollama was version 0.40.6 and OpenCode was 2.1.2.

[The historical diagnosis](opencode-historical-compaction.json) and [the frozen session audit](packaging-compaction-events.json) are sanitized projections of OpenCode's local SQLite session records via a read-only connection. The historical query selected one Packaging replacement worktree and matched the preceding assistant output counts to the earlier receipt. The frozen query selected the four attempt worktrees within the matrix window. Only event types, timestamps, status, error categories, and token counts are retained.

[The default OpenCode provider trace](packaging-provider-trace.json) records HTTP status, request timing, finish reason, and token usage for one repeated Packaging run. [The Codex comparison](codex-local-provider.json) includes its same-model Responses smoke and exploratory trial on the same Packaging checkpoint. Tool schemas, prompts, and completion semantics can differ between the two HTTP endpoints.

```sh
.venv/bin/python -m evals.frozen --model continuity-local/continuity-qwen3:4b \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/packaging-frozen.json

.venv/bin/python -m evals.frozen --trace-single-auto --model continuity-local/continuity-qwen3:4b \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/packaging-trace.json

.venv/bin/python -m evals.codex_local --model continuity-qwen3:4b \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/packaging-codex.json
```

[The scripted title probe](opencode-title-probe.json) verifies that an explicit title suppresses the auxiliary request on OpenCode 2.1.2. [The fixed-title live trace](packaging-fixed-title.json) records the same option against the frozen Packaging task.

```sh
.venv/bin/python -m evals.opencode_boundary --title-probe --output /tmp/opencode-title.json

.venv/bin/python -m evals.frozen --trace-single-auto --fixed-title \
  --model continuity-local/continuity-qwen3:4b --endpoint http://127.0.0.1:11434/v1 \
  --output /tmp/packaging-fixed-title.json
```


## Round 2 follow-up

[The round 2 prompts and hypotheses](../docs/research-loop.md) record controls and research decisions. The [delayed-publication receipt](delayed-publication.json) covers three trials for each receiver condition. The [receiver-first receipt](receiver-first-activation.json) covers three trials after interruption between receiver and local activation. The [handoff timing rehearsal](handoff-timing-rehearsal.json) contains scripted timings and no human observations.

```sh
.venv/bin/python -m evals.delayed_publication --output /tmp/delayed-publication.json
.venv/bin/python -m evals.delayed_publication --receiver-first --output /tmp/receiver-first.json
.venv/bin/python -m evals.handoff_timing --output /tmp/handoff-timing.json
```


[The transactional receiver restart receipt](receiver-restart.json) measures independent database readback immediately after death and after reconciliation. The receiver shares one SQLite transaction between the simulated effect and its receipt.

```sh
.venv/bin/python -m evals.receiver_restart --output /tmp/receiver-restart.json
```


[The reasoning matrix](packaging-reasoning-matrix.json) repeats four arms on one checkpoint. [The provider's advertised capabilities and model digests](reasoning-provider-metadata.json) and [initial arithmetic smoke](reasoning-smoke.json) identify the tested Ollama configuration. The request setting and the response channel counters are separate fields.

```sh
.venv/bin/python -m evals.frozen --reasoning-matrix \
  --model continuity-local/continuity-qwen3:4b --endpoint http://127.0.0.1:11434/v1 \
  --output /tmp/reasoning-matrix.json
.venv/bin/python -m evals.reasoning_smoke --endpoint http://127.0.0.1:11434/v1 \
  --output /tmp/reasoning-channel-check.json
```


[The follow-up arithmetic channel check](reasoning-channel-check.json) tests for exact output and literal think tags. [The bounded 4B receiver receipt](packaging-bounded-receiver.json) includes the splicer controls and the failed candidate.

```sh
.venv/bin/python -m evals.bounded_receiver --dry-run --output /tmp/bounded-controls.json
.venv/bin/python -m evals.bounded_receiver --endpoint http://127.0.0.1:11434/v1 \
  --output /tmp/bounded-4b.json
```


[The coding-model digests](coder-model-digests.json) identify the second local alias. [The bounded 7B trial](packaging-bounded-coder.json) applied a function that failed both change checks. [The adaptive trial](packaging-bounded-feedback.json) stopped at the guard before the feedback call. [The seeded trial](packaging-bounded-seeded-feedback.json) supplied a concrete failing input to the original helper. [The scripted control](packaging-feedback-scripted.json) returned the unchanged and upstream-equivalent functions in sequence and verifies the same feedback and grading path.

```sh
ollama pull qwen2.5-coder:7b
printf '%s\n' 'FROM qwen2.5-coder:7b' 'PARAMETER num_ctx 16384' \
  'PARAMETER num_predict 1500' > /tmp/continuity-coder-modelfile
ollama create continuity-coder:7b -f /tmp/continuity-coder-modelfile

.venv/bin/python -m evals.bounded_receiver --model continuity-coder:7b \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/bounded-coder.json
.venv/bin/python -m evals.bounded_receiver --feedback-once --model continuity-coder:7b \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/bounded-feedback.json
.venv/bin/python -m evals.bounded_receiver --seed-base-feedback --model continuity-coder:7b \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/bounded-seeded.json
```


## Round 3 contracts, oracle expansion, and durable activation

[The first contract matrix](packaging-body-contract.json) compared whole functions and bodies using one JSON schema and a shared checkpoint. [The expanded comparison](packaging-body-oracle.json) added a 1,111-input oracle on the same pinned upstream task. [The exact-request repeat](packaging-body-repeat.json) records the seed forwarded by the relay and the hashes of three independent responses.

[The original activation fixture](durable-activation.json) covered five interruption points. [The final activation fixture](prepared-activation.json) added death after worktree creation. Its 18 trials include separate durable coordinator, local authority, and receiver stores. The receiver administration credential stays within the fixture.

```sh
.venv/bin/python -m evals.body_contract --dry-run --output /tmp/contract-controls.json
.venv/bin/python -m evals.body_contract --endpoint http://127.0.0.1:11434/v1 \
  --output /tmp/contracts.json
.venv/bin/python -m evals.body_contract --expanded --endpoint http://127.0.0.1:11434/v1 \
  --output /tmp/contracts-expanded.json
.venv/bin/python -m evals.body_contract --expanded --repeat-seed 32 \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/contracts-repeat.json
.venv/bin/python -m evals.durable_activation --output /tmp/durable-activation.json
```


[The counterexample trial](packaging-body-refinement.json) supplied the first expanded-oracle disagreement to the candidate. [The normalization trial](packaging-wrapper-refinement.json) received the same response and applied it through the whole-function guard. The source hash identifies the resulting edit as identical to the earlier candidate.

```sh
.venv/bin/python -m evals.body_contract --refine --endpoint http://127.0.0.1:11434/v1 \
  --output /tmp/refine.json
.venv/bin/python -m evals.body_contract --refine --normalize-wrapper \
  --endpoint http://127.0.0.1:11434/v1 --output /tmp/refine-wrapper.json
```

## Round 4 authenticated recovery

[Authenticated recovery receipts](authenticated-recovery.json) contain the six credential controls, 18 authenticated crash trials, and three interrupted checkout cases from Click, Packaging, and attrs. Positive publication requests record actual HTTP statuses and compare the returned receipt body. The restore cases report tracked and selected note hashes independently and run the source predicate before and after recovery. The JSON records the four source hashes at [the experiment implementation](https://github.com/archit15singh/agent-task-continuity/commit/f5bdc06).

```sh
.venv/bin/python -m evals.authenticated_recovery --output /tmp/continuity-authenticated-recovery.json
```

The worker and coordinator credentials are generated per trial and omitted from the receipt. The effect is a SQLite row in a cooperating loopback service. The checkout fault applies the tracked part of a multi-file patch and stops the coordinator before the selected note is applied.
