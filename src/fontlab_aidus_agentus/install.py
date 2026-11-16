# this_file: src/fontlab_aidus_agentus/install.py
"""Install, check or remove the Aidus Agentus Scripts-menu folder in a FontLab user folder.

Ported from the legacy repository's install.py. The old
installer symlinked the whole plugin into FontLab's Scripts folder, replaced
whatever was there, and ran `uv sync` for the brain. Here the host package is
installed with `uv pip` (README), and this module only manages
`<user folder>/Scripts/Aidus Agentus`: the same three thin menu scripts as the
repository's `Scripts/Aidus Agentus/` folder plus a manifest (`.fontlab-aidus-agentus-install`,
format 1) holding the sha256 of every file it wrote. Ownership is per file:
unknown entries are kept, a modified, foreign or symlinked entry stops an install
before anything changes, and uninstall removes only unmodified owned files and
the folder only when it is then empty. A folder without a valid manifest,
including the workspace orchestrator's symlink, is never touched.

Run on the host, not inside FontLab: `fontlab-aidus-install {install,check,uninstall}`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import stat
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

MENU_FOLDER = "Aidus Agentus"
MARKER = ".fontlab-aidus-agentus-install"
MARKER_FORMAT = 1
PACKAGE = "fontlab-aidus-agentus"
FONTLAB = "FontLab 9"
ACTIONS = {
    "Enable FontLab MCP.py": ("enable_mcp", "Enable native FontLab MCP from FontLab's Scripts menu."),
    "Open Configuration.py": ("open_configuration", "Open the active host configuration from FontLab's Scripts menu."),
    "Start Aidus Agentus.py": ("start", "Open Aidus Agentus from FontLab's Scripts menu."),
}
SCRIPT = '''# this_file: Scripts/Aidus Agentus/{name}
"""{doc}"""

try:
    from fontlab_aidus_agentus.launchers import {action}
except ImportError:
    print(
        "[Aidus Agentus] Install or update fontlab-aidus-agentus in FontLab's Python path. "
        "Keep the AI brain in a separate Python 3.13+ environment. "
        "Setup (repository access required): "
        "https://github.com/fontlabcom/fontlab-aidus-agentus/blob/main/README.md"
    )
else:
    {action}()
'''


class InstallError(RuntimeError):
    """The requested change would touch an entry this installer does not own."""


def default_user_folder() -> Path:
    """Return FontLab 9's per-user folder (the parent of its Scripts folder)."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "FontLab" / FONTLAB
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise InstallError("APPDATA is not set; pass --user-folder")
        return Path(appdata) / "Fontlab" / FONTLAB
    raise InstallError(f"Unsupported platform {system}; pass --user-folder")


def menu_scripts() -> dict[str, str]:
    """Source text of each menu script, identical to the repository's `Scripts/Aidus Agentus/` files."""
    return {name: SCRIPT.format(name=name, doc=doc, action=action) for name, (action, doc) in ACTIONS.items()}


def menu_path(user_folder: Path | None = None) -> Path:
    return Path(user_folder or default_user_folder()).expanduser() / "Scripts" / MENU_FOLDER


def menu_state(target: Path) -> str:
    """Classify the menu entry: missing, link, empty (unmarked, nothing inside),
    copy (ours, valid manifest) or foreign."""
    if target.is_symlink():
        return "link"
    if not target.exists():
        return "missing"
    if not target.is_dir():
        return "foreign"
    if _load_marker(target) is not None:
        return "copy"
    return "empty" if not any(target.iterdir()) else "foreign"


def read_marker(target: Path) -> dict[str, Any] | None:
    """The validated ownership manifest, or None (absent, symlinked, malformed or foreign).

    `files` maps each owned script to the sha256 written last; while an install is
    in progress (`state: installing`) `pending` maps the scripts about to be
    written to their new sha256, so an interrupted run can be resumed.
    """
    loaded = _load_marker(target)
    return loaded[0] if loaded else None


