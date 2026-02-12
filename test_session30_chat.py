"""Session 30: Chat System Tests — 8 tests
채팅 시스템: 존 채팅, 파티 채팅, 귓속말, 시스템 메시지

MsgType:
  CHAT_SEND(240)     C→S: [channel(1) msg_len(1) message(N)]
  CHAT_MESSAGE(241)  S→C: [channel(1) sender_entity(8) sender_name(32) msg_len(1) message(N)]
  WHISPER_SEND(242)  C→S: [target_name_len(1) target_name(N) msg_len(1) message(N)]
  WHISPER_RESULT(243) S→C: [result(1) direction(1) other_name(32) msg_len(1) message(N)]
  SYSTEM_MESSAGE(244) S→C: [msg_len(1) message(N)]
"""
import socket, struct, time, subprocess, sys, os

PORT = 7777
HEADER = 6

# MsgType IDs
CHAT_SEND = 240
CHAT_MESSAGE = 241
WHISPER_SEND = 242
WHISPER_RESULT = 243
SYSTEM_MESSAGE = 244
PARTY_CREATE = 160
PARTY_INVITE = 161
PARTY_ACCEPT = 162
PARTY_INFO = 164

# ChatChannel
CH_GENERAL = 0
CH_PARTY = 1

# WhisperResult
WR_SUCCESS = 0
WR_TARGET_NOT_FOUND = 1

# WhisperDirection
WD_RECEIVED = 0
WD_SENT = 1


