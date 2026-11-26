# Using Worktree Ledger

## Start and hand off a task

Requires Python 3.11+, Git, and a Unix-like host. A runtime CLI is required only for automatic launch. Run the commands using the virtual environment from the [README quickstart](../README.md#quickstart).

```sh
export CONTINUITY_DB="$HOME/.continuity/tasks.sqlite"
python -m continuity start /absolute/path/to/repo \
  --objective "Implement and verify the requested change"
```

Store the returned owner token and operator recovery key privately. Set `TASK` to the ID and `CONTINUITY_OWNER` to the token. Save the checkpoint when concurrent edits have settled.

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
