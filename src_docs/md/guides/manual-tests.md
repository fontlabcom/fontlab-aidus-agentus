---
this_file: src_docs/md/guides/manual-tests.md
---

# Manual checks in FontLab

The automated suite (`./test.sh`) mocks FontLab and PythonQt. These checks cover
native behavior that needs a running FontLab 9. Ported from the legacy repository's
`tests/MANUAL_TESTS.md` and `docs/INTEGRATION_TESTS.md`, with authentication/timeout scenarios retained from `docs/TESTING.md`.
These are acceptance targets, not a record of passing native results.

Use a dedicated test session containing only **owned disposable copies** of fonts.
Record the actual FontLab build, host/brain package versions and loaded paths.
Keep settings/history tests in an isolated test account; never clear an owner's
chat history or change their credentials. Edits made by the agent are real.

## Before you start

1. Install the host package and the brain environment as in the
   [README](../index.md), and set `python_exe` ([CONFIGURE.md](../configure.md)).
2. Make the **Aidus Agentus** Scripts-menu folder available: either the
   orchestrator's link, or `fontlab-aidus-install install` (check with
   `fontlab-aidus-install check`).
3. Open a disposable font and select one glyph.

## Checks

| # | Do this | Expect |
|---|---|---|
| 1 | Scripts > Aidus Agentus > **Start Aidus Agentus** | The script returns at once; a dock appears; no traceback in the Output panel. |
| 2 | Watch the dock status | It reaches a ready state. The brain may take several seconds; native MCP discovery can take up to eight. |
| 3 | Run **Start Aidus Agentus** again | The existing dock is shown; no second brain process starts. |
| 4 | Ask "List the open fonts without changing them." | A streamed answer that matches FontLab's open fonts. |
| 5 | Ask for the metrics of the current glyph | Width, LSB and RSB match the Glyph panel. |
| 6 | Select the plugin backend as described below; ask to set an ordinary, non-automatic glyph layer's width to 700 | The width changes once. Edit > Undo ("Undo Aidus: Set Glyph Metrics") restores it; Redo reapplies it. Verify complete font preservation, not only width. |
| 7 | Ask to run a script that prints the glyph count | The count matches the font. |
| 8 | Close all fonts, then ask for current glyph info | A readable error, no traceback; the dock stays usable. |
| 9 | Quit the brain (or wait for an error), then click **Reconnect** | Reconnect is enabled only when disconnected or in error. A fresh session starts; pending requests are discarded, never replayed. |
| 10 | Ask for all glyphs with Unicode values (200+ glyphs); compare the displayed output with the actual tool result | Output streams; the dock scrolls; FontLab stays responsive. Check live display separately from the bounded saved-history policy below. |
| 11 | Select a non-Latin glyph and ask about it | Names and characters display correctly. |
| 12 | Switch FontLab between light and dark themes | The dock stays readable in both. |
| 13 | Send messages, run `fontlab_aidus_agentus.shutdown()`, start again | Earlier messages reappear (the newest 500 rows of `~/.config/aidus_agentus/history.json`). |
| 14 | Click **Clear** | The dock empties and `history.json` is removed. |
| 15 | Scripts > Aidus Agentus > **Enable FontLab MCP**, run `fontlab_aidus_agentus.shutdown()`, start again, ask to list open fonts | The Output panel confirms enabling; the dock shows a `list_fonts` tool row, which only the native MCP catalogue provides. |
| 16 | Set `python_exe` to a Python without the brain extra, start again | The Output panel shows `[Aidus brain]` lines and the dock shows the brain's exit code with its last messages. Restore `python_exe` afterwards. |
| 17 | Scripts > Aidus Agentus > **Open Configuration** | The active JSON opens in your editor; an existing file is never rewritten. |

After a timeout, the outcome of an edit is unknown: inspect the font before
asking again.

## Backend and preservation controls

