import subprocess
import sys
from pathlib import Path

import pytest

from make_shared import SharedError, default_out_path, make_shared

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "make_shared.py"


def _shared(text: str) -> str:
    return make_shared(text)


def _errors(text: str) -> list[tuple[int, str]]:
    with pytest.raises(SharedError) as exc:
        make_shared(text)
    return exc.value.errors


# 1. 제목 묶음


def test_heading_block_removed_until_same_or_higher_level():
    text = (
        "# 회의\n\n"
        "### 1.1 공유\n- a\n\n"
        "### 1.2 메모 (내부)\n- b\n\n"
        "#### 1.2.1 하위\n- c\n\n"
        "### 1.3 공유\n- d\n"
    )
    assert _shared(text) == "# 회의\n\n### 1.1 공유\n- a\n\n### 1.3 공유\n- d\n"


def test_heading_block_stops_at_higher_level():
    text = "## 3. 계획\n\n### 3.3 추가 할 일 (내부)\n- x\n\n## 4. 다음\n- y\n"
    assert _shared(text) == "## 3. 계획\n\n## 4. 다음\n- y\n"


def test_heading_block_to_end_of_file_takes_preceding_rule():
    text = (
        "## 3. 계획\n- a\n\n---\n\n"
        "## 4. 내부 논의 (내부)\n- b\n\n---\n\n"
        "## 5. 결정·보류 (내부)\n- c\n"
    )
    assert _shared(text) == "## 3. 계획\n- a\n"


def test_heading_block_keeps_rule_before_next_section():
    text = (
        "# 회의 종합본\n\n**일시** x\n\n"
        "### 회의 정보 (내부)\n- 참석자 a\n\n---\n\n"
        "## 1. 요약\n- b\n"
    )
    assert _shared(text) == "# 회의 결과 공유\n\n**일시** x\n\n---\n\n## 1. 요약\n- b\n"


# 2. 목록 묶음


def test_list_item_with_continuation_removed():
    text = (
        "- **소제목**  \n"
        "  공유 문장\n"
        "  - (내부) 메모 첫 줄  \n"
        "    이어지는 줄\n"
        "- **다음**  \n"
        "  공유\n"
    )
    assert _shared(text) == "- **소제목**  \n  공유 문장\n- **다음**  \n  공유\n"


def test_nested_list_under_internal_item_removed():
    text = "- a\n* (내부) b\n  - c\n    - d\n- e\n"
    assert _shared(text) == "- a\n- e\n"


def test_list_block_ends_at_blank_line():
    text = "- (내부) a\n\n  b\n"
    assert _shared(text) == "\n  b\n"


def test_list_trailing_spaces_preserved():
    text = "- **x**  \n  문장  \n  둘째\n  - (내부) y\n"
    assert _shared(text) == "- **x**  \n  문장  \n  둘째\n"


# 3·4. 표


def test_table_column_and_row_removed():
    text = (
        "| # | 의견 | 반영 방향 | (내부) 메모 |\n"
        "|---|---|---|---|\n"
        "| 1 | **a**<br>b | c | 메모1 |\n"
        "| (내부) 2 | d | e | f |\n"
        "| 3 | g | h |  |\n"
    )
    assert _shared(text) == (
        "| # | 의견 | 반영 방향 |\n"
        "|---|---|---|\n"
        "| 1 | **a**<br>b | c |\n"
        "| 3 | g | h |\n"
    )


def test_table_row_marked_in_first_content_cell_after_number_column():
    text = "| # | 내용 |\n|---|---|\n| 1 | a |\n| 2 | (내부) b |\n"
    assert _shared(text) == "| # | 내용 |\n|---|---|\n| 1 | a |\n"


def test_table_row_marked_in_first_cell():
    text = "| 영역 | 할 일 |\n|---|---|\n| (내부) OCP | a |\n| OCP | b |\n"
    assert _shared(text) == "| 영역 | 할 일 |\n|---|---|\n| OCP | b |\n"


# 오류


def test_internal_mid_sentence_is_error():
    errors = _errors("# t\n\n- 문장 중간 (내부) 표시\n")
    assert [line for line, _ in errors] == [3]


def test_internal_in_table_cell_middle_is_error():
    errors = _errors("| # | a |\n|---|---|\n| 1 | x (내부) y |\n")
    assert [line for line, _ in errors] == [3]


