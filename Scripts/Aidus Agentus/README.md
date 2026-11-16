---
this_file: Scripts/Aidus Agentus/README.md
---
# Aidus Agentus scripts for FontLab 9

These are the only scripts to expose in FontLab's Scripts menu. The orchestrator
links this folder into FontLab's Scripts folder; these scripts create no links.
They import the installed package, so copying this folder alone is insufficient.
Install the **current checkout's host package** first (the v0.2.0 release predates
these entry points). See [installation](../README.md) and [configuration](../CONFIGURE.md).

| Script | What happens |
| --- | --- |
| Start Aidus Agentus.py | Opens the chat dock, or shows the existing dock. |
| Enable FontLab MCP.py | Enables the native MCP listener through installed `fontlab-remopy`. Reconnect the dock afterward. |
| Open Configuration.py | Opens the loaded JSON file in your default application, or the first existing file for repair. If none exists, creates a minimal `~/.config/aidus_agentus/config.json` (or `AIDUS_CONFIG`). Existing files are preserved. |

Run these **inside FontLab 9**, not in a terminal. Enablement needs Remopy on
FontLab's Python path as well as in the external brain environment. The helper
changes `mcp.enabled` and notifies FontLab; it does not save all preferences.
For persistent setup, use FontLab Preferences > Aidus > Allow external MCP clients
to control FontLab.

Each launcher queues work on FontLab's Qt event loop and returns promptly to
respect the five-second script deadline. The brain may take longer to connect;
watch the dock and FontLab Output panel. No AI libraries load during the menu
script. Configuration is read on startup: after editing it, run
`fontlab_aidus_agentus.shutdown()` in FontLab, then Start Aidus Agentus again.
