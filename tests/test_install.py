# this_file: tests/test_install.py
"""Scripts-menu installer: temp FontLab-like user folders only, never ~/Library."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from fontlab_aidus_agentus import install

ROOT = Path(__file__).resolve().parents[1]
REPO_MENU = ROOT / "Scripts" / "Aidus Agentus"


@pytest.fixture
def user_folder(tmp_path):
    folder = tmp_path / "FontLab 9"
    (folder / "Scripts").mkdir(parents=True)
    return folder


@pytest.fixture(autouse=True)
def guard_real_scripts_folder(monkeypatch, isolated_home):
    """Any default-path call lands in the isolated HOME, never the owner's folder."""
    real = Path(os.path.expanduser("~"))
    assert real == isolated_home, "conftest must isolate HOME"


def test_menu_scripts_when_generated_match_repository_folder_byte_for_byte():
    generated = install.menu_scripts()
    repo = {p.name: p.read_text(encoding="utf-8") for p in REPO_MENU.glob("*.py")}
    assert generated == repo, "One source of truth: installed scripts equal Scripts/Aidus Agentus/*.py"


def test_install_when_folder_empty_writes_scripts_and_marker(user_folder):
    target = install.install(user_folder)
    assert target == user_folder / "Scripts" / "Aidus Agentus"
    names = {p.name for p in target.iterdir()}
    assert names == {*install.ACTIONS, install.MARKER}
    marker = json.loads((target / install.MARKER).read_text())
    assert marker["package"] == "fontlab-aidus-agentus"
    assert install.menu_state(target) == "copy"


def test_install_when_scripts_folder_missing_creates_it(tmp_path):
    folder = tmp_path / "fresh"
    target = install.install(folder)
    assert target.is_dir() and install.menu_state(target) == "copy"


def _marker(target):
    return json.loads((target / install.MARKER).read_text())


def _sha(text):
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_install_when_run_twice_keeps_unknown_entries(user_folder):
    target = install.install(user_folder)
    (target / "My Own Script.py").write_text("print('mine')\n")
    (target / "notes.txt").write_text("user note\n")
    install.install(user_folder)
    assert (target / "My Own Script.py").read_text() == "print('mine')\n", "X5 P1: user scripts survive reinstall"
    assert (target / "notes.txt").read_text() == "user note\n"


def test_install_when_marker_records_each_written_file_hash(user_folder):
    target = install.install(user_folder)
    marker = _marker(target)
    assert marker["format"] == install.MARKER_FORMAT and marker["package"] == "fontlab-aidus-agentus"
    assert marker["files"] == {name: _sha(text) for name, text in install.menu_scripts().items()}


def test_install_when_owned_file_is_older_version_refreshes_it(user_folder):
    target = install.install(user_folder)
    old = "print('previous release')\n"
    (target / "Start Aidus Agentus.py").write_text(old)
    marker = _marker(target)
    marker["files"]["Start Aidus Agentus.py"] = _sha(old)
    (target / install.MARKER).write_text(json.dumps(marker))
    install.install(user_folder)
    assert (target / "Start Aidus Agentus.py").read_text() == install.menu_scripts()["Start Aidus Agentus.py"]


def test_install_when_owned_file_dropped_from_release_removes_only_if_unmodified(user_folder):
    target = install.install(user_folder)
    for name, text in (("Retired.py", "print('retired')\n"), ("Edited Retired.py", "print('old')\n")):
        (target / name).write_text(text)
    marker = _marker(target)
    marker["files"]["Retired.py"] = _sha("print('retired')\n")
    marker["files"]["Edited Retired.py"] = _sha("print('different')\n")
    (target / install.MARKER).write_text(json.dumps(marker))
    install.install(user_folder)
    assert not (target / "Retired.py").exists()
    assert (target / "Edited Retired.py").read_text() == "print('old')\n", "A modified file is kept"
    assert "Edited Retired.py" not in _marker(target)["files"]


