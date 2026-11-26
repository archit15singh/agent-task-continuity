"""Rehearse restart timing and verification gates without a human participant."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from time import monotonic_ns

from continuity.workspace import git
from .run import CASES, NOTE, check_argv, download, execute, invoke, sha


def rehearsal(case, temp, order):
    temp.mkdir()
    source = download(case, temp / "source", reference=True)
    expected = git(
        source, "diff", "--binary", "--full-index", case["base"], case["reference"], "--", case["source"],
    )
    git(source, "apply", "--binary", "-", data=expected)
    note = f"Resume {case['id']}. Run the independent behavior check against the restored file.\n".encode()
    (source / NOTE).write_bytes(note)
    records = []
    for name in (*order, "clean_control"):
        db = temp / "ledger.db"
        destination = temp / name
        capture_start = monotonic_ns()
        if name == "managed":
            task = invoke(db, "start", source, "--objective", f"Verify the {case['id']} candidate")
            invoke(db, "checkpoint", task["task"], "--include", NOTE, "--note", note.decode().strip(),
                   owner=task["token"])
        elif name == "manual":
            patch = git(source, "diff", "--binary", "--full-index", "HEAD", "--", case["source"])
            exported_note = (source / NOTE).read_bytes()
        restart = monotonic_ns()
        if name == "managed":
            invoke(db, "continue", task["task"], "--into", destination, owner=task["token"])
        else:
            git(source, "worktree", "add", "--quiet", "--detach", str(destination), case["base"])
            if name == "manual":
                git(destination, "apply", "--binary", "-", data=patch)
                (destination / NOTE).write_bytes(exported_note)
        ready = monotonic_ns()
        result = execute(check_argv(case), cwd=destination)
        checked = monotonic_ns()
        actual = git(destination, "diff", "--binary", "--full-index", "HEAD", "--", case["source"])
        note_path = destination / NOTE
        restored = actual == expected and note_path.is_file() and note_path.read_bytes() == note
        verified = restored and result.returncode == 0
        records.append({
            "arm": name,
            "capture_ns": restart - capture_start,
            "restart_to_workspace_ns": ready - restart,
            "workspace_to_predicate_ns": checked - ready,
            "restart_to_first_verified_action_ns": checked - restart if verified else None,
            "predicate_exit": result.returncode,
            "restored": restored,
            "operator_active_ns": None,
        })
    return {"case": case["id"], "base": case["base"], "trials": records}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    with tempfile.TemporaryDirectory(prefix="continuity-handoff-timing-") as directory:
        reports = [
            rehearsal(case, Path(directory) / case["id"],
                      ("manual", "managed") if index % 2 == 0 else ("managed", "manual"))
            for index, case in enumerate(CASES)
        ]
    args.output.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
        "source": "scripted_rehearsal",
        "cases": reports,
    }, indent=2) + "\n")
    for case in reports:
        for arm in case["trials"]:
            negative = arm["arm"] == "clean_control"
            assert arm["predicate_exit"] == (1 if negative else 0), arm
            assert arm["restored"] == (not negative), arm
            assert (arm["restart_to_first_verified_action_ns"] is None) == negative, arm


if __name__ == "__main__":
    main()
