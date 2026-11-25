"""Capture the selected working tree using a private Git index."""

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile


class ContinuityError(Exception):
    pass


def git(path, *args, data=None, env=None):
    result = subprocess.run(
        ["git", "--literal-pathspecs", "-c", "core.hooksPath=/dev/null", *args],
        cwd=path, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    if result.returncode:
        raise ContinuityError(result.stderr.decode(errors="replace").strip() or "Git failed")
    return result.stdout


def root(path):
    return Path(os.fsdecode(git(path, "rev-parse", "--show-toplevel").strip())).resolve()


def capture(path, includes):
    path = Path(path).resolve()
    if path != root(path):
        raise ContinuityError("Use the root of a Git worktree")
    base = git(path, "rev-parse", "HEAD").decode().strip()
    for entry in includes:
        relative = Path(entry)
        candidate = path / relative
        if (
            relative.is_absolute() or ".." in relative.parts
            or not relative.parts or relative.parts[0].lower() == ".git"
            or not candidate.parent.resolve().is_relative_to(path)
            or not (candidate.is_file() or candidate.is_symlink())
        ):
            raise ContinuityError(f"Select an existing individual file inside the worktree: {entry}")
    with tempfile.TemporaryDirectory(prefix="continuity-index-") as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"))
        git(path, "read-tree", base, env=env)
        git(path, "add", "-u", "--", ".", env=env)
        if includes:
            git(path, "add", "--", *includes, env=env)
        index = git(path, "ls-files", "--stage", "-z", env=env)
        if any(entry.startswith(b"160000 ") for entry in index.split(b"\0")):
            raise ContinuityError("Git submodules are outside the snapshot contract")
        patch = git(
            path, "diff", "--cached", "--binary", "--full-index", "--no-color",
            "--no-ext-diff", "--no-textconv", "--no-renames", "--src-prefix=a/",
            "--dst-prefix=b/", base, "--", env=env,
        )
    return base, patch


def fingerprint(base, patch):
    return hashlib.sha256(base.encode() + b"\0" + patch).hexdigest()


def restore(repository, destination, base, patch):
    destination = Path(destination).resolve()
    git(repository, "worktree", "add", "--detach", str(destination), base)
    try:
        if patch:
            git(destination, "apply", "--binary", "--whitespace=nowarn", "-", data=patch)
    except BaseException:
        git(repository, "worktree", "remove", "--force", str(destination))
        raise
    return destination
