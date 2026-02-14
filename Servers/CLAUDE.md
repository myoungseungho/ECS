# Server Agent CLAUDE.md

## Role
서버 에이전트 — ECS MMORPG 서버 개발 담당

## Core Rules (CONVENTIONS.md 참조)
- Component = struct, 멤버 함수 금지
- System = ISystem 상속, 상태 금지
- System 간 직접 호출 금지, 싱글턴 금지
- 모듈 폴더에 MANIFEST.yaml 필수

## Communication
- 클라이언트 메시지: `_comms/client_to_server/` (inbox)
- 서버 응답: `_comms/server_to_client/` (outbox)
- 메시지 번호: S001~ (순차 증가)
- 대화 저널: `_comms/conversation_journal.json` (Single Source of Truth)
- conversation_style: "진짜 동료 개발자처럼. 사담/농담/감정표현. 딱딱한 보고서 금지."

## Project Structure
```
Servers/
  BridgeServer/   — TCP 브릿지 (Python asyncio, 포트 7777)
  FieldServer/    — 게임 서버 (C++ ECS)
  BusServer/      — 메시지 버스
  GateServer/     — 게이트 서버
Components/       — ECS 컴포넌트 (struct only)
Systems/          — ECS 시스템 (ISystem)
Core/             — 코어 엔진
_gdd/             — Game Design Document (21 YAML)
_comms/           — 에이전트 간 통신
_context/         — 영속 상태
```

## GDD Authority (크로스파일 충돌 시)
| 데이터 | 권위 파일 |
|--------|---------|
| 키바인딩 | flow.yaml |
| PvP 수치 | pvp.yaml |
| 어그로 | ai_behavior.yaml |
| 콤보 | animation.yaml |
| 아이템 | items.yaml |
| UI | ui.yaml |

## Key Decisions
- D009: 카메라 = 탑다운 쿼터뷰 (CEO 직접 지시, TPS 숄더캠 X)
- D010: GDD 권위 기준 정립 (전문 파일 우선)
- Protocol: PacketComponents.h 기반, protocol.yaml 참조
- 스킬: 8슬롯(QWERASDF) + V궁극기 + 1-4퀵슬롯

## State File
매 작업 완료 시 `_context/server_state.yaml` 반드시 업데이트:
- current_status, completed, pending_tasks, processed_messages
