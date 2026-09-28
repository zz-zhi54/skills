---
name: idea-debug
description: "Debugger-first runtime root-cause analysis for JVM code in IntelliJ IDEA. Use whenever concrete runtime state or control-flow evidence is needed (values, branches, call order, thread context, reachability), when answering the question would otherwise require tracing a long call chain across many files, or when the user explicitly asks to use the debugger, set breakpoints, step, or inspect values."
allowed-tools: bash
---

# IntelliJ IDEA Debugger Skill

Use the bundled `scripts/idea-debug.py` script to call the supported IntelliJ IDEA MCP debugger and run-configuration tools. Invoke tools only through this script, using the original MCP Tool name and, when needed, one JSON object argument. Resolve the script path relative to this skill, but keep the shell's working directory at the current DSH project workspace; the script uses that working directory as `IJ_MCP_SERVER_PROJECT_PATH`.

```bash
scripts/idea-debug.py xdebug_get_debugger_status
scripts/idea-debug.py xdebug_set_breakpoint \
  '{"filePath":"src/main/java/example/Foo.java","line":42,"logExpression":"value + 1","suspendPolicy":"NONE"}'
scripts/idea-debug.py xdebug_control_session '{"action":"DRAIN_EVENTS"}'
scripts/idea-debug.py xdebug_evaluate_expression \
  '{"sessionId":"xxx","frameIndex":0,"expression":"user.getName().trim()","depth":0}'
```

For the exact current contract of a supported tool, ask the script to fetch its `description` and `inputSchema` from IDEA MCP:

```bash
scripts/idea-debug.py xdebug_set_breakpoint --help
```

