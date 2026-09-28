"""Call the supported IntelliJ IDEA debugger tools through mcpc."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ENDPOINT = "http://127.0.0.1:64342/stream"
TOOLS = {
    "xdebug_set_breakpoint",
    "xdebug_start_debugger_session",
    "xdebug_get_debugger_status",
    "xdebug_control_session",
    "xdebug_get_threads",
    "xdebug_get_stack",
    "xdebug_get_frame_values",
    "xdebug_get_value_by_path",
    "xdebug_evaluate_expression",
    "xdebug_remove_breakpoint",
    "xdebug_list_breakpoints",
    "xdebug_run_to_line",
    "xdebug_set_variable",
    "get_run_configurations",
    "execute_run_configuration",
}


def main(argv):
    if not argv or len(argv) > 2:
        print("Usage: python idea-debug.py <tool> [JSON arguments | --help]", file=sys.stderr)
        return 2

    tool = argv[0]
    if tool not in TOOLS:
        print(f"Unsupported IDEA debugger tool: {tool}", file=sys.stderr)
        return 2

    show_help = len(argv) == 2 and argv[1] == "--help"
    json_arguments = argv[1] if len(argv) == 2 and not show_help else "{}"

    project_dir = Path.cwd().resolve()
    skill_path = Path(__file__).resolve().parent.parent
    if project_dir == skill_path or skill_path in project_dir.parents:
        print("Run this script from the DSH project directory, not from the Skill directory.", file=sys.stderr)
        return 2

    if shutil.which("mcpc") is None:
        print("mcpc was not found on PATH; install/configure apify/mcpc before using this Skill.", file=sys.stderr)
        return 127

    env = os.environ.copy()
    env["MCPC_HOME_DIR"] = str(project_dir / ".dsh" / "mcpc")
    session = "@idea"

    connect = subprocess.run([
        "mcpc", "connect", ENDPOINT, session, "--no-profile",
        "-H", f"IJ_MCP_SERVER_PROJECT_PATH: {project_dir}",
    ], env=env)
    if connect.returncode != 0:
        return connect.returncode

    if show_help:
        command = ["mcpc", session, "tools-get", tool]
    else:
        command = ["mcpc", "--json", session, "tools-call", tool, json_arguments]
    return subprocess.run(command, env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
