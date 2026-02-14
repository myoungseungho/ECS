# S044: 브레인스토밍 세션 — Phase 4 신규 4개 시스템 GDD 추가

## 요약
게임 디자이너 브레인스토밍 세션에서 **4개 신규 시스템**을 설계하여 GDD에 반영했습니다.
기존 시스템들과의 시너지를 극대화하면서, 무협 세계관에 어울리는 감성 + 리텐션 요소를 추가했습니다.

---

## 신규 시스템 4가지

### 1. 비급 & 트라이포드 시스템 (MsgType 520-524)
- **컨셉**: 스킬에 3단계 변형(초식→절초→오의) 적용. 비급 아이템으로 해금.
- **시너지**: 도감 시스템 + 탐험 + 빌드 다양성
- **rules**: `_gdd/rules/tripod.yaml`
- **서버 태스크**: TASK 15 (tripod_sub01~06, 6개)
- **클라 태스크**: TripodUI + ScrollDiscoverUI + ScrollCollectionUI (3개)

### 2. 강호 현상금 시스템 (MsgType 530-537)
- **컨셉**: 일일 현상금 3장 + 주간 월드보스 + PvP 현상금
- **시너지**: 일일 콘텐츠 + PvP + 날씨 시스템 + 파티 유도
- **rules**: `_gdd/rules/bounty.yaml`
- **서버 태스크**: TASK 16 (bounty_sub01~08, 8개)
- **클라 태스크**: BountyBoardUI + BountyCompleteUI + PvPBountyUI + RankingUI (4개)

### 3. 비경 탐험 시스템 (MsgType 540-544)
- **컨셉**: 필드에 랜덤 출현하는 비경 포탈. 5종 챌린지(시련/지혜/보물/수련/운명). 일일 3회.
- **시너지**: 날씨+시간 조합 특수 비경 + 비급 드롭처 + 솔로 콘텐츠
- **rules**: `_gdd/rules/secret_realm.yaml`
- **서버 태스크**: TASK 17 (realm_sub01~06, 6개)
- **클라 태스크**: SecretRealmPortal + SecretRealmHUD + 5종 내부 시각화 (3개)

### 4. 사제(師弟) 시스템 (MsgType 550-560)
- **컨셉**: 고레벨(Lv.40+)→저레벨(Lv.1~20) 사부-제자. 졸업 시 양쪽 보상.
- **시너지**: 친구 시스템(친밀도) + 파티 시너지 + 신규 유저 리텐션
- **rules**: `_gdd/rules/mentorship.yaml`
- **서버 태스크**: TASK 18 (mentor_sub01~07, 7개)
- **클라 태스크**: MentorshipUI + GraduationUI + MentorShopUI (3개)

---

## 클라이언트 할 일

### 즉시 가능 (서버 무관)
- 없음 — 모든 신규 UI는 서버 패킷 구현 후 착수

### 서버 대기 (blocked)
- GROUP I: TASK 15~18 대응 UI 13개 서브태스크 (`client_state.yaml` 참조)
- 서버 TASK 구현 완료 시 blocked→false 전환

---

## 변경된 파일 목록
1. `_gdd/game_design.yaml` — Phase 4 섹션 추가 (P4_S01~S04)
2. `_gdd/rules/tripod.yaml` — 신규 생성
3. `_gdd/rules/bounty.yaml` — 신규 생성
4. `_gdd/rules/secret_realm.yaml` — 신규 생성
5. `_gdd/rules/mentorship.yaml` — 신규 생성
6. `_context/server_state.yaml` — TASK 15~18 (27개 서브태스크) 추가
7. `_context/client_state.yaml` — GROUP I (13개 서브태스크) 추가

---

## MsgType 할당 요약
| 시스템 | MsgType 범위 | 패킷 수 |
|--------|-------------|---------|
| 비급/트라이포드 | 520-524 | 5개 |
| 현상금 | 530-537 | 8개 |
| 비경 | 540-544 | 5개 |
| 사제 | 550-560 | 11개 |

기존 할당: ~517. 신규: 520~560. **충돌 없음.**

---

서버는 현재 TASK 3(거래소) 진행 중이니, TASK 15~18은 TASK 3~14 이후에 순차 진행하면 됩니다.
다만 **TASK 15(비급)**은 P1 우선순위라 가능하면 빨리 착수하면 좋겠습니다!
