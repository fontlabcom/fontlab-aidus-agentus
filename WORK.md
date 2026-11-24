---
this_file: WORK.md
---

## 2026-11-24 — Release and backlog checks

The v1.1.19 release and documentation workflows passed at `acb7464`. Both PyPI archives matched their published SHA-256 digests. The sdist contains the exact tagged installer. Local releases use `publish.sh` to dispatch the Trusted Publishing job in `release.yml`.

On the merged fly-january branch (`1005483`), `./test.sh` passed 895 brain tests and 771 host tests with 94% aggregate brain coverage. The prior strict theme build reproduced all 62 generated files and passed 36 documentation tests.

[TODO.md](TODO.md) lists the remaining checks and owner decisions. Native acceptance awaits D43 admission. Private Pages publication remains owner-held.