def start_server():
    p = subprocess.Popen(
        [os.path.join("build", "FieldServer.exe"), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return p


def send(s, msg_type, payload=b""):
    length = HEADER + len(payload)
    s.sendall(struct.pack("<IH", length, msg_type) + payload)


def recv_pkt(s, timeout=2.0):
    s.settimeout(timeout)
    hdr = b""
    while len(hdr) < HEADER:
        hdr += s.recv(HEADER - len(hdr))
    length, msg_type = struct.unpack("<IH", hdr)
    payload = b""
    remaining = length - HEADER
    while len(payload) < remaining:
        payload += s.recv(remaining - len(payload))
    return msg_type, payload


def connect_and_login(username="tester"):
    """로그인 + 캐릭터 선택 + 게임 진입"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", PORT))
    uname = username.encode()
    pw = b"pass"
    send(s, 60, bytes([len(uname)]) + uname + bytes([len(pw)]) + pw)
    recv_pkt(s)  # LOGIN_RESULT
    send(s, 62)  # CHAR_LIST_REQ
    _, cl = recv_pkt(s)
    char_id = struct.unpack_from("<I", cl, 1)[0] if cl[0] > 0 else 2000
    send(s, 64, struct.pack("<I", char_id))  # CHAR_SELECT
    _, eg = recv_pkt(s)
    entity = struct.unpack_from("<Q", eg, 1)[0]
    # 캐릭터 이름 추출 (CHAR_LIST_RESP에서)
    char_name = ""
    if cl[0] > 0:
        name_bytes = cl[5:37]  # id(4) 다음 name(32)
        char_name = name_bytes.split(b'\x00')[0].decode('utf-8', errors='replace')
    drain(s)
    return s, entity, char_name


def drain(s, timeout=0.3):
    """버퍼에 남은 패킷 모두 읽기"""
    pkts = []
    try:
        s.settimeout(timeout)
        while True:
            pkts.append(recv_pkt(s, timeout))
    except:
        pass
    return pkts


def recv_specific(s, target_type, timeout=2.0):
    """특정 타입의 패킷이 올 때까지 수신 (다른 패킷은 무시)"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            remaining = max(0.1, deadline - time.time())
            t, p = recv_pkt(s, remaining)
            if t == target_type:
                return t, p
        except:
            break
    return None, None


def collect_all(s, timeout=0.5):
    """일정 시간 동안 모든 패킷 수집"""
    pkts = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            remaining = max(0.1, deadline - time.time())
            t, p = recv_pkt(s, remaining)
            pkts.append((t, p))
        except:
            break
    return pkts


def parse_chat_message(payload):
    """CHAT_MESSAGE 파싱: channel(1) sender_entity(8) sender_name(32) msg_len(1) message(N)"""
    channel = payload[0]
    sender_entity = struct.unpack_from("<Q", payload, 1)[0]
    sender_name = payload[9:41].split(b'\x00')[0].decode('utf-8', errors='replace')
    msg_len = payload[41]
    message = payload[42:42 + msg_len].decode('utf-8', errors='replace')
    return channel, sender_entity, sender_name, message


def parse_whisper_result(payload):
    """WHISPER_RESULT 파싱: result(1) direction(1) other_name(32) msg_len(1) message(N)"""
    result = payload[0]
    direction = payload[1]
    other_name = payload[2:34].split(b'\x00')[0].decode('utf-8', errors='replace')
    msg_len = payload[34]
    message = payload[35:35 + msg_len].decode('utf-8', errors='replace')
    return result, direction, other_name, message


# ━━━ Test Cases ━━━

def test_zone_chat_self():
    """Test 1: 존 채팅 — 발신자 본인도 수신"""
    s, e, name = connect_and_login("chat1")
    msg = b"Hello World!"
    send(s, CHAT_SEND, bytes([CH_GENERAL, len(msg)]) + msg)

    t, p = recv_specific(s, CHAT_MESSAGE)
    assert t == CHAT_MESSAGE, "Should receive CHAT_MESSAGE"
    ch, sender, sname, text = parse_chat_message(p)
    assert ch == CH_GENERAL, f"Expected channel GENERAL(0), got {ch}"
    assert sender == e, f"Expected sender entity {e}, got {sender}"
    assert text == "Hello World!", f"Expected 'Hello World!', got '{text}'"
    s.close()
    print(f"  PASS: zone chat self-receive (name={sname}, msg='{text}')")


def test_zone_chat_broadcast():
    """Test 2: 존 채팅 — 같은 존의 다른 플레이어도 수신"""
    s1, e1, name1 = connect_and_login("chat2a")
    s2, e2, name2 = connect_and_login("chat2b")
    time.sleep(0.1)

    msg = b"Broadcast test"
    send(s1, CHAT_SEND, bytes([CH_GENERAL, len(msg)]) + msg)
    time.sleep(0.2)

    # s2가 CHAT_MESSAGE 수신했는지 확인
    t, p = recv_specific(s2, CHAT_MESSAGE, timeout=1.0)
    assert t == CHAT_MESSAGE, "Player 2 should receive CHAT_MESSAGE"
    ch, sender, sname, text = parse_chat_message(p)
    assert sender == e1, f"Sender should be player 1 (entity {e1}), got {sender}"
    assert text == "Broadcast test", f"Expected 'Broadcast test', got '{text}'"

    s1.close()
    s2.close()
    print(f"  PASS: zone chat broadcast — player 2 received msg from player 1")


def test_zone_chat_different_zone():
    """Test 3: 존 채팅 — 다른 존에 있는 플레이어는 수신 안 함"""
    s1, e1, _ = connect_and_login("chat3a")  # zone 1 (default)
    s2, e2, _ = connect_and_login("chat3b")
    time.sleep(0.1)

    # s2를 zone 2로 이동
    send(s2, 120, struct.pack("<i", 2))  # ZONE_TRANSFER_REQ to zone 2
    t, _ = recv_specific(s2, 121)  # ZONE_TRANSFER_RESULT
    drain(s2)

    # s1이 존 채팅 전송 (zone 1에서)
    msg = b"Zone 1 only"
    send(s1, CHAT_SEND, bytes([CH_GENERAL, len(msg)]) + msg)
    time.sleep(0.3)

    # s2는 받지 않아야 함
    pkts = collect_all(s2, timeout=0.5)
    chat_pkts = [p for t, p in pkts if t == CHAT_MESSAGE]
    assert len(chat_pkts) == 0, f"Player in different zone should NOT receive chat, got {len(chat_pkts)}"

    s1.close()
    s2.close()
    print(f"  PASS: zone chat isolation — different zone player didn't receive")


def test_party_chat():
    """Test 4: 파티 채팅 — 파티원만 수신"""
    s1, e1, _ = connect_and_login("pchat1")
    s2, e2, _ = connect_and_login("pchat2")
    s3, e3, _ = connect_and_login("pchat3")  # 파티 미가입
    time.sleep(0.1)

    # s1이 파티 생성
    send(s1, PARTY_CREATE)
    t, p = recv_specific(s1, PARTY_INFO)
    party_id = struct.unpack_from("<I", p, 1)[0]

    # s1이 s2 초대
    send(s1, PARTY_INVITE, struct.pack("<Q", e2))
    drain(s1, 0.3)

    # s2가 수락
    send(s2, PARTY_ACCEPT, struct.pack("<I", party_id))
    drain(s1, 0.3)
    drain(s2, 0.3)

    # s1이 파티 채팅 전송
    msg = b"Party msg"
    send(s1, CHAT_SEND, bytes([CH_PARTY, len(msg)]) + msg)
    time.sleep(0.3)

    # s2는 수신해야 함
    t2, p2 = recv_specific(s2, CHAT_MESSAGE, timeout=1.0)
    assert t2 == CHAT_MESSAGE, "Party member should receive CHAT_MESSAGE"
    ch, _, _, text = parse_chat_message(p2)
    assert ch == CH_PARTY, f"Expected PARTY channel(1), got {ch}"
    assert text == "Party msg", f"Expected 'Party msg', got '{text}'"

    # s3는 수신하면 안 됨
    pkts3 = collect_all(s3, timeout=0.5)
    chat_pkts3 = [p for t, p in pkts3 if t == CHAT_MESSAGE]
    assert len(chat_pkts3) == 0, f"Non-party member should NOT receive party chat, got {len(chat_pkts3)}"

    s1.close()
    s2.close()
    s3.close()
    print(f"  PASS: party chat — member received, non-member didn't")


def test_whisper_success():
    """Test 5: 귓속말 — 수신자 + 발신자 에코"""
    s1, e1, name1 = connect_and_login("hero")
    s2, e2, name2 = connect_and_login("guest")
    time.sleep(0.1)

    # s1 → s2에게 귓속말 (이름으로)
    # s2의 캐릭터 이름 알아야 함. guest의 첫 캐릭터는 "Archer_Park"
    target = b"Archer_Park"
    msg = b"Secret message"
    payload = bytes([len(target)]) + target + bytes([len(msg)]) + msg
    send(s1, WHISPER_SEND, payload)
    time.sleep(0.3)

    # s2(수신자)가 WHISPER_RESULT 수신 (direction=RECEIVED)
    t2, p2 = recv_specific(s2, WHISPER_RESULT, timeout=1.0)
    assert t2 == WHISPER_RESULT, "Receiver should get WHISPER_RESULT"
    result, direction, other_name, text = parse_whisper_result(p2)
    assert result == WR_SUCCESS, f"Expected SUCCESS(0), got {result}"
    assert direction == WD_RECEIVED, f"Expected RECEIVED(0), got {direction}"
    assert text == "Secret message", f"Expected 'Secret message', got '{text}'"
    # other_name should be the sender's name
    print(f"    Receiver got whisper from '{other_name}': '{text}'")

    # s1(발신자)도 에코 수신 (direction=SENT)
    t1, p1 = recv_specific(s1, WHISPER_RESULT, timeout=1.0)
    assert t1 == WHISPER_RESULT, "Sender should get WHISPER_RESULT echo"
    result, direction, other_name, text = parse_whisper_result(p1)
    assert result == WR_SUCCESS, f"Expected SUCCESS(0), got {result}"
    assert direction == WD_SENT, f"Expected SENT(1), got {direction}"
    assert text == "Secret message"
    assert other_name == "Archer_Park", f"Expected 'Archer_Park', got '{other_name}'"

    s1.close()
    s2.close()
    print(f"  PASS: whisper success — both sender and receiver got message")


def test_whisper_target_not_found():
    """Test 6: 귓속말 — 존재하지 않는 대상"""
    s1, e1, _ = connect_and_login("wfail1")
    time.sleep(0.1)

    target = b"NonExistentPlayer"
    msg = b"Hello?"
    payload = bytes([len(target)]) + target + bytes([len(msg)]) + msg
    send(s1, WHISPER_SEND, payload)

    t, p = recv_specific(s1, WHISPER_RESULT, timeout=1.0)
    assert t == WHISPER_RESULT, "Should get WHISPER_RESULT"
    result, direction, other_name, text = parse_whisper_result(p)
    assert result == WR_TARGET_NOT_FOUND, f"Expected TARGET_NOT_FOUND(1), got {result}"
    assert direction == WD_SENT, f"Expected SENT(1), got {direction}"

    s1.close()
    print(f"  PASS: whisper to non-existent player returns TARGET_NOT_FOUND")


def test_empty_message():
    """Test 7: 빈 메시지 — 무시되어야 함"""
    s1, e1, _ = connect_and_login("empty1")
    time.sleep(0.1)

    # msg_len = 0
    send(s1, CHAT_SEND, bytes([CH_GENERAL, 0]))
    time.sleep(0.3)

    # 응답이 없어야 함
    pkts = collect_all(s1, timeout=0.5)
    chat_pkts = [p for t, p in pkts if t == CHAT_MESSAGE]
    assert len(chat_pkts) == 0, f"Empty message should be ignored, got {len(chat_pkts)} CHAT_MESSAGE"

    s1.close()
    print(f"  PASS: empty message ignored")


def test_party_chat_no_party():
    """Test 8: 파티 채팅 — 파티 없으면 본인에게만 에코"""
    s1, e1, _ = connect_and_login("noparty1")
    s2, e2, _ = connect_and_login("noparty2")
    time.sleep(0.1)

    msg = b"Party? What party?"
    send(s1, CHAT_SEND, bytes([CH_PARTY, len(msg)]) + msg)
    time.sleep(0.3)

    # s1은 에코 수신 (파티 없어도 본인에게는 보냄)
    t1, p1 = recv_specific(s1, CHAT_MESSAGE, timeout=1.0)
    assert t1 == CHAT_MESSAGE, "Sender should still get echo even without party"
    ch, _, _, text = parse_chat_message(p1)
    assert ch == CH_PARTY
    assert text == "Party? What party?"

    # s2는 수신 안 해야 함
    pkts2 = collect_all(s2, timeout=0.5)
    chat_pkts2 = [p for t, p in pkts2 if t == CHAT_MESSAGE]
    assert len(chat_pkts2) == 0, f"Non-party player should NOT receive, got {len(chat_pkts2)}"

    s1.close()
    s2.close()
    print(f"  PASS: party chat without party — self-echo only")


# ━━━ Runner ━━━

def main():
    server = None
    if "--no-server" not in sys.argv:
        server = start_server()
        print(f"Server started (PID={server.pid})")

    tests = [
        test_zone_chat_self,
        test_zone_chat_broadcast,
        test_zone_chat_different_zone,
        test_party_chat,
        test_whisper_success,
        test_whisper_target_not_found,
        test_empty_message,
        test_party_chat_no_party,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            print(f"\n{test.__doc__}")
            test()
            passed += 1
        except Exception as ex:
            failed += 1
            print(f"  FAIL: {ex}")

    print(f"\n{'='*50}")
    print(f"Session 30 Chat: {passed}/{len(tests)} passed, {failed} failed")

    if server:
        server.terminate()
        server.wait(timeout=5)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