The script only permits the debugger and run-configuration tools listed in [Tool Reference](#tool-reference). Supply arguments as one JSON object; values keep their JSON/MCP types. Omit unused optional properties rather than supplying fake placeholders. Store expressions as their original source text in JSON strings.

## Goal

Use debugger evidence to answer concrete runtime questions when static code reading is not enough, or to confirm ideas from static analysis — including whether execution reaches or does not reach agent-selected code locations. Gather this evidence with **minimal runtime disturbance**: by default observe without stopping threads and without editing source code.

## When To Use This Skill

Use this skill when at least one holds:
- a runtime value or control-flow fact is needed (actual values, branch taken, call order, thread context, or whether execution reaches a chosen location) and it cannot be derived confidently from source/logs;
- finding the relevant path would otherwise require reading many files or tracing a long call chain manually;
- the user explicitly asks to use the debugger (breakpoints, logpoints, stepping, inspect values, debugger session).

Manual activation by the user means launch and use the debugger when tools are available — do not reduce it to a conceptual discussion. Do not treat domain identifiers named `debug`/`debugger` in the user's own code as a debugger request; reason about what the user actually means.

## Activation Gate (tool availability)

Use this skill only when the IDEA MCP server and required debugger tools are available. Check the exact live contracts with `scripts/idea-debug.py <tool> --help`. Minimum required set:
- `xdebug_set_breakpoint` (important: sets logpoints, via `logExpression`)
- `xdebug_start_debugger_session`
- `xdebug_control_session`
- `xdebug_get_stack`
- at least one value tool: `xdebug_get_frame_values`, `xdebug_get_value_by_path`, or `xdebug_evaluate_expression`
- `get_run_configurations`

If the minimum set is unavailable: state the blocker explicitly, do not force a debugger workflow, and switch to the best fallback.

## Principle: Logpoint-First Debugging

**Logpoints are the primary way to communicate with the IntelliJ debugger.** A logpoint is a non-suspending breakpoint that does not stop execution: when the line is reached it evaluates an expression and logs the result. Reach for a logpoint first for almost every runtime question; treat suspending breakpoints, stepping, and expression evaluation as escalations you must justify, not as the default. Logpoints give runtime evidence without freezing threads — which matters for concurrent code, long-running services, flaky/timing-sensitive tests, and multi-agent workflows.

**Logpoint output is dumped to debugger events, and you read it back from there.** Each logpoint hit is captured as an event in the debug session's event buffer — not printed to your console and not written to any file. Collect that output by draining events:

```bash
scripts/idea-debug.py xdebug_control_session '{"action":"DRAIN_EVENTS"}'
```

The response returns accumulated logpoint output in `tracepointOutputsTail`. The logpoint loop is: install logpoint(s) → run the scenario → drain events → map each event back to source. Reading events is the normal, expected way to get logpoint results; if you find yourself wanting to write a file or add a print statement to capture output, drain events instead.

Prefer the **least disruptive** tool that answers the question, in this priority order:

1. **Non-suspending logpoints** — `xdebug_set_breakpoint` with `logExpression` and `suspendPolicy: "NONE"`. A logpoint evaluates the expression and logs the result on every hit without suspending; read output via `xdebug_control_session` with `action: "DRAIN_EVENTS"`. Providing `logExpression` is the most important input. This is the default first probe.
2. **Logpoints with condition / stack-trace logging** — add `condition` to filter and `isLogStack: true` for a call path. Use when events are too frequent, only specific cases matter, or a call path is needed.
3. **Thread / stack inspection of a suspended session** — call `xdebug_get_threads` and `xdebug_get_stack`. These read a *paused* session: if the program is running, suspend it first with `xdebug_control_session` and `action: "PAUSE"`. Use for hangs, concurrency issues, deadlocks, thread-state questions, or unclear call paths.
4. **Ordinary suspending breakpoints** — call `xdebug_set_breakpoint` without `logExpression` (default `suspendPolicy` is `ALL`). Use only when you must inspect live object graphs, evaluate multiple expressions interactively, step through code, or modify state.
5. **Evaluate expression / Set value** — use `xdebug_evaluate_expression` or `xdebug_set_variable`. Use only in a suspended context and only with explicit justification; these can alter what you are investigating.

Escalate down this list only when the cheaper option cannot answer the question, and say why you escalated.

## Safe Logpoint Expressions (no side effects)

`logExpression` and `condition` are evaluated inside the running program and **can change its behavior**. By default restrict them to **side-effect-free reads**: field/local/parameter access, non-mutating getters, arithmetic, `toString()` on trusted values, identity/`hashCode` checks. Expressions are sent as raw source expressions inside JSON string values; JSON quoting is only the transport representation and does not make an unsafe expression safe.

Do **not** use expressions that mutate state, perform I/O, advance iterators/streams, trigger side-effecting lazy initialization, or call methods with observable side effects — unless the user explicitly asked to enter a controlled mutation/debugging mode and accepted that program behavior may change.

## Logpoint Placement: Variable Scope And Initialization

A logpoint evaluates its `logExpression` **at the moment execution reaches the line, before that line's statement runs**. Every symbol the expression references must already be **assigned and in scope** at that point, or evaluation fails (you will see an error such as `Variable 'x' has not been initialized` / `Cannot find local variable 'x'` in `breakpointErrorsTail`, and no value is logged).

Rules for picking the line:
- Do **not** place a logpoint on the line that *declares or initializes* the variable you want to log, nor in the middle of a multi-line statement that assigns it. At that position the variable does not hold its value yet.
- For a multi-line assignment such as a fluent/builder chain
  ```java
  List<String> configured = jdbc.sql("…")   // line 20  ← declaration starts here
      .query(String.class)                   // line 21
      .list();                               // line 22  ← assignment completes here
  this.rate = new BigDecimal(configured.get(0)); // line 23
  ```
  a logpoint on line 21 logging `configured.get(0)` fails — `configured` is assigned only after line 22. Place it on the **first line after the statement's terminating `;`** (here line 23), where `configured` is initialized.
- General rule: put the logpoint on the earliest executable line where every symbol in the expression is already initialized and in scope. To capture a value at a method's entry, target the first executable line of the body, not the signature/parameter line.
- After installing, run once and read `breakpointErrorsTail`. If you see an uninitialized/unresolved-variable error, move the logpoint to a later line (or pick an expression whose inputs are already available) and rerun.

## Initial Triage Before Debugging

Start with minimal static triage (error text, stack trace, nearby source). Start debugger work when: static analysis leaves multiple plausible runtime hypotheses; deciding between them requires concrete values or exact control flow; stepping is cheaper than reading a large cross-file path; or the user explicitly asked. Install the first logpoint(s) early and collect evidence before changing runtime behavior.

## Mandatory Runtime Evidence

Before editing code for a runtime-behavior issue when debugger evidence is available, capture:
- for reachability/branch questions: logpoint output proving execution did or did not hit a chosen location (or its absence across a full reproduction);
- for state questions: at least one concrete runtime value, via a logpoint expression or — in a suspended session — `xdebug_get_frame_values` / `xdebug_get_value_by_path` / `xdebug_evaluate_expression`;
- when you suspend: the paused location (file/line) and the top call path via `xdebug_get_stack`.

Do not assert runtime conclusions before this evidence is captured unless a clear blocker is already stated.

## Hypothesis-Driven Batch Logpoints

Logpoints are cheap and non-suspending, so prefer installing a **batch** derived from your hypotheses, then run the scenario once:
1. Form 2–5 concrete hypotheses about where/why runtime behavior diverges.
2. Install one logpoint per hypothesis anchor (branch decision, mapping boundary, state transition, dynamic dispatch, error construction, queue handoff), each logging the values that confirm or refute that hypothesis.
3. Run the scenario once via `xdebug_start_debugger_session`.
4. Read output with `xdebug_control_session` and `action: "DRAIN_EVENTS"`; map each event to its source and hypothesis.
5. Refine hypotheses or escalate to stronger tools only when logpoint evidence is insufficient.

## Reproduction Mode Selection

1. `AUTO`: you can run/rerun the scenario directly. Use `xdebug_start_debugger_session` to launch with debugging, or `execute_run_configuration` for a non-debug run when you only need output/exit code.
2. `ASSISTED`: reproduction needs a user-only action (UI flow, auth, external dependency, hardware).
3. `HYBRID`: try `AUTO` once or twice, then switch to `ASSISTED` if it does not reproduce.

If the candidate target is a test, default to `AUTO`. Never ask the user to reproduce before logpoints/breakpoints are prepared.

## Test Task Execution

- To debug a test, call `xdebug_start_debugger_session` with its `filePath` and `line` at the test method, or `configurationName` for an existing test run configuration. To run without debugging (e.g. confirm it fails first), use `execute_run_configuration` with the same targeting modes.
- After triggering, inspect state with `xdebug_get_debugger_status` and continue inside the resulting session.
- Do not ask the user to rerun a test manually unless no available path can reproduce it or repro requires user-only setup.

## Argument Hygiene

- Optional JSON properties are omitted or set to real values; omitted means omitted.
- Never encode omitted properties with placeholder strings such as `""`, `"/"`, `"__omit__"`, `"."`, or fake paths.
- Preserve JSON types for booleans, numbers, arrays, and objects. Send expressions as the original expression text in JSON strings.
- Treat debugger IDs and paths as opaque runtime data: copy them from tool outputs, do not synthesize them.

## Session Binding

- Before preparing logpoints/breakpoints or launching, call `xdebug_get_debugger_status`.
- If an active relevant session exists, continue inside it instead of starting another.
- Capture the exact `sessionId` from status/start and reuse it in all session-scoped calls.
- If a session stops, times out, or disappears, do not reuse the old `sessionId`; refresh with `xdebug_get_debugger_status` first. After the paused location changes, re-read `frameIndex`/`path` from a fresh `xdebug_get_stack`.

## Run Configuration Resolution

- Resolve `configurationName` only from `get_run_configurations`; do not pass a test method name or other derived identifier.
- Use `supportsDynamicLaunchOverrides` from `get_run_configurations` as the source of truth for `programArguments`, `workingDirectory`, and `envs`.
- Use launch overrides only when they materially improve reproducibility/observability and the run config supports them.

## Breakpoint And Logpoint Ownership And Hygiene

- Start with `xdebug_list_breakpoints` and treat returned `owner` as source of truth (`user`/`agent`). Logpoints appear here too.
- Snapshot the **full** baseline of each breakpoint you may touch — `enabled`, `logExpression`, `condition`, `isLogMessage`, `isLogStack`, `suspendPolicy`, and `temporary` (all returned by `xdebug_list_breakpoints`). You need this because a `breakpointId`-mode update rewrites the whole breakpoint (see Targeting Modes).
- Avoid broad breakpoint churn between iterations — change the minimum set needed for the next probe.
- `xdebug_remove_breakpoint` defaults to `owner: "agent"`; global cleanup needs two calls: `owner: "agent"` then `owner: "user"`.

## Breakpoint And Logpoint Targeting Modes

`xdebug_set_breakpoint` (whether or not you pass `logExpression`) has two mutually exclusive modes — never mix in one call:
- **Location mode**: pass `filePath` + `line` (1-based); omit `breakpointId`.
- **`breakpointId` mode**: pass `breakpointId` (an opaque canonical id from a prior set/list response).

`breakpointId` mode rewrites the whole breakpoint, it does not patch it. Treat an update as "write the full breakpoint", never "tweak one flag".

After each call, inspect the returned `lineText` and confirm the excerpt matches the intended line. A successful response does not prove `condition`/`logExpression` is valid; verify via `breakpointErrorsTail` / `tracepointOutputsTail` after the next run.

## Core Workflow

1. Scope the failure: capture exact error text and expected vs actual; identify 2–5 candidate anchors and the value at each that would confirm/refute a hypothesis.
2. Prepare: `xdebug_get_debugger_status` → reuse a relevant session or plan a new one; pick `AUTO`/`ASSISTED`/`HYBRID`; install logpoints first and verify each `lineText`.
3. Run: reuse an active session, or call `xdebug_start_debugger_session` and let the scenario run (logpoints do not suspend).
4. Collect: call `xdebug_control_session` with `action: "DRAIN_EVENTS"`; map each output line to source + hypothesis.
5. Escalate only if needed: if a logpoint cannot capture the needed object graph or interactive evidence, add a suspending breakpoint at the proven-relevant line, then call `xdebug_control_session` with `action: "WAIT_FOR_PAUSE"` and inspect stack + values.
6. After every `RESUME` of a suspended session, always call `xdebug_control_session` with `action: "WAIT_FOR_PAUSE"`.
7. On wait timeout: call `PAUSE`, re-check enabled breakpoints and the expected path; after 2 consecutive timeouts on the same wait, stop retrying and expand logpoint coverage.
8. Continue until the first incorrect state transition is proven or you have a clearly stated blocker; then summarize root cause with concrete evidence.

## Default First Probe

For a reproducible runtime issue:
1. Call `xdebug_get_debugger_status`.
2. Reuse an active relevant session, otherwise install a logpoint with `xdebug_set_breakpoint`, `filePath`, `line`, `logExpression`, and `suspendPolicy: "NONE"`.
3. If no relevant session exists, call `xdebug_start_debugger_session`.
4. Call `xdebug_control_session` with `action: "DRAIN_EVENTS"` to read logpoint output.
5. Map output to source; escalate to a suspending breakpoint + `xdebug_get_stack` / `xdebug_get_frame_values` only if logpoints are insufficient.

## Tool Reference

The script only exposes the following official debugger/run-configuration tools. The live MCP contract is the source of truth for exact parameters and constraints; inspect it with `scripts/idea-debug.py <tool> --help` before calling a tool when needed.

| Tool | Purpose |
|---|---|
| `xdebug_set_breakpoint` | Set or update breakpoints and logpoints. |
| `xdebug_start_debugger_session` | Start debugging a run configuration or code location. |
| `xdebug_get_debugger_status` | List sessions and their states. |
| `xdebug_control_session` | Control a session, drain events, and wait for pauses. |
| `xdebug_get_threads` | List threads in a suspended session. |
| `xdebug_get_stack` | Read a thread's call stack. |
| `xdebug_get_frame_values` | Read locals and values in a frame. |
| `xdebug_get_value_by_path` | Inspect nested values by path. |
| `xdebug_evaluate_expression` | Evaluate an expression in a paused frame. |
| `xdebug_remove_breakpoint` | Remove breakpoints/logpoints by owner or location. |
| `xdebug_list_breakpoints` | List breakpoints/logpoints and ownership. |
| `xdebug_run_to_line` | Continue a suspended session to a line. |
| `xdebug_set_variable` | Mutate a value in a suspended frame. |
| `get_run_configurations` | Discover run configurations and runnable locations. |
| `execute_run_configuration` | Run a configuration without debugging. |

A few direct-call examples:

```bash
scripts/idea-debug.py xdebug_set_breakpoint \
  '{"filePath":"<p>","line":42,"logExpression":"value + 1","suspendPolicy":"NONE"}'
scripts/idea-debug.py xdebug_control_session '{"action":"DRAIN_EVENTS"}'
scripts/idea-debug.py xdebug_evaluate_expression \
  '{"sessionId":"xxx","frameIndex":0,"expression":"user.getName().trim()","depth":0}'
```

## Events, Logpoints, And Tracepoints

Logpoint and tracepoint output is buffered as **debugger events** on the session; consume it by draining, not by reading a console or file.

- **Read logpoint output:** call `xdebug_control_session` with `action: "DRAIN_EVENTS"`; it returns buffered output in `tracepointOutputsTail` (`xdebug_set_breakpoint` with `logExpression`, or `isLogMessage` / `isLogStack`).
- **Each event maps back to source.** A drained event carries the evaluated `message`, plus `breakpointId`, `filePath`, `line`, and a timestamp — use these to attribute every line to the logpoint and hypothesis that produced it. Distinguish logpoints by location/expression so concurrent or interleaved hits stay separable.
- **Drain is consuming:** events are removed from the buffer when drained, so each call returns only output produced since the last drain. Drain after the scenario finishes; for long-running or high-volume scenarios, drain periodically during the run so the bounded buffer does not overflow and drop the oldest events. Use `eventsLimit` to cap how many are returned per call.
- **Errors come back as events too:** every `xdebug_control_session` response carries `breakpointErrorsTail` with breakpoint/logpoint validation or runtime errors (e.g. a bad `logExpression`). After installing any logpoint/condition/tracepoint, do not trust it until you have drained and read both tails.
- Event tails are currently populated by JVM-based debuggers (Java, Kotlin, etc.).

## Expression Discipline

- `logExpression` and `condition` run in the program; keep them side-effect-free (see Safe Logpoint Expressions).
- `expression` (`xdebug_evaluate_expression`) runs in the current paused frame; pass raw expression text in that frame's language.
- `newValue` (`xdebug_set_variable`) must be a raw expression assignable to the target value.
- JSON string values should contain the original expression text. Do not pre-evaluate an expression or alter its meaning to fit transport formatting.
- Prefer fully-qualified names for global/static symbols in `condition`, `logExpression`, and `expression` to avoid unresolved-reference errors from missing imports.
- If paused, preflight a risky condition/log expression with `xdebug_evaluate_expression` before relying on it.

## Anti-Patterns

- adding temporary `print`/log statements to source (or trying to capture logpoint output to a file) instead of installing a logpoint and draining its events;
- concluding from a logpoint without draining events (`DRAIN_EVENTS`), or assuming a re-drain will return output already consumed by an earlier drain;
- defaulting to suspending breakpoints when a non-suspending logpoint would answer the question;
- using side-effecting log/condition expressions without explicit user consent;
- placing a logpoint on the line that initializes the variable it logs (or inside a multi-line assignment), so the variable is not yet initialized when the expression runs;
- claiming root cause without runtime values;
- invoking tools outside the supported `idea-debug` allowlist;
- encoding omitted properties with placeholder strings;
- reusing stale `sessionId`/`frameIndex`/`path` after the paused location changes;
- mixing location mode and `breakpointId` mode in one call;
- updating a breakpoint by id without re-passing its full state, clobbering a user's `logExpression`/`condition` or resetting its log/suspend flags;
- stopping at a downstream symptom without tracing producing state;
- asking the user to reproduce before probes are prepared;
- `RESUME` without a justified expected next stop;
- prolonged static-only analysis when one logpoint probe can disambiguate;
- ignoring library frames instead of reading their decompiled source.

## Wrap-up

After debugging:
1. Clean up: call `xdebug_remove_breakpoint` with `owner: "agent"`, restore disabled user breakpoints to baseline, and call `xdebug_control_session` with `action: "STOP"` if the session is no longer needed.
2. Report: root cause in one sentence; causal chain in 3–6 bullets; runtime evidence with exact observed values; code references (absolute path + line); if you fell back instead of debugging, the exact reason and what evidence is still missing.
3. Next action: if the user asked for diagnosis only, conclude with the report and a recommended fix; if the task implies a code change, implement the fix based on the proven root cause and collected evidence.
