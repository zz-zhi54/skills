#!/usr/bin/env python3
"""Call one of the supported IntelliJ IDEA MCP tools."""

import json
import os
import sys
import urllib.error
import urllib.request

URL = "http://127.0.0.1:64342/stream"
TOOLS = {"analyze_calls", "read_file", "rename_refactoring", "search_symbol"}
PROTOCOL_VERSION = "2025-03-26"


def post(payload, project_path, session_id=None, protocol_version=None):
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "IJ_MCP_SERVER_PROJECT_PATH": project_path,
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    if protocol_version:
        headers["MCP-Protocol-Version"] = protocol_version
    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.headers, response.read().decode()


def response_message(body, request_id):
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        for line in body.splitlines():
            if line.startswith("data:"):
                message = json.loads(line[5:].strip())
                if message.get("id") == request_id:
                    return message
    raise RuntimeError("IDEA MCP returned no JSON-RPC response")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in TOOLS:
        print(
            "Usage: scripts/idea.py {analyze_calls|read_file|rename_refactoring|search_symbol} '<JSON arguments>'",
            file=sys.stderr,
        )
        return 2

    tool_name = sys.argv[1]
    try:
        arguments = json.loads(sys.argv[2])
    except json.JSONDecodeError as error:
        print(f"Invalid JSON arguments: {error}", file=sys.stderr)
        return 2
    if not isinstance(arguments, dict):
        print("Arguments must be a JSON object", file=sys.stderr)
        return 2

    project_path = os.getcwd()
    try:
        init_headers, init_body = post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "dsh-idea-skill", "version": "1.0"},
                },
            },
            project_path,
        )
        initialized = response_message(init_body, 1)
        if "error" in initialized:
            raise RuntimeError(json.dumps(initialized["error"], ensure_ascii=False))

        session_id = init_headers.get("Mcp-Session-Id")
        protocol_version = initialized["result"]["protocolVersion"]
        post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            project_path,
            session_id,
            protocol_version,
        )
        _, body = post(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            project_path,
            session_id,
            protocol_version,
        )
        result = response_message(body, 2)
        if "error" in result:
            print(json.dumps(result["error"], ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        tool_result = result.get("result", {})
        print(json.dumps(tool_result, ensure_ascii=False, indent=2))
        return 1 if tool_result.get("isError") else 0
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"IDEA MCP request failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
