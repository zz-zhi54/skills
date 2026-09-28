---
name: idea
description: 通过 IntelliJ IDEA MCP 使用 IDEA 的符号索引、源码读取、语义调用层级和重命名重构。需要搜索项目/依赖/JDK 符号、读取依赖或反编译源码、确认真实调用关系，或执行代码符号重命名时使用；普通已知路径的项目文件优先用常规文件工具读取。
---

# IntelliJ IDEA

使用 Python 调用当前 Skill 内的脚本；下例中的 `python scripts/idea.py` 是 `python <已解析的 Skill 目录>/scripts/idea.py` 的简写。需要系统已安装 `mcpc`；若缺失，脚本会报错退出，不会自动安装。保持命令工作目录为当前 dsh 正在处理的项目目录；脚本用该目录作为 `IJ_MCP_SERVER_PROJECT_PATH`，并按项目路径生成稳定的 mcpc session 名。不要手动指定项目路径。参数使用 IDEA Tool 的原始名称和字段；一次只调用以下四个 Tool。需要查看 Tool 定义时使用 `python scripts/idea.py <tool> --help`。

- `search_symbol`：仅在需要 IDEA 索引定位符号时使用，可搜索项目、依赖及 SDK/JDK 符号。已知普通项目源码路径时直接用常规文件工具，不要固定执行 `search_symbol` 后接 `read_file`。
  - 必填：`q`。可选：`paths`（glob 数组）、`include_external`（布尔值）、`limit`（整数）。依赖或 SDK/JDK 符号未命中时再设 `include_external: true`。
- `read_file`：主要读取 IDEA 可解析但普通文件工具不便读取的内容，如依赖/Jar/JDK 源码或反编译 class。必填：`file_path`；可选：`offset`（起始行）、`limit`（行数）。
- `analyze_calls`：需要真实语义调用关系时使用，不要用文本搜索代替。`symbolFqn` 和 `analysisKind` 必填；`analysisKind` 为 `INCOMING_CALLS` 或 `OUTGOING_CALLS`。若名称不明确，先用 `search_symbol` 定位，歧义时使用工具返回的完整签名。可选：`depth`、`maxChildren`、`maxNodes`、`treePath`、`childOffset`、`timeout`。
- `rename_refactoring`：用户要求重命名代码符号时使用 IDEA 语义重构；不要用普通文本替换模拟。`pathInProject`（相对项目根目录）、`symbolName`（精确旧名称）和 `newName` 必填。此操作会修改项目代码，只在任务确实要求重命名时调用。

示例：

```text
python scripts/idea.py search_symbol '{"q":"OrderService"}'
python scripts/idea.py read_file '{"file_path":"/path/to/dependency-source.java"}'
python scripts/idea.py analyze_calls '{"symbolFqn":"com.example.OrderService.create","analysisKind":"INCOMING_CALLS"}'
python scripts/idea.py rename_refactoring '{"pathInProject":"src/main/java/com/example/OrderService.java","symbolName":"create","newName":"createOrder"}'
```
