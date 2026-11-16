---
this_file: src_docs/md/guides/fontlab-mcp.md
---

# FontLab MCP in Aidus Agentus

When the brain starts, it checks FontLab's native MCP server. If the bridge
returns a non-empty tool catalogue within eight seconds, the agents use native
MCP. Otherwise they fall back to the plugin executor and its sandbox. A bridge
that only initializes has not reached FontLab: discovery needs `tools/list`.

Bridge discovery, the authenticated transport and the SDK relay live in
[fontlab-remopy](https://github.com/fontlabcom/fontlab-remopy); Aidus calls them
(`src/fontlab_aidus_agentus/core/fontlab_mcp.py`).

## Setup

1. Install the brain environment as in the [README](../index.md). Remopy must
   be installed there. The enablement menu/helper also needs Remopy installed
   and importable in FontLab's host Python; the brain installation alone is
   insufficient. Follow the README's host `--no-deps` installation step.
2. Start FontLab 9 and enable **Preferences > Aidus > Allow external MCP clients
   to control FontLab**, or run **Enable FontLab MCP** from the Aidus Agentus
   Scripts menu.
3. Reconnect Aidus so the brain checks the server again.

The menu script calls Remopy's `enable_mcp()`. It sets the `mcp.enabled`
preference and calls `fontlab.flItems.notifyPreferencesChanged()`, which the
listener observes. No FontLab restart or font edit is needed. Do not keep a
Preferences dialog open with the old unchecked value and apply it later: that
disables MCP again.

The standalone script `run_in_fontlab/enable_fontlab_mcp.vfpy` does the same
in a FontLab session where the host can import Remopy (macOS, from the
repository root):

```bash
open -a '/Applications/FontLab 9.app' "$PWD/run_in_fontlab/enable_fontlab_mcp.vfpy"
```

You do not need to run `fontlab-mcp` as a background service. The brain launches
it as a child process and talks MCP over stdio. Started by hand, it just waits
for JSON-RPC input; it does not start FontLab or enable access.

Aidus looks for the bridge in this order: `AIDUS_FONTLAB_MCP_COMMAND`, then
Remopy's `FONTLAB_MCP_COMMAND`, `fontlab-mcp` on
`PATH`, `/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp`, then
`~/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp`. The bridge talks to
FontLab over local TCP at `127.0.0.1:47400`; it is not an HTTP server. It reads
the per-user authentication token itself, so never copy a token into
configuration.

For a development build, export the bridge path in the brain's environment:

```bash
export AIDUS_FONTLAB_MCP_COMMAND=/path/to/your/build/mcpbridge/fontlab-mcp
```

Use a bridge that matches the running FontLab build. The variable holds one
executable path, spaces included, not a shell command. If that explicit path is
unavailable, Aidus uses the plugin backend; it does not try another bridge.

Set `AIDUS_FONTLAB_MCP=off` to force plugin execution. The default is `auto`.
Both are process environment variables. The host JSON configuration does not
forward them to the brain.

The relay (`fontlab_remopy.mcp.relay`) drops an `isError: null` field from
successful results. FontLab build 9780 sent that value, and strict SDK
clients reject it. Real tool errors and RPC errors pass through unchanged.

## Behaviour

- The copilot gets every tool the server reports, with its schema.
- The analyst gets a fixed list of known read-only tools. Read/write tools,
  scripts and unknown future tools are left out.
- The coder gets those inspection tools plus `run_python`.
- The plugin shows native tool notifications without executing the operation
  again. Assistant text chunks are collected into complete chat rows.
- Without MCP, the three plugin tools (`get_current_glyph_info`,
  `set_glyph_metrics`, `run_fontlab_script`) run through the ACP extension
  method `fontlab/tool` (`_fontlab/tool` on the wire). The plugin registry, validation and script sandbox
  still apply.
- ACP uses protocol version 1 and slash-separated method names. Sessions stay
  in memory.

`run_python` runs in FontLab's main Python environment under its native MCP
execution policy, not in the plugin sandbox. The server choice is fixed when the
brain starts. If FontLab stops or disables MCP later, tools report errors;
reconnect Aidus. A mutation that timed out is never replayed automatically.

## Verification

`tests/` and `tests/core/test_mcp_roundtrip.py` start a real SDK stdio
server and the production brain with a deterministic model. They cover the ACP
client, MCP execution, plugin fallback, timeouts and process cleanup without a
provider call or font edit. Run them with `./test.sh`.

For a live check, enable MCP and ask Aidus to list open fonts. The brain's
stderr logs `starting_acp_server` with `backend: mcp` or `backend: plugin`.
Compare the returned font list with FontLab. The repository tests cannot prove
that your FontLab installation has external MCP enabled.

See [the source and installation audit](fontlab-installations.md) and
[external-agent MCP setup](external-agents-mcp.md).
