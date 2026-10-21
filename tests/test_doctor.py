from pathlib import Path

from doctor import check_config, check_tools, report


def _no_browser():
    raise FileNotFoundError


def test_missing_git_is_required_failure():
    checks = check_tools(which=lambda name: None, browser=_no_browser)
    text, code = report(checks)
    assert code == 1
    assert "[없음] git" in text
    assert "[선택] Edge·Chrome" in text


def test_optional_tools_do_not_fail():
    checks = check_tools(which=lambda name: "/bin/git" if name == "git" else None, browser=_no_browser)
    _, code = report(checks)
    assert code == 0


def test_config_files(tmp_path):
    assert all(not c.ok for c in check_config(tmp_path))
    for rel in ("_config/me.md", "_config/project.md", "_glossary/terms.md", "_glossary/speakers.md"):
        (tmp_path / rel).parent.mkdir(exist_ok=True)
        (tmp_path / rel).write_text("", encoding="utf-8")
    assert all(c.ok for c in check_config(tmp_path))


def test_browser_path_shown():
    checks = check_tools(which=lambda name: "/bin/git" if name == "git" else None, browser=lambda: Path("/x/msedge"))
    text, _ = report(checks)
    assert "[OK  ] Edge·Chrome" in text


def test_gpu_check_survives_broken_driver(monkeypatch):
    import subprocess

    import doctor

    def boom(*a, **k):
        raise subprocess.TimeoutExpired("nvidia-smi", 10)

    monkeypatch.setattr(doctor.subprocess, "run", boom)
    assert doctor._has_gpu(lambda name: "/bin/nvidia-smi") is False


def test_linux_hint(monkeypatch):
    import doctor

    monkeypatch.setattr(doctor.sys, "platform", "linux")
    assert doctor._hint("w", "m", "l") == "l"
