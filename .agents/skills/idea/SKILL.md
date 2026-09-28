---
name: idea
description: 通过 IntelliJ IDEA MCP 使用 IDEA 的符号索引、源码读取、语义调用层级和重命名重构。需要搜索项目/依赖/JDK 符号、读取依赖或反编译源码、确认真实调用关系，或执行代码符号重命名时使用；普通已知路径的项目文件优先用常规文件工具读取。
---

# IntelliJ IDEA

使用 Python 调用当前 Skill 内的脚本；下例中的 `python scripts/idea.py` 是 `python <已解析的 Skill 目录>/scripts/idea.py` 的简写。需要系统已安装 `mcpc`；若缺失，脚本会报错退出，不会自动安装。保持命令工作目录位于当前 DSH 项目中；脚本向上查找最近的 `.git` 目录或文件作为项目根目录（未找到时使用当前工作目录），并将该根目录作为 `IJ_MCP_SERVER_PROJECT_PATH`。mcpc 状态保存在 `<项目根目录>/.dsh/mcpc`，三个 IDEA Skills 共用固定 session `@idea`。不要手动指定项目路径。参数使用 IDEA Tool 的原始名称和字段；一次只调用以下四个 Tool。需要查看 Tool 定义时使用 `python scripts/idea.py <tool> --help`。

查询、搜索、文件读取和调用树等可能返回大量内容的操作，首轮必须限制在较小且相关的范围；只有当前结果不足以继续任务时才逐步扩大范围或分页。工具参数以 [JetBrains 官方 MCP Server 文档](https://www.jetbrains.com/help/idea/mcp-server.html) 为准；本 Skill 的保守限制会单独标明。

- `search_symbol`：仅在需要 IDEA 索引定位符号时使用，可搜索项目、依赖及 SDK/JDK 符号。已知普通项目源码路径时直接用常规文件工具，不要固定执行 `search_symbol` 后接 `read_file`。
  - 必填：`q`。可选：`paths`（glob 数组）、`include_external`（布尔值）、`limit`（整数）。首轮显式使用 `limit: 20`，能缩小范围时优先提供 `paths`；默认只搜索项目符号，没有合适的项目内结果后再设 `include_external: true`。`limit: 20` 是本 Skill 的保守策略，不是官方默认值。
- `read_file`：主要读取 IDEA 可解析但普通文件工具不便读取的内容，如依赖/Jar/JDK 源码或反编译 class。必填：`file_path`。可选参数：`mode`（`slice`、`lines`、`line_columns`、`offsets` 或 `indentation`）、`start_line`、`max_lines`、`end_line`、`start_column`、`end_column`、`start_offset`、`end_offset`、`context_lines`、`max_levels`、`include_siblings`、`include_header`。`slice` 模式使用 `start_line` 和 `max_lines`；`lines` 模式使用 `start_line` 和 `end_line`；`max_lines` 会限制所有模式的总输出行数。普通按行读取优先使用 `mode: "slice"`，并显式设 `max_lines: 200`（这是本 Skill 的保守策略，不是官方默认值）。已知目标位置时从附近开始读取；内容不足时再读取下一段，不要默认一次读取整个文件。不要再使用旧的 `offset`/`limit` 参数。
- `analyze_calls`：需要真实语义调用关系时使用，不要用文本搜索代替。`symbolFqn` 和 `analysisKind` 必填；`analysisKind` 为 `INCOMING_CALLS` 或 `OUTGOING_CALLS`。若名称不明确，先用 `search_symbol` 定位，歧义时使用工具返回的完整签名。可选：`depth`、`maxChildren`、`maxNodes`、`treePath`、`childOffset`、`timeout`。官方默认值为 `depth: 5`、`maxChildren: 50`、`maxNodes: 1000`、`childOffset: 0`；首轮显式限制为 `depth: 2`、`maxChildren: 20`、`maxNodes: 100`。这些首轮值是本 Skill 的保守策略，不是官方默认值。结果被截断时，根据返回的 `treePath` 和 `childOffset` 局部继续展开，不要一开始请求整个调用树。
- `rename_refactoring`：用户要求重命名代码符号时使用 IDEA 语义重构；不要用普通文本替换模拟。`pathInProject`（相对项目根目录）、`symbolName`（精确旧名称）和 `newName` 必填。此操作会修改项目代码，只在任务确实要求重命名时调用。

示例：

```text
python scripts/idea.py search_symbol '{"q":"OrderService","limit":20}'
python scripts/idea.py read_file '{"file_path":"/path/to/dependency-source.java","mode":"slice","start_line":40,"max_lines":200}'
python scripts/idea.py analyze_calls '{"symbolFqn":"com.example.OrderService.create","analysisKind":"INCOMING_CALLS","depth":2,"maxChildren":20,"maxNodes":100}'
python scripts/idea.py rename_refactoring '{"pathInProject":"src/main/java/com/example/OrderService.java","symbolName":"create","newName":"createOrder"}'
```
