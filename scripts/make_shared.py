# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""종합본에서 (내부) 묶음을 통째로 지워 공유본을 만든다.

인식하는 (내부) 표시는 네 가지뿐이다.
1. 제목 줄(#~######)에 (내부) 포함
   그 제목부터 같은 단계 또는 더 상위의 다음 제목 직전까지 삭제.
   삭제 범위 끝의 구분선(---)·빈 줄은 다음 절의 것으로 보고 남기고,
   제목 바로 앞(빈 줄만 사이에 둔)의 구분선은 함께 지운다.
2. 목록 항목 줄이 -/* 다음 (내부)로 시작 (들여쓰기 무관)
   그 줄과 더 깊게 들여쓴 이어지는 줄을 삭제. 빈 줄에서 묶음 종료.
3. 표 머리 행의 칸에 (내부) 포함
   그 열을 머리·구분선·모든 행에서 삭제.
4. 표 데이터 행의 첫 칸이 (내부)로 시작 (첫 열이 #이면 둘째 칸도 확인)
   그 행 삭제.

그 밖의 위치에 (내부)가 남거나 결과에 [? 로 시작하는 확인 표시가 있으면 공유본을 쓰지 않고
종합본 줄 번호와 함께 오류로 끝낸다 (종료 코드 1).
종합본 어디든(지워질 내부 묶음 안 포함) HTML 주석 <!-- 이 있어도 같은 오류로 끝낸다. 종합본에는 주석을 남기지 않는다.
오류 줄에는 확인 표시 전체(닫는 ]까지)와 문장 일부를 함께 적는다. 긴 줄은 표시 앞뒤만 남긴다.
첫 제목 "# {회의명} 종합본"은 "# {회의명} 결과 공유"로 바꾼다.
연속 빈 줄은 하나로 줄이고 파일 끝 개행은 1개. 그 밖의 글자는 그대로 둔다.

사용: uv run scripts/make_shared.py <종합본.md> [--out <공유본.md>]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MARK = "(내부)"
# 확인 표시는 [? 로 시작해 닫는 ] 까지 ([?], [?? 12:34], [? external 12:30 사유] 모두). ] 가 없으면 줄 끝까지
UNCERTAIN = re.compile(r"\[\?[^\]]*\]?")
SNIPPET_MAX = 80  # 이보다 긴 줄은 표시 앞뒤만 보여 줌
CONTEXT = 20

HEADING = re.compile(r"^(#{1,6})\s")
LIST_INTERNAL = re.compile(r"^(\s*)[-*]\s+\(내부\)")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
TITLE = re.compile(r"^# (.+) 종합본\s*$")


class SharedError(Exception):
    def __init__(self, errors: list[tuple[int, str]]):
        self.errors = errors
        super().__init__("\n".join(f"줄 {n}: {msg}" for n, msg in errors))


def _blank(line: str) -> bool:
    return line.strip() == ""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _mark_headings(lines: list[str], drop: set[int]) -> None:
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if not m or MARK not in line:
            continue
        level = len(m.group(1))
        end = len(lines)
        for j in range(i + 1, len(lines)):
            h = HEADING.match(lines[j])
            if h and len(h.group(1)) <= level:
                end = j
                break
        # 끝의 구분선·빈 줄은 다음 절 몫으로 남긴다 (파일 끝이면 모두 지운다)
        stop = end
        if end < len(lines):
            while stop > i + 1 and (_blank(lines[stop - 1]) or RULE.match(lines[stop - 1])):
                stop -= 1
        drop.update(range(i, stop))
        # 제목 바로 앞 구분선은 함께 지운다
        k = i - 1
        while k >= 0 and _blank(lines[k]):
            k -= 1
        if k >= 0 and RULE.match(lines[k]):
            drop.add(k)


def _mark_lists(lines: list[str], drop: set[int]) -> None:
    i = 0
    while i < len(lines):
        m = LIST_INTERNAL.match(lines[i])
        if not m:
            i += 1
            continue
        base = len(m.group(1).expandtabs(4))
        drop.add(i)
        i += 1
        while i < len(lines) and not _blank(lines[i]) and _indent(lines[i].expandtabs(4)) > base:
            drop.add(i)
            i += 1


def _split_row(line: str) -> tuple[str, list[str], str] | None:
    """'  | a | b |  ' → ('  ', [' a ', ' b '], '  '). 이스케이프된 \\| 는 칸 구분이 아니다."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    prefix = line[: len(line) - len(line.lstrip())]
    suffix = line[len(line.rstrip()):]
    body = stripped[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return prefix, cells, suffix


def _mark_tables(lines: list[str], drop: set[int], edits: dict[int, str]) -> None:
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        start = i
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            i += 1
        block = range(start, i)
        if len(block) < 2 or not TABLE_SEP.match(lines[start + 1]):
            continue
        header = _split_row(lines[start])[1]
        drop_cols = {c for c, cell in enumerate(header) if MARK in cell}
        number_col = header[0].strip() == "#"
        for n in block:
            prefix, cells, suffix = _split_row(lines[n])
            if n >= start + 2:
                firsts = cells[:2] if number_col else cells[:1]
                if any(c.strip().startswith(MARK) for c in firsts):
                    drop.add(n)
                    continue
            if drop_cols:
                kept = [c for k, c in enumerate(cells) if k not in drop_cols]
                edits[n] = prefix + "|" + "|".join(kept) + "|" + suffix


def _snippet(text: str, spans: list[tuple[int, int]]) -> str:
    """짧은 줄은 그대로, 긴 줄은 표시 앞뒤 CONTEXT자만 남긴다. 표시 자체는 자르지 않는다."""
    if len(text) <= SNIPPET_MAX:
        return text
    windows: list[list[int]] = []
    for a, b in sorted(spans):
        a, b = max(0, a - CONTEXT), min(len(text), b + CONTEXT)
        if windows and a <= windows[-1][1]:
            windows[-1][1] = max(windows[-1][1], b)
        else:
            windows.append([a, b])
    out = " … ".join(text[a:b].strip() for a, b in windows)
    if windows[0][0] > 0:
        out = "… " + out
    if windows[-1][1] < len(text):
        out = out + " …"
    return out


def _leftover_message(line: str) -> str | None:
    """남은 (내부)·확인 표시가 있으면 표시 전체와 문장 일부를 담은 오류 문구를 돌려준다."""
    text = line.strip()
    marks = list(UNCERTAIN.finditer(text))
    internals = [(m.start(), m.end()) for m in re.finditer(re.escape(MARK), text)]
    if not marks and not internals:
        return None
    labels = []
    if internals:
        labels.append(f"남은 {MARK}")
    if marks:
        labels.append("남은 확인 표시 " + " ".join(m.group(0) for m in marks))
    spans = internals + [(m.start(), m.end()) for m in marks]
    return f"{', '.join(labels)} : {_snippet(text, spans)}"


def make_shared(text: str) -> str:
    lines = text.splitlines()
    drop: set[int] = set()
    edits: dict[int, str] = {}
    _mark_headings(lines, drop)
    _mark_lists(lines, drop)
    _mark_tables(lines, drop, edits)

    kept: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        kept.append((i + 1, edits.get(i, line)))

    errors = []
    for i, line in enumerate(lines):
        text = line.strip()
        at = text.find("<!--")
        if at >= 0:
            errors.append((i + 1, f"남은 HTML 주석 : {_snippet(text, [(at, at + 4)])}"))
    for n, line in kept:
        msg = _leftover_message(line)
        if msg:
            errors.append((n, msg))
    if errors:
        raise SharedError(sorted(errors))

    out: list[str] = []
    title_done = False
    for _, line in kept:
        if not title_done and line.startswith("# "):
            title_done = True
            m = TITLE.match(line)
            if m:
                line = f"# {m.group(1)} 결과 공유"
        if _blank(line):
            if out and out[-1] == "":
                continue
            line = ""
        out.append(line)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def default_out_path(src: Path) -> Path:
    name = src.name
    if "_종합본" not in name:
        raise ValueError(f"파일명에 '_종합본'이 없어 공유본 경로를 정할 수 없음: {name} (--out 지정 필요)")
    head, _, tail = name.rpartition("_종합본")
    return src.with_name(head + "_공유본" + tail)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="종합본에서 (내부) 묶음을 지워 공유본 생성")
    parser.add_argument("src", type=Path, help="종합본 md")
    parser.add_argument("--out", type=Path, help="공유본 md (기본: 파일명의 _종합본 → _공유본)")
    args = parser.parse_args(argv)

    try:
        out = args.out or default_out_path(args.src)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2
    if out.resolve() == args.src.resolve():
        print("오류: 출력 경로가 종합본과 같음", file=sys.stderr)
        return 2

    text = args.src.read_text(encoding="utf-8-sig")
    try:
        shared = make_shared(text)
    except SharedError as e:
        print(f"공유본을 만들지 않음. 종합본 {args.src} 를 고친 뒤 다시 실행:", file=sys.stderr)
        for n, msg in e.errors:
            print(f"  줄 {n}: {msg}", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(shared)
    print(f"공유본 생성: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
