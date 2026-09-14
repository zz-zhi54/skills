# Agent Skills Collection

[简体中文](README.md)

A collection of reusable skills for AI coding agents. Each skill is stored in `.agents/skills/<skill-name>/` and is defined by a `SKILL.md` file with optional reference material, scripts, or assets.

## Included skills

| Skill | Description |
| --- | --- |
| [`context7-cli`](.agents/skills/context7-cli/) | Fetch current library documentation, manage coding skills, and configure Context7 MCP with the `ctx7` CLI. |
| [`convert-documents-to-markdown`](.agents/skills/convert-documents-to-markdown/) | Convert office documents, ebooks, CSV files, and PDFs to GitHub-Flavored Markdown. |
| [`create-agentsmd`](.agents/skills/create-agentsmd/) | Create a high-quality `AGENTS.md` file for a repository. |
| [`create-github-action-workflow-specification`](.agents/skills/create-github-action-workflow-specification/) | Create an AI-optimized specification for an existing GitHub Actions workflow. |
| [`debugging-code`](.agents/skills/debugging-code/) | Perform debugger-first runtime root-cause analysis in Rider-supported projects. |
| [`find-skills`](.agents/skills/find-skills/) | Discover and install skills from the open agent skills ecosystem. |
| [`idea-database`](.agents/skills/idea-database/) | Inspect IntelliJ IDEA database connections, schemas, objects, queries, and query status through IDEA MCP tools. |
| [`ij-debugger`](.agents/skills/ij-debugger/) | Perform debugger-first runtime analysis for JVM code in IntelliJ IDEA. |
| [`playwright-cli`](.agents/skills/playwright-cli/) | Automate browsers and work with Playwright tests through `playwright-cli`. |
| [`skill-creator`](.agents/skills/skill-creator/) | Create, improve, and evaluate agent skills. |
| [`tea-cli`](.agents/skills/tea-cli/) | Work with Gitea through the official `tea` command-line tool. |

## Repository layout

- `.agents/skills/` — skill source directories.
- `skills` — convenience symlink to `.agents/skills`.
- `skills-lock.json` — lock information for skills managed from external sources.

## Skill structure

Each skill contains a `SKILL.md` file with YAML frontmatter and instructions. Larger or specialized material is kept in subdirectories such as `references/`, `scripts/`, `agents/`, or `assets/` and is loaded only when needed.

## Adding a skill

1. Add a new directory under `.agents/skills/`.
2. Add a `SKILL.md` with a unique `name` and a useful `description` in its frontmatter.
3. Keep detailed reference material in focused supporting files and link to those files from `SKILL.md`.
4. Update `skills-lock.json` when the skill is managed by an external source.
