# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#   "faster-whisper>=1.1",
#   "av==14.2.0",
#   "nvidia-cublas-cu12; sys_platform != 'darwin'",
#   "nvidia-cudnn-cu12==9.*; sys_platform != 'darwin'",
# ]
# ///
"""녹음 파일을 Whisper로 전사해 문장 단위 json으로 저장한다.

사용: uv run scripts/transcribe_audio.py <회의 폴더>/0_source/external_audio.m4a [--force]
출력: <회의 폴더>/1_extract/external_whisper.json
      입력이 0_source 밖이면 같은 폴더의 <이름에서 _audio 뺀 것>_whisper.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GLOSSARY = REPO / "_glossary" / "terms.md"
HEADER_CELL = "표준 표기"

DEFAULT_MODEL = "large-v3"
DEFAULT_DEVICE = "cuda"
DEFAULT_COMPUTE = "float16"


def _glossary_rows(text: str) -> list[tuple[str, str]]:
    """용어사전 표의 (표준 표기, 자주 틀리게 전사되는 발음) 행 목록."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        first = cells[0]
        if not first or first == HEADER_CELL or not set(first) - set("-: "):
            continue
        rows.append((first, cells[1] if len(cells) > 1 else ""))
    return rows


def _unique_terms(firsts: list[str]) -> list[str]:
    terms: list[str] = []
    for first in firsts:
        for part in first.replace("[?]", "").split("/"):
            part = part.strip()
            if part and part not in terms:
                terms.append(part)
    return terms


def glossary_terms(text: str) -> list[str]:
    """용어사전 표의 첫 열(표준 표기)을 순서대로 중복 없이 뽑는다."""
    return _unique_terms([first for first, _ in _glossary_rows(text)])


def prompt_terms(text: str) -> list[str]:
    """실제 오인식 사례가 있는 용어를 앞에 둔다. 프롬프트 길이 한도에서 잘리는 쪽은 사례 없는 용어."""
    rows = _glossary_rows(text)
    return _unique_terms([f for f, wrong in rows if wrong] + [f for f, wrong in rows if not wrong])


def build_prompt(terms: list[str], limit: int = 400) -> str:
    """Whisper 초기 프롬프트 길이 한도 안에서 용어를 쉼표로 잇는다."""
    picked: list[str] = []
    size = 0
    for term in terms:
        add = len(term) + (2 if picked else 0)
        if size + add > limit:
            break
        picked.append(term)
        size += add
    return ", ".join(picked)


def output_path(audio: Path) -> Path:
    """0_source의 녹음은 형제 폴더 1_extract로, 그 밖은 같은 폴더로 보낸다."""
    name = f"{audio.stem.removesuffix('_audio')}_whisper.json"
    folder = audio.parent
    if folder.name == "0_source":
        folder = folder.parent / "1_extract"
    return folder / name


def _register_cuda_dlls() -> None:
    """Windows에서 pip로 받은 CUDA DLL 폴더를 검색 경로에 추가한다.

    uv는 의존성을 sys.path에 덧붙이는 방식이라 site.getsitepackages()로는 찾지 못한다.
    """
    if sys.platform != "win32":
        return
    import os

    for base in sys.path:
        for sub in ("nvidia/cublas/bin", "nvidia/cudnn/bin"):
            path = Path(base) / sub
            if path.is_dir():
                os.add_dll_directory(str(path))
                os.environ["PATH"] = f"{path}{os.pathsep}{os.environ['PATH']}"


def load_model(model: str, device: str, compute: str, factory=None):
    """지정 장치로 모델을 올리고, 실패하면 CPU(int8)로 다시 시도한다."""
    if factory is None:
        from faster_whisper import WhisperModel as factory
    try:
        return factory(model, device=device, compute_type=compute)
    except (RuntimeError, ValueError) as err:
        if device == "cpu":
            raise
        print(f"{device} 사용 불가({err}). CPU로 실행하며 GPU보다 몇 배 느림", file=sys.stderr)
        return factory(model, device="cpu", compute_type="int8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--compute", default=DEFAULT_COMPUTE)
    args = parser.parse_args(argv)

    out = output_path(args.audio)
    if out.exists() and not args.force:
        print(f"생략: {out.name} 이미 있음 (--force로 재생성)", file=sys.stderr)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    _register_cuda_dlls()
    if GLOSSARY.is_file():
        prompt = build_prompt(prompt_terms(GLOSSARY.read_text(encoding="utf-8")))
    else:
        print(f"용어사전 없음({GLOSSARY}). 용어 힌트 없이 전사한다. 세팅 절차로 만들 수 있음", file=sys.stderr)
        prompt = ""
    model = load_model(args.model, args.device, args.compute)
    segments, _ = model.transcribe(
        str(args.audio), language="ko", initial_prompt=prompt, vad_filter=True, beam_size=5
    )
    records = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            records.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": text})
            print(f"\r{seg.end / 60:6.1f}분", end="", file=sys.stderr)
    print(file=sys.stderr)

    out.write_text(
        json.dumps(
            {"model": args.model, "audio": args.audio.name, "prompt": prompt, "segments": records},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"저장: {out} ({len(records)}문장)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
