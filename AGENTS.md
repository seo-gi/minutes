# 회의록 도구

녹음·STT 원본·메모를 교차 대조해 전사문을 만들고, 지정 양식의 회의록(종합본·공유본·메일 본문)으로 정리하는 도구.

## 에이전트 공통 안내
- 이 파일이 모든 에이전트(Claude Code, Codex 등)의 작업 규칙 원본이다. `CLAUDE.md`는 이 파일을 가리키기만 한다.
- 작업 절차 원본은 `workflows/`에 있다. 요청에 맞는 파일을 읽고 그대로 따른다.

  | 요청 (예) | 절차 | Claude Code |
  |---|---|---|
  | 세팅해 줘 | `workflows/setup.md` | `/setup` |
  | 전사문 만들어 줘 | `workflows/transcript.md` | `/transcript` |
  | 회의록 만들어 줘 | `workflows/minutes.md` | `/minutes` |
  | 도구 업데이트해 줘 | `workflows/update.md` | `/update` |

  - 절차 파일 안의 `$ARGUMENTS`는 사용자가 덧붙인 말로 해석한다.
- 하위 에이전트가 없는 환경이면 "하위 에이전트로 점검" 단계를 직접 수행한다.
- `_config/me.md`나 `_config/project.md`가 없으면 다른 작업 전에 세팅 절차를 제안한다.

## 설정
- `_config/me.md` 개인 설정 (이름, 녹음·STT 파일을 받아 두는 폴더, 내 메일 틀). PC마다 하나, git 제외
- `_config/project.md` 과제 설정 (협업처, 회의록 독자, 공유본·메일 사용 여부와 수신자, 코드 대조 기준 레포, 정기 의무, 과제 메모). 과제 레포에 커밋해 팀원과 공유
- 두 파일의 칸마다 쓰이는 곳과 쓰는 법이 주석으로 있다. "정확히" 칸은 예시 형식을 지켜 읽고 쓴다. 과제 메모는 회의록 작성 시 함께 따른다.
- 절차·양식의 `{협업처}`는 project.md의 협업처 이름으로 채운다.
- 회의록 독자에 따라 톤을 나눈다. 내부용은 논의 맥락·기술 디테일 포함, 대외용은 결정사항·실행항목 중심의 간결한 톤.

## 도구 파일과 과제 데이터
이 레포는 도구 원본 `seo-gi/minutes`를 받아 과제별 레포(`minutes-<과제>`)로 쓴다.

| 구분 | 파일 | 바꾸는 곳 |
|---|---|---|
| 도구 | `scripts/` `tests/` `workflows/` `_templates/` `examples/` `.claude/commands/` `AGENTS.md` `CLAUDE.md` `README.md` `LICENSE` `.gitignore` `.gitattributes` `*_example.md` | 도구 원본. 과제 레포는 `workflows/update.md`로 받음 |
| 과제 데이터 | `_config/project.md` `_glossary/terms.md` `_glossary/speakers.md` `meetings/` | 과제 레포. 팀원끼리 push·pull |
| 개인 | `_config/me.md` | 각자 PC |

- 과제 레포에서 도구 파일을 고치는 것은 허용한다. 고치기 전에 두 가지를 알린다.
  - 다음 도구 갱신 때 같은 곳이 바뀌었으면 충돌이 나서 직접 골라야 한다.
  - 모든 과제에 쓸모 있는 개선이면 도구 원본에 반영하는 편이 낫다. 원본 레포를 따로 clone해 고치고 PR로 보낸다.
- 과제 레포의 커밋을 upstream(도구 원본)에 push하지 않는다. 회의 자료가 공개 레포로 나갈 수 있다.

## Backlog
- `BACKLOG.md`가 있으면 세션 시작 시 읽고, 현재 작업과 겹치는 항목이 있으면 처리를 제안한다.

