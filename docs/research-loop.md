# Agent continuity follow-up

## Goal prompt

Find out which failure boundaries prevent a replacement agent from finishing work on a recovered checkout. Use the public pinned Packaging case, hold the handoff fixed, run the existing independent graders, and preserve receipts for every attempted arm. Use small controlled fixtures to isolate compaction and edit application. Update the paper and README only where the evidence changes the conclusion.

## Loop prompt

Read the latest receipts. Choose the cheapest experiment that distinguishes the strongest remaining explanations. Pin inputs and state the expected observation before running it. Run a negative control, then the experiment. Record failures, versions, timings, scope, and what the result cannot establish. Continue while the next experiment can resolve a material uncertainty within the authorized scope. Stop identical retries after a deterministic error.

## Frozen diagnostic protocol

- Use the existing pinned Packaging parent and graders. The two inputs in `evals/fixtures/packaging` are study-authored replacements for the ephemeral historical Codex inputs. The original run recorded hashes only. Grade the frozen reproduction and independent predicate on the clean parent and upstream positive reference before launching agents. Give the agents only the pinned parent and frozen handoff.
- Repeat the OpenCode reference and OpenCode with auto compaction disabled twice each, alternating arms, with the same local Qwen3 4B alias and 180-second worker deadline. Keep native tests, restored files, scope, independent predicate, carried repro, and worker exit separate. Stop early on a deterministic setup failure. This is a diagnostic case with no held-out inference.
- After the reference preflight, probe Codex with the same local model if its API can run it. Treat a transport mismatch as a setup result. A successful comparison would still vary harness prompts, tools, and protocol.
- Use scripted tool calls for Click, varying only exact `oldString` matching. For compaction, use a synthetic provider to vary the reported context usage and response completion. Scripted outcomes establish behavior at the boundaries under controlled input.
