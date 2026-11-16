---
this_file: src_docs/md/configure.md
---

# Configure Aidus Agentus

Install the host and separate Python 3.13 brain first ([README](installation.md)).
Run **Aidus Agentus > Open Configuration** in FontLab's Scripts menu. It opens the
loaded file, or creates a small template at `~/.config/aidus_agentus/config.json`.
If no valid config loads but a file exists, it opens that file for repair.
Existing contents are preserved. Edit in a text editor and save as UTF-8 JSON
(double quotes, no comments).

## Minimal example

Replace the interpreter path with the brain environment's actual Python path:

```json
{
  "python_exe": "/absolute/path/to/brain/bin/python",
  "api_keys": {
    "openai": "~/.config/aidus_agentus/openai-key.txt",
    "anthropic": "~/.config/aidus_agentus/anthropic-key.txt"
  }
}
```

The bundled agents use OpenAI and Anthropic. To use another provider, change the
agent models as described in [agents and models](guides/architecture.md#agents-and-models).
Changing `api_keys` alone does not select a model.

## Keys in the JSON file

| Key | Default | Meaning |
| --- | --- | --- |
| `python_exe` | `null` | External Python 3.13+ executable with the brain extra installed. `AIDUS_PYTHON` overrides it; otherwise a `fontlab-aidus-python` executable on FontLab's PATH is tried. Use an absolute path; `~` is expanded. |
| `api_keys` | `{}` | Provider name to a private key-file path or `env:VARIABLE_NAME`. Never put the raw key here. File contents are stripped of surrounding whitespace. |
| `timeout_seconds` | `30` | Positive number of seconds allowed without matching progress on an outstanding ACP request. Idle time does not count. |
| `core_path` | `null` | Advanced: directory containing `core_launcher.py` (or legacy `boot.py`). Leave unset to use the installed launcher package. |
| `log_level` | `"INFO"` | Retained compatibility field; currently does not change logging. The brain configures INFO logging on stderr. |

The loader uses the **first valid JSON object**, in this order: `aidus_config.json`
beside the installed packages (repository root when running source), that filename
inside `src/fontlab_aidus_agentus/plugin/`, `~/.config/aidus_agentus/config.json`, then
`~/.aidus_config.json`. It overlays that one file on defaults; files are not merged.
Invalid/unreadable files are reported with their path and skipped, including
files saved in another encoding. Their contents are never printed or replaced.
Set `AIDUS_CONFIG` in FontLab's environment to use only that path; a
missing/invalid explicit file falls back to defaults.
`_loaded_from`, if shown by the loader, is diagnostic output, not a setting.

## Store provider keys safely

1. Outside the repository, create the two key files named in the example, using
   a text editor. Each file contains only its provider key. Do not paste keys
   into scripts, chat, screenshots or terminal commands.
2. On macOS/Linux, restrict access in a terminal:

   ```sh
   chmod 600 ~/.config/aidus_agentus/openai-key.txt ~/.config/aidus_agentus/anthropic-key.txt
   ```

3. Alternatively use a mapping such as `"openai": "env:MY_OPENAI_KEY"`. The
   variable must exist in **FontLab's process environment**; a terminal export
   does not update an already running GUI application. Without a mapping, the
   brain inherits canonical variables such as `OPENAI_API_KEY` from FontLab.

The plugin passes resolved mappings as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
to its child only; it does not add them to FontLab's parent environment or ACP
messages. Provider aliases `gemini` and `mistralai` map to `GOOGLE_API_KEY` and
`MISTRAL_API_KEY`. The external brain validates the selected models' credentials.

## Verify

In FontLab's Python console, check paths and key availability without printing keys:

```python
from fontlab_aidus_agentus.plugin.config import load_config, get_api_key
c = load_config()
print("Config:", c.get("_loaded_from", "defaults"))
print("Python:", c.get("python_exe"))
print("OpenAI key available:", bool(get_api_key(c, "openai")))
print("Anthropic key available:", bool(get_api_key(c, "anthropic")))
```

Shut down the dock with `fontlab_aidus_agentus.shutdown()` (import it first), then
run **Start Aidus Agentus** and wait for readiness. Ask for a read-only list of open
fonts. A `True` key check only confirms availability; a successful response checks
authentication. Reconnect alone does not reload host JSON or mapped key files.
See [troubleshooting](guides/troubleshooting.md) if it fails.
