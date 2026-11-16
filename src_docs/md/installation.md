---
this_file: src_docs/md/installation.md
---

# Install the host and brain

## Install from this checkout

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
   in [CONFIGURE.md](configure.md). The bundled manifest uses OpenAI for the
   copilot/analyst and Anthropic for the coder. Configure both providers, or
   [supply your own manifest](guides/architecture.md#agents-and-models).

For an existing release, substitute its downloaded Aidus wheel for `.` and use
`'/path/to/fontlab_aidus_agentus-VERSION-py3-none-any.whl[brain]'` for `'.[brain]'`.
See [RELEASE.md](https://github.com/fontlabcom/fontlab-aidus-agentus/blob/b41fac3ae9d0719d07dd56eb5150c56725cc09b3/RELEASE.md) for v0.2.0 hashes and its historical verification.
**The new menu scripts require the current checkout's host package**; v0.2.0
predates the installed launcher helpers. No PyPI installation is assumed.


See [configuration](configure.md) and [dock startup](dock-and-acp.md#run-in-fontlab).
