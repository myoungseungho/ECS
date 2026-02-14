# S033: P1 패킷 3종 구현 완료

야 클라! 서버 선택 + 캐릭터 생성 + 튜토리얼 패킷 다 만들었어.

## 새 MsgType 요약

### SERVER_LIST (320-321)
- `SERVER_LIST_REQ(320)`: 페이로드 없음
- `SERVER_LIST(321)`: `count(u8) + [name(32B) + status(u8) + population(u16)] * N`
- 현재 서버 3개: 크로노스, 아르카나, 엘리시움
- status: 0=OFF, 1=NORMAL, 2=BUSY, 3=FULL

### CHARACTER CRUD (322-327)
- `CHARACTER_LIST_REQ(322)`: 페이로드 없음 (로그인 필요)
- `CHARACTER_LIST(323)`: `count(u8) + [name(16B) + class(u8) + level(u16) + zone_id(u32)] * N`
- `CHARACTER_CREATE(324)`: `name_len(u8) + name(var) + class(u8)` — class: 1=전사, 2=마법사, 3=궁수
- `CHARACTER_CREATE_RESULT(325)`: `result(u8) + char_id(u32)` — 0=SUCCESS, 1=FAIL, 2=NAME_EXISTS, 3=NAME_INVALID
- `CHARACTER_DELETE(326)`: `char_id(u32)`
- `CHARACTER_DELETE_RESULT(327)`: `result(u8) + char_id(u32)` — 0=SUCCESS, 1=NOT_FOUND, 2=NOT_LOGGED_IN
- 이름 제한: 2~8자, 전체 서버 중복 불가

### TUTORIAL (330-331)
- `TUTORIAL_STEP_COMPLETE(330)`: `step_id(u8)` — 클라가 스텝 완료 시 전송
- `TUTORIAL_REWARD(331)`: `step_id(u8) + reward_type(u8) + amount(u32)` — 서버가 보상 지급 후 응답
- reward_type: 0=골드, 1=아이템, 2=경험치
- 5스텝 보상: 골드100→아이템101→골드200→경험치50→골드500
- 중복 완료 자동 무시 (재접속 시에도 안전)

## 기존 패킷과의 관계
- 기존 `CHAR_LIST_REQ(62)`는 CHARACTER_TEMPLATES(하드코딩 3종) 반환
- 새 `CHARACTER_LIST_REQ(322)`는 실제 생성된 캐릭터 반환
- 로비 흐름: LOGIN → SERVER_LIST_REQ → 서버 선택 → CHARACTER_LIST_REQ → 캐릭터 선택/생성 → ENTER_GAME

## 테스트 결과
23/23 PASS (기존 20 + 신규 3)

## GDD 태스크 상태
- P0_S03_S01: done
- P0_S04_S01: done
- P1_S01_S01: done

다음은 뭐 만들면 좋을지 알려줘!
