# 세팅 절차

처음 받은 사람이 "세팅해 줘"라고 하면 따른다. Claude Code는 `/setup`으로 실행한다.
질문은 단계마다 한 번에 묶어서 묻고, 모르는 값은 "미정"으로 두고 넘어갈 수 있다고 알린다.

1. 도구 점검
   - `command -v uv`로 uv를 확인한다. 없으면 설치하지 말고 아래 명령을 안내한 뒤, 사용자가 설치하고 나서 진행한다.
     - Windows PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
     - macOS·Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - `uv run scripts/doctor.py`를 실행한다. 도구 줄에서 빠진 것이 있으면 어떤 기능을 못 쓰는지와 설치 방법을 알린다.
     설정 줄(`_config/`·`_glossary/`)은 아래 단계에서 만든다.
2. 상황 판단
   - `_config/project.md`가 있으면 기존 과제 레포에 합류한 것이다. 3단계만 하고 7단계로 간다.
   - 없으면 같은 과제를 이미 이 도구로 정리하는 팀원이 있는지 묻는다.
     - 있으면 그 과제 레포(이름 `minutes-<과제>`)를 clone해 그 폴더에서 다시 세팅하라고 안내하고 멈춘다.
     - 없으면 새 과제로 3~6단계를 진행한다.
3. 개인 설정 `_config/me.md`
   - `_config/me_example.md`를 복사해 만들고 이름, 소속, 녹음·STT 파일을 받아 두는 폴더를 묻는다.
   - 예전에 직접 보낸 업무 메일 하나를 붙여 넣어 달라고 한다. 받으면 "보낸 메일 예시"에 그대로 두고,
     첫 줄·인사·자기소개·맺음·문장 습관(마침표, 접속어 사용 등)을 "말투 규칙"에 정리해 보여 주고 확인받는다.
     없으면 비워 두고 기본 틀을 쓴다고 알린다.
   - 각 칸의 주석(쓰이는 곳, 쓰는 법)을 지우지 않고 값만 채운다.
   - me.md는 git에 올라가지 않는다(`.gitignore`). PC마다 한 번씩 만든다는 것을 알린다.
4. 과제 설정 `_config/project.md`
   - `_config/project_example.md`를 복사해 만들고 과제명, 협업처(없으면 "없음"), 협업처 약칭, 회의록 독자를 묻는다.
     질문할 때 칸마다 주석의 "쓰이는 곳"을 한 줄로 함께 설명하고, "정확히" 칸은 예시 형식으로 받는다. 주석은 지우지 않는다.
   - 협업처가 있으면 공유본·메일 본문 사용 여부, 메일 받는 사람·참조·제목 머리·받는 분 호칭을 묻는다.
     협업처가 "없음"이면 묻지 않고 공유본·메일 본문을 "사용 안 함", 메일 항목은 "없음"으로 채운다.
   - 회의 내용을 연구 코드와 대조할 기준 레포·브랜치(없으면 "없음"), 협업처와 약속한 정기 의무, 과제 메모(이 과제만의 규칙)를 묻는다.
5. 사전 `_glossary/`
   - `terms_example.md`를 `terms.md`로, `speakers_example.md`를 `speakers.md`로 복사하고 예시 행을 지운다.
   - 참석자 명단을 알려 주면 speakers.md의 명단 표(Roster)를 채운다. 용어는 회의를 처리하며 채워도 된다고 알린다.
   - `meetings/` 폴더가 없으면 만든다.
6. git 연결 (새 과제만)
   - `git remote -v`로 확인한다. origin이 도구 원본(`seo-gi/minutes`)이면 `git remote rename origin upstream`.
     upstream은 도구 개선본을 받는 통로다(`workflows/update.md`). 이 레포의 커밋을 upstream에 push하지 않는다.
   - `.git`이 없으면(zip으로 받음) `git init`할지 묻는다. 하면 `git remote add upstream https://github.com/seo-gi/minutes.git`.
   - 과제 레포 이름은 `minutes-<과제 영문 약칭>`을 제안한다. 회의 자료가 들어가므로 비공개로 만든다.
     GitHub에 만드는 것은 밖으로 나가는 작업이므로, 위치(개인 계정·연구실 조직)와 이름을 확인받은 뒤
     `gh repo create <owner>/<이름> --private --source . --remote origin`으로 만든다. gh가 없거나 나중에 하겠다면 건너뛴다.
   - 설정·사전 파일의 첫 커밋과 push도 사용자에게 확인받고 한다.
   - 에이전트의 보호 모드(sandbox)가 `.git` 쓰기를 막아 git 명령이 실패하면, 실행할 명령을 그대로 보여 주고
     사용자에게 터미널에서 직접 실행해 달라고 한다.
7. 마무리
   - `uv run scripts/doctor.py`를 다시 실행해 필수 항목이 모두 OK인지 확인한다.
   - 다음 할 일을 안내한다.
     - 완성된 예시 회의 `examples/`를 열어 결과물 수준 확인
     - 첫 회의 폴더 만들기: `_templates/YYYY-MM-DD_meeting-name/`을 `meetings/`로 복사하고 이름 변경, `0_source/`에 원본 넣기
     - 전사와 회의록: Claude Code는 `/transcript` → `/minutes`, 다른 에이전트는 "전사문 만들어 줘" → "회의록 만들어 줘"
     - 도구 개선본 받기: "도구 업데이트해 줘" (`/update`). 도구 원본 연결(upstream)이 없으면 그때 자동으로 추가된다
