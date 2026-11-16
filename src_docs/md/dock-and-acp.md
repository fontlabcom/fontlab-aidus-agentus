---
this_file: src_docs/md/dock-and-acp.md
---

# Dock, package scope and ACP

## Run in FontLab

The root [Aidus Agentus](https://github.com/fontlabcom/fontlab-aidus-agentus/blob/b41fac3ae9d0719d07dd56eb5150c56725cc09b3/Aidus%20Code/README.md) folder holds three thin `.py`
entry scripts and a README for FontLab's Scripts menu. In this workspace the
orchestrator links it into FontLab's Scripts folder. Elsewhere, copy the scripts
with the installer from the host package (run it in a terminal, not in FontLab):

```sh
PYTHONPATH=~/.local/share/fontlab-aidus/host python3 -m fontlab_aidus_agentus.install install
PYTHONPATH=~/.local/share/fontlab-aidus/host python3 -m fontlab_aidus_agentus.install check
```

`--user-folder` selects another FontLab user folder. The installer writes
`Scripts/Aidus Agentus` plus a manifest with the sha256 of each file it wrote.
Your own files in that folder are kept. A script you edited, or a symlink in place
of one, stops `install` before anything changes; `uninstall` removes only the
unmodified files it wrote and the folder only if it is then empty. Each write or
removal re-checks its file first, and an interrupted install is completed by the
next run. A folder (or link) without a valid manifest is never touched. `check`
prints JSON and exits 0 only when the scripts are current and the brain Python
is configured. With a full `pip install`, the same commands are
`fontlab-aidus-install install|check|uninstall`.

1. Run **Open Configuration** to edit the host JSON file.
2. Run **Enable FontLab MCP**, or enable **Preferences > Aidus > Allow external
   MCP clients to control FontLab**. The script enables/notifies the running
   listener; it does not save the full preference set.
3. Run **Start Aidus Agentus**. It queues startup on FontLab's Qt event loop, then
   returns promptly. The separate brain may take longer to connect.
4. Wait for the dock to be ready. Ask: "List the open fonts without changing
   them." A streamed answer verifies a provider call; a tool result also checks
   the FontLab connection.

To start directly from FontLab's Python console:

```python
import fontlab_aidus_agentus
fontlab_aidus_agentus.run()
# Before starting again, or after editing host configuration:
fontlab_aidus_agentus.shutdown()
```

The menu launcher shows an existing dock instead of starting another child.
**Reconnect** starts a fresh child and ACP session using the already loaded host
settings. It discards pending requests and never replays an edit. After changing
host JSON or key files, shut down and start again to reload them. Idle sessions
stay connected. A response timeout means the outcome may be unknown; inspect
the font before resubmitting an edit.

Chat entries are saved locally to `~/.config/aidus_agentus/history.json` (newest
500 rows, at most 2 MB, messages cut at 20,000 characters) and reappear when the
dock starts; **Clear** clears the dock and removes
that file. There is no model picker in the dock. Metric edits made through the
fallback tools are one Edit > Undo step ("Aidus: Set Glyph Metrics"). Brain
warnings and errors appear in FontLab's Output panel as `[Aidus brain]` lines
(at most 50 per brain process); if the brain exits with an error, the dock shows
its exit code and last five messages.

## The dock (GUI)

The graphical part is `src/fontlab_aidus_agentus/plugin/ui.py`: `AidusAgentusDock`, a PythonQt
`QDockWidget` that docks left or right in FontLab 9 and is the only window Aidus
adds. It has a status label (connected or disconnected), **Reconnect** and **Clear**
buttons, a read-only chat transcript with a colour per role (user, assistant, tool
call, tool result, error), a "Thinking..." indicator and a one-line input field.
`src/fontlab_aidus_agentus/plugin/main.py` creates it, `client.py` feeds it streamed updates and
`transport.py` owns the brain process. It runs in the host and uses no PySide2.
The dock is chat only: there is no model picker or settings panel yet (see
[PLAN.md](development-and-limits.md)); configuration stays in the JSON file that **Open Configuration** shows.

## Code it can write: the FontLab package set

Aidus is the coding agent for the FontLab Python ecosystem, not only for the
native `fontlab` module. The maintained package guidance describes which layer to target, with import names and one-line usage. Private prompts are not published here:

| Package | Aidus writes code for |
| --- | --- |
| fontlab-echopy (`echopy`) | The documented, typed `fontlab`, `fontgate`, `fontpr` and `PythonQt` shims that Aidus builds upon |
| fontlab-fly (`fly`) | Short aliases (`fl`, `fg`, `tr`, `pr`, `qt`, `ap`, `qs`, `gp`, `fp`, `pens`) in scripts |
| fontlab-fontlabapp (`fontlabapp`) | Dialogs, panels, drawing, reports and guarded edits; glyph-window painters |
| pythonqtside | Qt5 widgets with PySide2-style names on host PythonQt |
| fontlab-glyport (`fontlab_glyport`) | Running Glyphs.app scripts and plugins |
| fontlab-fontport (`fontlab_fontport`) | FontParts and UFO interchange |
| fontlab-python-plugmix (current core: `fontlabapp.plugins`) | Native Reporter APIs through `fly.ap.plugins`; overlays use `flCanvas.appendPythonPainter` (with an `EditorPainters` fallback) |
| fontlab-python-pens (`fontlab_pens`) | Font drawing pens through `fly.pens` |
| fontlab-python-scriptmix | Scripts-menu tools (a folder of scripts, not an importable package) |
| fontlab-remopy (`fontlab_remopy`) | Driving FontLab from an external process; also the bridge Aidus itself uses |

Generated FontLab scripts use `fontlab-fly >=1.3.0` and the needed providers
in FontLab's scripting environment. Native APIs use `fly.fl`, dialogs use `fly.ap`,
and other providers use their Fly aliases. Missing packages need installation;
Aidus reports the requirement instead of generating direct provider imports.
The separate AI brain does not need Fly merely to generate these scripts.
Generated code runs through the native MCP `run_python` tool or the fallback
`run_fontlab_script`; neither installs packages. To see what a given FontLab
session can import, run `open -a "/Applications/FontLab 9.app" run_in_fontlab/check_aidus_in_fontlab.vfpy`
(or open it in FontLab). It writes a JSON report (`AIDUS_LOAD_CHECK` sets the path) and only imports.

## External ACP clients

The brain also provides `fontlab-aidus-acp` (alias `aidus-core`) for stdio ACP
protocol version 1. It is not an HTTP server. FontLab must be running with native
MCP available for an external editor to control fonts; the fallback executor is
provided by the embedded dock. The host JSON credential mappings are applied by
the plugin, so external clients must supply their own provider environment.
See [architecture](guides/architecture.md#external-clients).

## Automatic-layer metrics

`set_glyph_metrics` refuses explicit width or sidebearing assignments to native
automatic layers before setters or history notifications. This includes equal
values: the previous no-op path still invoked setters. An empty request remains
successful. This source guard does not qualify the current-glyph read path or
whole-font Undo/Redo preservation; native acceptance remains open.