def test_install_when_owned_script_modified_refuses_and_changes_nothing(user_folder):
    target = install.install(user_folder)
    (target / "Start Aidus Agentus.py").write_text("my edit\n")
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    with pytest.raises(install.InstallError, match="modified.*Start Aidus Agentus.py"):
        install.install(user_folder)
    assert {p.name: p.read_bytes() for p in target.iterdir()} == before


def test_install_when_unowned_file_takes_a_script_name_refuses(user_folder):
    target = install.install(user_folder)
    marker = _marker(target)
    del marker["files"]["Open Configuration.py"]
    (target / install.MARKER).write_text(json.dumps(marker))
    (target / "Open Configuration.py").write_text("someone else's\n")
    with pytest.raises(install.InstallError, match="foreign.*Open Configuration.py"):
        install.install(user_folder)
    assert (target / "Open Configuration.py").read_text() == "someone else's\n"


def test_install_when_unowned_file_already_identical_is_adopted(user_folder):
    target = install.install(user_folder)
    marker = _marker(target)
    del marker["files"]["Open Configuration.py"]
    (target / install.MARKER).write_text(json.dumps(marker))
    install.install(user_folder)
    assert "Open Configuration.py" in _marker(target)["files"]


def test_install_when_script_is_symlink_refuses_and_never_writes_through_it(user_folder, tmp_path):
    target = install.install(user_folder)
    outside = tmp_path / "outside.py"
    outside.write_text("precious\n")
    script = target / "Start Aidus Agentus.py"
    script.unlink()
    script.symlink_to(outside)
    with pytest.raises(install.InstallError, match="symlink.*Start Aidus Agentus.py"):
        install.install(user_folder)
    assert outside.read_text() == "precious\n" and script.is_symlink()


def test_install_when_owned_script_deleted_by_user_recreates_it(user_folder):
    target = install.install(user_folder)
    (target / "Enable FontLab MCP.py").unlink()
    install.install(user_folder)
    assert (target / "Enable FontLab MCP.py").read_text() == install.menu_scripts()["Enable FontLab MCP.py"]


@pytest.mark.parametrize(
    "marker_text",
    ["", "not json", "[]", '{"package": "fontlab-aidus-agentus"}',
     '{"format": 99, "package": "fontlab-aidus-agentus", "version": "1", "files": {}}',
     '{"format": 1, "package": "other", "version": "1", "files": {}}',
     '{"format": 1, "package": "fontlab-aidus-agentus", "version": "1", "files": {"x.py": "zz"}}',
     '{"format": 1, "package": "fontlab-aidus-agentus", "version": "1", "files": {"../escape.py": "%s"}}' % ("0" * 64)],
)
def test_menu_state_when_marker_invalid_is_foreign_and_install_refuses(user_folder, marker_text):
    target = user_folder / "Scripts" / "Aidus Agentus"
    target.mkdir()
    (target / install.MARKER).write_text(marker_text)
    assert install.menu_state(target) == "foreign"
    with pytest.raises(install.InstallError):
        install.install(user_folder)


def test_menu_state_when_marker_is_symlink_is_foreign(user_folder, tmp_path):
    real = install.install(tmp_path / "elsewhere") / install.MARKER
    target = user_folder / "Scripts" / "Aidus Agentus"
    target.mkdir()
    (target / install.MARKER).symlink_to(real)
    assert install.menu_state(target) == "foreign"
    with pytest.raises(install.InstallError):
        install.uninstall(user_folder)
    assert real.exists()


def test_install_when_foreign_folder_exists_refuses_and_leaves_it(user_folder):
    foreign = user_folder / "Scripts" / "Aidus Agentus"
    foreign.mkdir()
    (foreign / "mine.py").write_text("x = 1\n")
    with pytest.raises(install.InstallError, match="foreign"):
        install.install(user_folder)
    assert [p.name for p in foreign.iterdir()] == ["mine.py"]


def test_install_when_symlink_exists_refuses_and_keeps_link(user_folder, tmp_path):
    elsewhere = tmp_path / "checkout" / "Aidus Agentus"
    elsewhere.mkdir(parents=True)
    link = user_folder / "Scripts" / "Aidus Agentus"
    link.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(install.InstallError, match="link"):
        install.install(user_folder)
    assert link.is_symlink() and not any(elsewhere.iterdir())


