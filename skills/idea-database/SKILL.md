---
name: idea-database
description: Use IntelliJ IDEA MCP database tools to inspect database connections, schemas, objects, data, SQL queries, and query status for databases configured in IntelliJ IDEA.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# IntelliJ IDEA Database

Use IntelliJ IDEA MCP database tools for databases configured in the current IDE project.

Prefer them over:

* reading JDBC credentials from project files
* using `mysql`, `psql`, or other database CLI tools
* creating separate database connections
* guessing database structure from source code

Database tools may be Router-only and therefore absent from the direct tool list. When needed, use the IntelliJ IDEA MCP `execute_tool` router to invoke them.

Do not assume database functionality is unavailable merely because a tool is not directly visible.

## Workflow

### Connection

Use `list_database_connections` first.

The returned connection `id` is used as `connectionId` by database tools.

Exception: `test_database_connection` expects the parameter `id`.

### Schema and objects

Use:

`list_database_schemas`

to discover available databases and schemas.

Use:

`list_schema_objects`

to discover tables, views, and other objects. Pass `connectionId`, `databaseName`, and `schemaName`; optionally pass `kind` to filter by an object kind code.

If the required object kind is unknown, use:

`list_schema_object_kinds`

with `connectionId`.

Do not guess object kind codes.

### Object structure

Use:

`get_database_object_description`

with `connectionId`, `databaseName`, `schemaName`, `objectName`, and `kind`.

Prefer this for inspecting:

* columns
* types
* keys
* indexes

instead of manually querying database metadata tables.

### Metadata refresh

If schema metadata is missing or stale, use:

`introspect_schema`

with `connectionId`, `databaseName`, and `schemaName`, then retry the original operation.

Do not introspect unnecessarily.

### Preview data

Use:

`preview_table_data`

for a quick look at table-like data.

Pass `connectionId`, `databaseName`, `schemaName`, and `tableName`.

Use `maxRowCount` to control returned rows. The default is 100.

### SQL

Use:

`execute_sql_query`

with `connectionId`, `databaseName`, `schemaName`, and `queryText` when filtering, joins, aggregation, ordering, or custom SQL is required.

Prefer targeted, read-only queries unless modification is explicitly requested.

If more rows are required and a `resultSetId` is returned, use:

`fetch_query_result`

with the required `resultSetId` and `offset` instead of executing the query again.

### Connection problems

Use:

`test_database_connection`

when a connection fails or its status, DBMS, or driver information needs verification.

Pass the connection `id` as `id`.

### Query status

Use:

`list_recent_sql_queries`

with `connectionId` to inspect running or recent SQL queries.

Use:

`cancel_sql_query`

with the returned `sessionId` when a running query must be stopped.

## Connection management

Use `create_database_connection` only when no suitable IntelliJ IDEA data source exists. It requires `name`, `dbms`, `url`, and `needToCheckDs`.

Use `edit_database_connection` only when an existing connection actually needs modification. It requires `connectionId`, `dbms`, `url`, and `needToCheckDs`.

Do not modify connections merely to inspect database data.

## Safety

Prefer metadata inspection, previews, and read-only SQL.

Only execute modifying SQL when explicitly required, including:

`INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `ALTER`, `DROP`, and `CREATE`.

Do not assume an IntelliJ IDEA connection is read-only.

## Router-only tools

When these tools are not directly visible, invoke them through `execute_tool`:

* `list_database_connections`
* `list_database_schemas`
* `list_schema_object_kinds`
* `list_schema_objects`
* `get_database_object_description`
* `introspect_schema`
* `preview_table_data`
* `execute_sql_query`
* `fetch_query_result`
* `list_recent_sql_queries`
* `cancel_sql_query`
* `test_database_connection`
* `create_database_connection`
* `edit_database_connection`
