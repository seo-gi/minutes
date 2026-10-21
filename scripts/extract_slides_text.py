# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0"]
# ///
"""발표 자료(pptx)의 글을 페이지별로 위에서 아래 순서 그대로 출력한다.

제목 상자가 없는 자료가 많아 제목을 추측하지 않는다. 문구를 회의록 제목에 그대로 옮길 수 있도록
텍스트 상자는 문단 단위로, 표는 셀 단위로, 발표자 노트는 따로 표시한다.

사용: uv run scripts/extract_slides_text.py <0_source/slides.pptx> [--pages 1-3,7] [--out <1_extract/slides.md>]
--out을 주면 폴더를 만들고 UTF-8(LF)로 저장한다. 기본은 stdout.
PowerShell 리다이렉트(>)는 UTF-16으로 저장되므로 파일 저장에는 --out을 쓴다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _walk(shapes):
    """그룹 안 도형까지 펼친다."""
    for shape in shapes:
        if shape.shape_type == 6:  # MSO_SHAPE_TYPE.GROUP
            yield from _walk(shape.shapes)
        else:
            yield shape


def extract(path: Path) -> list[dict]:
    from pptx import Presentation

    slides = []
    for no, slide in enumerate(Presentation(str(path)).slides, 1):
        texts, tables = [], []
        for shape in _walk(slide.shapes):
            pos = (shape.top or 0, shape.left or 0)
            if getattr(shape, "has_table", False) and shape.has_table:
                rows = [[cell.text.strip() for cell in row.cells] for row in shape.table.rows]
                tables.append((pos, rows))
            elif shape.has_text_frame:
                paras = [p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip()]
                if paras:
                    texts.append((pos, paras))
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        slides.append(
            {
                "no": no,
                "blocks": [paras for _, paras in sorted(texts, key=lambda t: t[0])],
                "tables": [rows for _, rows in sorted(tables, key=lambda t: t[0])],
                "notes": notes,
            }
        )
    return slides


def render(slides: list[dict]) -> str:
    lines: list[str] = []
    for slide in slides:
        lines.append(f"=== p{slide['no']}")
        for i, paras in enumerate(slide["blocks"], 1):
            lines.append(f"[{i}] {paras[0]}")
            lines.extend(f"    {p}" for p in paras[1:])
        for rows in slide["tables"]:
            lines.extend("[표] " + " | ".join(row) for row in rows)
        if slide["notes"]:
            lines.append(f"[노트] {slide['notes']}")
        lines.append("")
    return "\n".join(lines)


def parse_pages(text: str) -> set[int]:
    pages: set[int] = set()
    for part in text.split(","):
        a, _, b = part.partition("-")
        pages.update(range(int(a), int(b or a) + 1))
    return pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--pages", type=parse_pages)
    parser.add_argument("--out", type=Path, help="출력 md (기본: stdout)")
    args = parser.parse_args(argv)

    slides = extract(args.pptx)
    if args.pages:
        slides = [s for s in slides if s["no"] in args.pages]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="\n") as f:
            f.write(render(slides))
        return 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        sys.stdout.write(render(slides))
    except BrokenPipeError:
        sys.stderr.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
