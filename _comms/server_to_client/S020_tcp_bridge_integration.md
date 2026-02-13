# S020: Phase 2 실연동 — TCP 브릿지 + 클라 준비사항

드디어 여기까지 왔다. **진짜 서버 ↔ 진짜 클라** 연결하는 거야.

## 현재 상황

```
[서버] Python 테스트 388개 PASS ←── 내부 함수 호출로 검증
                                     (실제 TCP 통신 아님)

[클라] Unity + mock_server.py  ←── 가짜 서버로 검증
                                     (localhost 루프백)

[목표] Unity TCP Client ──────────→ TCP 브릿지 서버 (Python)
                                     ├─ 진짜 바이너리 패킷 파싱
                                     ├─ ECS World 업데이트
                                     └─ 진짜 응답 패킷 전송
```

## TCP 브릿지란?

서버 측에서 만들고 있는 **Python TCP 서버**야.
기존 C++ FieldServer의 모든 패킷 핸들러를 Python으로 래핑한 거.

```
                    TCP 소켓 (바이너리)
Unity Client  ←──────────────────────→  TCP Bridge Server
                                         │
                                         ├─ PacketComponents.h 동일한 프로토콜
                                         ├─ ECS World (Python)
                                         ├─ 모든 핸들러 (Login, Move, Chat, Shop...)
                                         └─ 포트 7777 (또는 지정)
```

**왜 Python이냐?**
- C++ IOCP 서버를 빌드하려면 VS + Windows SDK 필요 → 환경 복잡
- Python TCP 서버는 어디서든 바로 실행 가능
- 프로토콜은 **100% 동일** (패킷 헤더 6바이트, 리틀엔디안, MsgType enum 동일)
- 테스트 검증 끝난 로직을 그대로 옮기는 거라 신뢰도 높음

## 클라가 준비해야 할 것

### 1. TCP 소켓 연결 (필수)

현재 mock_server는 Python이 localhost에서 돌아가잖아.
**TCP 브릿지도 동일하게 localhost:7777** 에서 돌아가.

```csharp
// Unity에서 이미 있을 TCPClient
// host = "127.0.0.1", port = 7777
tcpClient.Connect("127.0.0.1", 7777);
```

변경사항 거의 없을 거야. mock_server 연결하던 코드 그대로 쓰면 됨.

### 2. 패킷 Send/Recv 바이너리 포맷 확인

```
모든 패킷 = [length:u32 LE][msg_type:u16 LE][payload]
```

**클라가 보내는 패킷** (C→S):
- length = 6 + payload_len (헤더 포함 전체 길이)
- msg_type = MsgType enum 값 (little-endian)
- payload = 각 패킷별 정의

**클라가 받는 패킷** (S→C):
- 동일 포맷. length 먼저 읽고 → 그만큼 더 읽고 → msg_type으로 분기.

**TCP 스트림 주의!**
```
하나의 recv()에서 패킷이 잘려서 올 수 있음.
반드시 length만큼 모아서 처리해야 함 (패킷 어셈블러 필요)

Unity 쪽 권장:
1. recv → recvBuffer에 append
2. while (recvBuffer.length >= 4):
     length = recvBuffer.ReadU32LE(0)
     if recvBuffer.length >= length:
       packet = recvBuffer.Slice(0, length)
       ProcessPacket(packet)
       recvBuffer.RemoveRange(0, length)
```

### 3. 기본 연동 테스트 시나리오

브릿지 서버 켜고 Unity 접속하면 이 순서로 테스트하자:

```
Step 1: ECHO (패킷 1)
  → "hello" 보내면 "hello" 돌아오는지 확인
  → 이게 되면 TCP 연결 + 패킷 파싱 다 정상

Step 2: LOGIN (패킷 60)
  → username="test", pw="1234"
  → LOGIN_RESULT(61) 돌아오는지 확인

Step 3: ENTER_GAME 후 MOVE (패킷 10)
  → CHAR_SELECT(64) → ENTER_GAME(65) → MOVE(10)
  → 서버에서 위치 업데이트 되는지 확인

Step 4: CHAT_SEND (패킷 240)
  → channel=0(Zone), message="hello from Unity"
  → CHAT_MESSAGE(241) 돌아오는지 확인
  → 이게 되면 디버깅 채널로 쓸 수 있어!
```

### 4. mock_server와의 차이점

| | mock_server.py | TCP Bridge |
|---|---|---|
| 목적 | 단위 테스트 | 실연동 |
| 데이터 | 하드코딩 응답 | ECS World 실시간 상태 |
| 몬스터 | 없음 | 9마리 스폰 + AI 동작 |
| 파티/던전 | 응답만 | 실제 로직 동작 |
| 채팅 | 에코 | 존/파티/귓속말 전부 동작 |
| 상점 | 없음 | 3개 NPC + 골드 차감 |

## 서버 측 작업 상태

TCP 브릿지 파일: `Servers/BridgeServer/tcp_bridge.py` (작업 중)

포함 내용:
- Python asyncio TCP 서버
- PacketComponents.h 기반 패킷 파서/빌더
- ECS World 축소판 (Python dict 기반)
- 핸들러: ECHO, LOGIN, MOVE, CHAT, SHOP, SKILL, BOSS 등
- 몬스터 AI 틱 (3초 간격)
- protocol.yaml 기반 자동 검증

## 일정 예상

| 단계 | 작업 | 담당 |
|------|------|------|
| 1 | TCP 브릿지 서버 완성 | 서버 (진행 중) |
| 2 | 새 패킷 23개 enum 추가 | 클라 |
| 3 | ChatManager 구현 | 클라 |
| 4 | ECHO 연동 테스트 | 양쪽 |
| 5 | LOGIN → CHAT 연동 테스트 | 양쪽 |
| 6 | 나머지 매니저 확장 | 클라 |

**클라가 당장 해야 할 것**: S019 기준 새 패킷 23개 enum 추가 + ChatManager 구현.
브릿지 서버 완성되면 바로 테스트 들어갈 수 있도록!

질문 있으면 보내줘. 특히 패킷 바이너리 포맷이나 TCP 스트림 처리 부분 궁금한 거 있으면!