## Workflow
1. 전사문 생성 (`workflows/transcript.md`)
   - 대상은 `meetings/YYYY-MM-DD_회의명/` 회의 폴더
   - `0_source` 원본(녹음·STT 결과·메모)과 `1_extract` 기계 추출, 용어사전 교차 대조
   - `2_transcript/`에 `external.md`·`internal.md`와 `transcript_log.md` 생성, 회의 폴더 `README.md` 계보 갱신
   - 회의록 내용에 영향을 주는 `[?? MM:SS]`는 채팅 번호 목록으로 사용자에게 확인받아 전사문에 반영
2. 회의록 작성 (`workflows/minutes.md`)
   1. 회의 폴더 확인. 여러 개면 대상 질문.
   2. `_config/project.md`(과제 메모 포함), `_config/me.md`, `_glossary/terms.md`, `_glossary/speakers.md` 선행 로드.
   3. Correction Rules에 따라 원문 정제.
   4. 종합본 템플릿 미지정 시 종합본 템플릿 목록 제시 후 선택.
      `_minutes-shared`(공유본 생성 결과 양식)·`_minutes-email`(메일 본문용)는 선택 대상 아님.
   5. 종합본 작성. 공유본을 쓰는 과제면 `uv run scripts/make_shared.py <종합본>`으로 공유본 생성. 공유본은 직접 쓰지 않음.
      생성이 오류로 멈추면 종합본을 고친 뒤 다시 생성.
   6. `3_minutes/YYYY-MM-DD_회의명_종합본.md` 저장. project.md에서 "사용"이면 `_공유본.md`·`_메일 본문.md`도 저장.
      Notion에는 `uv run scripts/make_notion.py <종합본>` 결과를 붙인다. PDF는 요청 시 `scripts/make_pdf.py`로 변환.
      Notion용 파일은 직접 고치지 않고, 붙이기 직전과 종합본을 고친 뒤에는 항상 다시 생성 (차이는 2절 의견 표가 목록으로 바뀌고 다른 표의 `<br>`이 공백이 되는 것뿐).
   7. 회의 폴더 `README.md` 계보의 3_minutes 행 갱신.
   8. 신규 용어·화자 발견 시 사전 등록 여부 질문.
- 결과물의 형식과 밀도는 `examples/`의 완성된 예시 회의를 기준으로 맞춘다 (용어·화자 판단 근거로는 쓰지 않음).

## Input Conversion
입력은 두 종류다.
- **STT 결과** (STT 서비스가 녹음을 글로 바꿔 내보낸 파일)
  `0_source/<구간>_stt.*`에 둔다. 전사 절차가 Whisper와 대조한다.
- **이미 사람이 정리한 전사문**
  회의 폴더(없으면 만듦)의 `2_transcript/`에 `external.md`·`internal.md`로 둔다. 전사 절차 없이 회의록 절차로 간다.

| 형식 | 처리 |
|---|---|
| `.txt` `.md` `.srt` | 바로 처리 |
| `.pdf` `.docx` | 아래 명령으로 `.md`로 변환 후 처리. 원본은 삭제하지 않는다. STT 결과면 변환본을 `1_extract/<구간>_stt.md`에(0_source는 원본만), 정리된 전사문이면 `2_transcript/`에 둔다 |
| 음성 (`.m4a` `.mp3` `.wav`) | 회의 폴더 `0_source/`에 `external_audio.m4a` 형식으로 두면 전사 절차가 처리 |
| 영상 (`.mp4` 등) | 처리하지 말고 음성 파일이 필요하다고 안내 |

변환은 bash(Windows는 Git Bash)에서 실행. 명령 실행 전 도구 존재 확인은 Environment 규칙을 따른다.

```bash
# PDF (M = meetings/YYYY-MM-DD_회의명)
pdftotext -layout -enc UTF-8 "$M/2_transcript/external.pdf" "$M/2_transcript/external.md"

# DOCX (docx = zip, 본문은 word/document.xml)
unzip -p "$M/2_transcript/external.docx" word/document.xml \
  | sed -e 's|</w:p>|\n|g' -e 's|<[^>]*>||g' \
  | sed '/^[[:space:]]*$/d' > "$M/2_transcript/external.md"
```

