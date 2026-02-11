"""
Session 2 Validation Test - Packet Protocol + Message Dispatch
===============================================================

4단계 검증:
  Level 1: 기본 패킷 에코 (패킷 프로토콜로 보내고 받기)
  Level 2: 패킷 조립 (분할 전송, 연속 패킷)
  Level 3: 메시지 디스패치 (타입별 다른 핸들러)
  Level 4: 안전성 (미등록 타입, 잘못된 길이)
"""
import subprocess
import socket
import struct
import time
import sys
from pathlib import Path

EXE = Path(__file__).parent / "build" / "FieldServer.exe"
HOST = '127.0.0.1'
PORT = 7777

# ── 패킷 프로토콜 (서버와 동일한 구조) ──
HEADER_SIZE = 6  # 4(length) + 2(type)
MSG_ECHO = 1
MSG_PING = 2
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    """패킷 빌드: [4바이트 길이][2바이트 타입][페이로드]"""
    total_len = HEADER_SIZE + len(payload)
    header = struct.pack('<IH', total_len, msg_type)
    return header + payload


def parse_packet(data):
    """패킷 파싱: (msg_type, payload) 반환"""
    if len(data) < HEADER_SIZE:
        return None, None
    length, msg_type = struct.unpack('<IH', data[:HEADER_SIZE])
    payload = data[HEADER_SIZE:length]
    return msg_type, payload


def recv_packet(sock, timeout=5):
    """소켓에서 완성 패킷 하나를 수신"""
    sock.settimeout(timeout)
    # 먼저 헤더 수신
    header_data = b""
    while len(header_data) < HEADER_SIZE:
        chunk = sock.recv(HEADER_SIZE - len(header_data))
        if not chunk:
            return None, None
        header_data += chunk

    length, msg_type = struct.unpack('<IH', header_data)
    payload_len = length - HEADER_SIZE

    # 페이로드 수신
    payload = b""
    while len(payload) < payload_len:
        chunk = sock.recv(payload_len - len(payload))
        if not chunk:
            return msg_type, payload
        payload += chunk

    return msg_type, payload


def recv_all_packets(sock, expected_count, timeout=5):
    """여러 패킷을 수신"""
    packets = []
    sock.settimeout(timeout)
    for _ in range(expected_count):
        try:
            msg_type, payload = recv_packet(sock, timeout)
            if msg_type is not None:
                packets.append((msg_type, payload))
        except socket.timeout:
            break
    return packets


# ── 서버 관리 ──

