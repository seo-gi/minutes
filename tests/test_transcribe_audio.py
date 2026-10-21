from pathlib import Path

from transcribe_audio import build_prompt, glossary_terms, output_path

GLOSSARY = """# Glossary
## Optimization
| 표준 표기 | 자주 틀리게 전사되는 발음 | 비고 |
|---|---|---|
| fmincon | 에프민콘 | MATLAB |
| CasADi | 카사디 | |
| 싱글 슈팅 / 멀티포인트 슈팅 | | |
| BC4N[?] | | 차종 코드 |
| CasADi | | 중복 |
"""


def test_glossary_terms_skips_header_and_separator():
    terms = glossary_terms(GLOSSARY)
    assert "표준 표기" not in terms
    assert all(set(t) - set("-: ") for t in terms)


def test_glossary_terms_splits_slash_and_strips_unsure_mark():
    assert glossary_terms(GLOSSARY) == ["fmincon", "CasADi", "싱글 슈팅", "멀티포인트 슈팅", "BC4N"]


def test_glossary_terms_handles_crlf():
    assert glossary_terms(GLOSSARY.replace("\n", "\r\n"))[0] == "fmincon"


def test_build_prompt_respects_limit():
    prompt = build_prompt(["가" * 5, "나" * 5, "다" * 5], limit=12)
    assert prompt == "가가가가가, 나나나나나"


def test_output_path_in_source_goes_to_sibling_extract():
    audio = Path("meetings/2026-01-15_1월 정기회의/0_source/external_audio.m4a")
    assert output_path(audio) == Path("meetings/2026-01-15_1월 정기회의/1_extract/external_whisper.json")


def test_output_path_keeps_segment_number():
    audio = Path("meetings/M/0_source/internal_2_audio.m4a")
    assert output_path(audio) == Path("meetings/M/1_extract/internal_2_whisper.json")


def test_output_path_outside_source_stays_in_same_folder():
    audio = Path("experiments/val/internal_audio.m4a")
    assert output_path(audio) == Path("experiments/val/internal_whisper.json")


def test_prompt_terms_puts_misrecognized_terms_first():
    from transcribe_audio import prompt_terms

    text = """| 표준 표기 | 자주 틀리게 전사되는 발음 | 비고 |
|---|---|---|
| OCP | | |
| SoC | SOC | |
| IPOPT | 아이팝트 | |
"""
    assert prompt_terms(text) == ["SoC", "IPOPT", "OCP"]


def test_load_model_falls_back_to_cpu():
    from transcribe_audio import load_model

    calls = []

    def fake(model, device, compute_type):
        calls.append((device, compute_type))
        if device == "cuda":
            raise RuntimeError("no CUDA-capable device")
        return "cpu-model"

    assert load_model("large-v3", "cuda", "float16", factory=fake) == "cpu-model"
    assert calls == [("cuda", "float16"), ("cpu", "int8")]
