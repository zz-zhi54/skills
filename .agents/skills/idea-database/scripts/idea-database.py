#!/usr/bin/env python3
"""Call the supported IntelliJ IDEA Database MCP tools."""

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "http://127.0.0.1:64342/stream"
PROTOCOL_VERSION = "2025-03-26"
ALLOWED_TOOLS = {
    "list_database_connections",
    "list_database_schemas",
    "list_schema_object_kinds",
    "list_schema_objects",
    "get_database_object_description",
    "introspect_schema",
    "preview_table_data",
    "execute_sql_query",
    "fetch_query_result",
    "list_recent_sql_queries",
    "cancel_sql_query",
    "test_database_connection",
    "create_database_connection",
    "edit_database_connection",
}


def usage():
    return (
        "Usage:\n"
        "  idea-database.py <tool>\n"
        "  idea-database.py <tool> '{\"key\":\"value\"}'\n"
        "  idea-database.py <tool> --help"
    )


def parse_sse_messages(body):
    messages = []
    data_lines = []

    def flush():
        if not data_lines:
            return
        data = "\n".join(data_lines)
        data_lines.clear()
        try:
            messages.append(json.loads(data))
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Invalid JSON in MCP event-stream response: {data[:500]}"
            ) from error

    for line in body.splitlines():
        if not line:
            flush()
        elif line.startswith("data:"):
            data_lines.append(line[5:].removeprefix(" "))
    flush()
    return messages


def parse_response(body, content_type):
    if "text/event-stream" in content_type or body.lstrip().startswith(("event:", "data:")):
        return parse_sse_messages(body)
    try:
        return [json.loads(body)]
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON from IDEA MCP Server: {body[:500]}") from error


class McpClient:
    def __init__(self, project_path):
        self.project_path = str(project_path)
        self.session_id = None
        self.protocol_version = None
        self.next_id = 0

    def post(self, message, expect_response=True):
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
            data=json.dumps(message).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")
                content_type = response.headers.get("Content-Type", "")
                received_session_id = response.headers.get("Mcp-Session-Id")
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace").strip()
            suffix = f": {details[:1200]}" if details else ""
            raise RuntimeError(
                f"IDEA MCP Server returned HTTP {error.code}{suffix}"
            ) from error
        except URLError as error:
            raise RuntimeError(
                f"Could not reach IDEA MCP Server at {ENDPOINT}: {error.reason}"
            ) from error

        if received_session_id:
            self.session_id = received_session_id
        if not expect_response or status == 202:
            return None
        if not body.strip():
            raise RuntimeError("IDEA MCP Server returned an empty response to an MCP request.")

        messages = parse_response(body, content_type)
        reply = next(
            (item for item in messages if item and item.get("id") == message.get("id")),
            None,
        )
        if reply is None:
            raise RuntimeError(
                f"IDEA MCP Server response did not contain the reply for request {message.get('id')}."
            )
        if "error" in reply:
            error = reply["error"]
            details = f" ({json.dumps(error['data'])})" if "data" in error else ""
            raise RuntimeError(
                f"MCP protocol error {error.get('code')}: {error.get('message')}{details}"
            )
        return reply.get("result")

    def rpc(self, method, params):
        self.next_id += 1
        return self.post(
            {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        )


def render_result(result):
    if "structuredContent" in result:
        return json.dumps(result["structuredContent"], ensure_ascii=False, indent=2)
    content = result.get("content")
    if isinstance(content, list) and all(item.get("type") == "text" for item in content):
        return "\n".join(item.get("text", "") for item in content)
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    arguments = sys.argv[1:]
    if not arguments or len(arguments) > 2:
        raise RuntimeError(usage())

    tool_name = arguments[0]
    if tool_name not in ALLOWED_TOOLS:
        supported = ", ".join(sorted(ALLOWED_TOOLS))
        raise RuntimeError(
            f"Unsupported IDEA database tool: {tool_name}\nSupported tools: {supported}"
        )

    show_help = len(arguments) == 2 and arguments[1] == "--help"
    tool_arguments = {}
    if len(arguments) == 2 and not show_help:
        try:
            tool_arguments = json.loads(arguments[1])
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Invalid JSON arguments: {error}") from error
        if not isinstance(tool_arguments, dict):
            raise RuntimeError("Tool arguments must be a JSON object.")

    project_path = Path.cwd().resolve()
    skill_directory = Path(__file__).resolve().parent.parent
    script_directory = Path(__file__).resolve().parent
    if project_path in (skill_directory, script_directory):
        raise RuntimeError(
            "The current directory is the idea-database Skill itself, not the DSH project. "
            "Run this script while the DSH project directory is the current working directory."
        )

    client = McpClient(project_path)
    initialize = client.rpc(
        "initialize",
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "idea-database", "version": "1.0.0"},
        },
    )
    if not initialize or not initialize.get("protocolVersion"):
        raise RuntimeError(
            "IDEA MCP Server returned an invalid initialize response (missing protocolVersion)."
        )
    client.protocol_version = initialize["protocolVersion"]
    client.post({"jsonrpc": "2.0", "method": "notifications/initialized"}, False)

    if show_help:
        cursor = None
        tool = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            result = client.rpc("tools/list", params)
            if not result or not isinstance(result.get("tools"), list):
                raise RuntimeError("IDEA MCP Server returned an invalid tools/list response.")
            tool = next((item for item in result["tools"] if item.get("name") == tool_name), None)
            cursor = result.get("nextCursor")
            if tool or not cursor:
                break

        if not tool:
            raise RuntimeError(f"IDEA MCP Server does not expose the supported tool {tool_name}.")
        schema = json.dumps(tool.get("inputSchema", {}), ensure_ascii=False, indent=2)
        print(f"{tool_name}\n{tool.get('description') or '(no description)'}\n\nInput schema:\n{schema}")
        return

    result = client.rpc(
        "tools/call", {"name": tool_name, "arguments": tool_arguments}
    )
    if result is None:
        raise RuntimeError(f"IDEA MCP Server returned an empty result for {tool_name}.")

    output = render_result(result)
    if result.get("isError"):
        print(output, file=sys.stderr)
        raise RuntimeError(f"IDEA MCP tool {tool_name} reported an error.")
    print(output)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"idea-database: {error}", file=sys.stderr)
        sys.exit(1)