def test_uninstall_when_only_owned_files_removes_folder(user_folder):
    target = install.install(user_folder)
    report = install.uninstall(user_folder)
    assert report["removed"] == sorted(install.ACTIONS) and report["kept"] == []
    assert report["folder_removed"] is True and not target.exists()


def test_uninstall_when_user_files_present_keeps_them_and_the_folder(user_folder):
    target = install.install(user_folder)
    (target / "My Own Script.py").write_text("print('mine')\n")
    (target / "Start Aidus Agentus.py").write_text("edited by user\n")
    report = install.uninstall(user_folder)
    assert sorted(p.name for p in target.iterdir()) == ["My Own Script.py", "Start Aidus Agentus.py"]
    assert report["kept"] == ["Start Aidus Agentus.py"] and report["folder_removed"] is False
    assert not (target / install.MARKER).exists()


def test_uninstall_when_owned_name_is_now_symlink_keeps_link_and_target(user_folder, tmp_path):
    target = install.install(user_folder)
    outside = tmp_path / "outside.py"
    outside.write_text("precious\n")
    (target / "Start Aidus Agentus.py").unlink()
    (target / "Start Aidus Agentus.py").symlink_to(outside)
    report = install.uninstall(user_folder)
    assert "Start Aidus Agentus.py" in report["kept"] and outside.read_text() == "precious\n"


def test_uninstall_when_missing_returns_none(user_folder):
    assert install.uninstall(user_folder) is None


@pytest.mark.parametrize("kind", ["foreign", "link"])
def test_uninstall_when_not_ours_refuses(user_folder, tmp_path, kind):
    target = user_folder / "Scripts" / "Aidus Agentus"
    if kind == "link":
        target.symlink_to(tmp_path, target_is_directory=True)
    else:
        target.mkdir()
        (target / "theirs.py").write_text("x = 1\n")
    with pytest.raises(install.InstallError):
        install.uninstall(user_folder)
    assert target.exists() or target.is_symlink()


def test_menu_state_when_file_in_place_of_folder_is_foreign(user_folder):
    target = user_folder / "Scripts" / "Aidus Agentus"
    target.write_text("not a folder")
    assert install.menu_state(target) == "foreign"


def test_menu_path_when_unicode_and_spaces_in_folder_round_trips(tmp_path):
    folder = tmp_path / "Użytkownik 字体 folder"
    target = install.install(folder)
    assert target.parent.parent == folder
    assert install.check(folder)["menu_state"] == "copy"


def test_default_user_folder_when_macos_is_application_support(monkeypatch, isolated_home):
    monkeypatch.setattr(install.platform, "system", lambda: "Darwin")
    assert install.default_user_folder() == isolated_home / "Library/Application Support/FontLab/FontLab 9"