def _load_marker(target: Path) -> tuple[dict[str, Any], bytes, Path] | None:
    """(manifest, its bytes, where they were read).

    Falls back to a single manifest copy left aside (`.<MARKER>.<uuid>.aidus-old`)
    when a crash hit between moving the manifest aside and linking its successor.
    """
    path = target / MARKER
    candidates = [path] if os.path.lexists(path) else sorted(target.glob("." + MARKER + ".*.aidus-old"))
    loaded = [entry for entry in map(_parse_marker_file, candidates) if entry is not None]
    if len(candidates) != 1 or len(loaded) != 1:
        return None
    return loaded[0]


def _parse_marker_file(path: Path) -> tuple[dict[str, Any], bytes, Path] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("format") != MARKER_FORMAT or data.get("package") != PACKAGE:
        return None
    if not isinstance(data.get("version"), str) or data.get("state", "installed") not in ("installing", "installed"):
        return None
    for key in ("files", "pending"):
        table = data.get(key, {})
        if not isinstance(table, dict) or not all(_valid_entry(n, d) for n, d in table.items()):
            return None
    if not isinstance(data.get("files"), dict):
        return None
    return data, raw, path


def _valid_entry(name: Any, digest: Any) -> bool:
    return (isinstance(name, str) and name == Path(name).name and name.endswith(".py")
            and isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest))


def _owned(marker: dict[str, Any]) -> dict[str, set[str]]:
    """Every sha256 this installer may have left at each name (written or pending)."""
    owned: dict[str, set[str]] = {}
    for key in ("files", "pending"):
        for name, digest in marker.get(key, {}).items():
            owned.setdefault(name, set()).add(digest)
    return owned


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _current(path: Path) -> str | None:
    """sha256 of a regular file; None when absent; "!" for a symlink or other entry."""
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(mode):
        return "!"
    return _digest(path.read_bytes())


def _plan(target: Path, owned: dict[str, set[str]]) -> tuple[list[tuple], dict[str, str], list[str]]:
    """Decide every change before touching the disk: (actions, adopted, conflicts).

    Actions are ("create", name, data), ("replace", name, data, expected sha256)
    and ("remove", name, expected sha256); each is re-verified just before it runs.
    """
    actions, adopted, conflicts = [], {}, []
    for name, text in menu_scripts().items():
        data = text.encode("utf-8")
        current = _current(target / name)
        if current is None:
            actions.append(("create", name, data))
        elif current == "!":
            conflicts.append(("symlink: " if (target / name).is_symlink() else "foreign: ") + name)
        elif current == _digest(data):
            adopted[name] = current
        elif current in owned.get(name, ()):
            actions.append(("replace", name, data, current))
        elif name in owned:
            conflicts.append(f"modified: {name}")
        else:
            conflicts.append(f"foreign: {name}")
    for name in sorted(set(owned) - set(menu_scripts())):
        current = _current(target / name)
        if current is not None and current in owned[name]:
            actions.append(("remove", name, current))
    return actions, adopted, conflicts


