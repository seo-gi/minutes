# 회의록 도구

녹음과 STT 결과를 교차 대조해 전사문을 만들고, 정해진 양식의 회의록으로 정리하는 도구.
코딩 에이전트(Claude Code, Codex 등)에게 말로 시키면 절차대로 진행된다.

## 무엇을 만드나
- **전사문**  
  STT 결과(STT 서비스가 녹음을 글로 바꿔 내보낸 파일)와 Whisper(로컬 음성 인식) 결과, 메모, 발표 자료, 용어사전을 대조해 받아 적은 글
- **종합본**  
  내부 논의까지 담은 전체 회의록. Notion에 붙이는 용도
- **공유본** (협업처가 있을 때)  
  협업처에 보내는 요약본. 종합본에서 스크립트로 자동 생성되며 내부 내용은 빠짐. md와 PDF 두 벌
- **메일 본문** (협업처가 있을 때)  
  공유본을 보낼 때 쓰는 메일 초안

완성된 결과물 예시는 `examples/`에 있다. 가상 회의 하나를 원본부터 메일 본문까지 모두 담아 둠.

## 레포 구성
| 레포 | 역할 |
|---|---|
| `seo-gi/minutes` (이 레포) | 도구 원본. 스크립트·절차·양식 |
| `minutes-<과제>` | 과제별 레포. 도구 원본을 받아 과제 설정·용어사전·회의 자료를 더한 것. 같은 과제 팀원이 함께 씀 |

개인 설정(이름, 녹음 파일 폴더, 메일 말투)은 레포에 올리지 않고 각자 PC의 `_config/me.md`에 둔다.

## 시작하기

### 1. 준비물
- **git**
- **uv**  
  파이썬과 스크립트에 필요한 패키지를 자동으로 설치해 주는 도구. 설치 목록을 따로 관리하지 않아도 스크립트를 처음 실행할 때 필요한 것이 설치됨
  - Windows PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - macOS·Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **코딩 에이전트**  
  Claude Code 또는 Codex
- 있으면 좋은 것
  - NVIDIA GPU: Whisper가 한 시간 녹음을 약 10분에 처리. 없으면 몇 배 느리고, Whisper 없이 STT 결과만으로도 진행 가능
  - Edge 또는 Chrome: 공유본 PDF 변환
  - pdftotext: PDF 변환 결과 점검

### 2. 받기
같은 과제를 이미 이 도구로 정리하는 팀원이 있으면 그 과제 레포를 받는다.

```bash
git clone https://github.com/<owner>/minutes-<과제>.git
```

새 과제면 도구 원본을 받는다. git을 쓰지 않으면 GitHub 페이지의 Releases(배포 묶음)에서 zip을 받아도 된다. zip으로 받으면 나중에 도구 업데이트를 받을 때 git 연결이 필요하며, 세팅 절차가 안내한다.

```bash
git clone https://github.com/seo-gi/minutes.git minutes-<과제>
```

### 3. 세팅
받은 폴더에서 에이전트를 열고 이렇게 말한다.

- Claude Code: `/setup`
- Codex 등: "AGENTS.md 읽고 세팅해 줘"

에이전트가 준비물을 점검하고, 몇 가지를 물어본 뒤 설정 파일과 용어사전을 만든다.
새 과제면 GitHub에 비공개 과제 레포를 만드는 것까지 안내한다.

### 4. 회의 정리
1. `_templates/YYYY-MM-DD_meeting-name/`을 `meetings/`로 복사하고 날짜·회의명으로 이름 변경
2. `0_source/`에 원본을 넣음

   | 원본 | 이름 |
   |---|---|
   | 본회의 녹음 | `external_audio.m4a` (확장자 유지) |
   | 본회의 STT 결과 | `external_stt.txt` (`.md`·`.srt`도 가능) |
   | 회의 후 내부 논의 녹음·STT | `internal_audio.m4a`, `internal_stt.txt` |
   | 회의 중 메모 (손글씨 정리·실시간 타이핑) | `notes.md` 권장. 원래 이름 그대로 넣어도 됨 |
   | 발표 자료 최종본 | `slides.pptx` |

3. 에이전트에게 시킴

   | 할 일 | Claude Code | Codex 등 |
   |---|---|---|
   | 전사문 만들기 | `/transcript` | "전사문 만들어 줘" |
   | 회의록 만들기 | `/minutes` | "회의록 만들어 줘" |

- STT 서비스는 상관없음. 시각과 화자가 표시된 흔한 형식(다글로, 클로바노트, SRT 자막 등)을 인식
- 불확실한 부분은 에이전트가 채팅으로 번호 목록을 보여 주고 확인받음. 전사문을 직접 읽을 필요 없음

### 5. 도구 업데이트
도구 원본이 개선되면 받고 싶을 때 받는다. 받지 않으면 지금 상태 그대로 쓸 수 있다.

- Claude Code: `/update`
- Codex 등: "도구 업데이트해 줘"

## 폴더 구조
```
minutes-<과제>/
├── AGENTS.md            # 작업 규칙 원본 (모든 에이전트 공통)
├── CLAUDE.md            # AGENTS.md를 가리키는 포인터 (Claude Code용)
├── workflows/           # 절차 원본: setup, transcript, minutes, update
├── .claude/commands/    # Claude Code 슬래시 명령 (workflows/를 가리킴)
├── _config/             # project.md (과제 설정, 공유) · me.md (개인 설정, git 제외)
├── _glossary/           # terms.md (용어사전) · speakers.md (화자 명단)
├── _templates/          # 종합본·공유본·메일 본문 양식, 회의 폴더 틀
├── meetings/            # 회의 폴더 (과제 레포에만 있음)
├── examples/            # 완성된 가상 회의 예시
├── scripts/             # 전사·정렬·공유본·Notion·PDF 변환, 준비 상태 점검(doctor.py)
└── tests/
```

## 도구를 고치고 싶을 때
- **내 과제에만 필요한 수정**  
  과제 레포에서 바로 고친다. 다음 업데이트 때 같은 곳이 바뀌었으면 어느 쪽을 쓸지 골라야 함
- **모두에게 쓸모 있는 개선**  
  도구 원본을 따로 받아 고친 뒤 PR(변경 제안)로 보낸다. 과제 레포의 커밋은 회의 자료가 섞여 있으므로 원본으로 보내지 않음

## 라이선스
MIT. `LICENSE` 참고.