def test_default_user_folder_when_windows_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(install.platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert install.default_user_folder() == tmp_path / "Fontlab" / "FontLab 9"


def test_default_user_folder_when_windows_without_appdata_raises(monkeypatch):
    monkeypatch.setattr(install.platform, "system", lambda: "Windows")
    monkeypatch.delenv("APPDATA", raising=False)
    with pytest.raises(install.InstallError, match="APPDATA"):
        install.default_user_folder()


def test_default_user_folder_when_linux_raises(monkeypatch):
    monkeypatch.setattr(install.platform, "system", lambda: "Linux")
    with pytest.raises(install.InstallError, match="Unsupported"):
        install.default_user_folder()


def test_install_when_no_folder_given_uses_isolated_default(monkeypatch, isolated_home):
    monkeypatch.setattr(install.platform, "system", lambda: "Darwin")
    target = install.install()
    assert isolated_home in target.parents


def _executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_check_when_installed_and_python_configured_is_ready(user_folder, tmp_path, monkeypatch):
    install.install(user_folder)
    monkeypatch.setenv("AIDUS_PYTHON", str(_executable(tmp_path / "python")))
    report = install.check(user_folder)
    assert report["ready"] is True and report["menu_current"] is True
    assert report["python_ok"] is True and report["python_error"] is None


def test_check_when_nothing_configured_reports_missing_python(user_folder, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    report = install.check(user_folder)
    assert report["menu_state"] == "missing" and report["ready"] is False
    assert report["python_exe"] is None and "AIDUS_PYTHON" in report["python_error"]


def test_check_when_python_path_is_not_executable_reports_it(user_folder, tmp_path, monkeypatch):
    install.install(user_folder)
    missing = tmp_path / "no-such-python"
    monkeypatch.setenv("AIDUS_PYTHON", str(missing))
    report = install.check(user_folder)
    assert report["python_ok"] is False and report["ready"] is False
    assert "not an executable" in report["python_error"]


def test_check_when_copy_is_outdated_is_not_current(user_folder, tmp_path, monkeypatch):
    target = install.install(user_folder)
    (target / "Start Aidus Agentus.py").write_text("old\n")
    monkeypatch.setenv("AIDUS_PYTHON", str(_executable(tmp_path / "python")))
    report = install.check(user_folder)
    assert report["menu_current"] is False and report["ready"] is False


def test_check_when_linked_to_repository_folder_is_current(user_folder):
    (user_folder / "Scripts" / "Aidus Agentus").symlink_to(REPO_MENU, target_is_directory=True)
    report = install.check(user_folder)
    assert report["menu_state"] == "link" and report["menu_current"] is True


def test_check_when_python_from_config_file(user_folder, tmp_path, monkeypatch, isolated_home):
    python = _executable(tmp_path / "brain-python")
    config = isolated_home / ".config" / "aidus_agentus" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"python_exe": str(python)}), encoding="utf-8")
    assert install.check(user_folder)["python_exe"] == str(python)


def test_main_when_install_check_uninstall_round_trip(user_folder, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AIDUS_PYTHON", str(_executable(tmp_path / "python")))
    assert install.main(["install", "--user-folder", str(user_folder)]) == 0
    assert install.main(["check", "--user-folder", str(user_folder)]) == 0
    report = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert report["ready"] is True
    assert install.main(["uninstall", "--user-folder", str(user_folder)]) == 0
    assert "Removed 3 owned file(s)" in capsys.readouterr().out
    assert install.main(["uninstall", "--user-folder", str(user_folder)]) == 0
    assert "Nothing of ours" in capsys.readouterr().out


def test_main_when_check_not_ready_exits_1(user_folder):
    assert install.main(["check", "--user-folder", str(user_folder)]) == 1


def test_main_when_foreign_entry_exits_2_with_message(user_folder, capsys):
    (user_folder / "Scripts" / "Aidus Agentus").mkdir()
    (user_folder / "Scripts" / "Aidus Agentus" / "theirs.py").write_text("x = 1\n")
    assert install.main(["install", "--user-folder", str(user_folder)]) == 2
    assert "left unchanged" in capsys.readouterr().err


def test_main_when_bad_action_exits_with_usage():
    with pytest.raises(SystemExit) as error:
        install.main(["frobnicate"])
    assert error.value.code == 2


def test_module_when_run_as_script_reports_check(user_folder, tmp_path):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "fontlab_aidus_agentus.install", "check", "--user-folder", str(user_folder)],
        capture_output=True, text=True, env=env, timeout=30, cwd=tmp_path,
    )
    assert result.returncode == 1, result.stderr
    assert json.loads(result.stdout)["menu_state"] == "missing"


def test_check_when_owned_script_replaced_by_symlink_is_not_current(user_folder, tmp_path):
    target = install.install(user_folder)
    copy = tmp_path / "same.py"
    copy.write_text(install.menu_scripts()["Start Aidus Agentus.py"])
    (target / "Start Aidus Agentus.py").unlink()
    (target / "Start Aidus Agentus.py").symlink_to(copy)
    assert install.check(user_folder)["menu_current"] is False


# --- release review X5-2: temp files, races, interrupted installs --------


def test_install_when_unrelated_file_has_old_temp_name_keeps_it(user_folder):
    target = install.install(user_folder)
    unrelated = target / ".fontlab-aidus-agentus-install.fontlab-aidus-tmp"
    unrelated.write_text("not ours\n")
    install.install(user_folder)
    assert unrelated.read_text() == "not ours\n"


