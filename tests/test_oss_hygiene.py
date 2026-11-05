"""Open-source hygiene: community files, no Russian, no leaks, ignore rules."""

import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUSSIAN = set("ыъэЫЪЭ")


def read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class TestCommunityFiles:
    def test_contributing_exists_with_checklist(self):
        md = read("CONTRIBUTING.md")
        assert "pytest" in md and ("Російську" in md or "Russian" in md)

    def test_security_md_has_private_reporting(self):
        md = read("SECURITY.md")
        assert "Report a vulnerability" in md

    @pytest.mark.parametrize("tpl", ["bug_report.md", "feature_request.md"])
    def test_issue_templates_bilingual(self, tpl):
        md = read(os.path.join(".github", "ISSUE_TEMPLATE", tpl))
        assert "Language / Мова" in md or "Мова" in md
        assert "English" in md

    def test_no_russian_in_any_community_file(self):
        files = ["CONTRIBUTING.md", "SECURITY.md",
                 ".github/ISSUE_TEMPLATE/bug_report.md",
                 ".github/ISSUE_TEMPLATE/feature_request.md",
                 "README.md", "README.en.md", "INSTALL.md", "CHANGELOG.md"]
        for name in files:
            assert not (RUSSIAN & set(read(name))), f"Russian letters in {name}"


class TestReadmeOpenSource:
    def test_ua_readme_has_contributing_and_topics(self):
        md = read("README.md")
        assert "CONTRIBUTING.md" in md and "SECURITY.md" in md
        for topic in ("adhd", "productivity", "gtd", "pomodoro", "pwa",
                      "fastapi", "local-first"):
            assert f"`{topic}`" in md

    def test_en_readme_has_contributing_and_security(self):
        md = read("README.en.md")
        assert "CONTRIBUTING.md" in md and "SECURITY.md" in md


class TestIgnoreRules:
    def test_gitignore_covers_env_and_db(self):
        gi = read(".gitignore")
        for pattern in (".env", "*.db", "*.db-wal", "*.db-shm", "*.egg-info/"):
            assert pattern in gi, f".gitignore missing {pattern}"

    def test_no_env_or_db_files_tracked(self):
        import subprocess
        r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT)
        tracked = r.stdout.splitlines()
        assert not [f for f in tracked if f.endswith((".db", ".env", "-wal", "-shm"))]
        assert not [f for f in tracked if "egg-info" in f]


class TestNoSecrets:
    def test_no_token_patterns_anywhere_tracked(self):
        import subprocess
        r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT)
        patterns = (r"ghp_[A-Za-z0-9]{20,}", r"github_pat_", r"sk-[A-Za-z0-9]{20,}",
                    r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9]{16,}")
        for name in r.stdout.splitlines():
            path = os.path.join(ROOT, name)
            if not os.path.isfile(path) or os.path.getsize(path) > 200_000:
                continue
            try:
                blob = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for pat in patterns:
                assert not re.search(pat, blob), f"{name} looks like it contains a secret"
