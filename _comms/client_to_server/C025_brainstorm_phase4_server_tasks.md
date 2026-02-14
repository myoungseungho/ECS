# C025: 브레인스토밍 세션 — Phase 4 서버 태스크 안내

## 요약
게임 디자이너 브레인스토밍으로 **4개 신규 시스템**이 GDD에 추가되었습니다.
서버 TASK 15~18에 총 **27개 서브태스크**가 생성되었습니다.

---

## 서버 신규 태스크

### TASK 15: 비급 & 트라이포드 (MsgType 520-524) — P1
**rules 파일**: `_gdd/rules/tripod.yaml`

| ID | 설명 | 시간 |
|----|------|------|
| tripod_sub01 | TRIPOD_LIST_REQ(520)→TRIPOD_LIST(521) — 보유 비급+장착 현황 조회 | 10분 |
| tripod_sub02 | TRIPOD_EQUIP(522)→TRIPOD_EQUIP_RESULT(523) — 트라이포드 장착/변경 | 10분 |
| tripod_sub03 | SCROLL_DISCOVER(524) — 비급 획득 알림 + 도감 등록 | 10분 |
| tripod_sub04 | data/tripod_table.yaml 생성 — 3직업 * 8스킬 * 3단계 전체 정의 | 15분 |
| tripod_sub05 | 비급 드롭 로직 — 보스/정예/비경/퀘스트 연동 | 10분 |
| tripod_sub06 | 테스트 5개 | 10분 |

### TASK 16: 강호 현상금 (MsgType 530-537) — P1
**rules 파일**: `_gdd/rules/bounty.yaml`

| ID | 설명 | 시간 |
|----|------|------|
| bounty_sub01 | BOUNTY_LIST_REQ(530)→BOUNTY_LIST(531) — 현상금 목록 | 10분 |
| bounty_sub02 | BOUNTY_ACCEPT(532)→BOUNTY_ACCEPT_RESULT(533) — 수락 | 10분 |
| bounty_sub03 | BOUNTY_COMPLETE(534) — 처치 완료 + 보상 | 10분 |
| bounty_sub04 | BOUNTY_RANKING_REQ(535)→BOUNTY_RANKING(536) — 랭킹 | 10분 |
| bounty_sub05 | PVP_BOUNTY_NOTIFY(537) — PvP 현상금 | 10분 |
| bounty_sub06 | 일일 현상금 생성 로직 (06:00 리셋 + 날씨 연동) | 10분 |
| bounty_sub07 | data/world_bosses.yaml + 토큰 상점 | 10분 |
| bounty_sub08 | 테스트 5개 | 10분 |

### TASK 17: 비경 탐험 (MsgType 540-544) — P2
**rules 파일**: `_gdd/rules/secret_realm.yaml`

| ID | 설명 | 시간 |
|----|------|------|
| realm_sub01 | SECRET_REALM_SPAWN(540) — 비경 스폰 | 10분 |
| realm_sub02 | SECRET_REALM_ENTER(541)→RESULT(542) — 입장 | 10분 |
| realm_sub03 | SECRET_REALM_COMPLETE(543)/FAIL(544) — 결과 | 10분 |
| realm_sub04 | 날씨/시간 특수 비경 로직 | 10분 |
| realm_sub05 | data/secret_realm_conditions.yaml | 10분 |
| realm_sub06 | 테스트 4개 | 10분 |

### TASK 18: 사제 시스템 (MsgType 550-560) — P2
**rules 파일**: `_gdd/rules/mentorship.yaml`

| ID | 설명 | 시간 |
|----|------|------|
| mentor_sub01 | MENTOR_SEARCH(550)→MENTOR_LIST(551) — 사부/제자 검색 | 10분 |
| mentor_sub02 | MENTOR_REQUEST(552~555) — 요청/수락 | 10분 |
| mentor_sub03 | MENTOR_QUEST_LIST(556)→QUESTS(557) — 사제 퀘스트 | 10분 |
| mentor_sub04 | MENTOR_GRADUATE(558) — 졸업 이벤트 | 10분 |
| mentor_sub05 | MENTOR_SHOP(559~560) — 사문 상점 | 10분 |
| mentor_sub06 | 사제 경험치 버프 로직 | 10분 |
| mentor_sub07 | 테스트 5개 | 10분 |

---

## 우선순위 권장
1. 현재 진행 중인 **TASK 3(거래소)** 완료
2. **TASK 15(비급)** — P1, 빌드 다양성의 핵심
3. **TASK 16(현상금)** — P1, 일일 콘텐츠 핵심
4. 나머지 기존 태스크 (TASK 4~14) 순차 진행
5. **TASK 17~18** — P2, 여유 시 진행

---

## 핵심 참고
- rules 파일 4개 새로 생성됨 — 반드시 읽고 구현
- MsgType 520~560 사용 — 기존 ~517과 충돌 없음
- data/ 파일 2~3개 추가 생성 필요 (tripod_table.yaml, world_bosses.yaml, secret_realm_conditions.yaml)
- 모든 일일/주간 시스템은 기존 DAILY_RESET/WEEKLY_RESET과 연동

잘 부탁합니다!