- 변환 후 앞부분을 읽어 추출이 정상인지 확인한다. 깨진 글자·빈 결과면 사용자에게 알린다.
- 스캔 이미지 PDF는 텍스트가 추출되지 않는다. 이 경우 OCR된 전사문이 필요하다고 안내한다.

## Correction Rules
### 전사 단계
- 용어사전 표기 최우선. 다음은 두 엔진 일치 내용, 메모, 회의 맥락 순.
- 결정 불가 구간은 `[?? MM:SS]` 표시 후 `transcript_log.md`에 등록. 구간은 전사문 파일 이름이 나타냄.
- 회의록 내용에 영향을 주는 표시는 전사 마지막에 채팅으로 확인받아 해결. 사용자는 전사문을 직접 읽지 않음.
- 요약 금지. "어", "음" 등 의미 없는 군말만 제거하고 응답은 유지.
- 없는 내용 창작 금지.
- 말한 그대로 기록. 화자의 단위 말실수(예 배터리 용량 "85kW")도 전사 단계에서는 고치지 않음.

### 회의록 단계
- 용어사전 표기 최우선.
- 오인식 의심 고유명사는 문맥으로 교정. 확신 낮으면 `[? 구간 시각 사유]` 확인 표시 (예 `[? external 12:30 차종명]`).
- 전사문에 남은 `[?? MM:SS]` 중 해석의 여지가 있는 것만 종합본에 `[? <구간> MM:SS 사유]`로 옮김. 전사 단계에서 해결된 것은 다시 묻지 않음.
- 의미상 명백한 단위 말실수는 회의록에서 바로잡음 (예 배터리 용량 85kW → 85kWh).
- 끊긴 문장은 맥락으로 복원. 없는 내용 창작 금지.
- 화자 표기는 `_glossary/speakers.md` 기준으로 통일.
- 필러 제거. 단, 결정·이견·유보 발언은 누락 금지.

## Writing Rules
- 실행항목·결정·보류 구분 필수. 종합본 기준 외부 약속 할 일은 3.1, 내부 할 일은 3.3, 결정·보류는 5절.
- 담당자·기한은 회의에서 언급된 경우에만 적는다. 임의 기입 금지.
- 수치·날짜·이름은 원문 그대로.
- 출력 언어는 원문 언어.
- 소제목과 본문을 대시(—)로 한 줄에 잇지 않는다. 소제목은 볼드체, 줄바꿈 후 본문.
  목록 안에서는 소제목 줄 끝 공백 2개 + 본문 2칸 들여쓰기, 표 셀 안에서는 `<br>`.
- 소제목이 강조를 담당하므로 본문 안 볼드는 최소화.
- 한글/영어 표기·어휘 선택은 `_glossary/terms.md`의 기준을 따른다.
- 발표 자료 쪽수는 장표에 인쇄된 번호로 쓴다.
  `1_extract/slides.md`의 `pN`은 파일 순서이며 인쇄 번호와 다를 수 있음 (표지 무번호면 pN−1).
  인쇄 번호는 slides.md만으로 판정 불가. `0_source/slides.pptx` 확인 또는 사용자에게 질문.

## Environment
- 이 도구는 여러 사람·여러 PC에서 쓴다. **특정 PC의 도구 설치 여부를 이 파일에 기록하지 않는다.**
- 준비 상태는 `uv run scripts/doctor.py`로 점검한다.
- 외부 도구는 사용 직전 `command -v <도구>`로 존재를 확인한다.
  있으면 쓰고, 없으면 임의로 설치하지 말고 사용자에게 대안과 함께 물어본다.
- 파이썬 스크립트(`scripts/`)는 `uv run`으로 실행한다. 필요한 패키지는 각 스크립트 첫머리에 적혀 있어 처음 실행할 때 자동 설치된다.
  `uv`가 없거나 Whisper 실행이 실패하면 Whisper 없이(`no-whisper`) 진행할지 묻는다.
- 파일을 쓸 때 셸 리다이렉트(`>`)는 Windows PowerShell(5.1)에서 UTF-16으로 저장되므로 스크립트의 `--out` 옵션을 쓴다.

