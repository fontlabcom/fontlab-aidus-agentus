---
this_file: src_docs/md/guides/architecture.md
---
# How Aidus Agentus works

FontLab's embedded Python and modern AI dependencies have different interpreter
requirements. Aidus keeps the UI and FontLab API calls in the host and runs
AgentPool in an external child process.

```text
FontLab 9 / Python 3.11 / PythonQt
  Scripts/Aidus Agentus/*.py -> fontlab_aidus_agentus.launchers (queued Qt action)
  fontlab_aidus_agentus.plugin: dock -> ACP client -> QProcess transport
                                           | stdin/stdout JSON-RPC
External Python 3.13+                       v
  fontlab_aidus_agentus.core_launcher -> boot -> fontlab_aidus_agentus.core.boot
  AgentPool 2.8.8 + ACP server -> selected AI provider
                            -> native MCP bridge -> FontLab
                            OR plugin tool request -> embedded executor
```

| Location | Responsibility |
| --- | --- |
| `src/fontlab_aidus_agentus/` | Lazy public `run()`/`shutdown()`, Scripts-menu helpers and production ACP entry points. |
| `src/fontlab_aidus_agentus/plugin/` | PythonQt dock, JSON configuration, request/session state, child transport and fallback FontLab executor. |
| `src/fontlab_aidus_agentus/core/` | AgentPool manifest translation, provider models, ACP service and role-specific FontLab tool policy. |
| `fontlab-remopy` (dependency) | Native bridge discovery, authenticated MCP transport/relay and MCP enablement. |
| `Scripts/Aidus Agentus/` | Three small menu scripts importing installed helpers; no package implementation or credentials. |
| `run_in_fontlab/` | Developer checks and the PythonQt introspector, run inside FontLab by hand. |

The base wheel has no runtime dependencies. `fontlab` and PythonQt come from
FontLab. The optional brain extra installs the pinned AI stack in Python 3.13+.
Imports of the public package or menu helpers never import AgentPool. Qt timers
keep the menu run path short and perform host work on the GUI thread after the
script returns. They do not move FontLab API calls into a worker thread.

## Tool selection

At brain startup, native MCP is selected only if Remopy finds a bridge and its
`tools/list` probe returns a nonempty catalogue. Otherwise the brain imports the
legacy plugin tools. That fallback needs the embedded dock/client to execute
them in FontLab. Native tools use the bridge's own authentication; do not copy
its token into configuration.

The copilot receives discovered native tools. The analyst receives only the
explicit read-only allowlist; the coder receives that allowlist plus `run_python`.
Fallback tools are taken from the agent manifest. Native `run_python` executes
in FontLab's main Python environment; the fallback `run_fontlab_script` uses the
plugin's restricted execution namespace. Inspect results and verify font edits.

## Agents and models

The bundled `agents.yml` declares:

| Agent | Bundled model | Role |
| --- | --- | --- |
| `fontlab_copilot` | `openai:gpt-4o` | Main chat agent, including editing tools. |
| `fontlab_coder` | `anthropic:claude-sonnet-4-20250514` | Script-oriented tools. |
| `fontlab_analyst` | `openai:gpt-4o-mini` | Read-only tools. |

These are bundled identifiers, not a promise of present-day provider availability.
There is no dock model picker or automatic routing between these roles: the
production entry point explicitly selects `fontlab_copilot`. AgentPool constructs
the manifest's agents, so configure the providers referenced by that manifest.

To change models, copy `src/fontlab_aidus_agentus/core/agents.yml` and `prompts/` together to a
private configuration directory, preserving their relative layout. Set
`AIDUS_AGENTS_CONFIG` to the **absolute path** of your copy in FontLab's process
environment before starting Aidus. Edit each agent's `model` to an identifier
supported by the installed PydanticAI version and configure the corresponding
provider key. Keep `fontlab_copilot` present; changing only `default_agent` does
not switch the production entry point. Keep the existing per-agent fields:
`type`, `system_prompt`, `tools`, `max_tokens` and `temperature`. Prompt files
resolve relative to the manifest. TestModel manifests support offline checks
without provider credentials; see the production-entrypoint test.

## Environment reference

Set these in the process launching FontLab (or in its Python console through
`os.environ` before startup). A terminal export alone does not change a running
FontLab process. For an external ACP client, set them in that client's environment.

| Variable | Effect |
| --- | --- |
| `AIDUS_CONFIG` | Sole host JSON path; `~` is expanded. See [CONFIGURE.md](../configure.md). |
| `AIDUS_PYTHON` | Overrides JSON `python_exe`. |
| `AIDUS_AGENTS_CONFIG` | External brain manifest path; use an absolute path, with no `~`. |
| `AIDUS_FONTLAB_MCP` | `off` disables discovery and selects fallback tools; any other value attempts discovery. |
| `AIDUS_FONTLAB_MCP_COMMAND` | Explicit native bridge executable passed to Remopy discovery. |

Host JSON is not the legacy core `Settings` class. Its `core_host`/`core_port`
and `.env` assumptions do not configure the production stdio server.

## Sessions and local data

Transport uses newline-delimited JSON-RPC 2.0 over QProcess stdin/stdout; protocol
version 1 is negotiated through ACP. Brain logging goes to stderr. Matching
session progress renews an outstanding request deadline; idle READY sessions
have no response deadline. A timeout leaves an unknown outcome.

Reconnect stops the child, clears pending/session state and negotiates a new
session. It never replays a submitted request. Host settings and resolved key
mappings are captured at bootstrap, so reload them with `shutdown()` then start.
The dock saves displayed chat entries to `~/.config/aidus_agentus/history.json`;
Clear removes it. `AIDUS_CONFIG` does not relocate history. The brain uses
in-memory session storage, which is independent of the dock's saved entries.

## External clients

`fontlab-aidus-acp` and `aidus-core` invoke `fontlab_aidus_agentus.boot:main` in the
brain environment. An ACP-capable editor can launch that executable with no
arguments, a suitable working directory and provider environment variables.
There is no standalone terminal chat UI. Running the executable manually waits
for protocol messages on stdin.

External clients must supply credentials themselves: the host JSON mappings
are resolved by the embedded plugin, not by this executable. They also need
running FontLab/native MCP for FontLab tool calls; fallback tools depend on an
embedded client. Zed integration was an intended use of this interface; its
interactive UI was not part of the recorded native release verification.
