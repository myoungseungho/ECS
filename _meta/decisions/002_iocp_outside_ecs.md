# 결정 002: IOCP 네트워크 엔진을 ECS 바깥에 배치

## 날짜: 2026-02-11
## 상태: 채택

## 맥락
IOCP(I/O Completion Port)는 Windows의 비동기 I/O 메커니즘.
워커 스레드 여러 개가 동시에 소켓 이벤트를 처리함.
ECS의 게임 루프는 싱글스레드.

## 선택지
1. **IOCP를 ECS 안에 넣기** - NetworkSystem이 직접 IOCP 관리
2. **IOCP를 ECS 바깥에 두기** - IOCPServer(독립) → 이벤트 큐 → NetworkSystem이 폴링

## 결정: ECS 바깥

### 근거
- IOCP 워커 스레드는 멀티스레드, ECS 루프는 싱글스레드 → 직접 섞으면 동기화 지옥
- 이벤트 큐 패턴으로 분리하면 스레드 안전성이 큐 하나에 집중됨
- NetworkSystem은 PollEvents()만 호출하면 됨 → 단순함 유지
- IOCP 엔진 교체 시 NetworkSystem만 수정하면 됨 (모듈 독립성)

### 트레이드오프
- 이벤트 큐를 거치므로 미세한 지연 발생 (게임에서는 무시 가능, 1틱 이내)
- IOCPServer가 ECS 패턴을 따르지 않음 (인프라 레이어는 ECS 규칙 예외)
