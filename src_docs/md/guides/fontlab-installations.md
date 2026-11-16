---
this_file: src_docs/md/guides/fontlab-installations.md
---

# FontLab MCP source and installation audit

Inspected on 2026-10-13 against FontLab 9.0.9780 on the maintainer's machine,
before the migration into this repository. Paths and versions describe that
machine, not every FontLab distribution; re-check them against your build. No
token contents, license data or credentials were copied into this repository.
The complete historical audit remains in private recovery; it is not a site input.

## Source contract

Reference: the FontLab application source (`Proteus/`).

- `preferences/pref_fontographer.ui`: Aidus's external-MCP checkbox is
  `checkExternalMcp`. It is distinct from built-in Chat and says changes take
  effect on applying Preferences.
- `preferences/pref_fontographer.cpp`: the checkbox loads `QSettings` key
  `mcp.enabled`, whose default is false. Accept writes the same key. The external
  control is hidden in builds without `MCP_SERVER`.
- `common/mcp/mcpserver.cpp`: `MCPServer` observes
  `flItems::preferencesChanged`. `updateListener()` opens localhost TCP port
  **47400** when the setting is true; disabling it closes the listener and
  disconnects existing external sessions. Setting a preference file externally
  while FontLab is running does not emit that notification.
- `pygate/pyflitems.h`: the Python binding exposes
  `fontlab.flItems.notifyPreferencesChanged()`. The signal itself is not a
  callable attribute of the Python `flItems.instance()` wrapper. Use the public
  notification method, as in `run_in_fontlab/enable_fontlab_mcp.vfpy`.
- `common/flpreferences.cpp`, `flPreferences::saveDict()` and `loadDict()`:
  extended `save()` includes the existing QSettings keys, including `mcp.enabled`
  once that key exists. `load(dict)` writes the supplied keys and reloads the
  preferences; it does not require a full snapshot. The running build returned
  **624 keys**, including `mcp.enabled`, with no direct MCP attribute. The helper
  therefore uses the extended interface with a one-key dict, then notifies the
  MCP listener. It does not export the complete preferences or credentials.
- `common/mcp/mcpauth.h`: application and bridge use the shared
  `QStandardPaths::GenericDataLocation/FontLab/MCP/token` file. The listener
  creates it; the bridge reads it. The token is 64 hexadecimal characters and
  is supplied in the TCP `initialize` request. A bridge can initialize its own
  stdio interface even while the application is unavailable: use `tools/list`
  to prove an authenticated application connection.
- `mcpbridge/main.cpp`: the bridge connects lazily to `127.0.0.1:47400`, reads the
  platform's token, initializes the application connection, and relays requests.
  Its native connection timeout is 5 seconds and read timeout 60 seconds. It
  does not start the application, change Preferences, expose HTTP, or accept
  a token-file override.
- `common/mcp/mcptools.cpp`: journaling reads `result["isError"]` through the
  mutable Qt JSON subscript. This inserts a null member when a successful result
  omitted the optional error flag. The live build demonstrated that wire value;
  Aidus's SDK relay removes only this null member. The underlying source remedy
  would be reading through `result.value("isError")`; the FontLab checkout was
  not changed by this Aidus task.

## macOS installation

- Application: `/Applications/FontLab 9.app`.
- Bundle identifier: `com.fontlab.fontlab9`.
- Version: **9.0.9780**, bundle build **9780**, from `Contents/Info.plist`.
- Bridge: `/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp`.
- Shared token path: `~/Library/Application Support/FontLab/MCP/token`; its
  existence was verified, without reading its value into the report.
- The local development bridge is
  `Proteus/mcpbridge/fontlab-mcp`. `mcpbridge.pro` builds a Qt Core/Network console
  program; `build_universal.command` checks the macOS arm64/x86_64 build.

Preferred activation is in the application: launch the `.vfpy` helper with
`open -a`, then reconnect Aidus. This uses Qt's current application settings
namespace and emits the listener's notification. Avoid using `defaults write`
as the activation mechanism: it does not notify a running listener, and a
subsequent Preferences apply can overwrite an externally changed value.

Aidus (through fontlab-remopy) discovers and starts the bridge automatically. Running the executable
manually is useful for a protocol client, but is not an activation step.

## CrossOver Windows installation

The dated CrossOver observation used a private bottle. Its host paths and directory
inventory are omitted here. The Windows installation path below is a conventional
example, not a disclosure of a current installation:

```text
C:\Program Files\Fontlab\FontLab 9\FontLab 9.exe
```

- The uninstall metadata in the bottle's `system.reg` reports
  **FontLab 9 version 9.0.9780.0** and that installation directory.
