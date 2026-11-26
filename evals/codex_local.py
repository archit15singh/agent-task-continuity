"""Qualify a Codex replacement against the same local model used by OpenCode."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from continuity.runner import run, runtime_command
from continuity.workspace import git
from .frozen import CASE, FIXTURE, grade
from .live import NOTE, REPRO, read_summary, replacement_objective
from .provider_trace import trace_provider
from .run import download, execute, invoke, sha


def probe(workspace, home, endpoint, model, prompt, timeout):
    log = home.parent / (workspace.name + ".jsonl")
    with trace_provider(endpoint) as (relay, provider_requests):
        command = runtime_command("codex", prompt, model)
        command[-1:-1] = [
            "-c", 'model_provider="continuity_local"',
            "-c", 'model_providers.continuity_local.name="Continuity local Ollama"',
            "-c", f'model_providers.continuity_local.base_url="{relay}"',
            "-c", 'model_providers.continuity_local.wire_api="responses"',
            "-c", "model_providers.continuity_local.requires_openai_auth=false",
            "-c", "model_providers.continuity_local.supports_websockets=false",
            "-c", "model_context_window=16384",
            "-c", 'web_search="disabled"',
        ]
        worker = run(
            command, workspace, seconds=timeout, log=log,
            environment={"CODEX_HOME": str(home), "PATH": os.environ["PATH"]},
        )
    worker.update(read_summary(log))
    output = log.read_text(errors="replace")
    messages = []
    for line in output.splitlines():
        if line.startswith('{"type":"item.completed"'):
            item = json.loads(line).get("item", {})
            if item.get("type") == "agent_message":
                messages.append(item.get("text", "").strip().rstrip(".").lower())
    return {
        "worker": worker, "provider_requests": provider_requests,
        "ready_text_present": "local fixture ready" in messages,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--endpoint", required=True)
    cli.add_argument("--model", required=True)
    args = cli.parse_args()
    report = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_code_sha256": sha(Path(__file__).read_bytes()),
        "codex": execute(["codex", "--version"]).stdout.decode().strip(),
        "model": args.model,
    }
    with tempfile.TemporaryDirectory(prefix="continuity-codex-local-") as directory:
        temp = Path(directory).resolve()
        workspace, home = temp / "smoke", temp / "codex-home"
        workspace.mkdir()
        home.mkdir()
        git(workspace, "init", "-q")
        report["smoke"] = probe(
            workspace, home, args.endpoint, args.model,
            "/no_think\nReply with exactly: local fixture ready. Do not call tools.", 90,
        )
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        smoke = report["smoke"]
        if smoke["worker"]["exit_code"] or not smoke["ready_text_present"] or not smoke["provider_requests"]:
            return
        source = download(CASE, temp / "source", reference=False)
        for name in (NOTE, REPRO):
            (source / name).write_bytes((FIXTURE / name).read_bytes())
        db = temp / "ledger.db"
        task = invoke(db, "start", source, "--objective", replacement_objective(CASE, True))
        checkpoint = invoke(
            db, "checkpoint", task["task"], "--include", NOTE, "--include", REPRO, "--note",
            (FIXTURE / NOTE).read_text().strip(), owner=task["token"],
        )
        destination = temp / "replacement"
        handoff = invoke(db, "continue", task["task"], "--into", destination, owner=task["token"])
        result = probe(destination, home, args.endpoint, args.model, handoff["prompt"], 180)
        result["grade"] = grade(destination)
        result["grade"]["complete"] = (
            result["worker"]["exit_code"] == 0 and result["grade"]["files_restored"]
            and result["grade"]["changed_files"] == sorted([CASE["source"], NOTE, REPRO])
            and all(result["grade"][key] == 0 for key in ("predicate_exit", "repro_exit", "native_exit"))
        )
        report["packaging"] = {"base": CASE["base"], "checkpoint_sha256": checkpoint["digest"], **result}
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
