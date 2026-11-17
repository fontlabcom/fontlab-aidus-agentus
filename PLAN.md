---
this_file: PLAN.md
---

# Forward plan

## Functional work order — 2026-11-14

Prioritize usable generated Fly programs, package-aware menu scripts and guarded metric edits. Reconcile the host dock, separate brain, package knowledge and current App/Remopy providers together without widening provider access or weakening active-editor preservation.

Use small smoke checks and focused regressions for changed behavior and package boundaries. Keep the existing detailed acceptance tasks for a later testing pass; mandatory delivery hooks and current holds remain in force.

Issue 230 reconciliation is current. Issue 123 implementation remains paused; its acceptance backlog below is preserved, not resumed. Keep qualified Issue 207 candidates distinct from canonical source, ordinary installed artifacts, native acceptance and publication. Issue 210 defines the future plugin split; Issue 211 retains follow-up checks. The owner corrected the preparation catalogue reference to Issue 214.

## Issue 255 remaining native acceptance

After explicit D43 recovery and admission, qualify generated Fly programs and the package-load script in FontLab, retaining every package-aware, active-editor, M1–M11, authentication, dock lifecycle and shutdown scenario. Service/authentication behavior remains unexercised. Source, genuine artifact, ordinary external-install and release/download qualification for v1.1.12 is recorded in CHANGELOG. Existing private Pages and Issue 123 holds remain. Service/authentication was not exercised; CLI flags were not invoked because boot activates the brain. No prompt body or credentials are reproduced.

## Issue 242 Aidus Agentus rename

The source now lives in one package, `src/fontlab_aidus_agentus/` (`core/` brain, `plugin/` dock), distributed as `fontlab-aidus-agentus`. Remaining steps: independent review, coordinator repository/folder rename and release, then native qualification of the renamed menu folder and installer in an owned user folder. Configuration in `~/.config/aidus_code/config.json` stays readable as a fallback until owners have moved it.

## Host, brain and migration acceptance

Repair and qualify actual active-editor/CurrentGlyph payload preservation. Run every restored M1–M11 migration scenario and separate plugin/native-MCP preservation checks. Retain failed and held cases, especially provider authentication, dock lifecycle and quit cleanup. Preserve exact historical provenance and complete migration/native acceptance before operational brain cutover. Legacy retirement is already verified and remains separate.

Manually check the dock and the three menu scripts on the actual target FontLab build. Follow [docs/manual-tests.md](src_docs/md/guides/manual-tests.md). Automated runs cannot click the dock. Check analyst/coder MCP tool scopes against the 9783 catalogue contract; the earlier copilot check does not qualify these scoped agents.

## Read scope and metric writes

Natively qualify the `set_glyph_metrics` active-glyph guard: refuse when the workspace's active glyph differs from `CurrentGlyph()` by name or font. The glyph-info read has a dated native receipt; the refusal path has source tests only. Natively qualify automatic-layer metric refusal. The read investigation does not repair or accept the writer.

The read uses the workspace record only when it belongs to the active font; otherwise it errors. Native calibration remains required. Executor preflight error handling has separate source/artifact receipts in the v1.1.7 WORK.md (Git history).

## Package-aware native acceptance

In an owned FontLab session, run `run_in_fontlab/check_aidus_in_fontlab.vfpy`. Ask the dock for one task per package: a Plugmix Reporter, an App dialog, a Fontport UFO export and a Glyport import. Confirm that each generated program runs on an owned font. Preserve this four-scenario denominator and the package-load check. The package-aware prompt port was source-only and launched no FontLab; it has no native acceptance receipt.

Released App 1.2.15 provides `fontlabapp.plugins`, exposed to scripts as `fly.ap.plugins`; `fontlabapp.plugmix` is its deprecated compatibility alias and remains the metadata entry-point group name. Issue 255 source teaching has host-free provider identity evidence; native generated-code acceptance remains open.

## Unscheduled ideas

Keep multi-font awareness for generated scripts and a settings panel instead of JSON as unscheduled ideas. They are not prerequisites for the scoped migration MVP.

## Development checks

Prepare the two environments in README, then run `./test.sh`. The brain uses Python 3.13+; host tests use Python 3.11. `AIDUS_TEST_PYTHON` and `AIDUS_HOST_PYTHON` select existing interpreters. Never load provider keys during tests.

## Review, integration and cleanup

Use the detailed open tasks in [TODO.md](TODO.md) as the acceptance checklist. Complete one scoped MVP, then run the exact repository checks and unchanged 80% gate for each complete changed production module. Keep source, genuine artifacts, ordinary origins and native behavior separate. Obtain independent review before a milestone commit/push and verify the actual remote head. Reconcile concurrent source and all callers before main integration. Preserve recovery/unique work and fresh owner/worktree attachments before obsolete branch/file cleanup. Update TODO/PLAN and record only scoped verified results in CHANGELOG. Do not drive the owner's FontLab, install into its user folder or publish a site from this proposal.


## Documentation delivery gates

Obtain independent source/content/privacy review; deliver reviewed source X through
normal hooks, rebuild at X’s actual epoch, review generated Y and verify both actual
main-triggered jobs and immutable output parity. Private Pages configuration,
requests, deployment and live-site acceptance remain owner-held.
