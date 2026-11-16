---
this_file: src_docs/md/index.md
---

# Aidus Agentus for FontLab 9

Aidus Agentus adds an AI chat dock inside FontLab 9. You can ask about the current
glyph, inspect fonts and metrics, change spacing, or generate and run FontLab
Python code. Responses stream into the dock. The selected AI provider receives
your prompts and the tool results used by the agent; use a disposable font for
your first editing experiments.

The FontLab plugin runs in the host's Python 3.11/PythonQt environment. The AI
brain runs in a **separate Python 3.13+ process**, using AgentPool 2.8.8. Installing
AI libraries into FontLab's embedded Python is unnecessary.

Read [Configure Aidus Agentus](configure.md) for the short setup guide,
[architecture](guides/architecture.md) for the process/tool boundaries, and
[troubleshooting](guides/troubleshooting.md) when something fails.


## Guides

Use [installation](installation.md), [configuration](configure.md), [dock and ACP](dock-and-acp.md) and [development and limits](development-and-limits.md).
The complete existing guides remain available:

- [architecture](guides/architecture.md)
- [external-agents-mcp](guides/external-agents-mcp.md)
- [fontlab-installations](guides/fontlab-installations.md)
- [fontlab-mcp](guides/fontlab-mcp.md)
- [manual-tests](guides/manual-tests.md)
- [troubleshooting](guides/troubleshooting.md)

## Current acceptance

The maintained host/brain split is retained. Active-editor/CurrentGlyph preservation,
M1–M11, provider authentication, dock lifecycle, writer history/persistence and
operational brain cutover still need their separately recorded acceptance.
Legacy repository retirement is already verified; it does not qualify these workflows.
These source/build previews do not establish native or published operation.
