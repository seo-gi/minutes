# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""공유본 md를 흑백 인쇄용 HTML로 옮긴 뒤 Edge·Chrome headless로 같은 이름의 PDF를 만든다.

지원하는 md 문법은 회의록에 쓰는 것뿐이다.
제목(#~######), 볼드(**), 목록(-·*·숫자., 들여쓰기 중첩), 줄 끝 공백 2개 줄바꿈, 표, <br>.
HTML 주석과 구분선(---·***·___) 줄은 지운다. 구분선은 ## 제목마다 새 페이지라 그리지 않는다 (md 원본은 그대로).

인쇄 형식
- 흑백·회색조만 (표 머리 칸은 연회색), 맑은 고딕, A4 여백 위아래 18mm·좌우 16mm
- ## 제목마다 새 페이지 (첫 ## 은 문서 제목에 이어 배치)

브라우저는 EDGE_PATHS 순서, 없으면 PATH의 BROWSER_COMMANDS 순서로 찾는다 (Edge·Chrome·Chromium 모두 가능). 종료 코드 49라도 PDF가 새로 생기면 성공으로 본다.
임시 HTML은 끝나면 지운다. pdftotext가 있으면 PDF 글에 md의 ## 제목이 모두 있는지 점검해 알린다.

사용: uv run scripts/make_pdf.py <공유본.md> [--out <공유본.pdf>]
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EDGE_PATHS = [
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]
BROWSER_COMMANDS = ["microsoft-edge", "google-chrome", "chromium", "chromium-browser"]

CSS = """
@page { size: A4; margin: 18mm 16mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; font-size: 10pt; line-height: 1.6; color: #000; background: #fff; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 8pt; }
h2 { font-size: 13pt; margin: 14pt 0 6pt; padding-bottom: 3pt; border-bottom: 1px solid #000; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; }
h4, h5, h6 { font-size: 10pt; margin: 10pt 0 4pt; }
.page-break { break-before: page; page-break-before: always; }
p { margin: 4pt 0; }
ul, ol { margin: 4pt 0; padding-left: 16pt; }
li { margin: 2pt 0; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0; }
th, td { border: 1px solid #000; padding: 4pt 5pt; vertical-align: top; text-align: left; }
th { background: #eeeeee; font-weight: bold; }
tr { break-inside: avoid; page-break-inside: avoid; }
""".strip()

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
LIST_ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
BR = re.compile(r"&lt;br\s*/?&gt;", re.IGNORECASE)
BOLD = re.compile(r"\*\*(.+?)\*\*")


def inline(text: str) -> str:
    out = html.escape(text, quote=False)
    out = BR.sub("<br>", out)
    out = BOLD.sub(r"<strong>\1</strong>", out)
    return out


def _join(lines: list[str]) -> str:
    """줄 끝 공백 2개는 <br>, 그 밖의 줄바꿈은 공백 한 칸."""
    out = ""
    for k, line in enumerate(lines):
        if k:
            out += "<br>" if lines[k - 1].endswith("  ") else " "
        out += inline(line.strip())
    return out


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]


def _table(lines: list[str]) -> str:
    head = "".join(f"<th>{inline(c)}</th>" for c in _cells(lines[0]))
    rows = "".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in _cells(line)) + "</tr>" for line in lines[2:]
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def _list(items: list[tuple[int, str, list[str]]]) -> str:
    out: list[str] = []
    stack: list[tuple[int, str]] = []
    for indent, tag, lines in items:
        while stack and indent < stack[-1][0]:
            out.append(f"</li></{stack.pop()[1]}>")
        if stack and indent == stack[-1][0]:
            out.append("</li>")
        else:
            out.append(f"<{tag}>")
            stack.append((indent, tag))
        out.append(f"<li>{_join(lines)}")
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


