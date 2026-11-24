---
this_file: DEPENDENCIES.md
---

## 2026-11-09 — Issue 242 single distribution

The separate `aidus-code-core` brain distribution was removed in the Aidus Agentus restructure; the brain now ships only as the `[brain]` extra of `fontlab-aidus-agentus`. That extra keeps the seven exact AgentPool/Pydantic AI/provider SDK pins adopted on 2026-11-06: AgentPool 2.9.18 with Pydantic AI 2.66.0 broke real imports (removed `builtin_tools`) despite passing dependency checks. Upgrade the coherent tuple together after real consumer imports and the two-interpreter suite pass. No dependency was added to the embedded Python 3.11 host.

# Dependencies

Transport framing uses the Python standard library incremental UTF-8 decoder;
no dependency was added. API reference: [Python3.11 codecs](https://docs.python.org/3.11/library/codecs.html#incrementaldecoder-objects).

The embedded base has no external runtime dependencies. PythonQt and fontlab are provided by the host.

The Scripts-menu helpers add no dependencies. They use host PythonQt single-shot
QTimer instances and QDesktopServices with local-file QUrls; file creation uses
stdlib pathlib's exclusive-create mode. References consulted for this follow-up:
[QTimer](https://doc.qt.io/qt-6/qtimer.html),
[QDesktopServices](https://doc.qt.io/qt-6/qdesktopservices.html),
[PythonQt](https://mevislab.github.io/pythonqt/),
[pathlib](https://docs.python.org/3.11/library/pathlib.html), and
[uv package installation](https://docs.astral.sh/uv/pip/packages/).
The target FontLab PythonQt binding still needs a live launcher check.

The brain extra requires external Python 3.13+ through AgentPool 2.8.8's own Python requirement. PydanticAI slim and graph are pinned to 1.50.0: clean resolution originally selected 2.55.0, which removed `pydantic_ai.builtin_tools` required by AgentPool 2.8.8. Provider SDKs retain the verified versions: OpenAI 2.16.0, Anthropic 0.77.0, Mistral 1.9.11 and Google GenAI 1.61.0. OpenAI major 3 and Anthropic major 1 broke constructor compatibility: their new HTTPX2 clients reject the HTTPX clients passed by PydanticAI 1.50. AgentPool provides the existing coding agent and production ACP implementation. fontlab-remopy (>=1.2.0, the first release with the mcp.relay module) owns native remote control and SDK relay; mcp 1.x, AnyIO 4.x provide transport. Retained supporting dependencies are PyYAML, structlog, Pydantic, pydantic-settings, HTTPX, aiofiles and ag-ui-protocol. hatchling and hatch-vcs build tag-versioned artifacts; pytest and pytest-asyncio run tests.

API references checked: AgentPool 2.8.8 installed source (`agentpool.models.manifest`, `agentpool_server.acp_server.acp_agent`), MCP v1.26 installed source (`stdio_client`, `ClientSession`); https://doc.qt.io/archives/qt-5.15/qprocess.html (QByteArray readers and two-argument finished signal), https://mevislab.github.io/pythonqt/ (embedded binding).

## Re-evaluation 2026-10-15 (R046)

- The in-FontLab base and the `Scripts/Aidus Agentus/` launchers have no pip dependencies.
- `[brain]` runs in a separate CPython >=3.13 (AgentPool 2.8.8 requirement), never in
  FontLab's Python 3.11.
- `acp` (`acp_server.py`) is vendored inside the agentpool 2.8.8 wheel; it is not a
  separate distribution, and the agentpool pin covers it.
- Provider SDKs (openai 2.16.0, anthropic 0.77.0, mistralai 1.9.11, google-genai 1.61.0),
  pydantic-ai-slim/pydantic-graph 1.50.0 and ag-ui-protocol <0.2 are pinned for
  AgentPool 2.8.8 compatibility. Each is one or more major versions behind (latest:
  openai 3.31, anthropic 1.14, mistralai 3.2, google-genai 2.31, pydantic-ai 2.56,
  ag-ui-protocol 1.0). They will not receive upstream fixes.
- Review trigger: review the whole set when AgentPool publishes a release built on
  PydanticAI 2.x (the latest is 2.9.18, 2026-04-05), or when a security advisory
  affects a pinned SDK, AgentPool or pydantic-ai. Change the pins only together,
  and only after a full brain suite run.
- mcp stays `>=1.26,<2`, matching fontlab-remopy. MCP 2.x (2.3.0) exists; migrating is
  planned, separate work, never an implicit upgrade.
- Licences: all MIT, Apache-2.0, BSD-3-Clause, or MIT OR Apache-2.0.

## 2026-10-16 (issue 106)

- The dev extra adds `pytest-cov` (coverage 7.x; MIT/Apache-2.0) to measure all
  three packages. Coverage runs with `core = "sysmon"` (Python 3.12+
  sys.monitoring) and its subprocess patch, configured in pyproject.toml.
- The new installer and tests use only the standard library. The host-side test
  environment (`.venv-host`) holds pytest, pytest-asyncio, pytest-cov and
  fontlab-remopy without dependencies, mirroring what FontLab itself imports.


## Documentation only

A separate Python 3.13 environment installs fly-january 0.4.0 or later (remote theme assets) for the site's
FontLab menu and footer. `src_docs/requirements.txt` locks the theme and its
build dependencies by hash, including ProperDocs 1.6.7, MkDocs 1.6.1,
MaterialX 10.1.8 and PyMdown 11.0.1.
