---
this_file: src_docs/md/development-and-limits.md
---

# Development and acceptance limits

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
in the real application. [guides/manual-tests.md](guides/manual-tests.md) lists what
only a person at FontLab can check.

Build with `uv build`. Wheels contain the runtime packages, prompts and tool
definitions. The sdist also contains the menu scripts, user docs and tests.
[DEPENDENCIES.md](https://github.com/fontlabcom/fontlab-aidus-agentus/blob/b41fac3ae9d0719d07dd56eb5150c56725cc09b3/DEPENDENCIES.md) explains the dependency pins.

The v0.2.0 migration's native verification is recorded in the [v1.1.7 WORK.md](https://github.com/fontlabcom/fontlab-aidus-agentus/blob/v1.1.7/WORK.md) and
[RELEASE.md](https://github.com/fontlabcom/fontlab-aidus-agentus/blob/b41fac3ae9d0719d07dd56eb5150c56725cc09b3/RELEASE.md). The 2026-10-16 native check (FontLab 9.0.9783) covered
import from this checkout, the installer, the executor tools on an owned font and
deterministic ACP roundtrips through the fallback executor and native MCP; it did
not open the dock or run the menu scripts.


## Open acceptance

Active-editor/CurrentGlyph read and write preservation are separate. Automatic-layer
metric refusal must precede setters/history, including equal values; an empty request
remains successful. Source guards do not establish whole-font Undo/Redo or save/reopen.
Keep all M1–M11 and four package-aware native scenarios in the [manual guide](guides/manual-tests.md).
Provider key availability is separate from authentication. The dock has no model picker;
Reconnect reuses host settings while shutdown/start reloads them. A timeout is an
unknown outcome and never permission to replay a mutation.

Legacy retirement is complete; it supplies no new native, runtime CI or brain-cutover
result. Historical missing-component CI remains historical. This documentation workflow
builds only the locked site; it does not replace product tests or signed/release checks.
Private Pages configuration, requests and deployment are owner-held.
