# Worktree Ledger

Checkpoint unfinished coding-agent work and resume it in a fresh Git worktree. The local `continuity` CLI carries the selected files and handoff brief, transfers task ownership, and records which checks passed on the saved snapshot.

[Usage guide](docs/usage.md) · [Research paper](docs/paper.md) · [PDF](docs/paper.pdf) · [Evidence and reproduction](evidence/README.md)

## Why use it?

A transcript can explain a decision. The next worker still needs the exact files, the remaining checks, and a way to tell whether an external write already landed. Worktree Ledger stores the checkpoint in Git terms and keeps task authority, verification, and publication records in SQLite.

For a planned handoff with someone coordinating it, a Git patch and a copy of the selected untracked files may be enough. That baseline restored every case in our comparison. The ledger earns its keep when a worker dies mid-task, a replacement needs to verify the recovered files, or a publication receipt goes missing.

## Quickstart

Requires Python 3.11+, Git, and a Unix-like shell. The demo uses a disposable repository and runs without a model account.

```sh
git clone https://github.com/archit15singh/worktree-ledger.git
cd worktree-ledger
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Create a repository with an unfinished edit, save it, and take over from a fresh worktree.

```sh
demo="$(mktemp -d)"
git init -q "$demo/source"
printf 'draft\n' > "$demo/source/change.txt"
git -C "$demo/source" add change.txt
git -C "$demo/source" -c user.name=Demo -c user.email=demo@example.invalid commit -qm "Start draft"
printf 'ready\n' > "$demo/source/change.txt"
printf 'Verify the updated text.\n' > "$demo/source/notes.md"

export CONTINUITY_DB="$demo/tasks.sqlite"
json_field() {
  .venv/bin/python -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"
}
started="$(.venv/bin/continuity start "$demo/source" --objective "Finish the draft")"
task="$(printf '%s' "$started" | json_field task)"
CONTINUITY_OWNER="$(printf '%s' "$started" | json_field token)"
export CONTINUITY_OWNER
unset started

.venv/bin/continuity checkpoint "$task" --include notes.md \
  --note "Check that change.txt contains ready and that notes.md survived."
resumed="$(.venv/bin/continuity continue "$task" --into "$demo/replacement")"
CONTINUITY_OWNER="$(printf '%s' "$resumed" | json_field token)"
unset resumed
cat "$demo/replacement/change.txt" "$demo/replacement/notes.md"
```

The last command prints `ready` and `Verify the updated text.` The demo sets the new owner token for later checkpoints and verification. The [usage guide](docs/usage.md) covers automatic Codex and OpenCode launch, recovery keys, and reconciliation after a lost publication acknowledgment.

## What we measured

| Question | Observed result |
| --- | --- |
| Did the selected files survive a handoff? | Managed restore and manual Git each passed **3/3** across Click, Packaging, and attrs. A brief alone passed **0/3**. [Transport receipts](evidence/mechanical-final.json) |
| Did recovery handle interrupted writes? | The authenticated receiver fixture converged on one effect and one receipt in **18/18** local fault trials and **9/9** on a hosted VM. A separate GitHub test preserved the intended ref in **3/3** interrupted publications. [Local receiver](evidence/authenticated-recovery.json) · [Hosted receiver](evidence/hosted-receiver.json) · [GitHub refs](evidence/hosted-git.json) |
| Did a replacement finish the change? | On three frozen tasks, a signed-in Codex configuration passed **6/6** attempts, two per task. A local Qwen3 8B configuration verified **0/6** across Codex and OpenCode on the same tasks. The provider and model configurations differed. [Codex qualification](evidence/receiver-qualification.json) · [Repeat](evidence/receiver-qualification-repeat.json) · [Local model](evidence/paired-continuation.json) |

Restore success and task completion are separate outcomes. The research covers selected Git files at the last checkpoint and writes through the managed path with a cooperating receiver. Cross-host failover, real production side effects, and human time savings remain unmeasured. [Hypotheses, methods, and limitations](docs/paper.md)

## Reproduce and cite

From a full Git clone, verify the archived results and run the local tests. Both commands run without model credentials. The [reproduction guide](evidence/README.md#verify-the-artifact) covers rerunning the pinned repository cases and documents the requirements for live and hosted experiments.

```sh
.venv/bin/python -m evals.audit_evidence
.venv/bin/python -m unittest discover -s tests
```

Cite [Recovering Coding-Agent Work Across Runtime Boundaries](docs/paper.md) with the metadata in [CITATION.cff](CITATION.cff). Report reproduction issues with the commit, command, and observed result. [GitHub Issues](https://github.com/archit15singh/worktree-ledger/issues)

Worktree Ledger is a public research prototype. The repository currently has no published license.
