# Agent Skills 技能集合

[English](README.en.md)

这是一个面向 AI 编程代理的可复用技能集合。每个技能位于 `.agents/skills/<skill-name>/` 目录中，以 `SKILL.md` 为入口，并可附带参考文档、脚本或资源文件。

## 已包含的技能

| 技能 | 描述 |
| --- | --- |
| [`context7-cli`](.agents/skills/context7-cli/) | 使用 `ctx7` CLI 获取最新的库文档、管理编码技能并配置 Context7 MCP。 |
| [`convert-documents-to-markdown`](.agents/skills/convert-documents-to-markdown/) | 将办公文档、电子书、CSV 文件和 PDF 转换为 GitHub Flavored Markdown。 |
| [`create-agentsmd`](.agents/skills/create-agentsmd/) | 为代码仓库创建高质量的 `AGENTS.md` 文件。 |
| [`create-github-action-workflow-specification`](.agents/skills/create-github-action-workflow-specification/) | 为现有 GitHub Actions 工作流创建适合 AI 使用的规范说明。 |
| [`debugging-code`](.agents/skills/debugging-code/) | 在 Rider 支持的项目中，以调试器优先的方式分析运行时根因。 |
| [`find-skills`](.agents/skills/find-skills/) | 从开放的 agent skills 生态中发现并安装技能。 |
| [`idea-database`](.agents/skills/idea-database/) | 通过 IntelliJ IDEA MCP 工具检查数据库连接、模式、对象、查询和查询状态。 |
| [`ij-debugger`](.agents/skills/ij-debugger/) | 在 IntelliJ IDEA 中，以调试器优先的方式分析 JVM 代码运行时问题。 |
| [`playwright-cli`](.agents/skills/playwright-cli/) | 使用 `playwright-cli` 自动化浏览器并处理 Playwright 测试。 |
| [`skill-creator`](.agents/skills/skill-creator/) | 创建、改进和评估 agent skills。 |
| [`tea-cli`](.agents/skills/tea-cli/) | 使用官方 `tea` 命令行工具操作 Gitea。 |

## 仓库结构

- `.agents/skills/` — 技能源目录。
- `skills` — 指向 `.agents/skills` 的便捷符号链接。
- `skills-lock.json` — 从外部来源管理的技能的锁定信息。

## 技能结构

每个技能都包含带有 YAML frontmatter 和操作说明的 `SKILL.md` 文件。较大或专用的内容放在 `references/`、`scripts/`、`agents/` 或 `assets/` 等子目录中，并在需要时加载。

## 添加技能

1. 在 `.agents/skills/` 下创建新的技能目录。
2. 添加 `SKILL.md`，并在 frontmatter 中设置唯一的 `name` 和清晰的 `description`。
3. 将详细参考内容拆分到专门的文件中，并在 `SKILL.md` 中建立链接。
4. 如果技能由外部来源管理，请同步更新 `skills-lock.json`。
