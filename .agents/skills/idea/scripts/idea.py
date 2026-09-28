"""Call the supported IntelliJ IDEA MCP tools through mcpc."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ENDPOINT = "http://127.0.0.1:64342/stream"
TOOLS = {"analyze_calls", "read_file", "rename_refactoring", "search_symbol"}


def main(argv):
    if not argv or len(argv) > 2:
        print("Usage: python idea.py <tool> [JSON arguments | --help]", file=sys.stderr)
        return 2

    tool = argv[0]
    if tool not in TOOLS:
        print(f"Unsupported IDEA tool: {tool}", file=sys.stderr)
        return 2

    show_help = len(argv) == 2 and argv[1] == "--help"
    json_arguments = argv[1] if len(argv) == 2 and not show_help else "{}"

    project_path = Path.cwd().resolve()
    skill_path = Path(__file__).resolve().parent.parent
    if project_path == skill_path or skill_path in project_path.parents:
        print("Run this script from the DSH project directory, not from the Skill directory.", file=sys.stderr)
        return 2

    if shutil.which("mcpc") is None:
        print("mcpc was not found on PATH; install/configure apify/mcpc before using this Skill.", file=sys.stderr)
        return 127

    project_key = os.path.normcase(str(project_path)).encode("utf-8")
    session = "@idea-" + hashlib.sha256(project_key).hexdigest()[:16]

    connect = subprocess.run([
        "mcpc", "connect", ENDPOINT, session, "--no-profile",
        "-H", f"IJ_MCP_SERVER_PROJECT_PATH: {project_path}",
    ])
    if connect.returncode != 0:
        return connect.returncode

    if show_help:
        command = ["mcpc", session, "tools-get", tool]
    else:
        command = ["mcpc", "--json", session, "tools-call", tool, json_arguments]
    return subprocess.run(command).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