@pytest.mark.parametrize("mark", ["[?]", "[?? 12:34]", "[? external 12:30]", "[? internal 1:02:15 차종명]"])
def test_uncertain_marks_left_are_errors(mark):
    errors = _errors(f"# t\n\n- 확인 {mark}\n- (내부) 여긴 {mark} 괜찮음\n")
    assert [line for line, _ in errors] == [3]


def test_html_comment_is_error_even_inside_removed_block():
    text = "# t\n\n## 4. 내부 논의 (내부)\n\n<!-- 메모 -->\n\n- a\n\n<!-- 여러 줄\n     주석 -->\n"
    errors = _errors(text)
    assert [line for line, _ in errors] == [5, 9]
    assert "HTML 주석" in errors[0][1]


def test_marks_inside_removed_blocks_are_ok():
    text = "# t\n\n## 5. 결정 (내부)\n- 확인 [?] 문장 중 (내부)\n"
    assert _shared(text) == "# t\n"


# 제목·공백


def test_title_renamed_only_for_full_minutes_title():
    assert _shared("# 1월 정기회의 종합본\n\n본문\n") == "# 1월 정기회의 결과 공유\n\n본문\n"
    assert _shared("# 1월 정기회의\n") == "# 1월 정기회의\n"
    assert _shared("## 종합본 설명 종합본\n") == "## 종합본 설명 종합본\n"


def test_blank_lines_collapsed_and_single_final_newline():
    text = "a\n\n\n\nb\n\n\n"
    assert _shared(text) == "a\n\nb\n"


def test_br_and_spacing_preserved():
    text = "| # | 의견 |\n|---|---|\n|  1 |  **x**<br>y  |\n"
    assert _shared(text) == text


# CLI


def test_default_out_path():
    p = Path("m/3_minutes/2026-01-15_1월 정기회의_종합본.md")
    assert default_out_path(p) == Path("m/3_minutes/2026-01-15_1월 정기회의_공유본.md")


def test_default_out_path_requires_full_suffix():
    with pytest.raises(ValueError):
        default_out_path(Path("m/회의록.md"))


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_cli_writes_default_path(tmp_path):
    src = tmp_path / "2026-10-06_회의_종합본.md"
    src.write_text("# 회의 종합본\n\n- a\n  - (내부) b\n", encoding="utf-8")
    result = _run(src)
    assert result.returncode == 0, result.stderr
    out = tmp_path / "2026-10-06_회의_공유본.md"
    assert out.read_text(encoding="utf-8") == "# 회의 결과 공유\n\n- a\n"


def test_cli_out_option(tmp_path):
    src = tmp_path / "x_종합본.md"
    src.write_text("# x 종합본\n", encoding="utf-8")
    out = tmp_path / "sub.md"
    result = _run(src, "--out", out)
    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8") == "# x 결과 공유\n"


def test_cli_error_does_not_write(tmp_path):
    src = tmp_path / "x_종합본.md"
    src.write_text("# x 종합본\n\n- 확인 [?]\n", encoding="utf-8")
    result = _run(src)
    assert result.returncode == 1
    assert "3" in result.stderr
    assert not (tmp_path / "x_공유본.md").exists()


# 오류 메시지에 확인 표시 전체와 문장 일부


def _message(text: str) -> str:
    errors = _errors(text)
    assert len(errors) == 1
    return errors[0][1]


def test_error_shows_whole_mark_at_end_of_long_line():
    head = "가" * 120
    msg = _message(f"- {head} 문장 끝 [? external 1:02:15 차종명 확인 필요]\n")
    assert "[? external 1:02:15 차종명 확인 필요]" in msg
    assert "문장 끝" in msg
    assert head not in msg


def test_error_shows_whole_mark_at_start_of_long_line():
    tail = "나" * 120
    msg = _message(f"- [? internal 12:30 수치] 앞부분 {tail}\n")
    assert "[? internal 12:30 수치]" in msg
    assert "앞부분" in msg
    assert tail not in msg


def test_error_shows_short_sentence_whole():
    msg = _message("- 배터리 용량 85kWh [? external 05:24 단위]\n")
    assert "배터리 용량 85kWh [? external 05:24 단위]" in msg


def test_error_shows_every_mark_on_line():
    msg = _message("- a [? external 01:00 이름] 가운데 " + "다" * 80 + " b [? external 02:00 수치]\n")
    assert "[? external 01:00 이름]" in msg
    assert "[? external 02:00 수치]" in msg


def test_error_mark_without_closing_bracket_kept_to_line_end():
    msg = _message("- 문장 [? external 03:00 사유\n")
    assert "[? external 03:00 사유" in msg
