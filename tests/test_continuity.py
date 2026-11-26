import base64
import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import unittest

from continuity.publish import publish, settle
from continuity.runner import run, verify
from continuity.store import Store
from continuity.workspace import ContinuityError, fingerprint, git
from evals.publisher import publisher


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.use = self.enterContext(tempfile.TemporaryDirectory())
        self.directory = Path(self.use)
        self.source = self.directory / "source"
        self.source.mkdir()
        git(self.source, "init", "-q")
        (self.source / "code.py").write_text("x = 1\n")
        git(self.source, "add", "code.py")
        git(self.source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Fixture")
        self.store = Store(self.directory / "ledger.db")
        self.started = self.store.create(self.source, "Preserve the code")
        self.task = self.started["task"]
        self.owner = self.started["token"]

    def checkpoint(self):
        (self.source / "code.py").write_text("x = 2\n")
        (self.source / "binary.dat").write_bytes(b"\0\x81some data\r\n")
        (self.source / "excluded.txt").write_text("excluded")
        return self.store.checkpoint(self.task, self.owner, ["binary.dat"], "Continue verification")

    def test_runner_aligns_pwd_with_the_child_workspace(self):
        result = run(
            [sys.executable, "-c",
             "import os; from pathlib import Path; assert Path(os.environ['PWD']) == Path.cwd()"],
            self.source, seconds=10, environment={"PWD": str(self.directory)},
        )
        self.assertEqual(result["exit_code"], 0)

    def test_isolated_restore_and_stale_detection(self):
        self.checkpoint()
        assert git(self.source, "diff", "--cached") == b""
        dest = self.directory / "new"
        replaced = self.store.takeover(self.task, self.owner, dest)
        assert "Continue verification" in replaced["prompt"]
        assert (dest / "binary.dat").read_bytes() == b"\0\x81some data\r\n"
        assert not (dest / "excluded.txt").exists()
        assert self.store.inspect(self.task)["clean_match"]
        with self.assertRaisesRegex(ContinuityError, "Stale"):
            self.store.checkpoint(self.task, self.owner, [], "")
        (dest / "binary.dat").unlink()
        assert self.store.inspect(self.task)["missing_selected"] == ["binary.dat"]

    def test_portable_manifest_can_reproduce_the_snapshot_fingerprint(self):
        self.checkpoint()
        self.store.checkpoint(self.task, self.owner, ["binary.dat"], "Handoff",
                              {"next_actions": ["Run verification"]})
        manifest = self.store.manifest(self.task, with_patch=True)
        artifact = manifest["artifact"]
        assert manifest["version"] == 1
        assert manifest["context"]["next_actions"] == ["Run verification"]
        assert fingerprint(artifact["base"], base64.b64decode(
            artifact["git_binary_patch_base64"],
        )) == artifact["sha256"]
        assert self.owner not in json.dumps(manifest)
        assert self.started["recovery_key"] not in json.dumps(manifest)
        assert "git_binary_patch_base64" not in self.store.manifest(self.task)["artifact"]

    def test_only_one_concurrent_takeover_can_win(self):
        self.checkpoint()

        def attempt(target):
            try:
                return self.store.takeover(self.task, self.owner, self.directory / target)
            except ContinuityError:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, ("replace-one", "replace-two")))
        assert sum(outcome is not None for outcome in outcomes) == 1

    def test_lost_token_recovery_fences_previous_owner(self):
        self.checkpoint()
        with self.assertRaisesRegex(ContinuityError, "Invalid operator"):
            self.store.recover_owner(self.task, "wrong", self.directory / "wrong")
        recovered = self.store.recover_owner(
            self.task, self.started["recovery_key"], self.directory / "restore",
        )
        assert recovered["generation"] == 2
        with self.assertRaisesRegex(ContinuityError, "Stale"):
            self.store.takeover(self.task, self.owner, self.directory / "stale")

    def test_publish_reconciliation_and_revision_gate(self):
        self.checkpoint()
        receipt = verify(self.store, self.task, self.owner,
                         [sys.executable, "-c", "import code; assert code.x == 2"], 10)
        with publisher() as (remote, service):
            first = publish(self.store, self.task, self.owner, service, "fixture", receipt["evidence"])
            assert first["status"] == "unknown"
            replacement = self.store.takeover(self.task, self.owner, self.directory / "replacement")
            with self.assertRaisesRegex(ContinuityError, "Stale"):
                settle(self.store, self.task, self.owner, first["operation"])
            final = settle(self.store, self.task, replacement["token"], first["operation"])
            assert final["status"] == "confirmed"
            assert final["receipt"]["payload"]["digest"] == receipt["digest"]
            assert remote.puts == len(remote.events) == 1
            (Path(replacement["workspace"]) / "code.py").write_text("x = 3\n")
            assert not self.store.inspect(self.task)["verification"][0]["matches"]
            self.store.checkpoint(self.task, replacement["token"], ["binary.dat"], "changed")
            with self.assertRaisesRegex(ContinuityError, "passing evidence"):
                publish(self.store, self.task, replacement["token"], service, "changed",
                        receipt["evidence"])

    def test_rejects_outside_selection(self):
        external = self.directory / "external"
        external.mkdir()
        (external / "private").write_text("outside")
        (self.source / "linked").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ContinuityError, "inside"):
            self.store.checkpoint(self.task, self.owner, ["linked/private"], "outside")


if __name__ == "__main__":
    unittest.main()
