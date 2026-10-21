# 도구 갱신 절차

도구 원본(`seo-gi/minutes`)의 개선본을 이 레포로 받는다. "도구 업데이트해 줘"라고 하면 따른다.
Claude Code는 `/update`로 실행한다.

1. `git status`로 작업 트리를 확인한다. 커밋 안 된 변경이 있으면 먼저 커밋할지 사용자에게 묻는다.
2. `git remote -v`에 upstream이 없으면 `git remote add upstream https://github.com/seo-gi/minutes.git`.
3. `git fetch upstream` 후 `git log --oneline HEAD..upstream/main`으로 새로 들어올 변경을 요약해 보여 준다.
   없으면 "최신 상태"라고 알리고 끝낸다.
4. 사용자가 받기로 하면 `git merge upstream/main`.
   처음 받는 레포에서 "refusing to merge unrelated histories"로 멈추면 `--allow-unrelated-histories`를 붙여 다시 한다.
5. 충돌이 나면 파일 종류로 나눠 처리한다.
   - 도구 파일(`scripts/` `tests/` `workflows/` `_templates/` `examples/` `.claude/commands/` `AGENTS.md` `CLAUDE.md` `README.md` `LICENSE` `.gitignore` `.gitattributes`, `*_example.md`)
     upstream 쪽을 기본으로 제안한다. 이 레포에서 일부러 고친 부분이면 무엇이 사라지는지 보여 주고 사용자에게 묻는다.
   - 과제 데이터(`_config/project.md` `_glossary/terms.md` `_glossary/speakers.md` `meetings/`)
     upstream은 이 파일들을 갖고 있지 않으므로 충돌하지 않는다. 충돌하면 이 레포 쪽을 그대로 둔다.
6. `uv run --with pytest pytest -q`와 `uv run scripts/doctor.py`로 확인한다.
   양식·절차가 바뀌었으면 기존 회의록을 다시 만들 필요는 없다고 알린다. 새 회의부터 적용된다.
7. push는 사용자가 요청할 때만 한다 (과제 레포 origin으로. upstream으로는 하지 않는다).
