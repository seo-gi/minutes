import re
from pathlib import Path

import pytest

from make_pdf import body_html, default_out_path, find_edge, md_to_html, missing_headings


def test_headings_and_page_break_from_second_h2():
    html = body_html("# 회의 결과 공유\n\n## 1. 요약\n\n### 1.1 주제\n\n## 2. 의견\n\n## 3. 계획\n")
    assert "<h1>회의 결과 공유</h1>" in html
    assert '<h2>1. 요약</h2>' in html
    assert "<h3>1.1 주제</h3>" in html
    assert '<h2 class="page-break">2. 의견</h2>' in html
    assert '<h2 class="page-break">3. 계획</h2>' in html


def test_bold_and_escape_keep_br():
    html = body_html("**일시** 2026 · a < b & c<br>d\n")
    assert "<strong>일시</strong>" in html
    assert "a &lt; b &amp; c<br>d" in html


def test_paragraph_trailing_two_spaces_is_line_break():
    html = body_html("첫 줄  \n둘째 줄\n셋째\n")
    assert "<p>첫 줄<br>둘째 줄 셋째</p>" in html


def test_list_item_with_heading_and_indented_body():
    md = "- **소제목**  \n  본문 첫 문장.  \n  둘째 문단\n- 다음\n"
    html = body_html(md)
    assert "<ul><li><strong>소제목</strong><br>본문 첫 문장.<br>둘째 문단</li><li>다음</li></ul>" in html


def test_nested_list():
    html = body_html("- a\n  - b\n    - c\n- d\n")
    assert "<ul><li>a<ul><li>b<ul><li>c</li></ul></li></ul></li><li>d</li></ul>" in html


def test_ordered_list():
    html = body_html("1. 첫째\n2. 둘째\n")
    assert "<ol><li>첫째</li><li>둘째</li></ol>" in html


def test_table_with_header_and_br():
    md = "| # | 의견 | 반영 |\n|---|---|---|\n| 1 | **a**<br>b | c \\| d |\n"
    html = body_html(md)
    assert "<thead><tr><th>#</th><th>의견</th><th>반영</th></tr></thead>" in html
    assert "<tbody><tr><td>1</td><td><strong>a</strong><br>b</td><td>c | d</td></tr></tbody>" in html


def test_comment_removed():
    html = body_html("a\n\n<!-- 주석\n여러 줄 -->\nb\n")
    assert "주석" not in html
    assert "<p>b</p>" in html


@pytest.mark.parametrize("rule", ["---", "***", "___", "  -----  "])
def test_rule_not_drawn(rule):
    html = body_html(f"## 1. 요약\n\na\n\n{rule}\n\n## 2. 의견\n")
    assert "<hr" not in html
    assert "<p>a</p>" in html
    assert '<h2 class="page-break">2. 의견</h2>' in html


def test_rule_ends_paragraph_without_text():
    html = body_html("첫 문단\n---\n둘째 문단\n")
    assert "<hr" not in html
    assert "---" not in html
    assert "<p>첫 문단</p>" in html
    assert "<p>둘째 문단</p>" in html


def test_document_style_black_and_white_a4():
    html = md_to_html("# 제목\n", title="제목")
    assert "<title>제목</title>" in html
    assert re.search(r"@page\s*\{[^}]*size:\s*A4[^}]*margin:\s*18mm 16mm", html)
    assert "Malgun Gothic" in html
    assert re.search(r"th\s*\{[^}]*background:\s*#eee", html)
    assert re.search(r"\.page-break\s*\{[^}]*break-before:\s*page", html)
    colors = re.findall(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b", html)
    for c in colors:
        c = c if len(c) == 6 else "".join(ch * 2 for ch in c)
        assert c[0:2] == c[2:4] == c[4:6], f"회색조가 아닌 색 #{c}"


def test_default_out_path():
    assert default_out_path(Path("m/3_minutes/x_공유본.md")) == Path("m/3_minutes/x_공유본.pdf")


def test_find_edge_order_and_missing(tmp_path):
    a, b = tmp_path / "a.exe", tmp_path / "b.exe"
    b.write_text("")
    assert find_edge([a, b]) == b
    a.write_text("")
    assert find_edge([a, b]) == a
    with pytest.raises(FileNotFoundError):
        find_edge([tmp_path / "none.exe"], commands=[])


def test_find_edge_falls_back_to_path_command(tmp_path, monkeypatch):
    import make_pdf

    monkeypatch.setattr(make_pdf.shutil, "which", lambda name: "/usr/bin/chromium" if name == "chromium" else None)
    assert find_edge([tmp_path / "none.exe"], commands=["google-chrome", "chromium"]) == Path("/usr/bin/chromium")


def test_missing_headings_ignores_whitespace():
    md = "# 제목\n\n## 1. 보고 내용 요약\n\n## 2. 협업처 의견\n\n## 3. 향후 계획\n"
    pdf_text = "제목\n1.  보고 내용\n요약\n\f2. 협업처 의견\n"
    assert missing_headings(md, pdf_text) == ["3. 향후 계획"]
