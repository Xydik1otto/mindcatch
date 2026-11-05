"""Packaging: pyproject metadata, console entry point, version consistency."""

import os
import re
import tempfile
import tomllib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="mindcatch-pkg-")
os.environ["MINDCATCH_DB"] = os.path.join(TMP, "test.db")


def read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def pyproject():
    return tomllib.loads(read("pyproject.toml"))


class TestMetadata:
    def test_core_metadata(self, pyproject):
        p = pyproject["project"]
        assert p["name"] == "mindcatch"
        assert p["version"] == "1.0.0"
        assert "MIT" in str(p["license"])
        assert p["requires-python"] >= "3.12"

    def test_dependencies_match_requirements(self, pyproject):
        req = [r.strip().lower() for r in read("requirements.txt").splitlines()
               if r.strip() and not r.strip().startswith("#")]
        runtime = [r for r in req if not r.startswith("pytest")]
        deps = sorted(d.lower().split(">=")[0] for d in pyproject["project"]["dependencies"])
        assert sorted(d.split(">=")[0] for d in runtime) == deps

    def test_entry_point_declared(self, pyproject):
        assert pyproject["project"]["scripts"]["mindcatch"] == "app.cli:main"

    def test_no_russian_keywords(self, pyproject):
        blob = read("pyproject.toml")
        assert not (set("ыъэЫЪЭ") & set(blob))


class TestEntryPoint:
    def test_cli_module_imports(self):
        from app.cli import main  # noqa: F401

    def test_cli_respects_port_env(self, monkeypatch, capsys):
        monkeypatch.setenv("MINDCATCH_PORT", "8099")
        monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
        from app.cli import main
        main()
        assert "8099" in capsys.readouterr().out


class TestVersionConsistency:
    def test_app_version_is_1_0_0(self):
        from app.main import app
        assert app.version == "1.0.0"

    def test_readme_badges_updated(self):
        for name in ("README.md", "README.en.md"):
            assert "version-1.0.0" in read(name)

    def test_changelog_has_1_0_0(self):
        assert "## [1.0.0]" in read("CHANGELOG.md")


class TestInstallable:
    def test_pip_editable_install_works(self):
        import subprocess
        import sys
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet", "--no-deps"],
            capture_output=True, text=True, cwd=ROOT, timeout=300)
        assert r.returncode == 0, r.stderr[-2000:]
        assert "mindcatch" in r.stdout or r.returncode == 0
