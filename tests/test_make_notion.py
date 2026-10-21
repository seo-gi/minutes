import subprocess
import sys
from pathlib import Path

from make_notion import default_out_path, make_notion

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "make_notion.py"



def test_br_variants_in_table_row():
    text = "| a<br/>b | c<br />d | e<BR>f |\n"
    assert make_notion(text) == "| a b | c d | e f |\n"


def test_indented_table_row_handled():
    text = "  | a<br>b |\n"
    assert make_notion(text) == "  | a b |\n"


def test_br_outside_table_kept():
    text = "본문 a<br>b\n- 목록<br>c\n"
    assert make_notion(text) == text


def test_other_text_unchanged():
    text = "# 제목 종합본\n\n- **소제목**  \n  본문\n  - (내부) **메모**  \n    내용\n\n| x |\n|---|\n| y |\n"
    assert make_notion(text) == text


def test_crlf_and_trailing_newline_preserved():
    text = "| a<br>b |\r\n본문\r\n"
    assert make_notion(text) == "| a b |\r\n본문\r\n"


def test_default_out_path():
    src = Path("m/3_minutes/2026-10-06_회의_종합본.md")
    assert default_out_path(src) == Path("m/3_minutes/2026-10-06_회의_종합본_notion.md")


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_cli_writes_default_path(tmp_path):
    src = tmp_path / "x_종합본.md"
    src.write_text("| a<br>b |\n", encoding="utf-8")
    result = _run(src)
    assert result.returncode == 0, result.stderr
    out = tmp_path / "x_종합본_notion.md"
    assert out.read_text(encoding="utf-8") == "| a b |\n"
    assert src.read_text(encoding="utf-8") == "| a<br>b |\n"


def test_cli_out_option(tmp_path):
    src = tmp_path / "x.md"
    src.write_text("| a<br>b |\n", encoding="utf-8")
    out = tmp_path / "sub" / "y.md"
    result = _run(src, "--out", out)
    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8") == "| a b |\n"


def test_cli_refuses_same_path(tmp_path):
    src = tmp_path / "x.md"
    src.write_text("| a<br>b |\n", encoding="utf-8")
    result = _run(src, "--out", src)
    assert result.returncode == 2
    assert src.read_text(encoding="utf-8") == "| a<br>b |\n"

def test_numbered_title_table_becomes_list():
    text = (
        "| # | 의견 | 반영 방향 | (내부) 메모 |\n|---|---|---|---|\n"
        "| 1 | **제목A**<br>본문A | 반영A | 메모A |\n"
        "| 2 | **제목B**<br>본문B | 반영B |  |\n"
    )
    assert make_notion(text) == (
        "- **1. 제목A**  \n  본문A\n"
        "  - **반영 방향**  \n    반영A\n"
        "  - **(내부) 메모**  \n    메모A\n"
        "\n"
        "- **2. 제목B**  \n  본문B\n"
        "  - **반영 방향**  \n    반영B\n"
    )


def test_list_body_keeps_extra_line_breaks():
    text = "| # | 의견 |\n|---|---|\n| 1 | **t**<br>a<br>b |\n"
    assert make_notion(text) == "- **1. t**  \n  a  \n  b\n"


def test_table_without_title_pattern_stays_table():
    text = "| # | 항목 |\n|---|---|\n| 1 | a<br>b |\n"
    assert make_notion(text) == "| # | 항목 |\n|---|---|\n| 1 | a b |\n"



def test_escaped_pipe_is_not_cell_separator():
    from make_notion import _cells

    assert _cells(r"| 1 | a \| b | c |") == ["1", r"a \| b", "c"]
