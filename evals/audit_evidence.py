"""Verify selected paper results and provenance from public receipts without model calls."""

import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise SystemExit(f"Evidence check failed: {message}")


def read(name):
    return json.loads((ROOT / "evidence" / f"{name}.json").read_text())


def audit_design():
    cases = read("mechanical-final")["cases"]
    for arm, expected in (("brief-only", 0), ("manual-git", 3), ("managed", 3)):
        passed = sum(all(row["arms"][arm][gate] for gate in (
            "tracked_matches", "selected_untracked_matches", "source_predicate_passes",
        )) for row in cases)
        require((passed, len(cases)) == (expected, 3), f"transport {arm}")
    require(sum(sum(case["faults"].values()) for case in cases) == 39, "original fault predicates")
    for case in cases:
        kill = case["publication_client_killed"]
        require(case["provider"]["effects"] == kill["effects"] == 1
                and kill["replacement_confirmed"], "client-side publication recovery")
    for files, expected in (
        (("live-development", "live-held-out"), (0, 3)),
        (("opencode-9b-rerun",), (0, 3)),
        (("live-same-runtime",), (1, 1)),
    ):
        rows = [row for file in files for row in read(file)["cases"]]
        require((sum(row["grade"]["task_completed"] for row in rows), len(rows)) == expected, str(files))
        require(all(row["grade"]["restored_note"] and row["grade"]["restored_repro"] for row in rows),
                f"restored handoff files in {files}")


def audit_recovery():
    rows = read("git-publication")["trials"]
    require(len(rows) == 3 and all(row["only_update_was_expected_creation"]
                                   and row["ref_still_matches_candidate"] for row in rows), "Git publication")
    rows = read("receiver-restart")["trials"]
    require(len(rows) == 6 and all(row["effects_and_receipts_after_recovery"] == [1, 1]
                                   and row["replacement_status"] == "confirmed" for row in rows),
            "receiver restart")
    for label, rows in (
        ("prepared", read("prepared-activation")["trials"]),
        ("authenticated", read("authenticated-recovery")["fault_trials"]),
    ):
        require(len(rows) == 18 and all(row["final_effects_and_receipts"] == [1, 1]
                                         and row["final_status"] == "confirmed"
                                         and row["delayed_old_generation_http"] == 412 for row in rows),
                f"{label} activation")
    rows = read("authenticated-recovery")["restore_trials"]
    require(len(rows) == 3 and all(row["saved_and_restored_digests_match"] and row["prior_checkout_preserved"]
                                   for row in rows), "partial checkout retry")
    rows = read("git-restore-crash")["trials"]
    require(len(rows) == 3 and all(row["git_exit"] == -9 and row["partial_rejected"]
                                   and row["recovered_generation"] == 2 for row in rows), "native Git crash")


def audit_grading():
    oracle = {row["contract"]: row["expanded_oracle"] for row in read("packaging-body-oracle")["trials"]
              if row["candidate_applied"]}
    require(oracle == {"whole": {"examples": 1111, "mismatches": 279},
                       "body": {"examples": 1111, "mismatches": 123}}, "expanded Packaging oracle")
    pairs = list(read("paired-continuation")["attempts"].values())
    require(len(pairs) == 3 and all(len(pair) == 2 for pair in pairs), "paired denominator")
    workers = [row for pair in pairs for row in pair]
    require(all(row["restored_before_launch"] and all(row["grade"]["artifact_preserved"].values())
                and not row["grade"]["verified"] for row in workers), "paired worker results")
    require(sum(row["worker"]["timed_out"] for row in workers) == 3, "paired timeout count")
    for pair in pairs:
        require(all(pair[0][key] == pair[1][key] for key in ("checkpoint_sha256", "prompt_sha256")),
                "matched inputs")
    negative = read("paired-oracle-controls")["cases"]
    require(len(negative) == 3 and all(row["visible"]["exit"] == 0 and row["hidden_disagreements"]
                                       and all(test["exit"] == 0 for test in row["native"].values())
                                       for row in negative), "partial repair controls")
    positive = read("paired-alternate-controls")["cases"]
    require(len(positive) == 3 and sum(row["hidden_count"] for row in positive) == 247
            and all(row["reference_hidden_sha256"] == row["alternate_hidden_sha256"] for row in positive),
            "equivalent implementation controls")
    for file in ("paired-reasoning-control", "paired-reasoning-repeat"):
        rows = read(file)["trials"]
        require(len(rows) == 6 and all(row["off_requested"] == row["exact_answer"] for row in rows),
                f"endpoint qualification in {file}")
    for file in ("paired-click-reasoning-off", "paired-codex-click-reasoning-off"):
        result = read(file)
        attempt = result["attempt"]
        default = next(row for row in pairs[0] if row["runtime"] == attempt["runtime"])
        require(result["qualified"] and attempt["worker"]["exit_code"] == 0 and not attempt["grade"]["verified"]
                and all(attempt[key] == default[key] for key in ("checkpoint_sha256", "prompt_sha256"))
                and all(row["reasoning_effort"] == "none" for row in attempt["provider_requests"]), file)