def test_install_when_done_leaves_no_temp_files(user_folder):
    target = install.install(user_folder)
    install.install(user_folder)
    assert not [p.name for p in target.iterdir() if p.name.endswith(".tmp")]


def _after_plan(monkeypatch, action):
    real = install._plan

    def planned(*args):
        result = real(*args)
        action()
        return result

    monkeypatch.setattr(install, "_plan", planned)


def test_install_when_foreign_file_appears_after_planning_refuses_and_keeps_it(user_folder, monkeypatch):
    target = install.install(user_folder)
    (target / "Enable FontLab MCP.py").unlink()
    _after_plan(monkeypatch, lambda: (target / "Enable FontLab MCP.py").write_text("foreign\n"))
    with pytest.raises(install.InstallError, match="changed since planning.*Enable FontLab MCP.py"):
        install.install(user_folder)
    assert (target / "Enable FontLab MCP.py").read_text() == "foreign\n"


def test_install_when_owned_file_edited_after_planning_refuses_and_keeps_edit(user_folder, monkeypatch):
    target = install.install(user_folder)
    old = "print('previous release')\n"
    (target / "Start Aidus Agentus.py").write_text(old)
    marker = json.loads((target / install.MARKER).read_text())
    marker["files"]["Start Aidus Agentus.py"] = _sha(old)
    (target / install.MARKER).write_text(json.dumps(marker))
    _after_plan(monkeypatch, lambda: (target / "Start Aidus Agentus.py").write_text("edited meanwhile\n"))
    with pytest.raises(install.InstallError, match="changed since planning.*Start Aidus Agentus.py"):
        install.install(user_folder)
    assert (target / "Start Aidus Agentus.py").read_text() == "edited meanwhile\n"


def test_install_when_removal_target_edited_after_planning_keeps_it(user_folder, monkeypatch):
    target = install.install(user_folder)
    (target / "Retired.py").write_text("print('retired')\n")
    marker = json.loads((target / install.MARKER).read_text())
    marker["files"]["Retired.py"] = _sha("print('retired')\n")
    (target / install.MARKER).write_text(json.dumps(marker))
    _after_plan(monkeypatch, lambda: (target / "Retired.py").write_text("now mine\n"))
    with pytest.raises(install.InstallError, match="changed since planning.*Retired.py"):
        install.install(user_folder)
    assert (target / "Retired.py").read_text() == "now mine\n"


def test_install_when_interrupted_first_time_next_run_resumes(user_folder, monkeypatch):
    real = install._create
    calls = []

    def failing(path, data):
        calls.append(path.name)
        if len([c for c in calls if c.endswith(".py")]) == 2:
            raise OSError("disk full")
        return real(path, data)

    monkeypatch.setattr(install, "_create", failing)
    with pytest.raises(OSError):
        install.install(user_folder)
    target = user_folder / "Scripts" / "Aidus Agentus"
    assert install.menu_state(target) == "copy", "A provisional manifest keeps the folder ours"
    monkeypatch.setattr(install, "_create", real)
    install.install(user_folder)
    assert {p.name for p in target.iterdir()} == {*install.ACTIONS, install.MARKER}
    assert json.loads((target / install.MARKER).read_text())["state"] == "installed"


def test_install_when_interrupted_upgrade_next_run_resumes(user_folder, monkeypatch):
    target = install.install(user_folder)
    old = "print('previous release')\n"
    for name in install.ACTIONS:
        (target / name).write_text(old)
    marker = json.loads((target / install.MARKER).read_text())
    marker["files"] = {name: _sha(old) for name in install.ACTIONS}
    (target / install.MARKER).write_text(json.dumps(marker))
    real, writes = install._create, []

    def failing(path, data):
        writes.append(path.name)
        if path.name.endswith(".py") and len([s for s in writes if s.endswith(".py")]) == 2:
            raise OSError("interrupted")
        return real(path, data)

    monkeypatch.setattr(install, "_create", failing)
    with pytest.raises(OSError):
        install.install(user_folder)
    monkeypatch.setattr(install, "_create", real)
    install.install(user_folder)
    assert all((target / n).read_text() == t for n, t in install.menu_scripts().items())


