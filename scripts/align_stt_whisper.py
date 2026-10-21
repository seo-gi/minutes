# /// script
# requires-python = ">=3.11"
# ///
"""STT 서비스 원본과 Whisper 결과를 STT 블록 단위로 나란히 출력한다.

인식하는 STT 형식 (서비스 이름과 무관하게 모양으로 판단)
1. 시각 먼저 머리줄: 빈 줄 다음 `MM:SS 화자` 또는 `H:MM:SS 화자`, 다음 줄부터 본문 (다글로 등)
2. 화자 먼저 머리줄: 빈 줄 다음 `화자 MM:SS`, 다음 줄부터 본문 (클로바노트 등)
3. 한 줄 발화: `[MM:SS] 화자: 본문` 또는 `MM:SS 화자: 본문`
4. SRT 자막: `00:00:01,000 --> 00:00:03,000` 시각 줄 다음 본문
시각은 대괄호로 감싸도 되고 소수 초(,000 / .000)가 붙어도 된다. 100분이 넘는 회의를 `105:30`처럼 분으로 이어 써도 된다.

한계: 빈 줄 다음 본문이 시각으로 시작하거나(`10:30 다시 시작합니다`), 본문이 `결론: 그렇게 하죠`처럼
짧은 말 + 콜론이면 머리줄로 읽힐 수 있다. 정렬 출력은 대조용이므로 전사 단계에서 맥락으로 바로잡는다.

사용: uv run scripts/align_stt_whisper.py [--stt <0_source/external_stt.txt>] [--whisper <1_extract/external_whisper.json>]
                                          [--start MM:SS] [--end MM:SS]
긴 회의는 --start/--end로 시간 범위를 나눠 읽는다 (시작 포함, 끝 제외).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

CLOCK = r"(\[)?(?:(\d+):)?(\d{1,3}):(\d{2})(?:[.,]\d+)?\]?"
TIME_FIRST = re.compile(rf"^{CLOCK}(?:[ \t]+(.*))?$")
SPEAKER_FIRST = re.compile(rf"^(\S.*?)[ \t]+{CLOCK}$")
SRT_TIME = re.compile(r"^(\d+):(\d{2}):(\d{2})[,.]\d+\s+-->\s+")
MAX_SPEAKER_LEN = 20


@dataclass
class Block:
    start: int
    speaker: str
    text: str


def _seconds(h: str | None, m: str, s: str) -> int:
    return int(h or 0) * 3600 + int(m) * 60 + int(s)


def _split_inline(rest: str) -> tuple[str, str]:
    """`화자: 본문`이면 (화자, 본문), 아니면 (rest, "")."""
    head, sep, tail = rest.partition(":")
    if sep and 0 < len(head.strip()) <= MAX_SPEAKER_LEN and tail.strip():
        return head.strip(), tail.strip()
    return rest.strip(), ""


def _append(blocks: list[Block], line: str) -> None:
    blocks[-1].text = f"{blocks[-1].text} {line}".strip()


def parse_srt(text: str) -> list[Block]:
    blocks: list[Block] = []
    in_cue = False
    for raw in text.splitlines():
        line = raw.strip()
        match = SRT_TIME.match(line)
        if match:
            blocks.append(Block(_seconds(*match.group(1, 2, 3)), "", ""))
            in_cue = True
        elif not line:
            in_cue = False
        elif in_cue:
            if not blocks[-1].text:
                speaker, body = _split_inline(line)
                if body:
                    blocks[-1].speaker, line = speaker, body
            _append(blocks, line)
    return blocks


def parse_stt(text: str) -> list[Block]:
    """STT 결과를 블록으로 나눈다. 인식 형식은 모듈 설명 참고.

    본문 중 시각으로 시작하는 줄을 머리줄로 오인하지 않도록, 머리줄은 빈 줄 다음(또는 첫 줄)이거나
    `화자: 본문` 한 줄 발화이거나 대괄호 시각일 때만 인정한다.
    """
    if any(SRT_TIME.match(line.strip()) for line in text.splitlines()):
        return parse_srt(text)
    blocks: list[Block] = []
    prev_blank = True
    for raw in text.splitlines():
        line = raw.strip()
        head = TIME_FIRST.match(line)
        if head:
            speaker, body = _split_inline(head.group(5) or "")
            if (prev_blank or body or head.group(1)) and len(speaker) <= MAX_SPEAKER_LEN:
                blocks.append(Block(_seconds(*head.group(2, 3, 4)), speaker, body))
                prev_blank = False
                continue
        tail = SPEAKER_FIRST.match(line) if prev_blank else None
        if tail and len(tail.group(1)) <= MAX_SPEAKER_LEN:
            blocks.append(Block(_seconds(*tail.group(3, 4, 5)), tail.group(1).strip(), ""))
        elif line and blocks:
            _append(blocks, line)
        prev_blank = not line
    return blocks


def parse_clock(text: str) -> int:
    """`MM:SS` 또는 `H:MM:SS`를 초로 바꾼다."""
    total = 0
    for part in text.split(":"):
        total = total * 60 + int(part)
    return total


def fmt_time(sec: float) -> str:
    sec = int(sec)
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def assign(blocks: list[Block], segments: list[dict]) -> list[list[dict]]:
    """Whisper 문장을 시간이 겹치는 모든 블록에 배정한다.

    화자가 자주 바뀌는 원본은 4초 미만 블록이 많아, 경계에 걸친 문장을 한 블록에만 두면
    다른 블록의 [W]가 비어 버린다. 겹치는 블록이 없으면 직전 블록(없으면 첫 블록)으로.
    """
    groups: list[list[dict]] = [[] for _ in blocks]
    if not blocks:
        return groups
    ends = [b.start for b in blocks[1:]] + [float("inf")]
    for seg in segments:
        hits = [i for i, b in enumerate(blocks) if seg["start"] < ends[i] and seg["end"] > b.start]
        if not hits:
            hits = [max((i for i, b in enumerate(blocks) if b.start <= seg["start"]), default=0)]
        for i in hits:
            groups[i].append(seg)
    return groups


def render(blocks: list[Block], groups: list[list[dict]]) -> str:
    lines: list[str] = []
    for block, group in zip(blocks, groups):
        lines.append(f"=== {fmt_time(block.start)} | {block.speaker or '(화자 없음)'}")
        lines.append(f"[S] {block.text}")
        lines.extend(f"[W {fmt_time(seg['start'])}] {seg['text']}" for seg in group)
        lines.append("")
    return "\n".join(lines)


def render_whisper_only(segments: list[dict]) -> str:
    return "\n".join(f"[W {fmt_time(seg['start'])}] {seg['text']}" for seg in segments) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stt", type=Path)
    parser.add_argument("--whisper", type=Path)
    parser.add_argument("--start", type=parse_clock, default=0)
    parser.add_argument("--end", type=parse_clock, default=None)
    args = parser.parse_args(argv)
    if not args.stt and not args.whisper:
        parser.error("--stt 또는 --whisper 중 하나 이상 필요")

    def in_range(sec: float) -> bool:
        return sec >= args.start and (args.end is None or sec < args.end)

    # 편집기로 다시 저장한 원본은 BOM이 붙을 수 있어 utf-8-sig로 읽는다
    segments = []
    if args.whisper:
        data = json.loads(args.whisper.read_text(encoding="utf-8-sig"))
        if "segments" not in data:
            print(f"Whisper 결과에 segments가 없음: {args.whisper.name}. transcribe_audio.py 출력인지 확인할 것", file=sys.stderr)
            sys.exit(1)
        segments = data["segments"]
    if args.stt:
        blocks = parse_stt(args.stt.read_text(encoding="utf-8-sig"))
        if not blocks:
            print(
                f"STT 블록을 하나도 찾지 못함: {args.stt.name}. 인식 형식은 "
                "`MM:SS 화자` 머리줄, `화자 MM:SS` 머리줄, `[MM:SS] 화자: 본문`, SRT 자막. "
                "시각이 없는 원본이면 --whisper만 주고 STT 원본은 따로 읽어 대조할 것",
                file=sys.stderr,
            )
            sys.exit(1)
        pairs = [(b, g) for b, g in zip(blocks, assign(blocks, segments)) if in_range(b.start)]
        out = render([b for b, _ in pairs], [g for _, g in pairs])
    else:
        out = render_whisper_only([s for s in segments if in_range(s["start"])])
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        sys.stdout.write(out)
    except BrokenPipeError:
        # head 등으로 출력을 잘라 읽을 때 정상 종료
        sys.stderr.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
