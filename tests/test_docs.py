"""README consistency: bilingual docs, INSTALL.md, no Russian, no private paths."""

import os
import re
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-docs-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.main import app  # noqa: E402  (env must be set before import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture()
def client():
    db_path = os.environ["MINDCATCH_DB"]
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    with TestClient(app) as c:
        yield c


class TestBilingualReadme:
    def test_readme_en_exists_and_links_back(self):
        en = read("README.en.md")
        assert en.startswith("# Mindcatch")
        assert "README.md" in en

    def test_ua_readme_links_to_english(self):
        ua = read("README.md")
        assert "README.en.md" in ua

    def test_no_russian_in_any_doc(self):
        russian_letters = set("ыъэЫЪЭ")
        for name in ("README.md", "README.en.md", "INSTALL.md", "CHANGELOG.md"):
            blob = read(name)
            found = russian_letters & set(blob)
            assert not found, f"Russian letters {found} in {name}"

    def test_en_readme_documents_all_export_formats(self):
        en = read("README.en.md")
        for fmt in ("calendar.ics", "todoist.md", "items.csv", "/api/export/markdown"):
            assert fmt in en

    def test_version_mentions_v1(self):
        assert "1.0.0" in read("README.en.md")


class TestInstallGuide:
    def test_install_md_exists(self):
        assert read("INSTALL.md").startswith("# ")

    def test_covers_windows_linux_updates(self):
        md = read("INSTALL.md")
        assert "Windows" in md and ("systemd" in md or "Linux" in md)
        assert "Оновлення" in md or "Update" in md or "оновлення" in md.lower()

    def test_no_assumed_dev_knowledge_steps(self):
        md = read("INSTALL.md")
        assert "python" in md.lower() and "pip" in md.lower()

    def test_start_bat_exists_and_runs_server(self):
        bat = read("scripts/start.bat")
        assert "uvicorn" in bat.lower()


class TestPrivacyHygiene:
    """The repo goes open-source: no private paths, tokens or user data.

    github.com/bigpi/mindcatch is the project's own public URL — allowed.
    Everything else (local paths, machine usernames outside that URL,
    tokens, passwords) must stay out of the repo.
    """

    PRIVATE_MARKERS = (r"G:\\", r"G:/", r"C:\\Users", r"/c/Users", r"sk-[A-Za-z0-9]{10,}",
                       r"ghp_[A-Za-z0-9]{10,}", r"(?i)password\s*[:=]\s*\S")

    @pytest.mark.parametrize("name", ["README.md", "README.en.md", "INSTALL.md",
                                      "app/main.py", "app/db.py", "static/app.js",
                                      "static/index.html", "scripts/start.bat"])
    def test_no_private_paths_tokens_or_credentials(self, name):
        blob = read(name)
        for marker in self.PRIVATE_MARKERS:
            assert not re.search(marker, blob), f"{name} leaks {marker!r}"
        # machine username may appear only inside the public repo URL
        stripped = blob.replace("github.com/bigpi/mindcatch", "")
        assert "bigpi" not in stripped, \
            f"{name} mentions the machine username outside the repo URL"

    def test_test_fixtures_use_no_real_user_data(self):
        tests_dir = os.path.join(ROOT, "tests")
        for fn in os.listdir(tests_dir):
            if not fn.endswith(".py") or fn == "test_docs.py":  # self-scan excluded
                continue
            blob = read(os.path.join("tests", fn))
            for marker in ("@gmail.com", "@ukr.net", "+380"):
                assert marker not in blob, f"{fn} contains real-looking user data: {marker}"
