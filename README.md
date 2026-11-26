# Agent Task Continuity

Move an unfinished Git-backed task between coding agents. Restore the selected workspace, pass a concise brief, and transfer authority at the boundaries that accept checkpoints and publish verified results.

## Why

The artifact should own the history of the work. A conversation helps explain decisions. Git tells the next agent which bytes it has. A task record tells it what remains open, which checks refer to those bytes, and whether an external action already happened.

Use a Git patch and copy the relevant untracked files when an operator can coordinate a planned switch. That baseline matched managed restoration in all three repositories. Add a task ledger and a controlled write path when a worker may die halfway through an action. The managed path reconciled six interrupted publications with one effect each and rejected stale owners on the tested boundaries. In three additional bare-Git trials, independent ref readback confirmed the published SHA after the client was killed. The same-SHA retry made zero additional ref updates and a different SHA was rejected. For a delayed request, the receiver must enforce the current generation at application time. The loopback fixture allowed the old request when its generation lagged and rejected it once the generation advanced. In six separate SQLite receiver crashes, retries converged on one effect and one receipt when both shared a transaction. The combined activation fixture rejected the delayed old generation and converged in 18/18 trials, including recovery after a detached worktree was prepared. [Publication evidence](evidence/delayed-publication.json)

Measure workspace recovery and verified task completion separately. The timeout investigation found a stale `PWD` that sent OpenCode to the wrong checkout. The launcher now aligns it with the restored workspace. Ollama was also serving requests for roughly 177 of 180 seconds during the original Packaging replay.

With the launcher fixed, local Qwen3.5 9B preserved both handoff files in all three cases. It still completed **0/3** at the 180-second deadline. The attrs edit failed the change-specific checks. A separate Codex-to-Codex run completed Click. OpenCode's persisted record shows that the corrected 4B Packaging compaction failure hit the 1,500-token output cap. The frozen Packaging case produced zero verified fixes in two runs per compaction setting. Supplying a title removed one auxiliary request in the traced startup. A same-model Codex probe exited cleanly and also left the source unchanged. In the next round, a coding-tuned model returned a scoped edit that passed 238 native tests and failed both task-specific checks. A later body-only edit passed the initial checks and disagreed with upstream on 123 of 1,111 expanded inputs. Qualify a replacement with an independent behavior check before using it for unattended recovery. [Paper](docs/paper.md) · [Evidence](evidence/README.md)

## Start and hand off a task

Requires Python 3.11+, Git, and a Unix-like host. A runtime CLI is required only for automatic launch. Run these commands from the study checkout or install the package with `python -m pip install -e .`.

```sh
export CONTINUITY_DB="$HOME/.continuity/tasks.sqlite"
python -m continuity start /absolute/path/to/repo \
  --objective "Implement and verify the requested change"
```

Keep the returned task ID, owner token, and operator recovery key private. Set `TASK` to the ID and `CONTINUITY_OWNER` to the token. Save the checkpoint when concurrent edits have settled.

```sh
python -m continuity checkpoint "$TASK" --include notes.md \
  --note "Implementation is in place. Run the targeted test and inspect edge cases."
python -m continuity inspect "$TASK"
python -m continuity manifest "$TASK"

python -m continuity continue "$TASK" --into /absolute/path/to/replacement
```

Add `--constraint`, `--decision`, `--next`, and `--acceptance` to record structured context. The versioned manifest can include an optional Git patch via `--with-patch`. Review the patch and notes before sharing them.

An omitted `--include` captures tracked changes only. Use one flag per selected untracked file. The continuation command returns a new owner token and the brief. Set `CONTINUITY_OWNER` to the new token for subsequent commands. For automatic launch, add `--runtime codex` or `--runtime opencode --model PROVIDER/MODEL`. Use `--log /path/to/new-log` to keep child output. Launch failure still returns the transferred task and new token.

```sh
python -m continuity checkpoint "$TASK" --include notes.md \
  --note "Candidate ready for verification"
python -m continuity verify "$TASK" --command 'python -m pytest tests/test_feature.py'
```

Use an absolute verifier path where the tool or virtual environment lives outside the snapshot. Verification runs against a disposable copy of the checkpoint. The returned evidence includes the snapshot fingerprint, exit status, output hash, and basic host details.

## Recover a worker or reconcile a write

- `supervise` runs a bounded initial command and automatically transfers to one replacement after an abnormal exit or timeout. Use `--first 'COMMAND'`, `--replacement 'COMMAND'`, and `--into /path/to/fresh-worktree`. Checkpoint first. The replacement receives `CONTINUITY_PROMPT`; trusted integration commands also receive task and owner variables.
- `recover-owner` restores the last checkpoint into another worktree if the current owner token was lost. It requires the separately retained `CONTINUITY_RECOVERY_KEY`.
- To exercise managed publication, start `python -m evals.publisher --drop-first` in another terminal. Use the returned endpoint and passing evidence ID with `publish "$TASK" --endpoint URL --name candidate --evidence EVIDENCE_ID`. If the first result is unknown, use `operations "$TASK"` and `reconcile "$TASK" OPERATION_ID`. Add `--retry-absent` only when the provider honors stable operation IDs.

The gateway publishes a snapshot descriptor to a loopback HTTP endpoint. The fixture implements lookup and idempotent writes for that descriptor. The local trust boundary is SQLite and the controlled CLI. Use ordinary OS permissions to protect the database and tokens. The guarantees cover writes through the managed path, selected file contents under Git semantics, and changes durable at the last checkpoint. Runner and dependency setup, ignored files, staged-vs-unstaged state, and processes in other sessions require separate handling.

## Reproduce the study

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r evals/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m evals.run --set all --output /tmp/continuity-study.json
```

See the [implementation plan](docs/plan.md), [preregistered protocol](docs/protocol.md), [research paper](docs/paper.md), [PDF](docs/paper.pdf), the [follow-up protocol](docs/research-loop.md), the [literature review](docs/handoff-literature-review.md), and [machine-readable evidence](evidence/README.md). The pinned cases use Click, Packaging, and attrs. The native tests and application code run locally. Study publication targets a controlled loopback service and a separate disposable bare Git receiver.