def test_uninstall_when_install_was_interrupted_still_removes_owned_files(user_folder, monkeypatch):
    real = install._create

    def failing(path, data):
        if path.name == "Open Configuration.py":
            raise OSError("disk full")
        return real(path, data)

    monkeypatch.setattr(install, "_create", failing)
    with pytest.raises(OSError):
        install.install(user_folder)
    report = install.uninstall(user_folder)
    assert report["folder_removed"] is True and report["kept"] == []


# --- release review X5-3: lossless replace/remove, recoverable start, carried ownership


def _older_release(target):
    old = "print('previous release')\n"
    for name in install.ACTIONS:
        (target / name).write_text(old)
    marker = json.loads((target / install.MARKER).read_text())
    marker["files"] = {name: _sha(old) for name in install.ACTIONS}
    (target / install.MARKER).write_text(json.dumps(marker))


def test_install_when_owned_file_edited_while_temp_is_written_keeps_the_edit(user_folder, monkeypatch):
    target = install.install(user_folder)
    _older_release(target)
    real, edited = install._temporary, []

    def racing(folder, data):
        if not edited and data.startswith(b"# this_file: Scripts/Aidus Agentus/Enable"):  # the script's own temp
            (target / "Enable FontLab MCP.py").write_text("edited in the window\n")
            edited.append(True)
        return real(folder, data)

    monkeypatch.setattr(install, "_temporary", racing)
    with pytest.raises(install.InstallError, match="Enable FontLab MCP.py"):
        install.install(user_folder)
    assert (target / "Enable FontLab MCP.py").read_text() == "edited in the window\n"


def test_install_when_quarantined_copy_differs_restores_it(user_folder, monkeypatch):
    target = install.install(user_folder)
    _older_release(target)
    real = install._digest

    def edited_in_place(data):
        # The planned hash matched; the bytes taken aside no longer do (in-place edit).
        if data == b"print('previous release')\n" and any(p.name.endswith(".aidus-old") for p in target.iterdir()):
            return "0" * 64
        return real(data)

    monkeypatch.setattr(install, "_digest", edited_in_place)
    with pytest.raises(install.InstallError, match="changed since planning"):
        install.install(user_folder)
    monkeypatch.setattr(install, "_digest", real)
    assert (target / "Enable FontLab MCP.py").read_text() == "print('previous release')\n"
    assert not [p for p in target.iterdir() if p.name.endswith(".aidus-old")]


def test_uninstall_when_file_edited_right_before_removal_keeps_the_edit(user_folder, monkeypatch):
    target = install.install(user_folder)
    real = install._digest
    started = []

    def racing(data):
        if not started and any(p.name.endswith(".aidus-old") for p in target.iterdir()):
            started.append(True)
            (target / "Enable FontLab MCP.py").write_text("written during uninstall\n")
        return real(data)

    monkeypatch.setattr(install, "_digest", racing)
    install.uninstall(user_folder)
    assert (target / "Enable FontLab MCP.py").read_text() == "written during uninstall\n"


def test_uninstall_when_quarantined_copy_differs_puts_it_back_and_reports(user_folder, monkeypatch):
    target = install.install(user_folder)
    real = install._digest

    def changed(data):
        if any(p.name.endswith(".aidus-old") for p in target.iterdir()) and data.startswith(b"# this_file: Scripts/Aidus Agentus/Start"):
            return "1" * 64
        return real(data)

    monkeypatch.setattr(install, "_digest", changed)
    report = install.uninstall(user_folder)
    assert "Start Aidus Agentus.py" in report["kept"]
    assert (target / "Start Aidus Agentus.py").exists()
    assert not [p for p in target.iterdir() if p.name.endswith(".aidus-old")]


