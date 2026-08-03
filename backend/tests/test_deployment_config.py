"""Regression guards over deployment configuration files.

These parse text; they never build or run Docker. Cheap by design.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"


def _last_cmd_line() -> str:
    """Return the last CMD instruction (the one that takes effect)."""
    lines = DOCKERFILE.read_text().splitlines()
    cmds = [ln.strip() for ln in lines if ln.strip().upper().startswith("CMD")]
    assert cmds, "Dockerfile has no CMD instruction"
    return cmds[-1]


def test_dockerfile_cmd_is_exec_form_with_exec():
    """THEORY: Cloud Run stops a revision with SIGTERM to PID 1. A shell-form
    CMD makes /bin/sh PID 1, and sh swallows SIGTERM instead of forwarding it
    to uvicorn, so revisions die by SIGKILL after the grace period. The CMD
    must therefore be exec (JSON) form, and because it needs ${PORT} expansion
    it goes through `sh -c` — which only keeps the signal path intact if the
    command `exec`s uvicorn so uvicorn replaces the shell as PID 1.

    Reverting to shell form is silent locally and only shows up as killed
    revisions in production, hence this parse-level guard.
    """
    cmd = _last_cmd_line()

    # Exec form: CMD ["...", ...] — a JSON array after the keyword.
    match = re.match(r"CMD\s+(\[.*\])\s*$", cmd)
    assert match, f"CMD is shell form, must be exec (JSON) form: {cmd!r}"
    argv = json.loads(match.group(1))
    assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)

    # The uvicorn invocation must be exec'd so it replaces sh as PID 1.
    full = " ".join(argv)
    assert "uvicorn" in full, f"CMD does not start uvicorn: {cmd!r}"
    if argv[0] in ("sh", "/bin/sh", "bash", "/bin/bash"):
        assert re.search(r"\bexec\s+\S*uvicorn", full), (
            f"CMD wraps uvicorn in a shell without `exec` — "
            f"the shell would swallow SIGTERM: {cmd!r}"
        )
