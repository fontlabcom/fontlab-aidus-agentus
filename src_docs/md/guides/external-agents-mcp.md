---
this_file: src_docs/md/guides/external-agents-mcp.md
---

# Configure external agents for FontLab MCP

Checked against FontLab 9.0.9780 source and a local Codex CLI on 2026-10-13,
before the migration into this repository. OpenCode configuration follows its
official documentation; the OpenCode connection itself was not tested. This
guide changes no agent configuration; you apply it yourself.

## Connection and activation

Configure a **local stdio MCP server**. The agent starts a bridge subprocess;
the bridge authenticates to the running FontLab application's local TCP server.
There is no HTTP `/mcp` URL and no bearer token to put in agent configuration.

Start FontLab and enable **Preferences > Aidus > Allow external MCP clients to
control FontLab**, then apply Preferences. Alternatively, run this inside
FontLab with `fontlab-fly >=1.3.0` and its providers installed in FontLab's
scripting Python environment:

```python
from fly import fl
fl.flPreferences().load({"mcp.enabled": True})
fl.flItems.notifyPreferencesChanged()
```

On macOS, this repository's helper can start FontLab and perform activation
provided Remopy is already installed and importable in FontLab's host Python
(see the README host `--no-deps` installation step). Installing Remopy only in
the external brain/client environment is insufficient. The Fly API snippet
above requires Fly in FontLab, but does not require Remopy.

```bash
open -a '/Applications/FontLab 9.app' "$PWD/run_in_fontlab/enable_fontlab_mcp.vfpy"
```

Run that command from this repository's root. Restart/reconnect the external
agent's MCP connection after enabling the listener. Do not start a separate
background bridge: the external agent owns the bridge process.

## macOS: Codex CLI

Native bridge registration:

```bash
codex mcp add fontlab -- '/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp'
codex mcp get fontlab
```

Equivalent `~/.codex/config.toml` section:

```toml
[mcp_servers.fontlab]
command = "/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp"
args = []
```

The local `codex mcp add --help` confirms this stdio syntax, and
`codex mcp get fontlab` currently reports this native bridge configuration as
enabled. That verifies registration, not a tool call. Start a new Codex session
and ask it to use FontLab's `list_fonts` tool to check execution.

## macOS: OpenCode

Add this to project `opencode.json`, or merge the `mcp` entry into the global
`~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "fontlab": {
      "type": "local",
      "command": ["/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp"],
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

OpenCode's `command` is an argv array, so a path containing spaces remains one
element. `timeout` is milliseconds. Use `opencode mcp list` to check discovery,
then ask OpenCode to invoke `list_fonts`. These fields and the config locations
are documented in [OpenCode MCP servers](https://opencode.ai/docs/mcp-servers/)
and [OpenCode configuration](https://opencode.ai/docs/config/).

## Compatibility with FontLab build 9780

The native bridge in build 9780 can relay a successful result with
`isError: null`, which strict MCP SDK clients reject. If that affects your
agent, put the SDK normalization relay from fontlab-remopy in front of the
bridge. The relay needs no LLM API key. Any Python 3.11+ environment with
fontlab-remopy installed works, for example the Aidus brain environment from the
[README](../index.md). The Codex configuration then becomes:

```toml
[mcp_servers.fontlab]
command = "/absolute/path/to/brain/bin/python"
args = ["-m", "fontlab_remopy.mcp.relay", "/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp"]
```

For OpenCode, replace its `command` array with:

```json
[
  "/absolute/path/to/brain/bin/python",
  "-m",
  "fontlab_remopy.mcp.relay",
  "/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp"
]
```

Aidus Agentus has no relay of its own; use `fontlab_remopy.mcp.relay`. Keep the OpenCode `type`, `enabled` and `timeout` fields from the
complete example. Native SDK and live ACP roundtrips through this relay were
verified on 2026-10-13; no OpenCode tool call was verified.

## Windows

The inspected Windows FontLab 9.0.9780.0 installation contains MCP server code
but **does not include `fontlab-mcp.exe`**. Therefore there is no working native
stdio configuration for that installation until a matching Windows bridge is
provided. Changing an agent config cannot supply the missing executable.

Once a matching Windows bridge is installed at the example path below, native
Codex CLI registration from PowerShell is:

```powershell
codex mcp add fontlab -- 'C:\Program Files\Fontlab\FontLab 9\fontlab-mcp.exe'
codex mcp get fontlab
```

Equivalent TOML uses a literal string for Windows backslashes:

```toml
[mcp_servers.fontlab]
command = 'C:\Program Files\Fontlab\FontLab 9\fontlab-mcp.exe'
args = []
```

For OpenCode use the same complete JSON object as on macOS, replacing
`command` with this array (JSON requires doubled backslashes):

```json
["C:\\Program Files\\Fontlab\\FontLab 9\\fontlab-mcp.exe"]
```

These Windows paths are conditional examples, not files found in the installed
bottle. Use the actual path supplied with a compatible Windows bridge. Run
FontLab, the bridge and the agent as the same Windows user so the bridge can
read `%LOCALAPPDATA%\FontLab\MCP\token`.

For a macOS agent targeting CrossOver FontLab, a Windows bridge would need to
run through Wine in the **same bottle**, so it resolves the Windows token.
The current macOS bridge reads the macOS token and has no token-file override.
Such a host-to-bottle configuration is not currently provided or verified.
See [the installation audit](fontlab-installations.md).

## Port number

The port is **hardcoded to 47400** in both:

- `Proteus/common/mcp/mcpserver.cpp`: `MCP_PORT`.
- `Proteus/mcpbridge/main.cpp`: `APP_PORT`.

The current implementation has no preference, command-line argument or
environment variable for changing it. There is no port field to add to the
stdio agent configuration. Changing the port requires modifying and rebuilding
both the listener and its bridge, or first implementing coordinated port
configuration. If native macOS and CrossOver share localhost, they cannot both
bind this port at once.

Bridge initialization alone is insufficient verification because it can succeed
without contacting FontLab. Check `tools/list`, then a read-only `list_fonts`
call against the intended application.