def audit_round_six():
    capped = read("capped-reads")["attempts"]
    require([row["read_limit"] for row in capped] == [None, 4096, 4096, None], "read cap ordering")
    require(not any(row["grade"]["verified"] for row in capped), "read cap outcomes")
    require(all(len({row[key] for row in capped}) == 1 for key in ("checkpoint_sha256", "prompt_sha256")),
            "matched inputs for capped reads")
    baseline = read("paired-continuation")["attempts"]
    for file in ("receiver-qualification", "receiver-qualification-repeat"):
        attempts = read(file)["attempts"]
        require(len(attempts) == 3 and all(row["grade"]["verified"] for row in attempts), file)
        for row in attempts:
            original = baseline[row["case"]][0]
            require(all(original[key] == row[key] for key in ("checkpoint_sha256", "prompt_sha256")),
                    f"{file}: {row['case']} changed inputs")
    hosted_git = read("hosted-git")
    require(len(hosted_git["trials"]) == 3 and all(
        row["final_independent_readback"] == hosted_git["base_revision"] and row["removed_with_matching_lease"]
        and row["different_target_rejected_as_stale"] and row["same_target_up_to_date"]
        for row in hosted_git["trials"]), "hosted Git recovery")
    hosted = read("hosted-receiver")
    require(len(hosted["trials"]) == 9 and all(
        row["retired_bearer_current_generation_http"] == 403 and row["delayed_old_generation_http"] == 412
        and row["final_effects_and_receipts"] == [1, 1] and row["final_status"] == "confirmed"
        for row in hosted["trials"]), "hosted authenticated receiver")
    replay = read("scoped-click-replay")
    require(replay["upstream_edit_guard_control"] and replay["attempts"][1]["grade"]["hidden_disagreements"] == 4,
            "scoped Click replay")
    require(replay["attempts"][0]["output_sha256"] == read("scoped-click")["attempts"][0]["output_sha256"],
            "exact scoped model replay")
    for name in ("operator-pilot-rehearsal", "operator-pilot-reversed"):
        report = read(name)
        observations = report["observations"]
        require(report["mode"] == "scripted rehearsal" and len(observations) == 2
                and all(row["verified"] and row["operator_active_seconds_self_reported"] is None
                        for row in observations), name)


def audit_provenance():
    for receipt, revision in (
        ("authenticated-recovery", "f5bdc06"), ("paired-continuation", "d630a70"),
        ("capped-reads", "3026d2c"),
    ):
        for path, expected in read(receipt)["source_sha256"].items():
            source = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
            require(hashlib.sha256(source).hexdigest() == expected, f"{receipt}: {path}")
    for receipt, revision, module, key in (
        ("git-restore-crash", "7e7a054", "git_restore_crash", "source_sha256"),
        ("paired-oracle-controls", "543863f", "paired_oracle_controls", "source_sha256"),
        ("paired-alternate-controls", "c7d68ca", "paired_alternate_controls", "source_sha256"),
        ("paired-tool-control", "23551ee", "paired_tool_control", "source_sha256"),
        ("paired-reasoning-control", "2047533", "paired_reasoning_control", "runner_sha256"),
        ("paired-click-reasoning-off", "2047533", "paired_reasoning_control", "runner_sha256"),
        ("paired-reasoning-repeat", "f87f7c2", "paired_reasoning_control", "runner_sha256"),
        ("paired-codex-click-reasoning-off", "f87f7c2", "paired_reasoning_control", "runner_sha256"),
        ("hosted-git", "24daa95", "hosted_git", "source_sha256"),
        ("hosted-receiver", "a40b28e", "hosted_receiver", "runner_sha256"),
        ("operator-pilot-rehearsal", "d5561e1", "operator_pilot", "source_sha256"),
        ("operator-pilot-reversed", "d5561e1", "operator_pilot", "source_sha256"),
        ("receiver-qualification", "f2c178c", "receiver_qualification", "source_sha256"),
        ("receiver-qualification-repeat", "f2c178c", "receiver_qualification", "source_sha256"),
        ("scoped-click", "a65c445", "scoped_click", "source_sha256"),
        ("scoped-click-replay", "fdc4758", "scoped_click", "source_sha256"),
    ):
        source = subprocess.check_output(["git", "show", f"{revision}:evals/{module}.py"], cwd=ROOT)
        require(hashlib.sha256(source).hexdigest() == read(receipt)[key], f"{receipt}: {module}")
    for path in (ROOT / "evidence").glob("*.json"):
        json.loads(path.read_text())
    for file in ("README.md", "docs/paper.md", "docs/reporting-audit.md", "evidence/README.md"):
        doc = ROOT / file
        for target in re.findall(r"\]\(([^ )]+)\)", doc.read_text()):
            local = target.split("#", 1)[0]
            if local and "://" not in local:
                require((doc.parent / local).exists(), f"{file}: {target}")
    paper = (ROOT / "docs/paper.md").read_text()
    appendix = paper.split("## Appendix A.", 1)[1]
    hypothesis_ids = re.findall(r"^\| H(\d+) ·", appendix, re.MULTILINE)
    require(hypothesis_ids == [str(number) for number in range(1, 34)], "appendix coverage for H1–H33")
    rows = [line for line in appendix.splitlines() if re.match(r"^\| (?:H\d+|RQ\d+) ·", line)]
    require(all("../evidence/" in row for row in rows), "appendix receipt links")


if __name__ == "__main__":
    audit_design()
    audit_recovery()
    audit_grading()
    audit_round_six()
    audit_provenance()
    print("Verified headline receipt checks, source provenance, links and H1–H33 coverage.")
