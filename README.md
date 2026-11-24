---
this_file: README.md
---

## Development status — 2026-11-05

Canonical source inspected for this proposal: `37b7f48522a7`. This is a dated source observation, not an installed or native acceptance claim.

Reconcile the qualified Issue 207 consolidated `src/fontlab_aidus_agentus` and `Scripts/Aidus Agentus` candidate against this canonical split; do not describe the candidate as installed.

Qualify active-editor/CurrentGlyph preservation, M1–M11, provider authentication, dock lifecycle and shutdown before operational brain cutover.

## Repository and development

`src/fontlab_aidus_agentus/` is the host entry point; `src/fontlab_aidus_agentus/plugin/` owns the dock; `src/fontlab_aidus_agentus/core/` owns the brain. `Scripts/Aidus Agentus/` has the menu scripts and `run_in_fontlab/` the developer checks run inside FontLab.

Prepare the two environments in README, then run `./test.sh`. The brain uses Python 3.13+; host tests use Python 3.11. `AIDUS_TEST_PYTHON` and `AIDUS_HOST_PYTHON` select existing interpreters. Never load provider keys during tests.

Keep runtime, ordinary installed artifacts, native workflows and published documentation as separate acceptance results. Track open checks in [TODO.md](TODO.md), the implementation route in [PLAN.md](PLAN.md), and dated evidence in [CHANGELOG.md](CHANGELOG.md).

# Aidus Agentus for FontLab 9

Aidus Agentus adds an AI chat dock inside FontLab 9. You can ask about the current
glyph, inspect fonts and metrics, change spacing, or generate and run FontLab
Python code. Responses stream into the dock. The selected AI provider receives
your prompts and the tool results used by the agent; use a disposable font for
your first editing experiments.

The FontLab plugin runs in the host's Python 3.11/PythonQt environment. The AI
brain runs in a **separate Python 3.13+ process**, using AgentPool 2.8.8. Installing
AI libraries into FontLab's embedded Python is unnecessary.

Read [Configure Aidus Agentus](CONFIGURE.md) for the short setup guide,
[architecture](src_docs/md/guides/architecture.md) for the process/tool boundaries, and
[troubleshooting](src_docs/md/guides/troubleshooting.md) when something fails.

## Install from this checkout