def _temporary(folder: Path, data: bytes) -> str:
    """A fresh, exclusively created file in `folder`; only files made here are ever deleted."""
    handle, name = tempfile.mkstemp(prefix=".fontlab-aidus-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
    except BaseException:
        os.unlink(name)
        raise
    return name


def _create(path: Path, data: bytes) -> None:
    """Create `path` only if it is still absent (hard link fails on any existing entry)."""
    temporary = _temporary(path.parent, data)
    try:
        os.link(temporary, path)
    except FileExistsError:
        raise InstallError(f"{path.parent}: left unchanged; changed since planning: {path.name}") from None
    finally:
        os.unlink(temporary)


def _take(path: Path, expected: str) -> Path:
    """Move an owned file aside and confirm it is still the planned version.

    The rename is atomic, so whatever sits at `path` now is what gets checked; an
    edit made afterwards creates a new file at `path` that later steps never touch.
    On a mismatch the file goes back (or, if `path` was re-created meanwhile, stays
    beside it under its quarantine name) and the install stops.
    """
    aside = path.with_name(".%s.%s.aidus-old" % (path.name, uuid.uuid4().hex))
    try:
        os.rename(path, aside)
    except FileNotFoundError:
        raise InstallError(f"{path.parent}: left unchanged; changed since planning: {path.name}") from None
    if _current(aside) == expected:
        return aside
    try:
        os.link(aside, path)
        os.unlink(aside)
        kept = ""
    except FileExistsError:
        kept = f" (its previous content is kept as {aside.name})"
    raise InstallError(f"{path.parent}: left unchanged; changed since planning: {path.name}{kept}")


def _restore(aside: Path, path: Path) -> None:
    """Put a taken file back if nothing new appeared at `path`; otherwise keep it aside."""
    try:
        os.link(aside, path)
    except FileExistsError:
        return
    os.unlink(aside)


def _write_marker(target: Path, marker: dict[str, Any], previous: bytes, source: Path) -> tuple[bytes, Path]:
    """Replace the manifest read as `previous` from `source`, losslessly like a script.

    The current manifest is moved aside and must still hold `previous`; the new one
    is then created exclusively. A foreign file that appears meanwhile is kept and
    the run stops. Returns the new bytes and path, the next expected state.
    """
    data = (json.dumps(marker, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path = target / MARKER
    aside = _take(source, _digest(previous))
    try:
        _create(path, data)
    except BaseException:
        _restore(aside, source)  # never over a file recreated at `source` meanwhile
        raise
    os.unlink(aside)
    return data, path


def _make_folder(target: Path) -> None:
    """Exclusive creation: fails if anything (file, folder or link) is already there."""
    os.mkdir(target)


def _publish_folder(target: Path, marker: dict[str, Any]) -> bytes:
    """Create the menu folder, then its manifest at once.

    The folder exists without a manifest only between these two steps; an empty
    unmarked folder is recoverable (install takes it over, uninstall removes it).
    Nothing is ever renamed onto `target`.
    """
    data = (json.dumps(marker, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        _make_folder(target)
    except FileExistsError:
        raise InstallError(f"{target}: appeared during the install; left unchanged") from None
    try:
        _create(target / MARKER, data)
    except BaseException:
        try:
            os.rmdir(target)  # only while still empty
        except OSError:
            pass
        raise
    return data


def install(user_folder: Path | None = None) -> Path:
    """Write the menu scripts with an ownership manifest.

    Unknown files are kept. A script this installer wrote is replaced only while
    unmodified; a modified, foreign or symlinked entry stops an install before
    anything changes, and every write or removal re-checks its destination first.
    A provisional manifest goes first, so an interrupted install can be rerun.
    """
    target = menu_path(user_folder)
    state = menu_state(target)
    if state in ("link", "foreign"):
        raise InstallError(f"{target} exists and was not installed by fontlab-aidus-install ({state}); left unchanged")
    if state == "empty":
        try:
            os.rmdir(target)  # left by an interrupted uninstall; only ever removed while empty
        except OSError:
            raise InstallError(f"{target}: changed while installing; left unchanged") from None
    loaded = _load_marker(target) if state == "copy" else None
    marker = loaded[0] if loaded else None
    owned = _owned(marker) if marker else {}
    actions, adopted, conflicts = _plan(target, owned)
    if conflicts:
        raise InstallError(f"{target}: left unchanged; resolve these entries first: " + ", ".join(conflicts))
    final = {name: _digest(text.encode("utf-8")) for name, text in menu_scripts().items()}
    # Carry ownership forward: every owned file still on disk unmodified, plus adopted ones.
    files = {name: current for name in owned
             if (current := _current(target / name)) is not None and current in owned[name]}
    files.update(adopted)
    pending = {name: final[name] for name in final if name not in adopted}
    provisional = {"format": MARKER_FORMAT, "package": PACKAGE, "version": _version(),
                   "state": "installing", "files": files, "pending": pending}
    if marker is None:
        previous, source = _publish_folder(target, provisional), target / MARKER
    else:
        previous, source = _write_marker(target, provisional, loaded[1], loaded[2])
    for action in actions:
        kind, name = action[0], action[1]
        path = target / name
        if kind == "create":
            _create(path, action[2])
        elif kind == "replace":
            aside = _take(path, action[3])
            try:
                _create(path, action[2])
            except BaseException:
                _restore(aside, path)
                raise
            os.unlink(aside)
        else:
            os.unlink(_take(path, action[2]))
    _write_marker(target, {"format": MARKER_FORMAT, "package": PACKAGE, "version": _version(),
                           "state": "installed", "files": final}, previous, source)
    return target


def uninstall(user_folder: Path | None = None) -> dict[str, Any] | None:
    """Remove the unmodified files this installer wrote, then the folder if it is empty.

    Returns None when nothing of ours is installed, else {"removed", "kept", "folder_removed"}.
    """
    target = menu_path(user_folder)
    state = menu_state(target)
    if state == "missing":
        return None
    if state == "empty":  # an earlier uninstall stopped after removing the manifest
        try:
            os.rmdir(target)
        except OSError:
            return {"removed": [], "kept": [], "folder_removed": False}
        return {"removed": [], "kept": [], "folder_removed": True}
    if state != "copy":
        raise InstallError(f"{target} was not installed by fontlab-aidus-install ({state}); left unchanged")
    marker, marker_bytes, marker_path = _load_marker(target)
    removed, kept = [], []
    for name, digests in sorted(_owned(marker).items()):
        path = target / name
        current = _current(path)
        if current is None:
            continue
        if current not in digests:
            kept.append(name)
            continue
        try:
            os.unlink(_take(path, current))
            removed.append(name)
        except InstallError:
            kept.append(name)
    os.unlink(_take(marker_path, _digest(marker_bytes)))
    try:
        os.rmdir(target)  # succeeds only while empty
        folder_removed = True
    except OSError:
        folder_removed = False
    return {"removed": removed, "kept": kept, "folder_removed": folder_removed}


def check(user_folder: Path | None = None) -> dict[str, Any]:
    """Report menu, package and brain-interpreter state without changing anything."""
    target = menu_path(user_folder)
    state = menu_state(target)
    current = state in ("copy", "link") and all(
        (state == "link" or not (target / name).is_symlink())
        and (target / name).is_file() and (target / name).read_text(encoding="utf-8") == text
        for name, text in menu_scripts().items()
    )
    try:
        from fontlab_aidus_agentus.plugin.main import _resolve_paths

        python_exe = _resolve_paths()[0]
        python_error = None
    except (RuntimeError, OSError) as error:
        python_exe, python_error = None, str(error)
    python_ok = bool(python_exe) and os.path.isfile(python_exe) and os.access(python_exe, os.X_OK)
    if python_exe and not python_ok:
        python_error = "configured Python is not an executable file"
    return {
        "menu": str(target),
        "menu_state": state,
        "menu_current": current,
        "version": _version(),
        "python_exe": python_exe,
        "python_ok": python_ok,
        "python_error": python_error,
        "ready": current and python_ok,
    }


def _version() -> str:
    from fontlab_aidus_agentus import __version__

    return __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fontlab-aidus-install", description=__doc__.split("\n")[0])
    parser.add_argument("action", choices=["install", "check", "uninstall"])
    parser.add_argument("--user-folder", type=Path, help="FontLab user folder (default: this platform's FontLab 9 folder)")
    args = parser.parse_args(argv)
    try:
        if args.action == "install":
            print(f"Installed {install(args.user_folder)}. Restart {FONTLAB} or rescan its Scripts menu.")
            return 0
        if args.action == "uninstall":
            report = uninstall(args.user_folder)
            if report is None:
                print("Nothing of ours is installed.")
            else:
                print(f"Removed {len(report['removed'])} owned file(s); kept modified or replaced: "
                      f"{', '.join(report['kept']) or 'none'}; folder "
                      f"{'removed' if report['folder_removed'] else 'kept (other files remain)'}.")
            return 0
        report = check(args.user_folder)
    except InstallError as error:
        print(f"fontlab-aidus-install: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
