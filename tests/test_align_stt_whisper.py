from align_stt_whisper import Block, assign, fmt_time, parse_stt, render, render_whisper_only

LABELED = """00:00 참석자 1
이게 시작하시죠?

00:05 참석자 2
네 제가 발표 진행하도록 하겠습니다.
10:30 다시 하죠.

1:02:15 참석자 1
수고하셨습니다.
"""

UNLABELED = "00:06 \n발표 시작해보도록 하겠습니다.\n\n01:02 \n처음에 저희가\n"


def test_parse_labeled_blocks():
    blocks = parse_stt(LABELED)
    assert [(b.start, b.speaker) for b in blocks] == [(0, "참석자 1"), (5, "참석자 2"), (3735, "참석자 1")]


def test_time_like_body_line_is_not_header():
    blocks = parse_stt(LABELED)
    assert blocks[1].text == "네 제가 발표 진행하도록 하겠습니다. 10:30 다시 하죠."


def test_parse_unlabeled_blocks():
    blocks = parse_stt(UNLABELED)
    assert [(b.start, b.speaker, b.text) for b in blocks] == [
        (6, "", "발표 시작해보도록 하겠습니다."),
        (62, "", "처음에 저희가"),
    ]


def test_parse_crlf():
    blocks = parse_stt(LABELED.replace("\n", "\r\n"))
    assert blocks[0].speaker == "참석자 1"
    assert "\r" not in blocks[1].text


def test_fmt_time():
    assert fmt_time(65) == "01:05"
    assert fmt_time(3735) == "1:02:15"


def test_assign_uses_overlap():
    blocks = [Block(0, "", ""), Block(10, "", "")]
    segs = [
        {"start": 1.0, "end": 4.0, "text": "a"},
        {"start": 8.0, "end": 11.0, "text": "b"},
        {"start": 8.0, "end": 13.0, "text": "c"},
    ]
    groups = assign(blocks, segs)
    assert [[s["text"] for s in g] for g in groups] == [["a", "b", "c"], ["b", "c"]]


def test_assign_puts_early_segment_in_first_block():
    groups = assign([Block(5, "", "")], [{"start": 0.0, "end": 2.0, "text": "x"}])
    assert groups == [[{"start": 0.0, "end": 2.0, "text": "x"}]]


def test_render_shows_both_sources():
    out = render([Block(5, "참석자 2", "네")], [[{"start": 5.2, "end": 6.0, "text": "네."}]])
    assert "=== 00:05 | 참석자 2" in out
    assert "[S] 네" in out
    assert "[W 00:05] 네." in out


def test_render_whisper_only():
    out = render_whisper_only([{"start": 61.0, "end": 62.0, "text": "안녕"}])
    assert out.strip() == "[W 01:01] 안녕"


def test_parse_clock():
    from align_stt_whisper import parse_clock

    assert parse_clock("01:05") == 65
    assert parse_clock("1:02:15") == 3735


def test_main_range_limits_blocks(tmp_path, capsys):
    from align_stt_whisper import main

    stt = tmp_path / "d.txt"
    stt.write_text("00:00 참석자 1\n가\n\n00:30 참석자 2\n나\n\n01:00 참석자 1\n다\n", encoding="utf-8")
    main(["--stt", str(stt), "--start", "00:30", "--end", "01:00"])
    out = capsys.readouterr().out
    assert "[S] 나" in out
    assert "[S] 가" not in out
    assert "[S] 다" not in out


def test_main_range_limits_whisper_only(tmp_path, capsys):
    import json

    from align_stt_whisper import main

    wjson = tmp_path / "w.json"
    segs = [{"start": 10.0, "end": 12.0, "text": "가"}, {"start": 70.0, "end": 72.0, "text": "나"}]
    wjson.write_text(json.dumps({"segments": segs}, ensure_ascii=False), encoding="utf-8")
    main(["--whisper", str(wjson), "--start", "01:00"])
    out = capsys.readouterr().out
    assert "나" in out and "가" not in out


def test_main_unknown_format_reports_error(tmp_path, capsys):
    import pytest

    from align_stt_whisper import main

    stt = tmp_path / "d.txt"
    stt.write_text("회의 기록\n가\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--stt", str(stt)])
    assert exc.value.code != 0
    assert "블록" in capsys.readouterr().err


def test_main_reads_bom_files(tmp_path, capsys):
    import json

    from align_stt_whisper import main

    stt = tmp_path / "d.txt"
    stt.write_text("00:00 참석자 1\n첫 발언\n\n00:05 참석자 2\n네\n", encoding="utf-8-sig")
    wjson = tmp_path / "w.json"
    wjson.write_text(json.dumps({"segments": []}), encoding="utf-8-sig")
    main(["--stt", str(stt), "--whisper", str(wjson)])
    assert "=== 00:00 | 참석자 1" in capsys.readouterr().out


def test_assign_shows_straddling_segment_in_every_overlapped_block():
    blocks = [Block(5, "", ""), Block(7, "", ""), Block(20, "", "")]
    groups = assign(blocks, [{"start": 4.0, "end": 9.0, "text": "x"}])
    assert [[s["text"] for s in g] for g in groups] == [["x"], ["x"], []]


def test_parse_speaker_first_header():
    blocks = parse_stt("참석자 1 00:03\n안녕하세요\n\n참석자 2 1:00:07\n네\n")
    assert [(b.start, b.speaker, b.text) for b in blocks] == [(3, "참석자 1", "안녕하세요"), (3607, "참석자 2", "네")]


def test_parse_inline_lines():
    blocks = parse_stt("[00:01] 김민수: 시작하겠습니다\n[00:04] 이지은: 네\n00:09 김민수: 다음 장\n이어서 설명\n")
    assert [(b.start, b.speaker, b.text) for b in blocks] == [
        (1, "김민수", "시작하겠습니다"),
        (4, "이지은", "네"),
        (9, "김민수", "다음 장 이어서 설명"),
    ]


def test_parse_bracketed_header_with_fraction():
    blocks = parse_stt("[00:00:01.500] Speaker 1\n가\n[00:00:04.000] Speaker 2\n나\n")
    assert [(b.start, b.speaker, b.text) for b in blocks] == [(1, "Speaker 1", "가"), (4, "Speaker 2", "나")]


def test_parse_srt():
    srt = "1\n00:00:01,000 --> 00:00:03,000\n김민수: 시작합니다\n\n2\n00:01:05,000 --> 00:01:07,000\n네\n두 줄\n"
    blocks = parse_stt(srt)
    assert [(b.start, b.speaker, b.text) for b in blocks] == [(1, "김민수", "시작합니다"), (65, "", "네 두 줄")]


def test_parse_minutes_over_99():
    blocks = parse_stt("99:59 참석자 1\n가\n\n105:30 참석자 2\n나\n\n1:02:15 참석자 1\n다\n")
    assert [b.start for b in blocks] == [5999, 6330, 3735]


def test_main_whisper_without_segments_reports_error(tmp_path, capsys):
    import pytest

    from align_stt_whisper import main

    wjson = tmp_path / "w.json"
    wjson.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--whisper", str(wjson)])
    assert exc.value.code != 0
    assert "segments" in capsys.readouterr().err