- The executable is a Windows PE application, accompanied by `python311.dll`,
  `PythonQt-Qt5-Python3.11.dll`, `PythonQt_QtAll-Qt5-Python3.11.dll`, Qt 5 Core,
  Gui, Widgets, Network, Xml, Svg, Concurrent and PrintSupport DLLs, plus Qt
  plugins, translations and Resources.
- This embedded Python **3.11** is for native FontLab scripting. The Aidus
  brain requires a separate modern Python **3.13+** environment. A macOS `.venv/bin/python`
  is not a Windows executable that a Wine QProcess can launch.
- The dated application data directory observation was at
  `C:\users\crossover\AppData\Local\FontLab\FontLab 9`, containing `Autosave`
  and `Licenser`. Qt's shared MCP token location is separate:
  `%LOCALAPPDATA%\FontLab\MCP\token`.
  This follows Qt's documented
  [GenericDataLocation defaults](https://doc.qt.io/qt-6.8/qstandardpaths.html);
  operating-system configuration can change the actual writable location.
- The Windows executable contains the `mcp.enabled`, MCP authentication,
  `tools/list` and external-client preference strings. This is evidence that
  MCP code is present; it is not proof that the listener is currently enabled.
- The bottle's `user.reg` had no `mcp.enabled` entry during inspection, and the
  expected Windows MCP token file was absent. No Windows live MCP connection
  was claimed.
- A recursive installation inventory found **no MCP bridge file**, including
  no `fontlab-mcp.exe`, and no packaged `fontlab_python_mcp_spec.md`.
- CrossOver drive mappings and host-home access are private installation details, omitted from this guide.

The helper now imports Remopy. It requires Remopy installed and importable in
Windows FontLab's embedded Python, not only in the separate brain environment.
The historical file-access observation does not establish that dependency.

To activate Windows FontLab, run that helper with this prerequisite satisfied or use
Preferences > Aidus and apply the external-MCP checkbox. That enables the
listener, but the inspected distribution still needs a matching **Windows**
stdio bridge for a Windows brain/client. Do not point a Windows QProcess at the
macOS bridge. Do not assume the macOS bridge can authenticate to Wine FontLab:
it reads the macOS token, while Windows FontLab uses the bottle's token. The
current bridge has no argument to select another token file.

Both applications use localhost port 47400. If macOS and Wine share that port,
only one can listen; use one target at a time and verify authenticated
`tools/list` rather than identifying the application by an open port alone.
Concurrent Windows/macOS MCP service and a host-to-Wine transport adapter were
not implemented or verified in this task.

## Acceptance evidence

- Native embedded Python imported the updated Aidus ACP client and produced
  `initialize`, `session/new`, and `session/prompt` requests.
- The running macOS server exposed **46 tools**.
- The normalized SDK connection completed read-only `list_fonts` successfully.
- A complete live ACP client → Aidus brain → native macOS MCP → assistant
  response roundtrip passed, with no plugin executor invocation and clean EOF
  shutdown. AgentPool registered all 46 copilot tools and 20 analyst tools.
- The activation binding `flItems.notifyPreferencesChanged()` was verified
  in the live embedded Python environment, and the helper was run in FontLab.
- Automated tests cover active SDK MCP execution, inactive plugin fallback,
  role restrictions, startup deadlines, null-error normalization and clean
  process shutdown. They use deterministic models and do not edit fonts.

## Direct and extended preferences

These examples require `fontlab-fly >=1.3.0` and its providers in FontLab's
scripting Python environment. Prefer direct access when FontLab exposes an
attribute, for example:

```python
from fly import fl
preferences = fl.flPreferences()
preferences.generalDarkGlyph = not preferences.generalDarkGlyph
fl.flWorkspace.instance().updateActiveViewport()
```

The extended dict interface also supports the following snapshot/edit/load
pattern. For this particular display setting, the direct attribute above is
preferred; the example illustrates how the extended interface works:

```python
preferences = fl.flPreferences()
prefd = preferences.save()
prefd["general.dark_glyph"] = not prefd["general.dark_glyph"]
preferences.load(prefd)
fl.flWorkspace.instance().updateActiveViewport()
profiles = prefd.get("profiles", tuple())
```

The latter follows the documented snapshot/edit/load pattern; `profiles` is the
tuple of custom export profiles. MCP activation can use the smaller partial
dict below because the source confirms `loadDict()` only writes supplied keys:

```python
from fly import fl
fl.flPreferences().load({"mcp.enabled": True})
fl.flItems.notifyPreferencesChanged()
```

The viewport update in the display-preference example is unrelated to the MCP
listener; activating MCP needs the preferences notification, not a viewport
refresh. Avoid saving a full preference snapshot to a report: it can include
private application settings.
