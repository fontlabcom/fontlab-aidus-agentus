---
this_file: CHANGELOG.md
---

## Unreleased

- Documentation builds accept fly-january 0.3.0 or later.

- PyPI Trusted Publishing requires the project owner to configure GitHub repository `fontlabcom/fontlab-aidus-agentus`, workflow `release.yml` and environment `pypi`. The local `publish.sh` dispatches this workflow (`403fca2`).
- Issue 271 — the installer reached main at `acb7464`. Release run 44414672850 and Documentation run 44412329542 passed at that SHA. Both PyPI v1.1.19 archives matched their published SHA-256 digests, and the sdist installer matched the tagged source byte for byte.
- Issue 242 — verified the GitHub repository and primary checkout names with `git remote get-url origin` and `git rev-parse --git-common-dir`. At v1.1.12 (`aacf000c`), the ordinary wheel and sdist install checks matched all 42 host files.
- Issue 255 — reconciled authored Fly examples and package guidance with the host/brain split at `aacf000c`. The release checks passed 920 brain tests, 796 host tests and 11 provider routes.

- Site now uses the fly-january 0.2.1 theme (chrome: fontlab).

## 2026-11-18 — Issue 271 installer source alignment

The generated installer matches the reviewed Instamix 1.0.18 template: it requires
conflict preflight support, selects compatible local wheels and reports completed
work before an installation failure. Exact reviewed-template byte parity and import-sentinel/wheel-order smoke checks pass. Existing focused installer tests pass (exit 0, 12.07 seconds).
Consumer integration, released archives and native execution remain separate checks.

## 2026-11-17 — Installer stub from instamix 1.0.15 (Issue 259 follow-ups)

- `install.vfpy` is now the stub from fontlab-python-instamix 1.0.15. It replaces an
  installed instamix older than 1.0.13 and puts the old copy back if the upgrade
  fails; linked checkouts and local builds are kept. A download that fails for
  lack of root certificates (FontLab 9 for macOS) is retried with the system curl.

## 1.1.13 (2026-11-16)

- `install.vfpy` is now the short fontlab-instamix stub. It installs
  fontlab-instamix from PyPI when it is missing, then installs this checkout from
  its `[tool.fontlab-install]` table. The large legacy installer is gone.
- `tests/test_standalone_install.py` tests the stub, the install table and the sdist.
- The sdist now ships `install.vfpy`.
- README describes the stub install.
## 2026-11-14 — Functional work order documented

- Added the owner's functional-progress-first guidance and repository-specific priorities, including cross-package compatibility and a later detailed testing pass. Existing mandatory hooks, holds and unfinished work remain in force.
- This change updates guidance and planning only; it establishes no new runtime, installed, native or release result.

## 2026-11-13 — Issue 255 verified release qualification