For check6, set `AIDUS_FONTLAB_MCP=off` in the dedicated FontLab process before
starting Aidus. Shut down and start again after changing the environment; retain
the brain's `backend: plugin` evidence. A natural-language request alone does
not prove which tool ran: record the exact fallback tool call and arguments.
Run a separate native-MCP case with discovery enabled and recorded `backend: mcp`.
Do not assume native tools use the plugin's Undo label or history implementation.

For either writer path, compare the full owned font before, after, Undo, Redo and
save/reopen, including unrelated glyphs, metadata and dirty state. Test an explicit
metric assignment to an automatic layer separately: the candidate plugin guard
must refuse before setters/history. Glyph-info read preservation and native writer
qualification remain pending; a plausible metric value is insufficient evidence.

## Restored migration scenarios

The archived checklists also require these distinct cases. Keep failures visible;
replacing a failed native check with a mock test does not complete it.

| ID | Do this | Acceptance evidence |
| --- | --- | --- |
| M1 | With an owned font open, leave no current glyph and request glyph info. Separately test zero chart selection while a current glyph still exists. | No-current-glyph returns a readable refusal and leaves the font unchanged. Record selection and current-glyph states separately; zero selection alone does not prove no current glyph. |
| M2 | During a slow **read-only** response, change glyph selection, scroll the chat and resize the dock. | Each action remains responsive; no crash or duplicate request. Record which glyph the tool actually inspected. |
| M3 | Disconnect only the identified test brain process; try to send a message. | No edit is queued for later replay. The error is readable, visually distinct and provides connection/reconnect guidance; record any missing presentation as a failure. |
| M4 | Send several messages, close/hide the dock, reopen it through the Scripts menu. Then separately run full shutdown/start. | Compare message content and scroll position in each lifecycle; one dock/brain only. Closing a dock is not equivalent to shutdown. |
| M5 | Send a harmless prompt, then a follow-up referring to its answer. | Both turns appear and the response uses the current session context. Saved display history alone does not establish restored model context. |
| M6 | While a read-only response is pending, attempt a second submission. | Input is disabled or the submission is clearly refused; no overlapping/replayed request or lost first response. |
| M7 | In an owned temporary user folder, install/check/uninstall the menu scripts and reopen the menu. | Only installer-owned unmodified files disappear; unrelated files and edited scripts are preserved/refused. Use the current installer subcommands, not the archived flags. |
| M8 | Inspect installed host and brain versions/paths using the troubleshooting guide. | Record actual package identities and any compatibility warning. The old status-bar/About version-display requirement remains unverified; package metadata is a separate check, not proof of that UI feature. |
| M9 | Shut down Aidus; separately quit the dedicated document-free FontLab session. | The identified brain process exits in each case, with no orphan child. Do not kill unrelated Python processes. |
| M10 | Use a disposable brain configuration with required provider credentials deliberately absent. | A clear startup/request authentication failure reaches the dock, with no secret values or native mutation. Host-side key-check deferral does not prove this provider behavior. |
| M11 | Use a controlled slow read-only response and a short positive `timeout_seconds` in the isolated configuration. | Timeout is surfaced; reconnect creates a fresh session without replay. Retain the request outcome as unknown until reconciled. A client timeout does not prove native execution stopped. |

The old five-second brain initialization and automatic ten-second reconnection
expectations are not current promises. Measure startup separately from the short
menu action, and use the explicit Reconnect control after a failure.

## Live display versus retained history

Check a response with known start/end markers both while displayed and after
shutdown/start. The current dock displays incoming complete message text; saved
history keeps at most500rows and a bounded JSON payload (2MB), with each message
cut after20,000characters and marked `… [truncated]`. Verify the marker and retained
newest rows, rather than claiming the archived unlimited-retention requirement
still holds. Record any missing live output separately from expected history
truncation. Capture only owned fixture content in evidence.

Record pass/fail/held per case, actual build/package/backend identities, fixture
hashes, observed output and cleanup results. Historical v0.2.0 evidence does not
clear these current native acceptance targets.