def start_server():
    proc = subprocess.Popen(
        [str(EXE)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    time.sleep(2.5)
    if proc.poll() is not None:
        print("  [FAIL] Server exited immediately")
        sys.exit(1)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except:
        proc.kill()


def connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((HOST, PORT))
    time.sleep(0.3)
    return sock


# ── 테스트 프레임워크 ──

passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg)


# ════════════════════════════════════════════
print("=" * 60)
print("  Session 2 Validation Test")
print("  Packet Protocol + Message Dispatch")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # ── Level 1: Basic Packet Echo ──
    print("--- Level 1: Basic Packet Echo ---")
    print("  (packet protocol: send ECHO packet, get ECHO response)")
    print()

    c1 = connect()

    # 간단한 에코
    msg = b"hello packet world"
    pkt = build_packet(MSG_ECHO, msg)
    c1.sendall(pkt)
    rtype, rpayload = recv_packet(c1)

    test("ECHO packet round-trip",
         rtype == MSG_ECHO and rpayload == msg,
         f"type={rtype}, payload={rpayload}")

    # 빈 페이로드 에코
    pkt2 = build_packet(MSG_ECHO, b"")
    c1.sendall(pkt2)
    rtype2, rpayload2 = recv_packet(c1)

    test("Empty payload ECHO",
         rtype2 == MSG_ECHO and rpayload2 == b"",
         f"type={rtype2}, payload={rpayload2}")

    # 큰 페이로드 에코 (2KB)
    big_msg = b"X" * 2048
    pkt3 = build_packet(MSG_ECHO, big_msg)
    c1.sendall(pkt3)
    rtype3, rpayload3 = recv_packet(c1)

    test("2KB payload ECHO",
         rtype3 == MSG_ECHO and rpayload3 == big_msg,
         f"sent {len(big_msg)}, got {len(rpayload3) if rpayload3 else 0}")

    c1.close()
    time.sleep(0.3)
    print()

    # ── Level 2: Packet Assembly ──
    print("--- Level 2: Packet Assembly ---")
    print("  (split send, concatenated packets)")
    print()

    c2 = connect()

    # Test: 패킷을 바이트 단위로 쪼개서 전송
    split_msg = b"split_test_data!"
    split_pkt = build_packet(MSG_ECHO, split_msg)

    # 1바이트씩 나눠 보내기 (극단적 분할)
    for i in range(len(split_pkt)):
        c2.sendall(split_pkt[i:i+1])
        time.sleep(0.01)  # 서버가 각 조각을 따로 수신하도록

    time.sleep(0.3)  # 게임루프 틱 대기
    rtype_s, rpayload_s = recv_packet(c2)

    test("Split send (1 byte at a time) reassembled",
         rtype_s == MSG_ECHO and rpayload_s == split_msg,
         f"type={rtype_s}, payload={rpayload_s}")

    # Test: 3개 패킷을 하나의 send()로 붙여 보내기
    msgs = [b"packet_one", b"packet_two", b"packet_three"]
    combined = b""
    for m in msgs:
        combined += build_packet(MSG_ECHO, m)

    c2.sendall(combined)
    time.sleep(0.3)

    responses = recv_all_packets(c2, 3)

    test("3 concatenated packets separated correctly",
         len(responses) == 3,
         f"expected 3 responses, got {len(responses)}")

    if len(responses) == 3:
        all_match = all(
            responses[i][0] == MSG_ECHO and responses[i][1] == msgs[i]
            for i in range(3)
        )
        test("All 3 payloads match",
             all_match,
             f"responses: {[(r[0], r[1]) for r in responses]}")
    else:
        test("All 3 payloads match", False, "skipped (wrong count)")

    # Test: 큰 패킷을 10바이트 청크로
    chunk_msg = b"A" * 100
    chunk_pkt = build_packet(MSG_ECHO, chunk_msg)
    chunk_size = 10
    for i in range(0, len(chunk_pkt), chunk_size):
        c2.sendall(chunk_pkt[i:i+chunk_size])
        time.sleep(0.01)
    time.sleep(0.3)

    rtype_c, rpayload_c = recv_packet(c2)
    test("100-byte payload in 10-byte chunks",
         rtype_c == MSG_ECHO and rpayload_c == chunk_msg,
         f"payload len={len(rpayload_c) if rpayload_c else 0}")

    c2.close()
    time.sleep(0.3)
    print()

    # ── Level 3: Message Dispatch ──
    print("--- Level 3: Message Dispatch ---")
    print("  (different types get different handlers)")
    print()

    c3 = connect()

    # PING → PONG 응답
    ping_pkt = build_packet(MSG_PING, b"")
    c3.sendall(ping_pkt)
    rtype_p, rpayload_p = recv_packet(c3)

    test("PING -> PONG response",
         rtype_p == MSG_PING and rpayload_p == b"PONG",
         f"type={rtype_p}, payload={rpayload_p}")

    # STATS → ECS 내부 정보
    stats_pkt = build_packet(MSG_STATS, b"")
    c3.sendall(stats_pkt)
    rtype_st, rpayload_st = recv_packet(c3)

    test("STATS response received",
         rtype_st == MSG_STATS and rpayload_st is not None,
         f"type={rtype_st}")

    if rpayload_st:
        stats_text = rpayload_st.decode('utf-8')
        test("STATS contains entity_count",
             "entity_count=" in stats_text,
             f"response: {stats_text}")

    # ECHO와 PING을 번갈아 보내기
    c3.sendall(build_packet(MSG_ECHO, b"aaa"))
    c3.sendall(build_packet(MSG_PING, b""))
    c3.sendall(build_packet(MSG_ECHO, b"bbb"))
    time.sleep(0.3)

    r1 = recv_packet(c3)
    r2 = recv_packet(c3)
    r3 = recv_packet(c3)

    test("Interleaved ECHO/PING/ECHO dispatch",
         r1[0] == MSG_ECHO and r1[1] == b"aaa" and
         r2[0] == MSG_PING and r2[1] == b"PONG" and
         r3[0] == MSG_ECHO and r3[1] == b"bbb",
         f"r1={r1}, r2={r2}, r3={r3}")

    c3.close()
    time.sleep(0.3)
    print()

    # ── Level 4: Safety ──
    print("--- Level 4: Safety ---")
    print("  (unknown type, server stability)")
    print()

    c4 = connect()

    # 미등록 타입 → 서버 크래시 안 함
    unknown_pkt = build_packet(999, b"mystery")
    c4.sendall(unknown_pkt)
    time.sleep(0.5)

    # 서버가 살아있는지 확인: 정상 ECHO가 되는지
    c4.sendall(build_packet(MSG_ECHO, b"still_alive"))
    try:
        rtype_alive, rpayload_alive = recv_packet(c4, timeout=3)
        test("Unknown type ignored, server alive",
             rtype_alive == MSG_ECHO and rpayload_alive == b"still_alive",
             f"type={rtype_alive}, payload={rpayload_alive}")
    except socket.timeout:
        test("Unknown type ignored, server alive", False, "timeout after unknown type")

    # 서버 프로세스가 크래시하지 않았는지
    test("Server process still running",
         server.poll() is None,
         f"server exited with code {server.returncode}" if server.poll() is not None else "")

    c4.close()
    time.sleep(0.3)

    # 미등록 타입 후 새 접속도 정상
    c5 = connect()
    c5.sendall(build_packet(MSG_ECHO, b"fresh_connection"))
    rtype_fresh, rpayload_fresh = recv_packet(c5)
    test("New connection after unknown type works",
         rtype_fresh == MSG_ECHO and rpayload_fresh == b"fresh_connection",
         f"type={rtype_fresh}")
    c5.close()

except Exception as e:
    print(f"\n  [ERROR] Exception: {e}")
    import traceback
    traceback.print_exc()
    failed += 1

finally:
    print()
    stop_server(server)

# ── 결과 ──
print()
print("=" * 60)
print(f"  Result: {passed}/{total} PASSED, {failed} FAILED")
print()
if failed == 0:
    print("  +-------------------------------------------+")
    print("  | SESSION 2 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] Basic packet echo OK                  |")
    print("  | [O] Packet assembly (split/concat) OK     |")
    print("  | [O] Message dispatch (type routing) OK    |")
    print("  | [O] Safety (unknown type handling) OK     |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 2 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