- [fontlab-aidus-agentus v1.1.12](https://github.com/fontlabcom/fontlab-aidus-agentus/releases/tag/v1.1.12) is released at `aacf000c295f45393dc2c084fafbbff994d2dc8e`. Reviewed main/tag delivery, applicable CI and actual downloads match the qualified artifacts.
- Authored native examples, inline teaching and fallback guidance use Fly; the canonical plugin API and metadata entry-point group remain distinct. Private prompt text is retained only as a runtime resource.
- 920 brain tests pass on Python 3.13 and 796 host tests on arm64 Python 3.11; aggregate statement coverage is 94%. All 36 actual rebuilt documentation tests and exact 57-file parity pass. Genuine wheel/sdist host cohorts match all 42 installed files; the separate ordinary brain cohort contains 199 compatible packages with exact SDK pins. Socket-guarded SDK imports and 11 real provider routes pass without CLI/model/native activation. Normal main/tag hooks, CI and actual downloads are qualified.
- Ordinary external installation is qualified; installed FontLab/native acceptance remains unproved under D43. Service/authentication was not exercised; CLI flags were not invoked because boot activates the brain. No prompt body or credentials are reproduced.

## 2026-11-13 — Issue 255 Fly teaching source candidate

- Authored script examples and agent fallback guidance use Fly, including the Pens alias, supported Glyport public module and current App plugin API. Public guides state the host-side Fly prerequisite; the separate brain gains no dependency.
- Five private native examples and three public import-bearing examples preserve their original operations through namespace qualification. Raw legacy/modern binding diagnostics, actual provider-load checks, Remopy transport, menu generator parity and shared installer bytes remain unchanged.
- Exact source suite: 920 brain and 796 host tests pass. Actual rebuilt-output docs checks exposed a stale module-name oracle (35 passed/1 failed); the oracle now requires both the current provider module and Fly route, and all 36 docs tests pass. The earlier docs run checked previous committed output. Changed-test lint passes; full lint retains the same eight baseline findings. Candidate wheel/sdist ordinary installs match 26 runtime files and 11 authored help pages without publishing private prompts.
- Independent review, controller integration, committed artifacts, native execution and publication remain separate outstanding acceptance surfaces.

## 2026-11-13 — Live font testing section restored to AGENTS.md

- Adds the owner's "Live font testing in FontLab (owner instruction, 2026-11-10)" section to `AGENTS.md`, text copied unchanged from the owner checkout; it was the only owner-checkout text absent from main. Main's integration wording is kept. Docs only, no code change.

## 2026-11-12 — D46 documentation pass

- Records the licence state for the Apache-2.0 migration question: `pyproject.toml` declares `LicenseRef-Proprietary`, `LICENSE` is the Fontlab Ltd 2025 proprietary text and `LICENSE-3RD-PARTY.md` lists MIT/BSD-3 dependencies (workspace licence inventory, Aidus row, action X: owner decision whether proprietary repositories are in scope). Migration not started; new open TODO row.
- Documentation CI: success on `3ed19d7`, `151cfd1`, `74e0eda`. No code or behaviour change in this entry.

## 2026-11-11 — relay module discovery test (Issue 250)

- `test_server_config_when_relay_module_named_then_it_is_importable` pins that the module named in the generated args resolves under the brain extra (reviewer2 M-1 on 74e0eda). TODO row removed.

## 2026-11-11 — generated MCP config launches fontlab_remopy.mcp.relay (Issue 250)

- Tests: 904 passed (Aidus suite, Python 3.13, brain+dev extras, Remopy main). `server_config` now writes `-m fontlab_remopy.mcp.relay` instead of the deprecated `fontlab_remopy.mcp_bridge`, and `external-agents-mcp.md` and `fontlab-mcp.md` say the same. The `brain` extra raises its floor from `fontlab-remopy>=0.1` to `>=1.2.0`, the first release containing `mcp.relay` (commit a40c5df, 2026-11-03). Remopy keeps `mcp_bridge` as a re-export, so saved external configs still work. A new test pins the generated args.

## 2026-11-10 — live font editing rule (Issue 250, D44)

- AGENTS.md: agents test and edit the font open in FontLab 9, starting from the Desktop VFJs, and may save them.

## 2026-11-10 — install.vfpy always reinstalls scripts and dependencies

- Every install copies all files from `Scripts/` afresh and replaces any file
  already at the same path. A symlinked script folder is replaced by a real
  folder; the link target is never written. A directory where a script file
  belongs is still refused.
- Required packages are installed on every run. Packages that no package
  index carries (the fontlab-* packages, pythonqtside) are installed from
  checkouts beside this one through their own `install.vfpy`, once per run
  and safe against cycles. uv receives every other requirement, so version
  ranges, markers and extras are enforced. Without uv, sibling checkouts are
  still installed and only the remaining missing requirements are reported.
- The installer is byte-identical across all eleven installer repositories.

## 2026-11-09 — Issue 242: Aidus Code becomes Aidus Agentus

- Renamed the distribution `fontlab-aidus-code` to `fontlab-aidus-agentus` and the
  import package to `fontlab_aidus_agentus`; project URLs now point to
  github.com/fontlabcom/fontlab-aidus-agentus and the install id is
  `com.fontlab.aidus-agentus`. Entry points keep their command names.
- Consolidated `fontlab_aidus_code/`, `aidus_code_core/` and `aidus_code_plugin/`
  into one src-layout package: `src/fontlab_aidus_agentus/` (host entry,
  installer, launchers), `.core` (Python 3.13+ brain) and `.plugin` (dock).
  Tests moved to `tests/`, `tests/core/` and `tests/plugin/`; type stubs to `stubs/`.
- Menu scripts moved to `Scripts/Aidus Agentus/`; `Start Aidus Code.py` is now
  `Start Aidus Agentus.py`. In-FontLab checks and the PythonQt introspector moved
  to `run_in_fontlab/`. `install.vfpy` installs the package from `src/` and maps
  `Scripts/` onto FontLab's Scripts folder.
- Configuration moved to `~/.config/aidus_agentus/config.json`; the old
  `~/.config/aidus_code/config.json` is still read after it.
- Removed the recovery archive `original/` and `migration.json` (retained in Git
  history up to tag v1.1.7), the standalone `aidus-code-core` metadata, the
  duplicate core `fl.pyi` stub, the `mcp_bridge` re-export shim (the brain runs
  `fontlab_remopy.mcp_bridge` directly) and the unused `core.tools` parameter
  validators, with their self-tests. WORK.md now holds only current work.
- Verification: `HOME=$(mktemp -d) ./test.sh` (brain Python 3.13, host Python 3.11).
  Native FontLab behaviour of the renamed package is not yet checked.
- Upgrade notes:
  - Uninstall an old `com.fontlab.aidus-code` installation before installing
    `fontlab-aidus-agentus`. The new installer owns only `com.fontlab.aidus-agentus`
    items, so it leaves an old `Scripts/Aidus Code/` menu folder in place.
  - The legacy `aidus-code-core` and `fontlab-aidus-code` distributions are no
    longer recognised. Until you reinstall, `get_version` reports `0.0.0-dev`.
  - The removed `core.tools` parameter validators, including their forbidden-term
    filter, had no production caller. Tool requests were never checked by them, so
    removing them changes no runtime behaviour.

## 2026-11-07 — Ordinary installed error help candidate

- Deferred startup failures print readable absolute installation, configuration
  and troubleshooting help paths from either a checkout or an ordinary wheel.
  Missing, empty or unreadable local help gives host reinstall guidance.
- Wheels reuse eleven canonical authored Markdown files, preserving their offline
  links. No generated site assets, dependencies or public entry points changed.
- The installer and three thin menu scripts give self-contained missing-package
  guidance, distinguish the separate brain and qualify the GitHub setup reference.
- Sdist selection excludes repository CHANGELOG history containing inherited private
  machine paths; full repository history is preserved.
- Regression-first checks cover both deferred failures/layouts, missing resources,
  secrecy, timer cleanup and script parity. Complete test, module coverage and
  candidate artifact/origin evidence are recorded in WORK and the private writer
  report. Commit-bound artifacts, native behavior and publication remain separate.

## 2026-11-06 — ordinary package contract repair

Align standalone Core with the existing supported root brain tuple: AgentPool 2.8.8, Pydantic AI Slim/Graph 1.50.0 and the four verified provider SDK pins. Retain Python 3.13+, ag-ui and every other minimum/cap; root metadata and runtime are unchanged. Add a cross-distribution tuple regression.

At this precommit checkpoint, the isolated candidate was uncommitted; genuine dirty-VCS artifacts, normal installation and tests were recorded separately. Native acceptance, clean committed artifact requalification and controller review were still pending.

## 2026-11-05 — independently approved documentation applied

[Task 2 final review](../verification/issue-230/task-2-fix2-review.md) records
SPEC PASS / QUALITY APPROVED. The [78-file application receipt](../verification/issue-230/task-2-apply.json)
includes this repository's six guides and preserves all 21 repository heads,
branches, indexes and non-selected diffs. This is applied documentation evidence,
not a new product test, installed artifact, native result or publication.

The complete earlier handoff/history below retains its proposal-stage statements
and dated source pins. Later review, application and delivery status belong in the
[live workspace ledger](../verification/issue-230/progress.md). Original future,
native, artifact and preservation contracts remain binding.

## 2026-11-05 — documentation reconciliation proposal

Prepared repository-specific organization, test and MVP/delivery guidance from current source/test configuration and retained Issue 207–211 evidence. Distinguished current canonical layout from qualified candidates, future plugin ownership and unfinished native/artifact gates. Preserved all prior work and changelog evidence; no runtime completion, installation or publication is claimed. Historical checked tasks now require receipt/current-scope reconciliation rather than being silently counted complete.

## 2026-11-05 — planning chronology reconciliation

The November3 universal pause/D34-only/uncommitted handoff is superseded by current Issue230/207 authority. Native CurrentGlyph, M1–M11, read-scope/calibration and full four-package load-check scenarios remain open. Historical passing results retain their dated source and acceptance scope in the entries above and original history below. This documentation change creates no new runtime acceptance.

---
this_file: CHANGELOG.md
---

## Issue 201: package-aware agent and legacy residue port — 2026-11-03

- The agent prompt now has a "FontLab Python Packages You Can Target" section: echopy, fly,
  fontlabapp, pythonqtside, glyport, fontport, plugmix (Reporter overlays through
  `flCanvas.appendPythonPainter`), scriptmix and remopy, each with import name and usage,
  plus rules to probe before importing and to use the lowest layer that works.
- New `scripts/check_aidus_in_fontlab.vfpy` (successor of `temp/plugin_load_test.vfpy`)
  writes a JSON report of what Aidus and the package set can import in a FontLab session.
- 24 more legacy aidus-code files are archived verbatim in `original/` with sha256 records in
  `migration.json` (introspectors, scratch scripts, owner prompts, PRD, build/CI scripts). Vendor
  checkouts, `.claude/` templates, lockfile, tool configs, caches and secrets were not copied.
  Full classification: workspace `verification/issue-201/aidus-inventory.md`.
- README describes the dock GUI and the package set; AGENTS.md added.
- Fixed the glyph-info read-preservation failure: `get_current_glyph_info` and the glyph
  guard now use the workspace's active glyph (`flWorkspace.instance().currentGlyph.glyph`)
  instead of `CurrentGlyph()`, whose export drops the fresh `lib.note` mirror (fl#8525). The
  record must belong to `currentPackage`, else the tool returns an error; builds without a
  workspace glyph keep the `CurrentGlyph()` route. The `[CurrentGlyph]` regression now passes
  unchanged; full brain suite 844 pass, host subset 726 pass, executor coverage 95%.
  Verified natively in FontLab 9 on an owned font copy (2026-11-03): the workspace glyph equals
  `CurrentGlyph()`, the info read returns name, unicode and metrics, and a fresh note survives.
- Fixed a bug that the first version of this read shipped on main (d5bf1a8): every native
  `get_current_glyph_info` call failed with "Glyph no longer belongs to its registered font".
  `flWorkspace.findPackageId` takes the FontGate id (`package.fgId`), not `flPackage.id`
  (commit 3efd2b7; the test fakes now key `findPackageId` by `fgId`).
- Final-review fixes: `set_glyph_metrics` refuses to write when the workspace's active glyph
  differs from `CurrentGlyph()` (glyph name or owning font), so a read of glyph A can never
  be followed by a write to glyph B; with no `CurrentGlyph()` it answers "No glyph is
  currently selected". The stale-package check also rejects a null `currentPackage`.
  The current legacy CHANGELOG, PLAN, README and TODO (with the uncommitted 2026-11-03
  handoff blocks) are archived as `original/<name>.2026-11-03.md` with sha256 records. The
  prompt's plugmix row lists the `polygon` mark kind. `./test.sh` needs the two virtualenvs of
  the README "Develop and test" recipe.
- Tests: `tests/test_residue_port.py` (prompt covers every package, load-check script, every
  archive hash matches) and `tests/test_active_glyph_read.py` (stale, null and missing workspace
  glyph branches).

## Aidus preflight errors verified; active selection remains held — 2026-11-01

Moved font/glyph guards into the existing executor error boundary. ToolError and
ordinary getter exceptions now return the same structured errors as handlers;
failed guards never enter handlers or retry. KeyboardInterrupt still propagates.
Selection semantics, the inner Unicode reader and the failing whole-payload
regression are unchanged. ACP already caught escaped exceptions; this repairs
the executor's direct-call contract, not a claimed ACP crash.

Regression-first8fails/1pass; focused90pass; full Python3.13suite817pass/1known
CurrentGlyph preservation failure,0skips. Fresh wheel/sdist Python3.11installs
each27pass/1same failure,0skips. All29runtime files match source/archives/installs;
100sdist files plus licences and test bytes checked. Prior wheel fails8new cases,
with interruption control passing. Same-process installed origins and dependency
checks pass. Scoped Ruff and git diff --check exit0. No dependency changes.

Exact commands/exits, source/archive hashes, initial failures and JUnit:
verification/issue-123/aidus-preflight-errors-20261101.json and
verification/issue-123/aidus-preflight-error-artifacts-20261101.json.
External check.py red/full/older-negative exit1; focused exit0. Artifact run.py
and audit.py exit0 while each targeted installed pytest retains expected exit1.

The read-only binding audit verified23source hashes. Active native resolvers are
not registered in Python; getActiveGlyph matches are commented declarations;
FontWindow currentGlyph is not invokable through its QWidget pointer. Partial
text/paper routes cannot replace maximized-paper or Font-window current-cell
semantics. Root inspected these branches and reran baseline53pass/1knownfail.
Evidence: verification/issue-123/aidus-preflight-contract-20261101.json.

Do not replace the active glyph with stored/current/first-selected glyphs merely
to pass a double. Native build/API qualification remains gated by D30. No native
calls, canonical edits, obsolete-source retirement, promotion or publication.
D16/D27/D29/D30/D31 remain unchanged; this does not close public read preservation.

## Aidus full brain regression suite verified — 2026-11-01

Complete isolated source suite on Python3.13.16:808passed,1failed, zero skips.
Only CurrentGlyph preflight preservation remains failing. Statement coverage
is94%overall and95%executor; these figures do not claim branch/native coverage.
The source import probe resolves to the isolated candidate. Existing canonical
brain environment was used read-only; tests isolate configuration and history.

Exact command, coverage, source hash and JUnit:
verification/issue-123/aidus-inner-brain-20261101.json. Host subset and targeted
installed artifacts retain their separate evidence. No native execution,
canonical promotion or obsolete-source retirement; public read remains unsafe
on the historically affected host until the preflight is qualified.

## Aidus inner read verified in fresh artifacts — 2026-11-01

Fresh ordinary wheel/sdist0.2.2.dev4+gb07867092.d20261101 installs each pass18
targeted checks and retain exactly1failure: CurrentGlyph preflight preservation.
There are zero skips. All29runtime files match source/archives/installs;99sdist
files, licences and exact regression-test bytes were inspected. Both dependency
checks and same-process executor-origin checks pass. The suite remains red.

Hashes, commands and limitations:
verification/issue-123/aidus-inner-read-artifacts-20261101.json. These are owned
doubles, not native calibration. No full brain-runtime rerun, native execution,
live install, promotion, obsolete-source retirement or publication occurred.

## Aidus inner Unicode read repaired in source — 2026-11-01

The Unicode getter now resolves a registered owner and checks package/font IDs,
unique glyph name and record identity before reading FontGate Unicode. It no
longer exports glyph.fgGlyph; legacy width behavior is unchanged.17new checks
failed before implementation. Updated3existing native doubles with owner fields;
no behavioral assertions or original preservation tests were weakened.

Focused89passed/1failed; host subset690passed/1failed. Root independently ran
18passed/1failed and reviewed the diff. The remaining failure is exactly the
CurrentGlyph preflight preservation case. First implementation exposed3outdated
fixture failures; those logs are retained. Scoped lint/diff checks pass.

Commands, source hashes and limitations:
verification/issue-123/aidus-inner-read-20261101.json. Fresh artifacts, installed
checks and native calibration remain open; public read preservation is not fixed.
D16obsolete-source protection and D30native hold remain unchanged.

## 2026-11-01 — Retain uncertain child termination

ACPTransport.stop now reportsFalse and retains its QProcess when final kill/wait
cannot confirm exit; successful/no-child shutdown reportsTrue. Main shutdown,
client reconnect and scheduled transport reconnect stop on explicitFalse.
The dock/session remain available for reconciliation; no replacement is started.
A finished signal, including one delivered during a wait, can confirm exit.
Start refuses reentrant replacement while stop is in progress.

Five initial regression failures became focused111passes. Two signal timing
controls were added; another reentrant-start control failed before its guard.
Full results and exact commands are in the workspace receipt and external
issue123/aidus-stop-20261101 logs. Existing fresh-note read-preservation tests
remain in the run as untracked investigation evidence, unchanged from prior
candidate. No full-green or native-exit claim is made.

Qt5 QProcess wait contract consulted:
https://doc.qt.io/archives/qt-5.15/qprocess.html#waitForFinished
Current callers and diff received bounded independent review; subsequent
reentrant-start guard is directly regression-tested. Ruff reports the pre-existing
unused sys import in main.py; it is unrelated to this change.

Native dock/process lifetime, FontLab quit behavior and descendant process
cleanup remain unqualified under D30. No canonical promotion or publication.

## 2026-11-01 — Restore migrated native acceptance scenarios

Restore11distinct manual acceptance cases dropped/narrowed by the old document
rewrite: no current glyph, responsive selection/scroll/resize, disconnected
send, dock close/reopen, multi-turn, rapid input, ownership-aware uninstall,
version identity, child cleanup, missing credentials and timeout handling.
Separate plugin/native-MCP writer proof, live output and bounded saved history.
These are pending native targets; no native success is asserted.

Correct host-side Remopy prerequisites in all three MCP guides. The brain's
installation alone cannot run the enable helper inside FontLab. Direct API
activation remains separate. No runtime or original archive bytes changed.

Fresh checks: all74original archive SHA256records match; all11M-case identifiers
present; three prerequisite explanations verified; git diff --check exit0.
External evidence: issue123/aidus-migration-docs-20261101/archive-records.json.
Workspace routing review: verification/issue-123/aidus-document-dispositions-20261101.md.
No runtime suite rerun for this documentation-only change. Native D30 and source
read-preservation failures remain open; protected aidus-code unchanged.

## 2026-11-01 — automatic-layer metric assignment guard (source checkpoint)

Refuse explicit native metric assignments when the selected/fallback layer is
automatic, before metric comparison, any setter or history notification. Direct
autoLayer lookup also fails before mutation if the property is unreadable.
Equal/within-tolerance explicit assignments are refused: the old no-op path still
calls setters. Empty requests and ordinary native/legacy behavior remain.

19new cases:17failed2passed before runtime change (initial reserved pytest
parameter name caused collection failure, retained); focused116passed after.
Tests inspect zero setters/history, complete fixture payload, fallback layer,
unknown flags, ordinary history and one ACP refusal response without handler
replay. They model CurrentGlyph as inert; they do not fix or qualify that getter.
Independent scoped review found no blocking issues.

Full brain:2failed782passed,94%coverage. Host subset:2failed664passed. Both failures
are the existing, unchanged fresh-note read-preservation regressions through
CurrentGlyph and fgGlyph. They remain untracked source investigation evidence;
no full-green, safe-read or native acceptance is claimed. Protected aidus-code
and canonical checkout unchanged. No push while these acceptance failures remain.

Exact commands through rtk proxy, candidate cwd:
- env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<isolated read candidate> .venv-host/bin/python -B -m pytest --import-mode=importlib -p pytest_asyncio.plugin -p no:cacheprovider -q tests/test_executor_config_edges.py tests/test_native_boundaries.py:exit0,71baseline.
- Same command tests/test_automatic_metric_guard.py before fix:exit1,17failed2passed; after fix plus tests/test_executor_config_edges.py tests/test_native_boundaries.py tests/test_client_protocol.py:exit0,116passed.
- Same environment with COVERAGE_FILE=<evidence folder>/automatic.coverage and .venv/bin/python -B -m pytest --import-mode=importlib -p pytest_cov -p pytest_asyncio.plugin -p no:cacheprovider --cov --cov-report=term -q:exit1,2failed782passed.
- Host interpreter -B -m pytest --import-mode=importlib -p pytest_asyncio.plugin -p no:cacheprovider -q aidus_code_plugin/tests tests --ignore=tests/test_production_entrypoint.py --ignore-glob='tests/test_brain_*':exit1,2failed664passed.
- ruff check --select F821 tests/test_automatic_metric_guard.py aidus_code_plugin/executor.py; git diff --check:each exit0.

Wait, but: initial CurrentGlyph preflight can still alter metadata on affected
hosts. This guard protects setters/notifications only; whole-call/native writer
preservation, current-host calibration and migration removal remain open.
Evidence: external aidus-read-evidence-20261101/automatic-*.log.

# Verified changes

## 2026-11-10 — Issue 250 documentation round

- AGENTS.md describes the delegation, integration and release workflow.
- WORK.md reset to the current round; the earlier bytes are archived on the owner's workspace data volume, not public.

## 2026-11-01 — read-preservation investigation only (unmerged)

- Added two deliberately RED regressions for fresh note/lib loss through both
  public CurrentGlyph preflight and inner Unicode export. No runtime fix.
- Recorded source-qualified active-selection blocker and native continuation
  requirements in WORK.md; no native or broad migration acceptance claimed.

## 2026-10-16 — plugin gaps closed (branch aidus-gaps; released in v0.2.1)

- Fallback metric edits are now one Edit > Undo step: the executor notifies
  `[layer, glyph]` before and after the change (FontLab stores state per
  notification and Undo restores the previous one). A request that matches
  the current metrics sends nothing and adds no Undo entry.
- The dock reloads `history.json` on start, keeping the newest 500 rows (also
  the cap when saving).
- Brain stderr is visible: `aidus_code_plugin.brain_log.BrainLog` prints
  warning/error/plain-text lines to the Output panel (50 per process, 1000
  characters each) and keeps a 200-line tail; a non-zero exit or transport
  error shows the last five lines in the dock. Shutdown disconnects these slots.
- Installer (release review X5): ownership is tracked per file in a validated
  format-1 manifest with sha256 digests. User files survive reinstall and
  uninstall; modified, foreign or symlinked scripts stop an install before any
  change; writes never follow symlinks; uninstall leaves a non-empty folder.
- Installer (re-review X5-2): exclusive temp files (never deletes an entry it
  did not create), every write/removal re-verified just before it runs, and a
  provisional manifest so an interrupted install is resumed. Owned files are
  moved aside and hashed before being replaced or removed, so a concurrent edit
  is kept; a new folder appears only together with its manifest, and the
  manifest itself is updated and removed the same way.
- Brain stderr keeps text left without a final newline and starts a fresh tail
  for each child; history is also bounded to 2 MB and 20,000 characters per message.
- Script sandbox: the timeout now fires inside one-line loops on CPython 3.11
  (opcode tracing; no measurable cost against the previous line tracing).
- Tests: 696 on Python 3.13 (95% coverage), 580 on Python 3.11, all failing
  first where behaviour changed. Native (FontLab 9.0.9783, owned GetGo copy):
  Undo 670→640 and Redo →670 via MCP readback, 3 history rows restored and a 4th
  saved, a failing child's tail in the dock and its error lines printed.
  After the X5 fixes: 724 (3.13, 94%) and 608 (3.11) tests; native installer
  run in temp FontLab-like folders (real Scripts folder unchanged).

## 2026-10-16 — aidus-code migration finished, extensive tests (issue 106, D16; released in v0.2.1)

- Inventoried every aidus-code file (HEAD 6377303 plus the owner's working
  tree; 1705 entries): none left missing. 21 more files were migrated with
  provenance (`original/`, `migration.json`), each exclusion has a reason.
- New `fontlab_aidus_code.install` (`fontlab-aidus-install install|check|
  uninstall`) ports the old install.py: manages only
  `<user folder>/Scripts/Aidus Code` and never replaces entries it did not
  write.
- Ported docs: `docs/fontlab-mcp.md`, `docs/external-agents-mcp.md`,
  `docs/fontlab-installations.md`, `docs/manual-tests.md`.
- Fixed: the fallback executor failed on every metrics call in real FontLab,
  because `CurrentGlyph()` returns an fgGlyph; it now wraps it as flGlyph.
- Fixed: the brain health check reported 0.0.0-dev instead of the installed
  fontlab-aidus-code version.
- Fixed: a sandboxed script switched off any trace function (debugger,
  coverage) running in FontLab; the previous tracer is now restored.
- Tests: 668 on Python 3.13 (94% line coverage of all three packages) and
  566 host-side on arm64 Python 3.11; fakes of PythonQt, QProcess and
  `fontlab`, an end-to-end plugin boot, HOME/API-key isolation. `./test.sh`
  runs both environments.
- Native (FontLab 9.0.9783): import from this checkout, installer, executor
  tools on an owned GetGo copy with MCP readback, and deterministic ACP
  roundtrips whose model called a fallback tool (plugin backend) and a native
  MCP tool (MCP backend).

## 2026-10-15 — configuration repair review fix (released in v0.2.1)

- Catch non-UTF-8 config decoding errors so Open Configuration can open existing
  files for repair. Report invalid encoding/JSON/object shape/read failures with
  the path and a safe description, without exposing contents or changing bytes.
- Preserve fallback to the next valid configuration and document UTF-8 JSON.
- Added eight fail-first regressions for UTF-16, invalid UTF-8, malformed JSON
  and non-object JSON: editor invocation/unchanged bytes and loader precedence.
  Configuration/menu suites: 51 passed; full Python 3.13 suite: 377 passed.

## 2026-10-15 — fallback brain/executor argument contract (released in v0.2.1)

- Send the brain wrapper's public `script` argument as the executor's canonical
  `code` parameter. Retain the executor's existing compatibility alias.
- Add seven round-trip cases through the real ACP extension helper and executor
  for all three brain tools, including omitted/zero metrics and a negative
  sidebearing. Validate canonical arguments before aliases and check actual
  results/glyph changes. Add a coverage guard for every wrapper calling
  `call_plugin`; no other name mismatches were found.
- Updated the existing script payload assertion. Regression-first checks caught
  the mismatch; all 13 focused tests and 369 full-suite tests pass on Python 3.13.

## 2026-10-15 — documentation and Scripts-menu launchers (released in v0.2.1)

- Rewrote installation/run guidance around separate host/brain environments and
  explicit Remopy artifacts; added CONFIGURE.md and architecture/troubleshooting
  guides covering actual JSON precedence, credentials, models and reconnect.
- Added `Aidus Code/` with Start Aidus Code, Enable FontLab MCP and Open
  Configuration scripts plus README. Installed helpers defer work through Qt,
  reuse an existing dock, preserve configuration files and report missing
  packages without printing exception values or credentials.
- Included user docs/menu scripts in the sdist and installed helpers in the
  wheel, with no new dependencies. New scripts require this checkout's host
  package, rather than the historical v0.2.0 wheel.
- Added 20 launcher regressions; all 361 source and extracted-sdist tests pass
  on Python 3.13. A clean Python 3.11 host wheel passes compilation/mock launch
  checks for all three scripts without AI dependencies. Native launcher timing
  and editor/menu integration remain unverified in this follow-up.

## 2026-10-15 — completed checklist (moved from TODO.md)

- Record current source provenance and baseline.
- Implement complete package migration and scoped modernization.
- Verify wheel, sdist, isolated installs and privacy.
- Verify installed production ACP and native rendered client/MCP behavior.
- Controller review and any integration fixes.
- Resolve retained legacy fallback glyph metric attributes against native FontLab9 APIs.
- Verify fresh-session reconnect and child-only configured credentials.
- Complete all three full-project iterations.
- Push, tag, release and verify assets.
- Fix idle ACP timeout and incremental UTF-8 framing with request/cancellation/restart regressions.

## v0.2.1 (2026-10-16)

Finished migration of aidus-code into fontlab-aidus-code (1705 entries inventoried; migrated with provenance, every exclusion reasoned) and closed the plugin gaps: Undo pre/post with no-op skip, bounded history reload, BrainLog, installer with per-file ownership manifest and lossless rename-aside protocol (no data loss under crash/permission injection), staging, sandboxed-script timeout restoring the caller's trace function.


- Extracted the existing FontLab ACP plugin and AgentPool coding brain into a hatch-vcs package with fontlab_aidus_code API and fontlab-aidus-acp executable.
- Added explicit lightweight host/optional Python3.13 brain boundary and verified dependency versions.
- Delegated native bridge, discovery and setup to FontLab Remopy; retained agent role/tool policies and legacy imports.
- Fixed installed package imports, external interpreter selection, native QObject lookup, QByteArray conversion, Qt5 process completion, process-start verification, reentrant shutdown and ACP EOF cleanup.
- Fixed native dock registration and missing retained UI state attributes; verified actual rendered native chat and read-only MCP interaction.
- Preserved original source/tests/fixtures/licenses with hash accounting; excluded private/build artifacts from distributions.

- Review round1: corrected native fallback glyph Unicode/advance/sidebearing APIs with disposable readback proof; implemented client-owned fresh-session reconnect without replay; propagated configured keys into child-only provider environment and delegated selected-model readiness to the external brain.

- Corrected native scroll/input property reads and button-slot arguments; tested actual reconnect and submit paths.

- Keep healthy idle ACP sessions connected; time outstanding requests from submission and matching progress, preserving unknown-outcome errors without replay.
- Preserve split UTF-8 characters across native QProcess reads; report malformed/incomplete ACP stdout and reset decoders across connection boundaries.

## v0.2.0 publication verified

Actual publication and independent downloaded-asset verification complete.
Three full-project iterations pass; installed tagged wheel/sdist each457tests.
Downloaded native smoke covers all eight packages and both formats, including
production ACP/native UI and TypeRig composition. Exact release URLs, immutable
code commit and asset digests are in RELEASE.md. This follow-up changes only
completion evidence; release code and tag are unchanged.

## 2026-10-15 — workspace plan and checklist reconciliation

Completed repository scope archived after reading WORK.md and checking the
workspace evidence. Workspace release/integration gates remain in the parent
PLAN.md. Historical verification limits below remain part of the record.

### Archived PLAN.md

# Plan

## Issue 104 review: configuration repair

Complete: eight regression cases failed first; all 51 focused configuration/menu
tests and 377 full-suite tests now pass. Invalid-file bytes and editor invocation
are verified with the actual loader and mocked Qt, including fallback precedence.

1. Reproduce the review's UTF-16 failure with a binary-content launcher test;
   cover invalid UTF-8, malformed JSON and non-object JSON with safe diagnostics.
2. Catch config decoding failures alongside parse/read failures, report the
   affected path without file contents, and preserve repair-file selection and
   exclusive creation. Verify fallback to a later valid config still works.
3. Run the full Python 3.13 suite and scoped checks; update evidence/docs. The
   review lists no Minor findings. Do not stage, commit or access private sources.

## Fallback tool argument contract

Complete: canonical script mapping corrected, all three brain wrappers audited,
13 focused tests and 369 full-suite tests pass on Python 3.13.

1. Add regression coverage that routes each brain tool using `call_plugin`
   through the real ACP extension helper and `FontLabExecutor.run`, with a
   mocked FontLab glyph. Check canonical arguments before executor aliases,
   tool results and glyph readback; guard coverage for newly added brain tools.
2. Send `code` from the brain's script wrapper, preserving its public `script`
   argument. Audit all other wrappers for name/argument mismatches.
3. Run `.venv/bin/python -m pytest --import-mode=importlib -q`, inspect the diff
   and status, and record results without staging or committing.

## Documentation and menu follow-up

The issue 101 migration was released as v0.2.0 (see RELEASE.md). This follow-up
covers user documentation and FontLab Scripts-menu entry points only.

Status (2026-10-15): all six steps below are complete. Verification: 361 source
tests and 361 extracted-sdist tests pass; the clean Python 3.11 host wheel runs
all three scripts with mocked FontLab/Qt and heavy imports forbidden. WORK.md
records evidence. Live Scripts-menu/timer/editor verification remains an
environment check for the orchestrator; no symlinks, commits or publication were
performed here.

1. Audit the current host, brain, configuration, MCP and distribution code; run
   the existing Python 3.13 suite as a baseline.
2. Rewrite README.md and add focused architecture/troubleshooting docs. Describe
   local and released-asset installation accurately, the host/brain boundary,
   configuration precedence, model selection and the verification limits.
3. Add a short CONFIGURE.md covering all host JSON keys, a minimal example,
   child-only provider credentials and a safe verification procedure.
4. Add exactly the runnable thin .py launchers and README.md in `Aidus Code/`.
   Delegate work to installed packages with lazy imports; defer dock startup
   through Qt to respect the five-second Scripts-menu deadline. Support start,
   MCP enablement and opening the active configuration without overwriting it.
   Do not create symlinks or modify the owner's private source directory.
5. Test compilation/import, missing dependencies, bounded script size, deferred
   startup and configuration creation/opening with mocked FontLab/Qt modules.
   Ensure the sdist includes the scripts and their documentation/tests.
6. Run the full Python 3.13 pytest suite with actual brain/dev dependencies,
   check distribution contents and intended Git changes, then record counts and
   limitations in WORK.md and CHANGELOG.md. Do not stage or commit.

### Archived TODO.md

# Tasks

- [x] Reproduce issue 104 non-UTF-8 configuration repair with failing tests.
- [x] Report invalid configs safely and open existing repair files unchanged.
- [x] Verify fallback precedence, full suite and review evidence.

- [x] Round-trip every brain fallback tool through the real plugin executor.
- [x] Send canonical script arguments and fix any other discovered mismatches.
- [x] Run the full suite and record fallback-tool regression evidence.

- [x] Audit code and run the Python 3.13 baseline suite.
- [x] Update README and architecture/troubleshooting docs to match the code.
- [x] Add short CONFIGURE.md with all JSON keys and safe provider-key setup.
- [x] Add thin FontLab launchers and README in `Aidus Code/`; create no symlinks.
- [x] Test scripts without FontLab, lazy/deferred startup and missing packages.
- [x] Include launchers/docs in sdist and inspect built artifacts.
- [x] Run the complete Python 3.13 suite, record results and check Git status.

No implementation tasks remain in this follow-up. The orchestrator owns linking
the folder and checking it in the target FontLab runtime (see WORK.md).

### 2026-11-01 — Reviewed branch consolidation

Integrated registered-Unicode reads and preflight error handling. The source
suite has817passes and one deliberately retained failing preservation regression:
`test_info_when_note_is_fresh_preserves_full_payload[CurrentGlyph]`. Reading
CurrentGlyph can still clear a fresh note's lib mirror in FontLab; this merge
does not resolve that host defect or qualify native use. Executor combined
coverage is90.93%. The owner explicitly authorized a consolidation-only push
exception for this one failure. All other tests and coverage remain mandatory.
Startup checks pass in an isolated Python3.13 environment; a system-package
overlay had incorrectly activated an unrelated optional Jinja filter import.
No runtime dependency pin or regression expectation was weakened.

## 2026-11-03 — installer options, licence and cleanup

- `install.vfpy` reads optional `[tool.fontlab-install]` keys: `name` (the distribution
  record), `packages` (`[]` installs scripts only) and `dependencies` (what FontLab needs,
  instead of `project.dependencies`). Symlinks inside `Scripts/` are not copied.

## 2026-11-03 — install.vfpy fixes from runs inside FontLab 9

Verified by installing all nine packages inside FontLab 9 (Python 3.11.6, arm64).
- Dependencies with console scripts (glyphsLib, fontTools) failed: uv writes them to
  `site-packages/../../../bin`, which resolves through the venv link to the FontLab
  folder. `bin`, `share` and `include` there now link back into `.venv`.
- A failed install appends a `"failed"` record with the traceback and uv's output to
  `install.log`; List/Uninstall ignore failed records.
- Package records include `WHEEL`, so `uv pip check` accepts them.
- Scripts are copied file by file into FontLab's `Scripts` folder, from a package's
  `Scripts/` folder (exact case) and from folders listed in `[tool.fontlab-install] scripts`.
  Folders shared by several packages merge, e.g. two packages' `Scripts/Kerning`. The
  installer refuses to overwrite a file another package or the user put there; uninstall
  removes only its own files, their `.pyc`, and folders left empty. An older install's
  folder link (`Scripts/Aidus Code`) is replaced by copied files.
- `*.vfpyc` (FontLab's compiled `install.vfpy`) is ignored by Git.

## 2026-11-03 — install.vfpy creates FontLab's venv

FontLab's `python/3.11/site-packages` is now always a real folder; packages are
symlinked into it, so no `.pth` processing is needed. `install.vfpy` creates `.venv` with
uv from FontLab's exact Python version and processor type, and links the venv's
site-packages to FontLab's folder, so `uv pip install --python .venv/bin/python` installs
into FontLab. An older layout (FontLab's folder linked into `.venv`) is migrated.

## 2026-11-03 — reverse-domain extension id and install.log

`[tool.fontlab-install] id = "com.fontlab.aidus-code"` names this extension. `install.vfpy` keeps
`Extensions/com.fontlab.aidus-code/install.log` (JSON Lines; the last line lists every installed file),
puts copied code in `Extensions/com.fontlab.aidus-code/lib/`, and adds Scripts > Extensions >
List Extensions and Uninstall com.fontlab.aidus-code.

## 2026-11-03 — install.vfpy without uv

`install.vfpy` now needs only FontLab's Python. It asks FontLab for its data folder
(`flPreferences().dataPathDefault`), links a Git checkout or copies a plain folder into
`Extensions/`, and writes a `.pth` plus `.dist-info` into `python/3.11/site-packages`.
uv is used only to add missing dependencies. It never replaces folders it does not own. `[tool.fontlab-install] scripts` puts `Aidus Code` in FontLab's Scripts menu.

## 2026-11-03 — release scripts

Added `build.sh` (uv build into dist/), `publish.sh` (`uv publish`; refuses a dirty
tree or an untagged HEAD) and `install.vfpy` (editable install into FontLab's venv
from inside FontLab). Version stays hatch-vcs from `vX.Y.Z` tags.

<!-- workspace-handoff:2026-11-03 -->
## 2026-11-03 — documentation handoff for November 2–3

The isolated identity candidate has 146 focused checks on both Python versions and828 full-suite passes, with one real CurrentGlyph preservation failure.

The newer candidate is uncommitted;D34waived consolidation only. Legacy retirement and exact archive/inventory recovery remain open.

Observed canonical checkout: `main` at `d5bf1a8f4e80`. No source integration is performed by this update.

Updated the requested AGENTS/TODO/PLAN/CHANGELOG/README documentation and
recorded the paused state. Existing project text, examples and history remain;
no runtime source, installation, native session, branch/ref, release or site was
changed by this documentation maintenance. Source/archive/ordinary/native and
promotion acceptance remain separate claims. Detailed workspace evidence is
recorded in the root CHANGELOG and retained verification reports.
<!-- /workspace-handoff -->

## Aidus preflight errors verified; active selection remains held — 2026-11-01

Moved font/glyph guards into the existing executor error boundary. ToolError and
ordinary getter exceptions now return the same structured errors as handlers;
failed guards never enter handlers or retry. KeyboardInterrupt still propagates.
Selection semantics, the inner Unicode reader and the failing whole-payload
regression are unchanged. ACP already caught escaped exceptions; this repairs
the executor's direct-call contract, not a claimed ACP crash.

Regression-first8fails/1pass; focused90pass; full Python3.13suite817pass/1known
CurrentGlyph preservation failure,0skips. Fresh wheel/sdist Python3.11installs
each27pass/1same failure,0skips. All29runtime files match source/archives/installs;
100sdist files plus licences and test bytes checked. Prior wheel fails8new cases,
with interruption control passing. Same-process installed origins and dependency
checks pass. Scoped Ruff and git diff --check exit0. No dependency changes.

Exact commands/exits, source/archive hashes, initial failures and JUnit:
verification/issue-123/aidus-preflight-errors-20261101.json and
verification/issue-123/aidus-preflight-error-artifacts-20261101.json.
External check.py red/full/older-negative exit1; focused exit0. Artifact run.py
and audit.py exit0 while each targeted installed pytest retains expected exit1.

The read-only binding audit verified23source hashes. Active native resolvers are
not registered in Python; getActiveGlyph matches are commented declarations;
FontWindow currentGlyph is not invokable through its QWidget pointer. Partial
text/paper routes cannot replace maximized-paper or Font-window current-cell
semantics. Root inspected these branches and reran baseline53pass/1knownfail.
Evidence: verification/issue-123/aidus-preflight-contract-20261101.json.

Do not replace the active glyph with stored/current/first-selected glyphs merely
to pass a double. Native build/API qualification remains gated by D30. No native
calls, canonical edits, obsolete-source retirement, promotion or publication.
D16/D27/D29/D30/D31 remain unchanged; this does not close public read preservation.

## Aidus full brain regression suite verified — 2026-11-01

Complete isolated source suite on Python3.13.16:808passed,1failed, zero skips.
Only CurrentGlyph preflight preservation remains failing. Statement coverage
is94%overall and95%executor; these figures do not claim branch/native coverage.
The source import probe resolves to the isolated candidate. Existing canonical
brain environment was used read-only; tests isolate configuration and history.

Exact command, coverage, source hash and JUnit:
verification/issue-123/aidus-inner-brain-20261101.json. Host subset and targeted
installed artifacts retain their separate evidence. No native execution,
canonical promotion or obsolete-source retirement; public read remains unsafe
on the historically affected host until the preflight is qualified.

## Aidus inner read verified in fresh artifacts — 2026-11-01

Fresh ordinary wheel/sdist0.2.2.dev4+gb07867092.d20261101 installs each pass18
targeted checks and retain exactly1failure: CurrentGlyph preflight preservation.
There are zero skips. All29runtime files match source/archives/installs;99sdist
files, licences and exact regression-test bytes were inspected. Both dependency
checks and same-process executor-origin checks pass. The suite remains red.

Hashes, commands and limitations:
verification/issue-123/aidus-inner-read-artifacts-20261101.json. These are owned
doubles, not native calibration. No full brain-runtime rerun, native execution,
live install, promotion, obsolete-source retirement or publication occurred.

## Aidus inner Unicode read repaired in source — 2026-11-01

The Unicode getter now resolves a registered owner and checks package/font IDs,
unique glyph name and record identity before reading FontGate Unicode. It no
longer exports glyph.fgGlyph; legacy width behavior is unchanged.17new checks
failed before implementation. Updated3existing native doubles with owner fields;
no behavioral assertions or original preservation tests were weakened.

Focused89passed/1failed; host subset690passed/1failed. Root independently ran
18passed/1failed and reviewed the diff. The remaining failure is exactly the
CurrentGlyph preflight preservation case. First implementation exposed3outdated
fixture failures; those logs are retained. Scoped lint/diff checks pass.

Commands, source hashes and limitations:
verification/issue-123/aidus-inner-read-20261101.json. Fresh artifacts, installed
checks and native calibration remain open; public read preservation is not fixed.
D16obsolete-source protection and D30native hold remain unchanged.

## 2026-11-01 — Retain uncertain child termination

ACPTransport.stop now reportsFalse and retains its QProcess when final kill/wait
cannot confirm exit; successful/no-child shutdown reportsTrue. Main shutdown,
client reconnect and scheduled transport reconnect stop on explicitFalse.
The dock/session remain available for reconciliation; no replacement is started.
A finished signal, including one delivered during a wait, can confirm exit.
Start refuses reentrant replacement while stop is in progress.

Five initial regression failures became focused111passes. Two signal timing
controls were added; another reentrant-start control failed before its guard.
Full results and exact commands are in the workspace receipt and external
issue123/aidus-stop-20261101 logs. Existing fresh-note read-preservation tests
remain in the run as untracked investigation evidence, unchanged from prior
candidate. No full-green or native-exit claim is made.

Qt5 QProcess wait contract consulted:
https://doc.qt.io/archives/qt-5.15/qprocess.html#waitForFinished
Current callers and diff received bounded independent review; subsequent
reentrant-start guard is directly regression-tested. Ruff reports the pre-existing
unused sys import in main.py; it is unrelated to this change.

Native dock/process lifetime, FontLab quit behavior and descendant process
cleanup remain unqualified under D30. No canonical promotion or publication.

## 2026-11-01 — Restore migrated native acceptance scenarios

Restore11distinct manual acceptance cases dropped/narrowed by the old document
rewrite: no current glyph, responsive selection/scroll/resize, disconnected
send, dock close/reopen, multi-turn, rapid input, ownership-aware uninstall,
version identity, child cleanup, missing credentials and timeout handling.
Separate plugin/native-MCP writer proof, live output and bounded saved history.
These are pending native targets; no native success is asserted.

Correct host-side Remopy prerequisites in all three MCP guides. The brain's
installation alone cannot run the enable helper inside FontLab. Direct API
activation remains separate. No runtime or original archive bytes changed.

Fresh checks: all74original archive SHA256records match; all11M-case identifiers
present; three prerequisite explanations verified; git diff --check exit0.
External evidence: issue123/aidus-migration-docs-20261101/archive-records.json.
Workspace routing review: verification/issue-123/aidus-document-dispositions-20261101.md.
No runtime suite rerun for this documentation-only change. Native D30 and source
read-preservation failures remain open; protected aidus-code unchanged.

## 2026-11-01 — automatic-layer metric assignment guard (source checkpoint)

Refuse explicit native metric assignments when the selected/fallback layer is
automatic, before metric comparison, any setter or history notification. Direct
autoLayer lookup also fails before mutation if the property is unreadable.
Equal/within-tolerance explicit assignments are refused: the old no-op path still
calls setters. Empty requests and ordinary native/legacy behavior remain.

19new cases:17failed2passed before runtime change (initial reserved pytest
parameter name caused collection failure, retained); focused116passed after.
Tests inspect zero setters/history, complete fixture payload, fallback layer,
unknown flags, ordinary history and one ACP refusal response without handler
replay. They model CurrentGlyph as inert; they do not fix or qualify that getter.
Independent scoped review found no blocking issues.

Full brain:2failed782passed,94%coverage. Host subset:2failed664passed. Both failures
are the existing, unchanged fresh-note read-preservation regressions through
CurrentGlyph and fgGlyph. They remain untracked source investigation evidence;
no full-green, safe-read or native acceptance is claimed. Protected aidus-code
and canonical checkout unchanged. No push while these acceptance failures remain.

Exact commands through rtk proxy, candidate cwd:
- env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<isolated read candidate> .venv-host/bin/python -B -m pytest --import-mode=importlib -p pytest_asyncio.plugin -p no:cacheprovider -q tests/test_executor_config_edges.py tests/test_native_boundaries.py:exit0,71baseline.
- Same command tests/test_automatic_metric_guard.py before fix:exit1,17failed2passed; after fix plus tests/test_executor_config_edges.py tests/test_native_boundaries.py tests/test_client_protocol.py:exit0,116passed.
- Same environment with COVERAGE_FILE=<evidence folder>/automatic.coverage and .venv/bin/python -B -m pytest --import-mode=importlib -p pytest_cov -p pytest_asyncio.plugin -p no:cacheprovider --cov --cov-report=term -q:exit1,2failed782passed.
- Host interpreter -B -m pytest --import-mode=importlib -p pytest_asyncio.plugin -p no:cacheprovider -q aidus_code_plugin/tests tests --ignore=tests/test_production_entrypoint.py --ignore-glob='tests/test_brain_*':exit1,2failed664passed.
- ruff check --select F821 tests/test_automatic_metric_guard.py aidus_code_plugin/executor.py; git diff --check:each exit0.

Wait, but: initial CurrentGlyph preflight can still alter metadata on affected
hosts. This guard protects setters/notifications only; whole-call/native writer
preservation, current-host calibration and migration removal remain open.
Evidence: external aidus-read-evidence-20261101/automatic-*.log.

# Verified changes

## 2026-11-01 — read-preservation investigation only (unmerged)

- Added two deliberately RED regressions for fresh note/lib loss through both
  public CurrentGlyph preflight and inner Unicode export. No runtime fix.
- Recorded source-qualified active-selection blocker and native continuation
  requirements in WORK.md; no native or broad migration acceptance claimed.

## 2026-10-16 — plugin gaps closed (branch aidus-gaps; released in v0.2.1)

- Fallback metric edits are now one Edit > Undo step: the executor notifies
  `[layer, glyph]` before and after the change (FontLab stores state per
  notification and Undo restores the previous one). A request that matches
  the current metrics sends nothing and adds no Undo entry.
- The dock reloads `history.json` on start, keeping the newest 500 rows (also
  the cap when saving).
- Brain stderr is visible: `aidus_code_plugin.brain_log.BrainLog` prints
  warning/error/plain-text lines to the Output panel (50 per process, 1000
  characters each) and keeps a 200-line tail; a non-zero exit or transport
  error shows the last five lines in the dock. Shutdown disconnects these slots.
- Installer (release review X5): ownership is tracked per file in a validated
  format-1 manifest with sha256 digests. User files survive reinstall and
  uninstall; modified, foreign or symlinked scripts stop an install before any
  change; writes never follow symlinks; uninstall leaves a non-empty folder.
- Installer (re-review X5-2): exclusive temp files (never deletes an entry it
  did not create), every write/removal re-verified just before it runs, and a
  provisional manifest so an interrupted install is resumed. Owned files are
  moved aside and hashed before being replaced or removed, so a concurrent edit
  is kept; a new folder appears only together with its manifest, and the
  manifest itself is updated and removed the same way.
- Brain stderr keeps text left without a final newline and starts a fresh tail
  for each child; history is also bounded to 2 MB and 20,000 characters per message.
- Script sandbox: the timeout now fires inside one-line loops on CPython 3.11
  (opcode tracing; no measurable cost against the previous line tracing).
- Tests: 696 on Python 3.13 (95% coverage), 580 on Python 3.11, all failing
  first where behaviour changed. Native (FontLab 9.0.9783, owned GetGo copy):
  Undo 670→640 and Redo →670 via MCP readback, 3 history rows restored and a 4th
  saved, a failing child's tail in the dock and its error lines printed.
  After the X5 fixes: 724 (3.13, 94%) and 608 (3.11) tests; native installer
  run in temp FontLab-like folders (real Scripts folder unchanged).

## 2026-10-16 — aidus-code migration finished, extensive tests (issue 106, D16; released in v0.2.1)

- Inventoried every aidus-code file (HEAD 6377303 plus the owner's working
  tree; 1705 entries): none left missing. 21 more files were migrated with
  provenance (`original/`, `migration.json`), each exclusion has a reason.
- New `fontlab_aidus_code.install` (`fontlab-aidus-install install|check|
  uninstall`) ports the old install.py: manages only
  `<user folder>/Scripts/Aidus Code` and never replaces entries it did not
  write.
- Ported docs: `docs/fontlab-mcp.md`, `docs/external-agents-mcp.md`,
  `docs/fontlab-installations.md`, `docs/manual-tests.md`.
- Fixed: the fallback executor failed on every metrics call in real FontLab,
  because `CurrentGlyph()` returns an fgGlyph; it now wraps it as flGlyph.
- Fixed: the brain health check reported 0.0.0-dev instead of the installed
  fontlab-aidus-code version.
- Fixed: a sandboxed script switched off any trace function (debugger,
  coverage) running in FontLab; the previous tracer is now restored.
- Tests: 668 on Python 3.13 (94% line coverage of all three packages) and
  566 host-side on arm64 Python 3.11; fakes of PythonQt, QProcess and
  `fontlab`, an end-to-end plugin boot, HOME/API-key isolation. `./test.sh`
  runs both environments.
- Native (FontLab 9.0.9783): import from this checkout, installer, executor
  tools on an owned GetGo copy with MCP readback, and deterministic ACP
  roundtrips whose model called a fallback tool (plugin backend) and a native
  MCP tool (MCP backend).

## 2026-10-15 — configuration repair review fix (released in v0.2.1)

- Catch non-UTF-8 config decoding errors so Open Configuration can open existing
  files for repair. Report invalid encoding/JSON/object shape/read failures with
  the path and a safe description, without exposing contents or changing bytes.
- Preserve fallback to the next valid configuration and document UTF-8 JSON.
- Added eight fail-first regressions for UTF-16, invalid UTF-8, malformed JSON
  and non-object JSON: editor invocation/unchanged bytes and loader precedence.
  Configuration/menu suites: 51 passed; full Python 3.13 suite: 377 passed.

## 2026-10-15 — fallback brain/executor argument contract (released in v0.2.1)

- Send the brain wrapper's public `script` argument as the executor's canonical
  `code` parameter. Retain the executor's existing compatibility alias.
- Add seven round-trip cases through the real ACP extension helper and executor
  for all three brain tools, including omitted/zero metrics and a negative
  sidebearing. Validate canonical arguments before aliases and check actual
  results/glyph changes. Add a coverage guard for every wrapper calling
  `call_plugin`; no other name mismatches were found.
- Updated the existing script payload assertion. Regression-first checks caught
  the mismatch; all 13 focused tests and 369 full-suite tests pass on Python 3.13.

## 2026-10-15 — documentation and Scripts-menu launchers (released in v0.2.1)

- Rewrote installation/run guidance around separate host/brain environments and
  explicit Remopy artifacts; added CONFIGURE.md and architecture/troubleshooting
  guides covering actual JSON precedence, credentials, models and reconnect.
- Added `Aidus Code/` with Start Aidus Code, Enable FontLab MCP and Open
  Configuration scripts plus README. Installed helpers defer work through Qt,
  reuse an existing dock, preserve configuration files and report missing
  packages without printing exception values or credentials.
- Included user docs/menu scripts in the sdist and installed helpers in the
  wheel, with no new dependencies. New scripts require this checkout's host
  package, rather than the historical v0.2.0 wheel.
- Added 20 launcher regressions; all 361 source and extracted-sdist tests pass
  on Python 3.13. A clean Python 3.11 host wheel passes compilation/mock launch
  checks for all three scripts without AI dependencies. Native launcher timing
  and editor/menu integration remain unverified in this follow-up.

## 2026-10-15 — completed checklist (moved from TODO.md)

- Record current source provenance and baseline.
- Implement complete package migration and scoped modernization.
- Verify wheel, sdist, isolated installs and privacy.
- Verify installed production ACP and native rendered client/MCP behavior.
- Controller review and any integration fixes.
- Resolve retained legacy fallback glyph metric attributes against native FontLab9 APIs.
- Verify fresh-session reconnect and child-only configured credentials.
- Complete all three full-project iterations.
- Push, tag, release and verify assets.
- Fix idle ACP timeout and incremental UTF-8 framing with request/cancellation/restart regressions.

## v0.2.1 (2026-10-16)

Finished migration of aidus-code into fontlab-aidus-code (1705 entries inventoried; migrated with provenance, every exclusion reasoned) and closed the plugin gaps: Undo pre/post with no-op skip, bounded history reload, BrainLog, installer with per-file ownership manifest and lossless rename-aside protocol (no data loss under crash/permission injection), staging, sandboxed-script timeout restoring the caller's trace function.


- Extracted the existing FontLab ACP plugin and AgentPool coding brain into a hatch-vcs package with fontlab_aidus_code API and fontlab-aidus-acp executable.
- Added explicit lightweight host/optional Python3.13 brain boundary and verified dependency versions.
- Delegated native bridge, discovery and setup to FontLab Remopy; retained agent role/tool policies and legacy imports.
- Fixed installed package imports, external interpreter selection, native QObject lookup, QByteArray conversion, Qt5 process completion, process-start verification, reentrant shutdown and ACP EOF cleanup.
- Fixed native dock registration and missing retained UI state attributes; verified actual rendered native chat and read-only MCP interaction.
- Preserved original source/tests/fixtures/licenses with hash accounting; excluded private/build artifacts from distributions.

- Review round1: corrected native fallback glyph Unicode/advance/sidebearing APIs with disposable readback proof; implemented client-owned fresh-session reconnect without replay; propagated configured keys into child-only provider environment and delegated selected-model readiness to the external brain.

- Corrected native scroll/input property reads and button-slot arguments; tested actual reconnect and submit paths.

- Keep healthy idle ACP sessions connected; time outstanding requests from submission and matching progress, preserving unknown-outcome errors without replay.
- Preserve split UTF-8 characters across native QProcess reads; report malformed/incomplete ACP stdout and reset decoders across connection boundaries.

## v0.2.0 publication verified

Actual publication and independent downloaded-asset verification complete.
Three full-project iterations pass; installed tagged wheel/sdist each457tests.
Downloaded native smoke covers all eight packages and both formats, including
production ACP/native UI and TypeRig composition. Exact release URLs, immutable
code commit and asset digests are in RELEASE.md. This follow-up changes only
completion evidence; release code and tag are unchanged.

## 2026-10-15 — workspace plan and checklist reconciliation

Completed repository scope archived after reading WORK.md and checking the
workspace evidence. Workspace release/integration gates remain in the parent
PLAN.md. Historical verification limits below remain part of the record.

### Archived PLAN.md

# Plan

## Issue 104 review: configuration repair

Complete: eight regression cases failed first; all 51 focused configuration/menu
tests and 377 full-suite tests now pass. Invalid-file bytes and editor invocation
are verified with the actual loader and mocked Qt, including fallback precedence.

1. Reproduce the review's UTF-16 failure with a binary-content launcher test;
   cover invalid UTF-8, malformed JSON and non-object JSON with safe diagnostics.
2. Catch config decoding failures alongside parse/read failures, report the
   affected path without file contents, and preserve repair-file selection and
   exclusive creation. Verify fallback to a later valid config still works.
3. Run the full Python 3.13 suite and scoped checks; update evidence/docs. The
   review lists no Minor findings. Do not stage, commit or access private sources.

## Fallback tool argument contract

Complete: canonical script mapping corrected, all three brain wrappers audited,
13 focused tests and 369 full-suite tests pass on Python 3.13.

1. Add regression coverage that routes each brain tool using `call_plugin`
   through the real ACP extension helper and `FontLabExecutor.run`, with a
   mocked FontLab glyph. Check canonical arguments before executor aliases,
   tool results and glyph readback; guard coverage for newly added brain tools.
2. Send `code` from the brain's script wrapper, preserving its public `script`
   argument. Audit all other wrappers for name/argument mismatches.
3. Run `.venv/bin/python -m pytest --import-mode=importlib -q`, inspect the diff
   and status, and record results without staging or committing.

## Documentation and menu follow-up

The issue 101 migration was released as v0.2.0 (see RELEASE.md). This follow-up
covers user documentation and FontLab Scripts-menu entry points only.

Status (2026-10-15): all six steps below are complete. Verification: 361 source
tests and 361 extracted-sdist tests pass; the clean Python 3.11 host wheel runs
all three scripts with mocked FontLab/Qt and heavy imports forbidden. WORK.md
records evidence. Live Scripts-menu/timer/editor verification remains an
environment check for the orchestrator; no symlinks, commits or publication were
performed here.

1. Audit the current host, brain, configuration, MCP and distribution code; run
   the existing Python 3.13 suite as a baseline.
2. Rewrite README.md and add focused architecture/troubleshooting docs. Describe
   local and released-asset installation accurately, the host/brain boundary,
   configuration precedence, model selection and the verification limits.
3. Add a short CONFIGURE.md covering all host JSON keys, a minimal example,
   child-only provider credentials and a safe verification procedure.
4. Add exactly the runnable thin .py launchers and README.md in `Aidus Code/`.
   Delegate work to installed packages with lazy imports; defer dock startup
   through Qt to respect the five-second Scripts-menu deadline. Support start,
   MCP enablement and opening the active configuration without overwriting it.
   Do not create symlinks or modify the owner's private source directory.
5. Test compilation/import, missing dependencies, bounded script size, deferred
   startup and configuration creation/opening with mocked FontLab/Qt modules.
   Ensure the sdist includes the scripts and their documentation/tests.
6. Run the full Python 3.13 pytest suite with actual brain/dev dependencies,
   check distribution contents and intended Git changes, then record counts and
   limitations in WORK.md and CHANGELOG.md. Do not stage or commit.

### Archived TODO.md

# Tasks

- [x] Reproduce issue 104 non-UTF-8 configuration repair with failing tests.
- [x] Report invalid configs safely and open existing repair files unchanged.
- [x] Verify fallback precedence, full suite and review evidence.

- [x] Round-trip every brain fallback tool through the real plugin executor.
- [x] Send canonical script arguments and fix any other discovered mismatches.
- [x] Run the full suite and record fallback-tool regression evidence.

- [x] Audit code and run the Python 3.13 baseline suite.
- [x] Update README and architecture/troubleshooting docs to match the code.
- [x] Add short CONFIGURE.md with all JSON keys and safe provider-key setup.
- [x] Add thin FontLab launchers and README in `Aidus Code/`; create no symlinks.
- [x] Test scripts without FontLab, lazy/deferred startup and missing packages.
- [x] Include launchers/docs in sdist and inspect built artifacts.
- [x] Run the complete Python 3.13 suite, record results and check Git status.

No implementation tasks remain in this follow-up. The orchestrator owns linking
the folder and checking it in the target FontLab runtime (see WORK.md).

### 2026-11-01 — Reviewed branch consolidation

Integrated registered-Unicode reads and preflight error handling. The source
suite has817passes and one deliberately retained failing preservation regression:
`test_info_when_note_is_fresh_preserves_full_payload[CurrentGlyph]`. Reading
CurrentGlyph can still clear a fresh note's lib mirror in FontLab; this merge
does not resolve that host defect or qualify native use. Executor combined
coverage is90.93%. The owner explicitly authorized a consolidation-only push
exception for this one failure. All other tests and coverage remain mandatory.
Startup checks pass in an isolated Python3.13 environment; a system-package
overlay had incorrectly activated an unrelated optional Jinja filter import.
No runtime dependency pin or regression expectation was weakened.


## 2026-11-06 — Issue 233 Aidus host/brain documentation source

Twelve authored pages preserve all six existing guides and their icon, host/brain installation, configuration, package scope, ACP, CurrentGlyph and M1–M11 limits. Maintained guide paths and the sdist follow src_docs/md; the sole runtime delta is launcher troubleshooting guidance. Host arm64 Python 3.11 baseline/current 29 tests pass; launchers.py has 100% combined statement/branch coverage with no exclusions. Genuine wheel/sdist/from-sdist-wheel and a noneditable arm64 ordinary install preserve runtime/source/legal payloads and verify RECORD. No provider, brain or FontLab execution occurred.

All 20 documentation boundary tests and strict clean builds pass. The independent
31-package hash-locked Python 3.13 environment reproduces every generated byte and
mode twice at the source epoch. Local Git fixtures verify source/output lineage,
concurrent push refusal and ignored/untracked output parity. These are local
source/build checks, not actual main Actions, native acceptance or publication.
Private Pages configuration, requests and deployment remain owner-held.
Independent review and controller source-X/fresh-epoch/generated-Y delivery remain
required; the writer made no commit, push, tag or canonical installation.


## 2026-11-07 — Exact frontend notices and English search assets

Added exact upstream frontend notices and source-map provenance for the existing MaterialX 10.1.8 payload. Explicit English configuration and a small build hook reject language, corpus, reference, asset-set or hash drift before omitting the 35 unused language helpers. All nine retained core assets, original product legal files, guides, catalogue rows, media, runtime and dependency/build locks are preserved.

The strict site build and all 35 documentation tests pass. The complete new hook has 100% statement/branch coverage; real Git staging, checkout and archives preserve exact legal bytes. An independently installed matching lock reproduces all 57 output bytes and modes. Existing immutable source/output, epoch, concurrency and full-parity workflow checks remain active. Browser and independent review evidence are separate from these local checks.

Private Pages configuration, grants, requests and publication remain owner-held; this source follow-up adds none.
No product release or installation is claimed. Prior ordinary artifacts remain bound to their recorded revisions; a later Git revision changes genuine hatch-vcs metadata. Full current source archives include these documentation additions; no unchanged-sdist or whole-wheel identity is asserted. Native acceptance and owner installation remain separate.


## 2026-11-07 — installed icon path-tuple inventory refinement

The current HTML/CSS contains 45 distinct ordered SVG path tuples. A complete scan of the four installed MaterialX icon families finds 43 exact installed matches and two unmatched Lucide tuples, refining the earlier known-candidate inventory. The additional installed match is the Font Awesome version caret-down. Its existing CSS header and full notice retain Font Awesome Free 7.1.0, Fonticons and CC-BY-4.0 icon attribution. The official NPM caret SVG has different raw path bytes; no unmodified-primary SVG, whole-geometry or optimizer-recipe equivalence is claimed. The two unmatched Lucide tuples retain their pinned SCSS source attribution.

A new actual-output regression derives these counts and checks installed matches, unmatched CSS references and the caret header. It fails against the prior 42 count and passes with the corrected metadata. All 36 current documentation tests pass; full strict and independent exact-lock builds match every output byte and mode. Only the legal paragraph, corresponding inventory and legal search row change in the site. Runtime, packaging, generators, vendor assets, full notices, existing guidance and the Fly search fix remain exact. Fresh browser verification and independent review are recorded separately. No private Pages operation, delivery, installed-product upgrade or native acceptance is claimed.
