"""Run the authenticated fixture across an isolated Docker service boundary."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

from .durable_activation import ACTIVATION_ENV, AUTH_ENV, trial
from .run import PROJECT, sha


IMAGE = "python:3.13-slim"


def docker(*args, env=None, timeout=35):
    return subprocess.check_output(["docker", *args], env=env, text=True, timeout=timeout).strip()


class Container:
    def __init__(self, identifier):
        self.identifier = identifier

    def wait(self, timeout):
        return int(docker("wait", self.identifier, timeout=timeout))


@contextmanager
def docker_receiver(database, port, fault, *, module, env):
    fixture_env = {**os.environ, ACTIVATION_ENV: env[ACTIVATION_ENV], AUTH_ENV: env[AUTH_ENV]}
    container = docker(
        "run", "--detach", "--env", ACTIVATION_ENV, "--env", AUTH_ENV,
        "--publish", f"127.0.0.1:{port or ''}:8080",
        "--volume", f"{PROJECT}:/study:ro",
        "--volume", f"{database.parent}:/receiver",
        "--workdir", "/study", IMAGE,
        "python", "-m", module, "--worker", f"/receiver/{database.name}",
        "--bind", "0.0.0.0", "--port", "8080", "--fault", fault, env=fixture_env,
    )
    try:
        bound_port = int(docker("port", container, "8080/tcp").rsplit(":", 1)[1])
        deadline = time.monotonic() + 10
        while True:
            try:
                with socket.create_connection(("127.0.0.1", bound_port), timeout=0.3):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Receiver failed to bind: " + docker("logs", container))
                time.sleep(0.1)
        yield Container(container), bound_port
    finally:
        docker("rm", "--force", container)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    docker("pull", IMAGE, timeout=120)
    metadata = json.loads(docker("image", "inspect", IMAGE))[0]
    report = {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "hosted_workflow_revision": os.environ.get("GITHUB_SHA"),
              "hosted_run_id": os.environ.get("GITHUB_RUN_ID"),
              "container_image_id": metadata["Id"], "container_image_digests": metadata["RepoDigests"],
              "runner_sha256": sha(Path(__file__).read_bytes()), "trials": []}
    with tempfile.TemporaryDirectory(prefix="continuity-hosted-receiver-") as directory:
        root = Path(directory)
        for index, stage in enumerate(("receiver", "before", "after") * 3):
            row = trial(root / str(index), stage, authenticated=True, receiver_factory=docker_receiver)
            report["trials"].append(row)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            assert row["invalid_activation_http"] == 403 and row["delayed_old_generation_http"] == 412
            assert row["retired_bearer_current_generation_http"] == 403
            assert row["coordinator_exit"] == (32 if stage == "receiver" else 0)
            assert row["effect_receiver_exit"] == {"before": 22, "after": 23}.get(stage)
            assert row["effects_and_receipts_after_first_publish"] == ([0, 0] if stage == "before" else [1, 1])
            assert row["final_status"] == "confirmed" and row["final_effects_and_receipts"] == [1, 1]
            print(f"Hosted receiver trial {index + 1}/9 passed", flush=True)


if __name__ == "__main__":
    main()
