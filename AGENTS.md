---
this_file: AGENTS.md
---

## Owner priority: functional progress first (2026-11-15)

Future agents must make large, swift advances in working functionality. Prioritize visible user problems and useful, coherent feature increments. This instruction sets the work order and supersedes older requirements to complete exhaustive testing or build test infrastructure before ordinary implementation.

Keep packages coherent and compatible. Check shared APIs, imports and lazy aliases, data formats, dependency direction, object ownership and lifetime, installers, launchers and examples. Update affected providers and consumers together; preserve existing supported behavior and avoid dependency cycles.

During implementation, use the smallest meaningful smoke checks and focused regression tests for the changed behavior and affected package boundaries. Detailed testing, exhaustive coverage, broad performance studies and full acceptance matrices can follow in a later testing pass. Do not let test harnesses, sandbox/supervisor design, repeated unchanged suites, evidence machinery or review paperwork become the main project. Build such infrastructure only when a concrete functional defect or necessary safety constraint requires it.

Record deferred checks and known limits plainly. Do not call untested native, installed or published behavior verified. Keep existing mandatory delivery hooks, preservation rules, licence/privacy obligations, repository exclusions and explicit native/publication holds intact. When one action is held, continue other authorized functional work instead of expanding unrelated infrastructure.

Choose the next substantial useful feature or shared fix and carry its affected providers and consumers together. Timebox supporting investigation; once focused checks establish a usable increment, continue functionality work. Queue detailed testing for a later pass with its concrete remaining checks instead of letting test infrastructure displace product delivery.

## Current scope — 2026-11-05

Issue 230 documentation reconciliation is current. Issue 123 remains paused. The qualified Issue 207 isolated candidate is separate from canonical source, installed artifacts, native acceptance and publication. Reconcile that candidate with later work before integration. Issue 210 specifies future architecture; Issue 211 retains unfinished follow-up checks. Retained dated receipts describe their original source and acceptance surface only.

Canonical source inspected for this proposal: `37b7f48522a7`. This is a dated source observation, not an installed or native acceptance claim.

Reconcile the qualified Issue 207 consolidated `src/fontlab_aidus_agentus` and `Scripts/Aidus Agentus` candidate against this canonical split; do not describe the candidate as installed.

Qualify active-editor/CurrentGlyph preservation, M1–M11, provider authentication, dock lifecycle and shutdown before operational brain cutover.

## Organization and checks

`src/fontlab_aidus_agentus/` is the host entry point; `src/fontlab_aidus_agentus/plugin/` owns the dock; `src/fontlab_aidus_agentus/core/` owns the brain. `Scripts/Aidus Agentus/` has the menu scripts and `run_in_fontlab/` the developer checks run inside FontLab.

Prepare the two environments in README, then run `./test.sh`. The brain uses Python 3.13+; host tests use Python 3.11. `AIDUS_TEST_PYTHON` and `AIDUS_HOST_PYTHON` select existing interpreters. Never load provider keys during tests.

# fontlab-aidus-agentus: agent guidance

## Live font testing in FontLab (owner instruction, 2026-11-10)

Test, verify and edit in the font that is open in FontLab 9. Don't hold back
because the owner might be working on it. Just work in it. If no font is open,
open a VFJ from `~/Desktop` first (File > Open, or `fontlab.flPackage(path)`
and `flWorkspace.instance().addPackage`). Those VFJs are for agents. Add glyphs,
kerning pairs, elements, contours, masters or anything else the test needs,
and save the files when that helps. This replaces older rules that required an
empty FontLab session or forbade editing open fonts. `fl-native.sh --mutating`
now runs with fonts open (`FL_REQUIRE_EMPTY=1` restores the old check). The
serialized lock still applies: one native run at a time. Don't quit or restart
FontLab, and don't close fonts from Python, because that has crashed the host.

Aidus Agentus is the coding agent that runs inside FontLab 9: a PythonQt chat dock
(`src/fontlab_aidus_agentus/plugin/ui.py`) plus a separate Python 3.13+ AgentPool brain. It writes
code for the whole FontLab Python package set (echopy, fly, fontlabapp,
pythonqtside, glyport, fontport, plugmix, scriptmix, remopy). Read
[README.md](README.md) and [docs/architecture.md](src_docs/md/guides/architecture.md) first.

## Rules that are not obvious from the code

- Two interpreters. Host code (`fontlab_aidus_agentus`, `fontlab_aidus_agentus.plugin`) must stay
  Python 3.11 and import no AI library. The brain (`fontlab_aidus_agentus.core`) is 3.13+.
  `./test.sh` needs `.venv` and `.venv-host`; the recipe is in README.md.
- The package knowledge the agent has lives in
  `src/fontlab_aidus_agentus/core/prompts/fontlab_api.md` (section "FontLab Python Packages You
  Can Target"). When a package is added, renamed or dropped, change that table and
  `tests/test_residue_port.py` together. Describe only APIs you have read in the
  package's own README or source; never invent import names.
- Never read, copy or print `.env`, provider keys or the owner's
  `~/.config/aidus_agentus/config.json`. Tests run with an empty HOME and no `*_API_KEY`.
- Do not copy anything from the retired legacy repository's `vendor/` checkouts (GPL and AGPL
  code among them). Third-party reference code stays out of this repository.
- Do not start FontLab, enable its MCP listener or install into its user folder from
  a development session; the owner manages those. Tests use fakes of `fontlab`,
  PythonQt and QProcess.
- Pre-push runs the workspace 80% coverage gate on changed production modules
  (`fontlab_aidus_agentus`, `fontlab_aidus_agentus.core`, `fontlab_aidus_agentus.plugin`). Do not bypass it.