## Concurrent Editing
- 사용자가 편집기로 `3_minutes/` 회의록을 열어 검토·수정하는 일이 잦다.
  에이전트 수정과 충돌 시 사용자 버전을 기준으로 삼아 병합한다.
- git 커밋·푸시는 사용자가 diff 검토 후 직접 수행. 요청 없이 하지 않는다.

## Folder Convention
- `_` prefix: 사용자가 내용을 채우거나 고르는 리소스 (`_config`, `_glossary`, `_templates`). `_templates`의 양식 자체는 도구가 제공한다.
- no prefix: 데이터 (`meetings`). `examples`는 도구가 제공하는 예시 데이터.
- 신규 템플릿·용어는 사용자 확인 후 추가.
- 파일명 구분자는 `_`. 중간에 `.` 사용 금지.

**회의 폴더 `meetings/YYYY-MM-DD_회의명/`**
- `0_source/` 원본. 녹음 `<구간>_audio.*`, STT 결과 `<구간>_stt.*`, 메모 `notes.md`, 발표 자료 `slides.pptx`
  - 메모는 회의 중 손으로 적거나 타이핑한 기록. 기본 이름은 `notes.md`이고, `<구간>_audio`·`<구간>_stt` 접두가 아닌 `.md`·`.txt`는 이름과 상관없이 메모 후보 (전사 절차가 확인)
- `1_extract/` 기계 추출. Whisper 결과 `<구간>_whisper.json`, 발표 자료 텍스트 `slides.md`, pdf·docx STT 결과의 변환본 `<구간>_stt.md`
- `2_transcript/` 전사문 `external.md`·`internal.md`, 전사 기록 `transcript_log.md`(1절 확인 요청, 2절 메모 분류표, 3절 불일치·가정. 사용자는 읽지 않음)
  - 전사문의 확인 표시는 `[?? MM:SS]`. 회의록 내용에 영향을 주는 것은 전사 절차 끝에 채팅으로 확인받고, 남은 것 중 해석의 여지가 있는 것만 종합본에 `[? 구간 시각 사유]`로 남김
- `3_minutes/` 회의록 `YYYY-MM-DD_회의명_종합본.md`·`_공유본.md`(·`.pdf`)·`_메일 본문.md`, Notion용 `_종합본_notion.md`(커밋 제외)
- `README.md` 단계별 계보 (만든 주체·입력·시점)

**구간**
- `external` 본회의 (질의 포함). 협업처가 있으면 협업처와 함께한 회의이며 공유본 대상
- `internal` 회의 후 내부 논의 (교수님 피드백·스탠드업, 내부 전용)
- 협업처가 "없음"인 과제도 본회의는 `external`, 회의 후 논의는 `internal`로 둔다. 이때는 공유본이 없으므로 구간은 녹음 구분 용도뿐
- 녹음 하나가 구간 하나. 같은 구간이 둘이면 `internal_2_audio.m4a`처럼 번호

**규칙**
- `0_source` 폴더의 파일은 원본이며 수정 금지
- 발표 자료는 실제 발표에 쓴 최종본만 `slides.pptx`로 보관
- 회의 폴더 `README.md`에 계보 기록. 전사·회의록 절차에서 갱신
- 녹음(`*.m4a` `*.mp3` `*.wav`)과 발표 자료(`*.pptx`)는 커밋 제외, `*_whisper.json`은 커밋
- `examples/`는 도구 원본이 제공하는 가상 회의다. 결과물의 형식과 밀도의 기준이며 실제 회의의 용어·화자 판단 근거로 쓰지 않는다
- `experiments/`가 있으면 실험 기록이다. 전사문·회의록·용어 판단의 근거로 쓰지 않는다

**원본 넣기**
- 원본은 사용자가 직접 넣음
  1. 회의 폴더 틀 `_templates/YYYY-MM-DD_meeting-name/`을 `meetings/`로 복사하고 날짜·회의명으로 이름 변경 (예 `2026-02-19_2월 정기회의`)
  2. `0_source/`에 아래 이름 규칙대로 원본 넣기
  3. 전사 절차 실행