def test_install_when_first_temp_file_is_denied_leaves_nothing_and_retry_works(user_folder, monkeypatch):
    real = install.tempfile.mkstemp

    def denied(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(install.tempfile, "mkstemp", denied)
    with pytest.raises(PermissionError):
        install.install(user_folder)
    target = user_folder / "Scripts" / "Aidus Agentus"
    assert not target.exists(), "No unmarked folder is left behind"
    assert not [p for p in (user_folder / "Scripts").iterdir()], "Nothing is left behind"
    monkeypatch.setattr(install.tempfile, "mkstemp", real)
    install.install(user_folder)
    assert install.menu_state(target) == "copy"


def test_install_when_interrupted_twice_keeps_ownership_of_every_written_script(user_folder, monkeypatch):
    target = install.install(user_folder)
    _older_release(target)
    real = install._create
    for allowed in (1, 1):  # each run writes one more script, then is interrupted
        made = []

        def failing(path, data):
            if path.name.endswith(".py"):
                made.append(path.name)
                if len(made) > allowed:
                    raise OSError("interrupted")
            return real(path, data)

        monkeypatch.setattr(install, "_create", failing)
        with pytest.raises(OSError):
            install.install(user_folder)
    monkeypatch.setattr(install, "_create", real)
    owned = install._owned(install.read_marker(target))
    assert set(install.ACTIONS) <= set(owned), "Adopted scripts stay in the ownership tables"
    report = install.uninstall(user_folder)
    assert report["kept"] == [] and report["folder_removed"] is True


# --- release review X5-4: the manifest follows the same lossless protocol --


def test_install_when_manifest_replaced_after_planning_keeps_the_foreign_file(user_folder, monkeypatch):
    target = install.install(user_folder)
    foreign = b'{"someone": "else"}\n'
    _after_plan(monkeypatch, lambda: (target / install.MARKER).write_bytes(foreign))
    with pytest.raises(install.InstallError, match="changed since planning.*" + install.MARKER):
        install.install(user_folder)
    assert (target / install.MARKER).read_bytes() == foreign


def test_install_when_manifest_replaced_before_final_write_keeps_the_foreign_file(user_folder, monkeypatch):
    target = install.install(user_folder)
    _older_release(target)
    foreign = b'{"someone": "else"}\n'
    real, done = install._create, []

    def racing(path, data):
        result = real(path, data)
        if path.name == "Start Aidus Agentus.py" and not done:
            done.append(True)
            (target / install.MARKER).write_bytes(foreign)
        return result

    monkeypatch.setattr(install, "_create", racing)
    with pytest.raises(install.InstallError, match="changed since planning"):
        install.install(user_folder)
    assert (target / install.MARKER).read_bytes() == foreign


def test_uninstall_when_manifest_replaced_meanwhile_keeps_the_foreign_file(user_folder, monkeypatch):
    target = install.install(user_folder)
    foreign = b'{"someone": "else"}\n'
    real = install._owned

    def racing(marker):
        owned = real(marker)
        (target / install.MARKER).write_bytes(foreign)
        return owned

    monkeypatch.setattr(install, "_owned", racing)
    with pytest.raises(install.InstallError, match="changed since planning.*" + install.MARKER):
        install.uninstall(user_folder)
    assert (target / install.MARKER).read_bytes() == foreign


def test_menu_state_when_only_an_aside_manifest_remains_recovers_it(user_folder):
    target = install.install(user_folder)
    (target / install.MARKER).rename(target / (".%s.%s.aidus-old" % (install.MARKER, "0" * 32)))
    assert install.menu_state(target) == "copy", "A crash between moving the manifest aside and relinking"
    install.install(user_folder)
    assert (target / install.MARKER).is_file()
    assert not [p.name for p in target.iterdir() if p.name.endswith(".aidus-old")]


def test_uninstall_when_folder_is_empty_and_unmarked_removes_it(user_folder):
    target = user_folder / "Scripts" / "Aidus Agentus"
    target.mkdir()
    report = install.uninstall(user_folder)
    assert report == {"removed": [], "kept": [], "folder_removed": True} and not target.exists()


def test_install_when_folder_is_empty_and_unmarked_takes_it_over(user_folder):
    target = user_folder / "Scripts" / "Aidus Agentus"
    target.mkdir()
    install.install(user_folder)
    assert install.menu_state(target) == "copy"


def _foreign_marker_when_hashing_aside(monkeypatch, target, foreign):
    """Reviewer's injection: a foreign manifest lands right after ours was taken aside/verified."""
    real_current, real_temp = install._current, install._temporary

    def current(path):
        result = real_current(path)
        if path.name.startswith("." + install.MARKER) and not (target / install.MARKER).exists():
            (target / install.MARKER).write_bytes(foreign)
        return result

    def temporary(folder, data):
        name = real_temp(folder, data)
        if data.startswith(b'{\n  "files"') and (target / install.MARKER).exists():
            (target / install.MARKER).write_bytes(foreign)  # old code: between verify and swap
        return name

    monkeypatch.setattr(install, "_current", current)
    monkeypatch.setattr(install, "_temporary", temporary)


def test_install_when_manifest_replaced_inside_the_write_window_keeps_it(user_folder, monkeypatch):
    target = install.install(user_folder)
    foreign = b'{"someone": "else"}\n'
    _foreign_marker_when_hashing_aside(monkeypatch, target, foreign)
    with pytest.raises(install.InstallError):
        install.install(user_folder)
    assert (target / install.MARKER).read_bytes() == foreign


def test_uninstall_when_manifest_replaced_inside_the_removal_window_keeps_it(user_folder, monkeypatch):
    target = install.install(user_folder)
    foreign = b'{"someone": "else"}\n'
    real_current = install._current

    def current(path):
        result = real_current(path)
        if path.name.startswith("." + install.MARKER) and not (target / install.MARKER).exists():
            (target / install.MARKER).write_bytes(foreign)
        return result

    monkeypatch.setattr(install, "_current", current)
    install.uninstall(user_folder)
    assert (target / install.MARKER).read_bytes() == foreign


# --- release review X5-5: no rename may clobber a path that can reappear ----


def test_install_when_recovered_aside_manifest_name_is_recreated_keeps_user_bytes(user_folder, monkeypatch):
    """Reviewer repro: crash-left aside manifest, resume, user recreates that name, publish fails."""
    target = install.install(user_folder)
    source = target / (".%s.%s.aidus-old" % (install.MARKER, "0" * 32))
    (target / install.MARKER).rename(source)
    user_bytes = b"user bytes that must survive\n"
    real_take, real_create = install._take, install._create

    def take(path, expected):
        aside = real_take(path, expected)
        if path == source:
            source.write_bytes(user_bytes)
        return aside

    def create(path, data):
        if path.name == install.MARKER:
            raise PermissionError("denied")
        return real_create(path, data)

    monkeypatch.setattr(install, "_take", take)
    monkeypatch.setattr(install, "_create", create)
    with pytest.raises(PermissionError):
        install.install(user_folder)
    assert source.read_bytes() == user_bytes
    copies = [p for p in target.iterdir() if p.name.endswith(".aidus-old") and p != source]
    assert len(copies) == 1 and install._parse_marker_file(copies[0]) is not None, "Our manifest is kept aside"


def test_install_when_folder_appears_before_creation_refuses_and_keeps_it(user_folder, monkeypatch):
    real = install._make_folder

    def racing(target):
        target.mkdir()
        (target / "theirs.txt").write_text("x\n")
        return real(target)

    monkeypatch.setattr(install, "_make_folder", racing)
    with pytest.raises(install.InstallError):
        install.install(user_folder)
    assert (user_folder / "Scripts" / "Aidus Agentus" / "theirs.txt").read_text() == "x\n"


def test_installer_source_when_scanned_has_no_clobbering_rename():
    """Every rename/replace destination must be a fresh unique name; restores use link+unlink."""
    import ast

    tree = ast.parse(Path(install.__file__).read_text(encoding="utf-8"))
    found = []
    for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for call in [n for n in ast.walk(function) if isinstance(n, ast.Call)]:
            name = getattr(call.func, "attr", getattr(call.func, "id", ""))
            if name in ("rename", "replace", "renames"):
                found.append((function.name, name))
    assert found == [("_take", "rename")], (
        "Only _take may rename (onto a new uuid name); everything else must not clobber: %r" % found)
