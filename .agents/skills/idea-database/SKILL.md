---
name: idea-database
description: Use IntelliJ IDEA MCP database tools to inspect database connections, schemas, objects, data, SQL queries, and query status for databases configured in IntelliJ IDEA. Use this skill whenever a database task should use an IntelliJ IDEA datasource, including discovery, metadata inspection, previews, read-only queries, connection diagnostics, and carefully requested database changes.
---

# IntelliJ IDEA Database

Use IntelliJ IDEA MCP database tools for databases configured in the current IDE project. Prefer them over:

- reading JDBC credentials from project files
- using `mysql`, `psql`, or other database CLI tools
- creating separate database connections
- guessing database structure from source code

All database capabilities in this skill are invoked through the bundled Python script at `<resolved Skill directory>/scripts/idea-database.py`. Do not use `execute_tool` or another router. The script connects to the local IntelliJ IDEA MCP Server, sets `IJ_MCP_SERVER_PROJECT_PATH` from the active DSH command working directory, and calls the named IDEA MCP tool. Run it with Python using its resolved path while keeping the DSH project directory as the command working directory; do not `cd` into the Skill directory. Examples use `python scripts/idea-database.py` as shorthand for `python <resolved Skill directory>/scripts/idea-database.py`.

The script accepts an IDEA MCP tool name and, when needed, one JSON object containing the tool's arguments. It passes JSON values through as provided; preserve IDEA's original argument names and types. Use `python scripts/idea-database.py <tool> --help` to retrieve that tool's description and `inputSchema` from MCP `tools/list`. The script only supports the Database tools listed below. MCP protocol errors and tool errors are reported and return a non-zero exit code.

Supported tools:

- `list_database_connections`
- `list_database_schemas`
- `list_schema_object_kinds`
- `list_schema_objects`
- `get_database_object_description`
- `introspect_schema`
- `preview_table_data`
- `execute_sql_query`
- `fetch_query_result`
- `list_recent_sql_queries`
- `cancel_sql_query`
- `test_database_connection`
- `create_database_connection`
- `edit_database_connection`

## Workflow

### Connection

Use `list_database_connections` as the default entry point:

```bash
python scripts/idea-database.py list_database_connections
```

Use the returned connection `id` as `connectionId` for subsequent database tools. The exception is `test_database_connection`, which expects the original parameter name `id`:

```bash
python scripts/idea-database.py test_database_connection '{"id":"xxx"}'
```

### Schema and objects

Use `list_database_schemas` to discover available databases and schemas:

```bash
python scripts/idea-database.py list_database_schemas '{"connectionId":"xxx"}'
```

Use `list_schema_objects` to discover tables, views, and other objects. Pass `connectionId`, `databaseName`, and `schemaName`; optionally pass `kind` to filter by an object kind code:

```bash
python scripts/idea-database.py list_schema_objects '{"connectionId":"xxx","databaseName":"app","schemaName":"public"}'
```

If the required object kind is unknown, call `list_schema_object_kinds` with `connectionId` before filtering. Do not guess object kind codes. Do not query system tables with SQL as a substitute for IDEA's available metadata tools.

### Object structure

Use `get_database_object_description` with `connectionId`, `databaseName`, `schemaName`, `objectName`, and `kind` to inspect columns, types, keys, and indexes:

```bash
python scripts/idea-database.py get_database_object_description '{"connectionId":"xxx","databaseName":"app","schemaName":"public","objectName":"users","kind":"table"}'
```

Prefer this over manually querying database metadata tables.

### Metadata refresh

Use `introspect_schema` only when required metadata is missing or clearly stale. Pass `connectionId`, `databaseName`, and `schemaName`, then retry the original metadata operation. Do not introspect as a default first step.

### Preview data

For a quick look at table-like data, prefer `preview_table_data` rather than immediately writing `SELECT *`:

```bash
python scripts/idea-database.py preview_table_data '{"connectionId":"xxx","databaseName":"app","schemaName":"public","tableName":"users"}'
```

Use `maxRowCount` to control returned rows; the default is 100.

### SQL

Use `execute_sql_query` when filtering, joins, aggregation, ordering, or another custom query is needed:

```bash
python scripts/idea-database.py execute_sql_query '{"connectionId":"xxx","databaseName":"app","schemaName":"public","queryText":"select * from users limit 10"}'
```

Prefer targeted, read-only SQL by default. If the response includes a `resultSetId` and more rows are needed, use `fetch_query_result` with that `resultSetId` and the required `offset`; do not execute the SQL again just to fetch more results.

### Connection problems

Use `test_database_connection` when a connection fails or its status, DBMS, or driver information needs verification. Pass the connection's `id` as `id`, not `connectionId`.

### Query status

Use `list_recent_sql_queries` with `connectionId` to inspect running or recent SQL queries. Use `cancel_sql_query` with a returned `sessionId` when a running query needs to be stopped.

### Connection management

Use `create_database_connection` only when no suitable IntelliJ IDEA datasource exists. Use `edit_database_connection` only when an existing connection actually needs modification. Do not create or modify a connection merely to query data. Preserve the tool's native argument names; use `python scripts/idea-database.py <tool> --help` to inspect the current schema when needed.

## Safety

Prefer metadata inspection, data previews, and read-only SQL. Execute modifying SQL only when the user explicitly requests it, including `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `ALTER`, `DROP`, and `CREATE`. Do not assume an IntelliJ IDEA connection is read-only just because it is already configured.
