#!/usr/bin/env python3
"""Thin Streamable HTTP client for the supported IntelliJ IDEA debugger tools."""

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
TIMEOUT_SECONDS = 300


class MCPError(Exception):
    pass


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def usage_error(message):
    print(f"idea-debug: {message}", file=sys.stderr)
    print(
        "usage: idea-debug <supported-tool> [JSON-object | --help]",
        file=sys.stderr,
    )
    raise SystemExit(2)


def parse_arguments(argv):
    if not argv:
        usage_error("missing IDEA MCP Tool name")

    tool_name = argv[0]
    if tool_name not in TOOLS:
        supported = ", ".join(sorted(TOOLS))
        usage_error(f"unsupported tool {tool_name!r}; supported tools: {supported}")

    if len(argv) == 2 and argv[1] == "--help":
        return tool_name, None, True
    if len(argv) == 1:
        return tool_name, {}, False
    if len(argv) != 2:
        usage_error("pass at most one JSON object argument")

    try:
        arguments = json.loads(argv[1])
    except json.JSONDecodeError as error:
        usage_error(f"invalid JSON arguments: {error}")
    if not isinstance(arguments, dict):
        usage_error("arguments must be one JSON object")
    return tool_name, arguments, False


def decode_sse(body):
    """Decode JSON-RPC messages from the data fields of an SSE response."""
    messages = []
    data_lines = []
    for line in body.decode("utf-8").splitlines() + [""]:
        if line == "":
            if data_lines:
                data = "\n".join(data_lines)
                try:
                    messages.append(json.loads(data))
                except json.JSONDecodeError as error:
                    raise MCPError(f"invalid JSON in MCP event stream: {error}") from error
                data_lines = []
        elif line.startswith("data:"):
            value = line[5:]
            data_lines.append(value[1:] if value.startswith(" ") else value)
    return messages


def decode_response(body, content_type):
    if not body:
        return []
    if "text/event-stream" in content_type.lower():
        return decode_sse(body)
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MCPError(f"invalid JSON MCP response: {error}") from error
    return value if isinstance(value, list) else [value]


def response_detail(body, content_type):
    if not body:
        return "(empty response body)"
    try:
        return pretty(json.loads(body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body.decode("utf-8", errors="replace")


class StreamableHTTPMCP:
    def __init__(self, project_path):
        self.project_path = project_path
        self.session_id = None
        self.protocol_version = None
        self.next_id = 1

    def post(self, message, *, expects_response=True):
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "IJ_MCP_SERVER_PROJECT_PATH": self.project_path,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version

        request = Request(
            ENDPOINT,
            data=json.dumps(message, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                body = response.read()
                if not expects_response:
                    if status not in (200, 202, 204):
                        raise MCPError(f"unexpected HTTP status for MCP notification: {status}")
                    return None
                messages = decode_response(body, content_type)
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self.session_id = session_id
        except HTTPError as error:
            body = error.read()
            detail = response_detail(body, error.headers.get("Content-Type", ""))
            raise MCPError(f"IDEA MCP HTTP {error.code} {error.reason}:\n{detail}") from error
        except URLError as error:
            reason = getattr(error, "reason", error)
            raise MCPError(f"could not connect to {ENDPOINT}: {reason}") from error
        except TimeoutError as error:
            raise MCPError(f"request to {ENDPOINT} timed out") from error

        if status < 200 or status >= 300:
            raise MCPError(f"IDEA MCP returned HTTP {status}")
        if not messages:
            raise MCPError("IDEA MCP returned no JSON-RPC response")

        expected_id = message.get("id")
        for response_message in messages:
            if not isinstance(response_message, dict) or response_message.get("id") != expected_id:
                continue
            if response_message.get("jsonrpc") != "2.0":
                raise MCPError("IDEA MCP returned a response with an invalid JSON-RPC version")
            if "error" in response_message:
                raise MCPError(f"IDEA MCP JSON-RPC error:\n{pretty(response_message['error'])}")
            if "result" not in response_message:
                raise MCPError("IDEA MCP response has neither result nor error")
            return response_message["result"]
        raise MCPError(f"IDEA MCP response did not contain request id {expected_id}")

    def request(self, method, params):
        request_id = self.next_id
        self.next_id += 1
        response = self.post(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        return response

    def initialize(self):
        result = self.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "idea-debug", "version": "1.0"},
            },
        )
        if not isinstance(result, dict) or not isinstance(result.get("protocolVersion"), str):
            raise MCPError("IDEA MCP initialize response has no protocolVersion")
        self.protocol_version = result["protocolVersion"]
        self.post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            expects_response=False,
        )

    def list_tools(self):
        tools = []
        cursor = None
        seen_cursors = set()
        while True:
            params = {} if cursor is None else {"cursor": cursor}
            result = self.request("tools/list", params)
            if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
                raise MCPError("IDEA MCP tools/list response has no tools array")
            tools.extend(result["tools"])
            cursor = result.get("nextCursor")
            if not cursor:
                return tools
            if cursor in seen_cursors:
                raise MCPError("IDEA MCP tools/list repeated a pagination cursor")
            seen_cursors.add(cursor)


def main(argv):
    tool_name, arguments, help_requested = parse_arguments(argv)
    try:
        project_path = str(Path.cwd().resolve(strict=True))
        if not Path(project_path).is_dir():
            raise MCPError("current DSH working directory is not a directory")
        os.environ["IJ_MCP_SERVER_PROJECT_PATH"] = project_path

        client = StreamableHTTPMCP(os.environ["IJ_MCP_SERVER_PROJECT_PATH"])
        client.initialize()
        if help_requested:
            tool = next((item for item in client.list_tools() if item.get("name") == tool_name), None)
            if tool is None:
                raise MCPError(f"IDEA MCP tools/list does not contain {tool_name!r}")
            print(
                pretty(
                    {
                        "name": tool_name,
                        "description": tool.get("description"),
                        "inputSchema": tool.get("inputSchema"),
                    }
                )
            )
            return 0

        result = client.request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )
        if not isinstance(result, dict):
            raise MCPError("IDEA MCP tools/call result is not an object")
        if result.get("isError") is True:
            raise MCPError(f"IDEA MCP Tool {tool_name} returned an error:\n{pretty(result)}")
        print(pretty(result))
        return 0
    except (MCPError, OSError, ValueError) as error:
        print(f"idea-debug: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
