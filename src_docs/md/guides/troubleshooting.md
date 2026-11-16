---
this_file: src_docs/md/guides/troubleshooting.md
---
# Troubleshoot Aidus Agentus

Start with FontLab's Output panel and the dock's error messages. Never paste
provider key values or private chat history into a report.

| Symptom | Check / fix |
| --- | --- |
| Menu script says to install/update the package | Install this checkout's host package, then add its host folder to FontLab's Python path as in [README](../index.md). Installing only in the brain environment does not install the host. The v0.2.0 wheel predates the new launcher helpers. |
| `fontlab-remopy` is missing during installation | Supply the downloaded Remopy wheel or a maintained Remopy source checkout explicitly alongside `'.[brain]'` / `'.[brain,dev]'`. It may be absent from the registry. |
| Enable FontLab MCP reports a missing dependency | Also install Remopy into the host folder using `--no-deps`; the native enable helper does not need external AI/MCP libraries in FontLab. |
| Script says to run inside FontLab | Run it from FontLab 9's Scripts menu. A terminal Python does not supply FontLab's PythonQt runtime. |
| No dock appears / action reports `RuntimeError` | Set `python_exe` to an existing external Python 3.13+ executable; check `AIDUS_PYTHON` is not overriding it. Watch Output after the queued action runs. |
| Brain exits with an import error | Install the declared brain extra into that exact interpreter. Keep the verified dependency pins in `pyproject.toml`; the host's Python 3.11 cannot run AgentPool. |
| Configuration edits have no effect | Check `_loaded_from` using [CONFIGURE](../configure.md). A package-local file may take priority. Shut down and start the dock again; Reconnect reuses host settings/key mappings. |
| Configuration is skipped as invalid or not UTF-8 | Output identifies the affected path and reason. Open that file in a text editor and save a UTF-8 JSON object, with double quotes and no comments/trailing commas. Open Configuration can open an existing invalid file for repair when no valid file loads; it never replaces the original contents. With `AIDUS_CONFIG`, an invalid file produces defaults. |
| Open Configuration does not show an editor | Its path is printed in Output. Open that file in a text editor yourself; a system association for JSON is required for automatic opening. Existing content is never replaced. |
| Key check is false / provider rejects a request | Check private file existence, permissions and `env:` spelling without printing contents. Variables must be in FontLab's environment. A true availability check does not prove the key/account/model is valid. |
| Missing Anthropic credentials despite an OpenAI copilot | The bundled manifest also constructs an Anthropic coder. Configure both providers or copy and edit the manifest to use your chosen provider for every agent. |
| Model is unavailable / wrong model responds | Edit your private manifest and set `AIDUS_AGENTS_CONFIG` to its absolute path. The dock has no model picker; production selects `fontlab_copilot`. |
| Dock connects but native MCP is unavailable | Enable external MCP access in FontLab Preferences > Aidus, check the bridge and running FontLab, then Reconnect. Native discovery can take up to eight seconds before fallback. |
| Brain termination outcome unknown | Shutdown retains the process and dock; reconnect refuses to start a replacement until exit is confirmed. Inspect the identified brain process and wait for its completion signal, or retry shutdown after reconciliation. Do not treat a failed wait as proof that an edit stopped. |
| Response timeout / disconnected during an edit | Inspect the font before retrying; an edit might already have happened. Reconnect starts a fresh session and never replays edits. Increase positive `timeout_seconds` only if requests need more time. |
| `fontlab-aidus-acp` appears silent in a terminal | It is a stdio protocol server waiting for an ACP client, not an interactive chat command. Ctrl-D / EOF shuts it down. |

## Check the two installations

In FontLab's Python console:

```python
import fontlab_aidus_agentus
print(fontlab_aidus_agentus.__version__)
print(fontlab_aidus_agentus.__file__)
from fontlab_aidus_agentus.plugin.config import load_config
c = load_config()
print(c.get("_loaded_from", "defaults"), c.get("python_exe"))
```

In a terminal, using your configured brain interpreter:

```sh
/absolute/path/to/brain/bin/python -c 'import sys, importlib.metadata as m; print(sys.version); print(m.version("fontlab-aidus-agentus")); print(m.version("agentpool")); import fontlab_remopy'
```

Do not print the complete config or child environment: they can contain private
paths or inherited secrets. The retained `check_health()` helper checks manifest
shape; it does not prove provider authentication, native MCP reachability or a
working GUI. A successful read-only chat/tool request checks the actual connection.

## Verification boundaries

The repository suite runs without FontLab, using mocks and a real AgentPool
TestModel ACP subprocess. Its launcher tests verify imports, script size,
deferred work, failure guidance and configuration preservation. Actual dock
rendering, PythonQt timers, system editor associations, Scripts-menu discovery
and the five-second deadline still need verification in the target FontLab build.
The historical v0.2.0 native results in [RELEASE.md](https://github.com/fontlabcom/fontlab-aidus-agentus/blob/b41fac3ae9d0719d07dd56eb5150c56725cc09b3/RELEASE.md) cover that
release, not these new scripts. CrossOver/Windows and interactive external-editor
behavior are not established by those macOS checks.