def body_html(md: str) -> str:
    lines = COMMENT.sub("", md).splitlines()
    blocks: list[str] = []
    h2_seen = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = HEADING.match(line)
        if m:
            level = len(m.group(1))
            attr = ""
            if level == 2:
                if h2_seen:
                    attr = ' class="page-break"'
                h2_seen = True
            blocks.append(f"<h{level}{attr}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if RULE.match(line):  # 큰 제목마다 새 페이지라 구분선은 그리지 않는다
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            start = i
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                i += 1
            blocks.append(_table(lines[start:i]))
            continue
        if LIST_ITEM.match(line):
            items: list[tuple[int, str, list[str]]] = []
            while i < len(lines) and lines[i].strip():
                lm = LIST_ITEM.match(lines[i])
                if lm:
                    tag = "ol" if lm.group(2)[0].isdigit() else "ul"
                    items.append((len(lm.group(1).expandtabs(4)), tag, [lm.group(3)]))
                else:
                    items[-1][2].append(lines[i])
                i += 1
            blocks.append(_list(items))
            continue
        start = i
        while (
            i < len(lines)
            and lines[i].strip()
            and not HEADING.match(lines[i])
            and not RULE.match(lines[i])
            and not LIST_ITEM.match(lines[i])
            and not lines[i].lstrip().startswith("|")
        ):
            i += 1
        if i == start:  # 표 구분선 없는 | 줄 등은 문단으로
            i += 1
        blocks.append(f"<p>{_join(lines[start:i])}</p>")
    return "\n".join(blocks)


def md_to_html(md: str, title: str = "") -> str:
    return (
        '<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n<style>\n{CSS}\n</style>\n</head>\n<body>\n"
        f"{body_html(md)}\n</body>\n</html>\n"
    )


def default_out_path(src: Path) -> Path:
    return src.with_suffix(".pdf")


def find_edge(candidates: list[Path] = EDGE_PATHS, commands: list[str] = BROWSER_COMMANDS) -> Path:
    for path in candidates:
        if Path(path).is_file():
            return Path(path)
    for name in commands:
        found = shutil.which(name)
        if found:
            return Path(found)
    raise FileNotFoundError("Edge·Chrome을 찾지 못함: " + ", ".join([*map(str, candidates), *commands]))


def missing_headings(md: str, pdf_text: str) -> list[str]:
    """md의 ## 제목 중 PDF 글에 없는 것. 공백·줄바꿈 차이는 무시한다."""
    flat = re.sub(r"\s+", "", pdf_text)
    titles = [m.group(2) for m in map(HEADING.match, COMMENT.sub("", md).splitlines()) if m and len(m.group(1)) == 2]
    return [t for t in titles if re.sub(r"\s+", "", BOLD.sub(r"\1", t)) not in flat]


def print_pdf(edge: Path, html_path: Path, out: Path) -> None:
    before = out.stat().st_mtime_ns if out.exists() else None
    result = subprocess.run(
        [
            str(edge), "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={out.resolve()}", html_path.resolve().as_uri(),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    created = out.exists() and out.stat().st_size > 0 and out.stat().st_mtime_ns != before
    if not created:
        raise RuntimeError(f"PDF가 생성되지 않음 (종료 코드 {result.returncode})\n{result.stderr.strip()}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="공유본 md를 흑백 인쇄용 PDF로 변환")
    parser.add_argument("src", type=Path, help="공유본 md")
    parser.add_argument("--out", type=Path, help="출력 PDF (기본: 같은 이름의 .pdf)")
    args = parser.parse_args(argv)

    out = args.out or default_out_path(args.src)
    try:
        edge = find_edge()
    except FileNotFoundError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2

    md = args.src.read_text(encoding="utf-8-sig")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="make_pdf_"))
    try:
        html_path = tmp / "print.html"
        html_path.write_text(md_to_html(md, title=args.src.stem), encoding="utf-8")
        print_pdf(edge, html_path, out)
    except RuntimeError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"PDF 생성: {out}")

    if shutil.which("pdftotext"):
        text = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", str(out), "-"], capture_output=True
        ).stdout.decode("utf-8", errors="replace")
        missing = missing_headings(md, text)
        if missing:
            print("점검: PDF 글에서 찾지 못한 ## 제목 " + ", ".join(missing))
        else:
            print("점검: ## 제목 모두 PDF에 있음")
    else:
        print("점검 생략: pdftotext 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
