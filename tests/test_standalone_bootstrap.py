# this_file: tests/test_standalone_bootstrap.py
"""Run the shipped bootstrap against owned wheels and disposable data folders."""
import io
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "install.vfpy").read_text()


@pytest.fixture
def bootstrap(tmp_path, monkeypatch):
    monkeypatch.setenv("FONTLAB_DATA_DIR", str(tmp_path / "data"))
    saved = {k: v for k, v in sys.modules.items() if k.startswith("fontlab_instamix")}
    old_path = sys.path.copy()
    for key in saved:
        del sys.modules[key]
    ns = {"__name__": "install_vfpy_import", "__file__": str(ROOT / "install.vfpy")}
    exec(compile(SOURCE, str(ROOT / "install.vfpy"), "exec"), ns)  # noqa: S102 - execute the owned canonical installer
    ns["HERE"] = tmp_path
    yield ns
    for key in list(sys.modules):
        if key.startswith("fontlab_instamix"):
            del sys.modules[key]
    sys.modules.update(saved)
    sys.path[:] = old_path


def wheel(root, version="1.0.18", *, changes=None):
    info = f"fontlab_python_instamix-{version}.dist-info"
    files = {
        "fontlab_instamix/__init__.py": f"__version__ = {version!r}\n",
        "fontlab_instamix/legacy.py": "",
        "fontlab_instamix/extension.py": "def preflight_plugin_migration(*a): pass\ndef preflight_destinations(*a): pass\n",
        "fontlab_instamix/bootstrap.py": "def _legacy_rollback(*a): pass\ndef install_project(*a): return [{'id':'fixture','version':'1'}]\n",
        "fontlab_instamix/gui.py": "def message(text, **kwargs): print(text)\n",
        info + "/METADATA": f"Name: fontlab-python-instamix\nVersion: {version}\n",
        info + "/WHEEL": "Wheel-Version: 1.0\n",
        info + "/RECORD": "",
        info + "/licenses/LICENSE": "Owned test fixture\n",
    }
    files.update(changes or {})
    target = root / "dist" / f"fontlab_python_instamix-{version}-py3-none-any.whl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w") as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return target


def test_bootstrap_when_wheel_installed_then_reuse_and_metadata_are_real(bootstrap):
    ns = bootstrap
    root = ns["HERE"]
    wheel(root, "1.0.17")
    wheel(root)
    package = ns["ensure"]()
    assert package.__version__ == "1.0.18"
    assert Path(package.__file__).is_relative_to(ns["site"]())
    assert ns["ensure"]() is package
    assert ns["installed_version"]() == "1.0.18"
    assert ns["wheel_version"]("1.0.9") < ns["wheel_version"]("1.0.18")
    assert ns["wheel_version"]("1.0.18rc1") < ns["wheel_version"]("1.0.18")
    with pytest.raises(RuntimeError, match="unsupported"):
        ns["wheel_version"]("bad")


@pytest.mark.parametrize("failure", ["metadata", "capability", "old", "unsafe"])
def test_bootstrap_when_replacement_invalid_then_previous_files_survive(bootstrap, failure):
    ns = bootstrap
    site = ns["site"]()
    old = site / "fontlab_instamix"
    old.mkdir(parents=True)
    (old / "owner.txt").write_text("previous")
    version = "1.0.9" if failure == "old" else "1.0.18"
    changes = {}
    if failure == "metadata":
        changes[f"fontlab_python_instamix-{version}.dist-info/METADATA"] = "Name: wrong\nVersion: 1.0.18\n"
    if failure == "capability":
        changes["fontlab_instamix/extension.py"] = ""
    if failure == "unsafe":
        changes["fontlab_instamix/../../escape"] = "unsafe"
    wheel(ns["HERE"], version, changes=changes)
    with pytest.raises((ImportError, RuntimeError)):
        ns["ensure"](force=True)
    assert (old / "owner.txt").read_text() == "previous"
    assert sorted(p.name for p in site.iterdir()) == ["fontlab_instamix"]
    assert not (site / "escape").exists()


def test_download_when_same_self_path_or_conflicting_build_then_deduplicates_or_refuses(bootstrap):
    ns = bootstrap
    root = ns["HERE"] / "fontlab-python-instamix"
    root.mkdir()
    ns["HERE"] = root
    wheel(root)
    ns["download"](root / "stage")
    assert (root / "stage/fontlab_instamix/__init__.py").is_file()
    ns["HERE"] = root.parent / "consumer"
    ns["HERE"].mkdir()
    wheel(ns["HERE"], changes={"fontlab_instamix/legacy.py": "different"})
    with pytest.raises(RuntimeError, match="conflicting"):
        ns["download"](root / "refused")
    assert not (root / "refused").exists()


def test_download_when_pypi_response_or_bad_digest_then_validates_before_extract(bootstrap, monkeypatch):
    ns = bootstrap
    local = wheel(ns["HERE"])
    blob = local.read_bytes()
    local.unlink()
    info = {"urls": [{"packagetype": "bdist_wheel", "filename": "fixture-py3-none-any.whl", "url": "wheel", "digests": {"sha256": ns["hashlib"].sha256(blob).hexdigest()}}]}
    monkeypatch.setitem(ns, "fetch", lambda url, timeout: blob if url == "wheel" else json.dumps(info).encode())
    ns["download"](ns["HERE"] / "stage")
    assert (ns["HERE"] / "stage/fontlab_instamix/__init__.py").is_file()
    info["urls"][0]["digests"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="sha256"):
        ns["download"](ns["HERE"] / "refused")
    assert not (ns["HERE"] / "refused").exists()


def test_fetch_when_success_or_certificate_failure_then_uses_verified_transport(bootstrap, monkeypatch):
    ns = bootstrap
    monkeypatch.setattr(ns["urllib"].request, "urlopen", lambda *a, **k: io.BytesIO(b"response"))
    assert ns["fetch"]("https://fixture.invalid", 1) == b"response"
    def fail(*a, **k):
        raise ns["urllib"].error.URLError(ns["ssl"].SSLCertVerificationError("fixture"))
    monkeypatch.setattr(ns["urllib"].request, "urlopen", fail)
    monkeypatch.setattr(sys, "platform", "darwin")
    is_file = Path.is_file
    monkeypatch.setattr(Path, "is_file", lambda path: path == Path("/usr/bin/curl") or is_file(path))
    commands = []
    def run(command, **kwargs):
        commands.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=b"curl response")
    monkeypatch.setattr(ns["subprocess"], "run", run)
    assert ns["fetch"]("https://fixture.invalid", 1) == b"curl response"
    assert "--proto-redir" in commands[0][0] and "=https" in commands[0][0]


def test_entry_when_project_fails_then_prints_committed_and_incomplete_records(bootstrap, capsys):
    ns = bootstrap
    code = """def _legacy_rollback(*a): pass
def install_project(*a):
    error = RuntimeError('owned conflict')
    error.installed_records = [{'id':'done','version':'1'}, {'id':'partial','version':'2','requires_failed':True}]
    raise error
"""
    wheel(ns["HERE"], changes={"fontlab_instamix/bootstrap.py": code})
    ns["ensure"]()
    ns["__name__"] = "__main__"
    exec(compile(SOURCE, str(ROOT / "install.vfpy"), "exec"), ns)  # noqa: S102 - execute the owned canonical installer
    output = capsys.readouterr().out
    assert "Installed done 1 (before failure)" in output
    assert "Incomplete requirements for partial 2" in output
    assert "owned conflict" in output
