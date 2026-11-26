"""Prepare a paired recovery exercise and measure separate phases on one host."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from time import monotonic_ns

from continuity.workspace import git
from .run import CASES, NOTE, check_argv, download, execute, invoke, sha


ARMS = ("manual", "managed")
PHASES = ("start", "captured", "restored", "finish")
LIMIT_SECONDS = 240
SELECTED_CASES = (CASES[0], CASES[1])


def prepare(root, sequence, *, rehearsal=False):
    root.mkdir()
    order = ARMS if sequence % 2 == 0 else ARMS[::-1]
    cases = SELECTED_CASES if sequence < 2 else SELECTED_CASES[::-1]
    tasks = {}
    for arm, case in zip(order, cases, strict=True):
        source = download(case, root / arm, reference=True)
        patch = git(source, "diff", "--binary", case["base"], case["reference"], "--", case["source"])
        git(source, "apply", "--binary", "-", data=patch)
        source_bytes = (source / case["source"]).read_bytes()
        (source / NOTE).write_text("Checkpoint contains the candidate implementation. Restore the source and this note, then run the independent check.\n")
        tasks[arm] = {"case": case["id"], "source_sha256": sha(source_bytes),
                      "note_sha256": sha((source / NOTE).read_bytes()), "phases": {}}
    state = {"mode": "scripted rehearsal" if rehearsal else "human pilot", "sequence": sequence,
             "order": order, "tasks": tasks}
    save(root, state)
    return state


def save(root, state):
    pending = root / "study.tmp"
    pending.write_text(json.dumps(state, indent=2) + "\n")
    pending.replace(root / "study.json")


def mark(root, arm, phase):
    state = json.loads((root / "study.json").read_text())
    tasks = state["tasks"]
    phases = tasks[arm]["phases"]
    if phases.keys() != set(PHASES[:PHASES.index(phase)]):
        raise SystemExit("Phase missing or already recorded")
    if arm == state["order"][1] and "finish" not in tasks[state["order"][0]]["phases"]:
        raise SystemExit("Finish the first arm before starting the second")
    phases[phase] = monotonic_ns()
    if phase == "finish":
        case = next(case for case in SELECTED_CASES if case["id"] == tasks[arm]["case"])
        replacement = root / f"{arm}-restored"
        candidate, note = replacement / case["source"], replacement / NOTE
        restored = (candidate.is_file() and note.is_file() and sha(candidate.read_bytes()) == tasks[arm]["source_sha256"]
                    and sha(note.read_bytes()) == tasks[arm]["note_sha256"])
        outcome = execute(check_argv(case), cwd=replacement).returncode if restored else None
        tasks[arm]["verified"] = restored and outcome == 0
    save(root, state)
    return state


def receipt(root, output):
    state = json.loads((root / "study.json").read_text())
    observations = []
    for arm in state["order"]:
        task = state["tasks"][arm]
        phases = task["phases"]
        if "finish" not in phases:
            observations.append({"arm": arm, "case": task["case"], "completed": False, "last_phase": next(reversed(phases), None)})
            continue
        total = (phases["finish"] - phases["start"]) / 1e9
        measurements = {f"{a}_to_{b}_seconds": (phases[b] - phases[a]) / 1e9 for a, b in zip(PHASES, PHASES[1:])}
        observations.append({"arm": arm, "case": task["case"], "completed": True,
                             "verified": task["verified"] and total <= LIMIT_SECONDS,
                             "phase_elapsed": measurements, "total_seconds": total,
                             "operator_active_seconds": None})
    output.write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                  "mode": state["mode"], "sequence": state["sequence"],
                                  "limit_seconds": LIMIT_SECONDS, "source_sha256": sha(Path(__file__).read_bytes()),
                                  "observations": observations}, indent=2) + "\n")


def rehearse(root, sequence, output):
    state = prepare(root, sequence, rehearsal=True)
    for arm in state["order"]:
        source = root / arm
        case = next(case for case in SELECTED_CASES if case["id"] == state["tasks"][arm]["case"])
        dest = root / f"{arm}-restored"
        db = root / "task.db"
        mark(root, arm, "start")
        if arm == "manual":
            patch = git(source, "diff", "--binary", "HEAD")
            saved_note = (source / NOTE).read_bytes()
        else:
            task = invoke(db, "start", source, "--objective", "Restore the saved candidate and note")
            invoke(db, "checkpoint", task["task"], "--include", NOTE, "--note", "Restore and verify",
                   owner=task["token"])
        mark(root, arm, "captured")
        if arm == "manual":
            git(source, "worktree", "add", "--detach", str(dest), case["base"])
            git(dest, "apply", "--binary", "-", data=patch)
            (dest / NOTE).write_bytes(saved_note)
        else:
            invoke(db, "continue", task["task"], "--into", dest, owner=task["token"])
        mark(root, arm, "restored")
        assert mark(root, arm, "finish")["tasks"][arm]["verified"]
    receipt(root, output)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("command", choices=("prepare", "mark", "receipt", "rehearse"))
    cli.add_argument("workspace", type=Path)
    cli.add_argument("--sequence", type=int, choices=range(4), default=0)
    cli.add_argument("--arm", choices=ARMS)
    cli.add_argument("--phase", choices=PHASES)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    root = args.workspace.resolve()
    if args.command in ("receipt", "rehearse") and args.output is None:
        cli.error("--output is required")
    if args.command == "prepare":
        state = prepare(root, args.sequence)
        for arm in state["order"]:
            print(arm, state["tasks"][arm]["case"], root / arm)
    elif args.command == "mark":
        if args.arm is None or args.phase is None:
            cli.error("--arm and --phase are required")
        mark(root, args.arm, args.phase)
    elif args.command == "receipt":
        receipt(root, args.output)
    else:
        rehearse(root, args.sequence, args.output)


if __name__ == "__main__":
    main()
