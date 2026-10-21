# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""이 PC에서 회의록 도구를 쓸 준비가 됐는지 점검한다.

필수(git, 설정 파일)가 빠지면 종료 코드 1. 선택 도구는 없을 때 어떤 기능이 빠지는지와 설치 방법만 알린다.
uv는 이 스크립트를 실행했다는 것으로 확인된다.

사용: uv run scripts/doctor.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_pdf import find_edge  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


@dataclass
class Check:
    name: str
    ok: bool
    required: bool
    note: str  # 없을 때 보여 줄 안내
    found: str = ""  # 있을 때 보여 줄 위치


def _hint(windows: str, mac: str, linux: str) -> str:
    if sys.platform == "darwin":
        return mac
    return windows if sys.platform == "win32" else linux


def _has_gpu(which) -> bool:
    if not which("nvidia-smi"):
        return False
    try:
        return subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def check_tools(which=shutil.which, browser=find_edge) -> list[Check]:
    checks = [
        Check("git", bool(which("git")), True,
              "설치: " + _hint("winget install Git.Git", "xcode-select --install", "sudo apt install git")),
        Check("gh (GitHub CLI)", bool(which("gh")), False,
              "새 과제 레포를 GitHub에 만들 때 사용. 설치: " + _hint("winget install GitHub.cli", "brew install gh", "sudo apt install gh")),
    ]
    try:
        path = browser()
        checks.append(Check("Edge·Chrome", True, False, "", str(path)))
    except FileNotFoundError:
        checks.append(Check("Edge·Chrome", False, False, "PDF 변환(make_pdf.py)에 필요. Edge나 Chrome 설치"))
    checks.append(Check("pdftotext", bool(which("pdftotext")), False,
                        "PDF 변환 결과 점검·PDF 전사문 읽기에 사용. 설치: "
                        + _hint("winget install oschwartz10612.Poppler", "brew install poppler", "sudo apt install poppler-utils")))
    checks.append(Check("NVIDIA GPU", _has_gpu(which), False,
                        "없으면 Whisper가 CPU로 몇 배 느리게 돈다. 너무 느리면 Whisper 없이(no-whisper) STT 결과만으로 전사"))
    return checks


def check_config(repo: Path = REPO) -> list[Check]:
    setup = "세팅 절차(workflows/setup.md)로 만든다"
    return [
        Check("_config/me.md (개인 설정)", (repo / "_config/me.md").is_file(), True, setup),
        Check("_config/project.md (과제 설정)", (repo / "_config/project.md").is_file(), True, setup),
        Check("_glossary/terms.md (용어사전)", (repo / "_glossary/terms.md").is_file(), True, setup),
        Check("_glossary/speakers.md (화자 명단)", (repo / "_glossary/speakers.md").is_file(), True, setup),
    ]


def report(checks: list[Check]) -> tuple[str, int]:
    lines = []
    for c in checks:
        mark = "OK  " if c.ok else ("없음" if c.required else "선택")
        extra = c.found if c.ok else c.note
        lines.append(f"[{mark}] {c.name}" + (f"  {extra}" if extra else ""))
    missing = [c.name for c in checks if c.required and not c.ok]
    lines.append("")
    lines.append("필수 항목 모두 준비됨" if not missing else "필수 항목 없음: " + ", ".join(missing))
    return "\n".join(lines) + "\n", 1 if missing else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    text, code = report(check_tools() + check_config())
    sys.stdout.write(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
