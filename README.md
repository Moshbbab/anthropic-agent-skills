# Anthropic Agent Skills Archive

Personal archive of [anthropics/skills](https://github.com/anthropics/skills) focused on document handling skills (docx, pdf, pptx, xlsx) and core Agent Skills patterns. This repo also works as a **Claude Code plugin marketplace** (see below) for the skills that are safe to redistribute.

**Note:** Original repo name `skills` was taken by a ClawdHub historical archive, so this is named `anthropic-agent-skills`.

## Plugin Marketplace

This repo registers as a Claude Code plugin marketplace via [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json). In an interactive Claude Code session (terminal or desktop — the `/plugin` command isn't available on Claude Code on the web):

```
/plugin marketplace add Moshbbab/anthropic-agent-skills
/plugin install skill-creator@anthropic-agent-skills
```

Only Apache-2.0-licensed skills are packaged as installable plugins here (currently [`skills/skill-creator`](./skills/skill-creator)). See the licensing note below for why the document skills are excluded.

## Document Skills

These power Claude's document capabilities upstream:

- [`skills/docx`](https://github.com/anthropics/skills/tree/main/skills/docx) - Word document creation, editing, track changes, comments
- [`skills/pdf`](https://github.com/anthropics/skills/tree/main/skills/pdf) - PDF read/create/merge/split/forms/OCR
- `skills/pptx` - PowerPoint (not mirrored here, see below)
- `skills/xlsx` - Excel (not mirrored here, see below)

**Licensing note:** `docx`, `pdf`, `pptx`, and `xlsx` in the upstream repo are **source-available, not open source** — their `LICENSE.txt` explicitly prohibits extracting, copying, or redistributing those materials outside Anthropic's own Services. Only their `SKILL.md` files (`docx`, `pdf`) are kept here as personal reference notes; the full skill directories (scripts, schemas) are intentionally **not** mirrored, and none of the four are listed in the plugin marketplace above. `skill-creator` and most other "example skills" in the upstream repo are Apache 2.0 and don't carry this restriction.

## Core Agent Skills Patterns

- [`skills/skill-creator`](./skills/skill-creator) - Create, iterate on, and benchmark new Agent Skills (drafting SKILL.md, running evals, optimizing trigger descriptions). Also installable as a plugin — see [Plugin Marketplace](#plugin-marketplace) above.

## Status

- Forked / archived: 2026-08-04
- Purpose: Personal collection for multi-platform AI agent system (Claude, Codex, Gemini, MCP)
- Testing: Document skills verified operational in local environment (sample PDF + DOCX generated)

## Related Personal Repos

- [claude-skills](https://github.com/Moshbbab/claude-skills) - Comprehensive community skills (alirezarezvani)
- [codex-plugin-cc](https://github.com/Moshbbab/codex-plugin-cc) - OpenAI Codex <-> Claude Code bridge
- [skills-mcp](https://github.com/Moshbbab/skills-mcp) - MCP bridge for skills
- [MY-appraisal-ai-skills](https://github.com/Moshbbab/MY-appraisal-ai-skills) - Personal real-estate valuation skills

## Next Steps

1. Curate high-value document + valuation skills into a unified personal layer
2. Test multi-platform compatibility via MCP
3. Integrate with HVOS valuation report generators
