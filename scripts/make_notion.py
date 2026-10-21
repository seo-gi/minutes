# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""종합본을 Notion에 붙일 md로 바꾼다.

Notion은 md로 붙인 표 칸 안의 <br>을 글자 그대로 보여 주고, md에는 칸 안 줄바꿈 문법이 없다.
- 첫 열이 #이고 "**소제목**<br>본문" 칸이 있는 번호 표(2절 의견 표)는 목록으로 바꾼다.
  행마다 "- **번호. 소제목**" + 줄 끝 공백 2개 + 본문, 나머지 열은 "  - **열 이름**" 하위 항목(빈 칸 생략)
- 그 밖의 표는 행 안의 <br>·<br/>·<br />만 공백 한 칸으로 바꾼다.
그 밖의 글자는 그대로 둔다.

사용: uv run scripts/make_notion.py <종합본.md> [--out <출력.md>]
기본 출력은 같은 폴더의 <입력 파일명>_notion.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
TITLE_CELL = re.compile(r"^\*\*([^*]+)\*\*\s*<br\s*/?>\s*(.*)$", re.IGNORECASE)


def _cells(line: str) -> list[str]:
    """표 행을 칸으로 나눈다. 이스케이프된 \\|는 칸 구분이 아니며 글자 그대로 둔다."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", body)]


def _table_to_list(rows: list[str], nl: str) -> list[str] | None:
    """번호 표를 목록 줄로 바꾼다. 대상이 아니면 None."""
    if len(rows) < 3:
        return None
    head = _cells(rows[0])
    if not head or head[0] != "#":
        return None
    data = [_cells(r) for r in rows[2:]]
    if not any(TITLE_CELL.match(c) for row in data for c in row[1:]):
        return None
    blocks = []
    for row in data:
        num = row[0] if row else ""
        lines = []
        rest = []
        for name, value in zip(head[1:], row[1:]):
            m = TITLE_CELL.match(value)
            if m and not lines:
                body = BR.sub("  " + nl + "  ", m.group(2))
                lines.append(f"- **{num}. {m.group(1)}**  ")
                if body:
                    lines.append(f"  {body}")
            elif value:
                rest.append((name, BR.sub(" ", value)))
        if not lines:
            lines.append(f"- **{num}.**")
        for name, value in rest:
            lines.append(f"  - **{name}**  ")
            lines.append(f"    {value}")
        blocks.append(nl.join(lines) + nl)
    return [nl.join(blocks)]


def make_notion(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out = []
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i])
                i += 1
            nl = "\r\n" if rows[0].endswith("\r\n") else "\n"
            converted = _table_to_list([r.rstrip("\r\n") for r in rows], nl)
            if converted is None:
                out.extend(BR.sub(" ", r) for r in rows)
            else:
                out.extend(converted)
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def default_out_path(src: Path) -> Path:
    return src.with_name(src.stem + "_notion" + src.suffix)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="종합본의 표 칸 <br>을 공백으로 바꿔 Notion용 md 생성")
    parser.add_argument("src", type=Path, help="종합본 md")
    parser.add_argument("--out", type=Path, help="출력 md (기본: <입력 파일명>_notion.md)")
    args = parser.parse_args(argv)

    out = args.out or default_out_path(args.src)
    if out.resolve() == args.src.resolve():
        print("오류: 출력 경로가 입력과 같음", file=sys.stderr)
        return 2

    with args.src.open(encoding="utf-8-sig", newline="") as f:
        text = f.read()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        f.write(make_notion(text))
    print(f"Notion용 md 생성: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