- 파일 역할별 이름

  | 원본 파일 (예) | `0_source/` 이름 |
  |---|---|
  | 본회의 녹음 (`YYYY-MM-DD 회의명.m4a`) | `external_audio.*` (확장자 유지) |
  | 본회의 STT 결과 (`… 회의명_STT.txt`) | `external_stt.*` (`.txt`·`.md`·`.srt`·`.docx`·`.pdf`) |
  | 회의 후 내부 논의 녹음 (`… 회의명 후 스탠드업.m4a`) | `internal_audio.*` (확장자 유지) |
  | 내부 논의 STT 결과 | `internal_stt.*` |
  | 메모 (손글씨 정리·실시간 타이핑 `.md`·`.txt`) | `notes.md` 권장. 원래 이름 그대로 넣어도 됨 |
  | 발표 최종본 (`….pptx`) | `slides.pptx` |

- STT 서비스 안에서 수정한 뒤 내보낸 파일(예 이름에 "수정본")은 원본이 아니므로 넣지 않음
- 에이전트는 원본을 임의로 찾지 않음
  - `0_source/`가 비었거나 필요한 파일이 없으면 `_config/me.md`의 "녹음·STT 파일을 받아 두는 폴더"를 찾아봐도 되는지 먼저 질문
  - 허락받은 경우에만 그 폴더에서 찾아 위 이름 규칙대로 `0_source/`에 복사. 원래 파일은 지우지 않음
  - 후보가 여럿이면(발표 자료 버전 여러 개 등) 어느 파일인지 사용자에게 확인
- 회의 폴더 `README.md` 계보의 0_source 행은 전사 절차가 채움 (만든 주체·입력·시점)

## Official Document Export
협업처에 보내는 공식 문서는 **md와 이를 변환한 PDF 두 벌**로 만들고 내용을 일치시킨다. docx는 사용하지 않는다.

- **PDF는 md 생성 시점에 만들지 않는다.** 수정이 잦으므로, 사용자가 요청하는 시점에 최종 md 기준으로 변환한다.

  ```bash
  uv run scripts/make_pdf.py "<회의 폴더>/3_minutes/YYYY-MM-DD_회의명_공유본.md"
  ```

  - md를 흑백 인쇄용 HTML로 옮긴 뒤 Edge·Chrome headless로 같은 이름의 `.pdf` 저장, 임시 HTML 삭제
  - 종료 코드 49라도 PDF가 생기면 성공으로 처리
  - `pdftotext`가 있으면 PDF 글에 md의 `##` 제목이 모두 있는지 점검해 출력
  - 브라우저를 찾지 못하면 오류로 끝남. 이때는 Environment 규칙대로 사용자에게 대안과 함께 확인
- 파일명은 `YYYY-MM-DD_회의명_공유본`으로 md·pdf 동일하게 맞추고 회의 폴더 `3_minutes/`에 함께 둔다.
- 종합본 PDF는 사용자가 요청할 때만 같은 스크립트로 변환 (발송용 아님, 출력용).
- 내용 수정 시 md를 고친 뒤 PDF를 다시 변환한다.
- 발송은 사용자가 직접 수행 (자동 발송 금지). 협업처 전달물은 공유본 md·pdf 2개뿐이다.
- `_config/project.md`의 정기 의무(예 매 정기회의 후 공유본 발송)가 있으면 해당 회의 처리 시 처음에 알린다.

### Formatting Rules
- **색상 금지.** 흑백·회색조만 (표 헤더 음영은 연회색까지 허용).
- PDF 변환 시 큰 제목(`##`)마다 새 페이지에서 시작한다 (표가 페이지를 넘지 않도록. 첫 섹션은 문서 제목에 이어 배치).
- **한글 전용.** 한영 병기하지 않는다. 제목은 "회의록"만 쓰고 "MEETING MINUTES"를 붙이지 않는다.
- 원어가 표준인 기술 용어(MPC, PID, CAN, GPS 등)는 예외.