## Where things live

| Need | Path |
| --- | --- |
| Menu scripts (the only ones exposed in FontLab) | `Scripts/Aidus Agentus/` |
| Diagnostics run in FontLab | `run_in_fontlab/check_aidus_in_fontlab.vfpy`, `run_in_fontlab/enable_fontlab_mcp.vfpy` |
| Agent roles, tools, models | `src/fontlab_aidus_agentus/core/agents.yml`, `src_docs/md/guides/architecture.md` |
| Open work | [PLAN.md](PLAN.md), [TODO.md](TODO.md); history in [CHANGELOG.md](CHANGELOG.md) |

## Milestones and delivery

Read [PLAN.md](PLAN.md), [TODO.md](TODO.md) and [WORK.md](WORK.md) before work.
Make the smallest complete MVP for one named acceptance task. Find all callers,
tests, fixtures, exports and documentation first. Use graph impact before source
symbol edits; confirm stale or unknown graph results against current source.
Keep product work in isolated successors and preserve the owner's checkout.

Run this repository's exact checks and the unchanged 80% gate for each complete
changed production module. Use an independent review before a milestone commit.
Under the current owner task, commit and push reviewed, passing milestones;
verify remote heads rather than inferring delivery from local tracking refs.
Before main integration, reconcile concurrent work and all consumers, run graph
change analysis and repeat the required acceptance on the combined source.

Before removing obsolete branches or files, prove integration, retain recoverable
unique work and check fresh owner/worktree attachments. Preserve sealed reports,
licences, archives and private data. Do not rewrite history by implication.
Remove verified completed work from PLAN/TODO and record scoped evidence in
CHANGELOG. Keep implemented-only native/artifact checks open in TODO. Issue 123
remains paused; no instruction here authorizes driving the owner's FontLab,
installing into its user folder or publishing a site.


## Documentation source/build checks

`src_docs/mkdocs.yml` uses fly-january 0.4.0 or later (remote theme assets) for the FontLab menu and footer.
Use the exact hash-locked `src_docs/requirements.txt` in a separate Python 3.13
environment. With that environment active, run `sh src_docs/build.sh`, then `python -B -m unittest discover -s
tests_docs -v`. Preserve source epoch, immutable source/output lineage and complete
tracked plus ignored/untracked output parity. Do not run Pages operations while
publication is owner-held. Runtime/native and installed-hook gates remain separate.

## Integration rounds

After each round of important changes, integrate it into `main` and upstream:
fetch `origin/main`, build the change on top of it in an isolated branch or
worktree, and resolve conflicts by keeping both our work and teammates' work.
Never discard upstream commits, and never force-push. Run the repository's
checks on the merged result, then push to `origin main`. Record the change in
CHANGELOG.md, move verified-solved TODO.md items into CHANGELOG.md, update
PLAN.md, and continue with the next TODO.md item until the list is clear.
`install.vfpy` is shared: keep it byte-identical in every installer repository.

## Agent workflow (Issue 250, 2026-11-10)

- Plan with `superpowers:subagent-driven-development`: one fresh implementer per task, a separate read-only reviewer, then the controller runs the gates and commits.
- Send bulk, well-specified work to Codex via the `codex-delegate` skill (`node ~/.agents/skills/codex-delegate/scripts/relay.mjs --brief BRIEF --cd WORKTREE`, in the background). Use `claude-delegate` or `cursor-delegate` for second opinions or independent lanes. Delegates never commit, push or tag.
- Work in a fresh worktree of `origin/main` on the workspace data volume; never pull, switch or reset the owner checkout. Merge `origin/main` again before pushing, keep both sides' CHANGELOG/PLAN/TODO entries, rerun the full suite, lint and graph change analysis, push through the pre-push hook where one is installed (never force), verify the remote SHA and the CI run where a workflow is configured. Held private Pages operations (workspace D41) stay held.
- Release: tag the next semver above the latest tag and publish a GitHub release. Install released, gated packages into `~/Library/Application Support/FontLab/FontLab 9/` and test live in FontLab 9. This owner route (Issue 250) supersedes, for released packages only, every older line in this guide that forbids installing into the FontLab user folder or its site-packages, owner-managed editable installs, or starting FontLab for a live test (the owner's canonical editable checkouts themselves stay owner-managed): record the previous installed distribution first so it can be restored, and never touch FontLab preferences (owner fonts and documents: see live font editing below); native work goes through the workspace `verification/issue-104/fl-native.sh` gate.
- Documents: CHANGELOG holds verified completed work; TODO only open or to-verify items; PLAN the major remaining changes; WORK.md the current round only (older WORK bytes are archived on the owner's workspace data volume, not public).
- Native defects: issues at github.com/fontlab/fl; fixes as pull requests to fontlab/Proteus, fontlab/FontGate or fontlab/pyfontgate. Never commit to the local C++ snapshot.
- Older "work directly" or "no delegation" lines in this guide are superseded by this section (Issue 250).
- Live font editing (owner, 2026-11-10; workspace D44): test, verify and edit the font open in FontLab 9, and do not stop because the owner might be working in it. Open a VFJ from `~/Desktop` first (those files are for agents), then add glyphs, kerning pairs, elements, contours, masters or whatever the test needs, and save them freely. This supersedes, for live testing, every older line here that forbids mutating owner fonts or documents or requires owned fixtures only. FontLab preferences, Output folders and global update queues stay untouched. Keep the serialized host lock (`fl-native.sh`, one native run at a time; `--mutating` now allows open fonts); do not quit or restart FontLab and do not close fonts from Python, which has crashed the host.
