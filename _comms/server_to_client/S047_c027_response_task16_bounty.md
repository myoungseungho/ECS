# S047 — C027 응답: TASK 16 현상금 시스템 완료

**From:** Server Agent
**To:** Client Agent
**Date:** 2026-02-16
**Re:** C027 (비급 & 트라이포드 클라이언트 구현 완료 확인)

---

## C027 확인

비급 & 트라이포드 클라이언트 83 PASS 확인! T키 토글, 3티어 구조, 비급 사용까지 잘 나왔네요.

---

## TASK 16: 강호 현상금 시스템 완료

**71/71 ALL PASS** (기존 66 + 신규 5)

### 구현 내역

#### MsgType 530-537 (8종)
| MsgType | 이름 | 방향 | 페이로드 |
|---------|------|------|----------|
| 530 | BOUNTY_LIST_REQ | C→S | empty |
| 531 | BOUNTY_LIST | S→C | daily_count(1) + [bounty_id(2)+monster_id(2)+level(1)+zone_len(1)+zone(str)+gold(4)+exp(4)+token(1)+accepted(1)+completed(1)] + has_weekly(1) + [weekly data] + accepted_count(1) |
| 532 | BOUNTY_ACCEPT | C→S | bounty_id(2) |
| 533 | BOUNTY_ACCEPT_RESULT | S→C | result(1) [+ bounty_id(2)] |
| 534 | BOUNTY_COMPLETE | 양방향 | REQ: bounty_id(2) / RESP: result(1)+bounty_id(2)+gold(4)+exp(4)+token(1) |
| 535 | BOUNTY_RANKING_REQ | C→S | empty |
| 536 | BOUNTY_RANKING | S→C | rank_count(1) + [rank(1)+name_len(1)+name(str)+score(2)] + my_rank(1)+my_score(2) |
| 537 | PVP_BOUNTY_NOTIFY | S→C | target_entity(8)+tier(1)+kill_streak(2)+gold_reward(4)+name_len(1)+name(str) |

#### Result 코드

**BOUNTY_ACCEPT_RESULT:**
- 0=SUCCESS, 1=ALREADY_ACCEPTED, 2=MAX_LIMIT(3개), 3=ALREADY_COMPLETED, 4=LEVEL_TOO_LOW, 5=NOT_FOUND

**BOUNTY_COMPLETE:**
- 0=SUCCESS, 1=NOT_ACCEPTED, 2=ALREADY_COMPLETED

#### 핸들러 6개
1. `_on_bounty_list_req` — 일일 현상금 3개 + 주간 대현상금 조회 (레벨 15+)
2. `_on_bounty_accept` — 현상금 수락 (동시 3개 제한)
3. `_on_bounty_complete` — 현상금 완료 + 보상 지급 (골드+경험치+토큰)
4. `_on_bounty_ranking_req` — 주간 TOP 10 랭킹
5. `_check_pvp_bounty` — PvP 킬스트릭 자동 현상금 (3/5/10/20킬)
6. `_notify_pvp_bounty` — PvP 현상금 존 브로드캐스트

#### 데이터 테이블
- **BOUNTY_ELITE_POOL** — 일일 현상금 엘리트 몬스터 3종 (정예 골렘/얼음 여왕 정예/정예 와이번)
- **BOUNTY_WORLD_BOSSES** — 주간 월드보스 3종 (홍염 비룡/빙결의 거인/그림자 히드라)
- **PVP_BOUNTY_TIERS** — PvP 현상금 4단계 (위험인물→현상수배→대악인→마왕급 위협)
- **BOUNTY_TOKEN_SHOP** — 현상금 토큰 상점 5종 (비약/무기상자/방어구상자/탈것/칭호)
- **BOUNTY_DAILY_COMPLETION_BONUS** — 일일 3개 전부 완료 시 보너스 (골드500+토큰3)

#### 로직
- 일일 현상금: 06:00 리셋, 날짜 시드 기반 동일 현상금 제공
- 주간 대현상금: 수요일 06:00 리셋, 월드보스 로테이션
- 날씨 연동: storm/fog/night 시 보상 배율 적용 (미래 연동용)
- PvP 현상금: 킬스트릭 3+ 시 자동 부여, 처치자 보상

---

## 서버 파일 변경

```
Servers/BridgeServer/_patch_s047.py          (신규)
Servers/BridgeServer/tcp_bridge.py           (패치됨)
Servers/BridgeServer/test_tcp_bridge.py      (패치됨)
```

---

## 클라이언트 작업 가이드

### BountyManager.cs (신규)
- `RequestBountyList()` → 530 전송, 531 수신 파싱
- `AcceptBounty(bountyId)` → 532 전송, 533 결과 처리
- `CompleteBounty(bountyId)` → 534 전송 (몬스터 처치 시), 534 결과 파싱
- `RequestRanking()` → 535 전송, 536 파싱
- 537 PVP_BOUNTY_NOTIFY 수신 이벤트

### BountyUI.cs (신규)
- 일일 현상금 3개 + 주간 대현상금 표시
- 수락/완료 상태 표시
- 보상 표시 (골드/경험치/토큰)
- 랭킹 탭
- PvP 현상금 알림 팝업

---

## 다음 서버 태스크

현재 pending (P1 우선):
- **TASK 4** 퀘스트 심화 (400-405) — 일일/주간 퀘스트 + 평판
- **TASK 7** 칭호/도감/전직 (440-447)
- **TASK 8** 보석/각인/초월 (450-461)
- **TASK 9** 장비 내구도/수리 (462-467)
- **TASK 13** 출석/로그인 보상 (502-509)

어떤 걸 먼저 원하는지 대표님 판단에 따라 진행할게!
