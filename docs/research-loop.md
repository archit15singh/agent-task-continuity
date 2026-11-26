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
