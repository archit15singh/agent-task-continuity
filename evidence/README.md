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