To install into FontLab 9, open `install.vfpy` from a checkout in FontLab
(double-click it or drop it onto FontLab), then restart FontLab. The file is a
short stub that hands the work to
[fontlab-instamix](https://github.com/fontlabcom/fontlab-python-instamix); if
instamix is not installed yet, the stub installs it from PyPI first. Instamix
installs the package into FontLab's own `site-packages` and records the install
under the extension id `com.fontlab.aidus-agentus`.

You need FontLab 9, [uv](https://docs.astral.sh/uv/), and access to the
[FontLab Remopy wheel](https://github.com/fontlabcom/fontlab-remopy/releases).
Download that wheel first; replace the example wheel path below with its actual
path. These commands run in a terminal **at this repository's root**.

1. Install the lightweight host package into a dedicated folder:

   ```sh
   uv pip install --python 3.11 --target ~/.local/share/fontlab-aidus/host .
   # Optional: required for the Enable FontLab MCP menu script.
   uv pip install --python 3.11 --target ~/.local/share/fontlab-aidus/host --no-deps /path/to/fontlab_remopy-VERSION-py3-none-any.whl
   ```

   Remopy's in-FontLab enable helper needs only the host's `fontlab` module;
   its external MCP dependencies belong in the brain environment.

2. In FontLab's Python console, make that host folder importable:

   ```python
   import os, site
   site.addsitedir(os.path.expanduser("~/.local/share/fontlab-aidus/host"))
   import fontlab_aidus_agentus
   print(fontlab_aidus_agentus.__version__)
   ```

   This adds the path for the current FontLab session. Repeat after restarting
   FontLab, or have your FontLab environment setup add it on each launch. The
   Scripts-menu folder link alone does not install the package or add this path.

3. Create the separate brain environment and install the real AI dependencies:

   ```sh
   uv venv --python 3.13 ~/.local/share/fontlab-aidus/brain
   uv pip install --python ~/.local/share/fontlab-aidus/brain/bin/python '.[brain]' /path/to/fontlab_remopy-VERSION-py3-none-any.whl
   ```

   Remopy is supplied explicitly because it may be absent from the package
   registry. If you maintain a sibling `fontlab-remopy` checkout, use its path
   instead of the wheel. On Windows use the environment's `Scripts/python.exe`
   wherever these examples use `bin/python`.

4. Set `python_exe` and provider-key sources in the host JSON file as described
   in [CONFIGURE.md](CONFIGURE.md). The bundled manifest uses OpenAI for the
   copilot/analyst and Anthropic for the coder. Configure both providers, or
   [supply your own manifest](src_docs/md/guides/architecture.md#agents-and-models).

For an existing release, substitute its downloaded Aidus wheel for `.` and use
`'/path/to/fontlab_aidus_agentus-VERSION-py3-none-any.whl[brain]'` for `'.[brain]'`.
See [RELEASE.md](RELEASE.md) for v0.2.0 hashes and its historical verification.
**The new menu scripts require the current checkout's host package**; v0.2.0
predates the installed launcher helpers. No PyPI installation is assumed.

## Run in FontLab

The root [Aidus Agentus](Aidus%20Code/README.md) folder holds three thin `.py`
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
[PLAN.md](PLAN.md)); configuration stays in the JSON file that **Open Configuration** shows.

## Code it can write: the FontLab package set

Aidus is the coding agent for the FontLab Python ecosystem, not only for the
native `fontlab` module. The system prompt
([`src/fontlab_aidus_agentus/core/prompts/fontlab_api.md`](src/fontlab_aidus_agentus/core/prompts/fontlab_api.md))
teaches the agents which layer to target, with import names and one-line usage:

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
See [architecture](src_docs/md/guides/architecture.md#external-clients).

## Automatic-layer metrics

`set_glyph_metrics` refuses explicit width or sidebearing assignments to native
automatic layers before setters or history notifications. This includes equal
values: the previous no-op path still invoked setters. An empty request remains
successful. This source guard does not qualify the current-glyph read path or
whole-font Undo/Redo preservation; native acceptance remains open.

## Develop and test

`./test.sh` needs two environments: the brain (Python 3.13+, `.venv`) and a
host-like one (arm64 CPython 3.11, `.venv-host`, like FontLab's own Python):

```sh
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e '.[brain,dev]' /path/to/fontlab_remopy-VERSION-py3-none-any.whl
uv venv --python cpython-3.11-macos-aarch64-none .venv-host
uv pip install --python .venv-host/bin/python pytest pytest-asyncio pytest-cov
uv pip install --python .venv-host/bin/python --no-deps /path/to/fontlab_remopy-VERSION-py3-none-any.whl
./test.sh          # extra arguments go to the brain run, e.g. ./test.sh -x -k config
```

The brain run measures coverage of all three packages; the host run repeats the
plugin, launcher and installer tests on 3.11 without AI libraries. Tests use
fakes of PythonQt, QProcess and `fontlab`, and a deterministic AgentPool
TestModel: no provider calls and no live FontLab. Every test gets an empty HOME
and no `*_API_KEY` variables, and the run stops if an `aidus_config.json` sits at
the repository root. Menu-script tests check the scheduling contract, not timing
in the real application. [docs/manual-tests.md](src_docs/md/guides/manual-tests.md) lists what
only a person at FontLab can check.

Build with `uv build`. Wheels contain the runtime packages, prompts, tool definitions and authored offline
help. Deferred startup errors print absolute paths to readable installation,
configuration or troubleshooting Markdown without opening it. The sdist also
contains the menu scripts, user docs and tests.
[DEPENDENCIES.md](DEPENDENCIES.md) explains the dependency pins.

The v0.2.0 migration's native verification is recorded in the [v1.1.7 WORK.md](https://github.com/fontlabcom/fontlab-aidus-agentus/blob/v1.1.7/WORK.md) and
[RELEASE.md](RELEASE.md). The 2026-10-16 native check (FontLab 9.0.9783) covered
import from this checkout, the installer, the executor tools on an owned font and
deterministic ACP roundtrips through the fallback executor and native MCP; it did
not open the dock or run the menu scripts.

## History

Aidus Agentus was called Aidus Code (distribution `fontlab-aidus-code`) until
Issue 242. It absorbed the former `aidus-code` repository; that legacy repository
is retired, and its verbatim recovery archive (`original/`, `migration.json`) was
removed from this tree in the rename. Both remain in this repository's Git history
up to tag `v1.1.7`. The MCP bridge moved to fontlab-remopy, and the API
introspectors were superseded by fontlab-echopy and fontlab-python-docs.

License: proprietary Fontlab Ltd.; original notices retained.


## Documentation source

The maintained site source is [src_docs/md/index.md](src_docs/md/index.md);
[src_docs/mkdocs.yml](src_docs/mkdocs.yml) configures ProperDocs with fly-january
0.3.0 or later and the FontLab menu and footer. To rebuild the tracked `docs/` site and
run its tests from the repository root:

```sh
uv venv --python 3.13 .docs-venv
uv pip install --python .docs-venv/bin/python --require-hashes -r src_docs/requirements.txt
PATH="$PWD/.docs-venv/bin:$PATH" sh src_docs/build.sh
.docs-venv/bin/python -B -m unittest discover -s tests_docs -v
```

Private Pages publication remains owner-held.
