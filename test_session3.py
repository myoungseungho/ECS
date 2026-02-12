"""
Session 3 Validation Test - Movement + Broadcast
==================================================

5단계 검증 (커리큘럼 acceptance_criteria):
  S3-BUILD     : 빌드 성공 (build.py에서 별도 확인)
  S3-POSITION  : 이동 후 위치 갱신 확인
  S3-BROADCAST : A 이동 → B가 A의 이동 패킷 수신
  S3-SELF-NO-ECHO : A 이동 → A는 브로드캐스트 미수신
  S3-MULTI-MOVE : 3명 동시 이동 → 각각 다른 2명의 이동 수신
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

# ── 패킷 프로토콜 ──
HEADER_SIZE = 6
MSG_ECHO = 1
MSG_PING = 2
MSG_MOVE = 10
MSG_MOVE_BROADCAST = 11
MSG_POS_QUERY = 12
MSG_LOGIN = 60
MSG_LOGIN_RESULT = 61
MSG_CHAR_LIST_REQ = 62
MSG_CHAR_LIST_RESP = 63
MSG_CHAR_SELECT = 64
MSG_ENTER_GAME = 65
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    header = struct.pack('<IH', total_len, msg_type)
    return header + payload


def build_move_packet(x, y, z):
    """MOVE 패킷: [x(float)] [y(float)] [z(float)]"""
    payload = struct.pack('<fff', x, y, z)
    return build_packet(MSG_MOVE, payload)


def recv_packet(sock, timeout=5):
    """소켓에서 완성 패킷 하나를 수신"""
    sock.settimeout(timeout)
    header_data = b""
    while len(header_data) < HEADER_SIZE:
        chunk = sock.recv(HEADER_SIZE - len(header_data))
        if not chunk:
            return None, None
        header_data += chunk

    length, msg_type = struct.unpack('<IH', header_data)
    payload_len = length - HEADER_SIZE

    payload = b""
    while len(payload) < payload_len:
        chunk = sock.recv(payload_len - len(payload))
        if not chunk:
            return msg_type, payload
        payload += chunk

    return msg_type, payload


def try_recv_packet(sock, timeout=1.0):
    """타임아웃 짧게 잡고 패킷 수신 시도. 없으면 (None, None) 반환"""
    try:
        return recv_packet(sock, timeout)
    except socket.timeout:
        return None, None


def recv_all_available(sock, timeout=1.0):
    """모든 수신 가능한 패킷을 수집"""
    packets = []
    while True:
        msg_type, payload = try_recv_packet(sock, timeout)
        if msg_type is None:
            break
        packets.append((msg_type, payload))
        timeout = 0.3  # 첫 패킷 이후 짧게
    return packets


def parse_move_broadcast(payload):
    """MOVE_BROADCAST 페이로드 파싱: (entity_id, x, y, z)"""
    if len(payload) < 20:
        return None, None, None, None
    entity_id = struct.unpack('<Q', payload[:8])[0]
    x, y, z = struct.unpack('<fff', payload[8:20])
    return entity_id, x, y, z


def parse_pos_response(payload):
    """POS_QUERY 응답 파싱: (x, y, z)"""
    if len(payload) < 12:
        return None, None, None
    x, y, z = struct.unpack('<fff', payload[:12])
    return x, y, z


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


def connect_and_login(username):
    """Connect, login, char select, enter game, drain packets"""
    s = connect()

    # Login
    uname = username.encode('utf-8')
    pw = b"pass123"
    payload = bytes([len(uname)]) + uname + bytes([len(pw)]) + pw
    s.sendall(build_packet(MSG_LOGIN, payload))

    # Wait for login result
    rtype, rpayload = recv_packet(s, timeout=5)
    if rtype != MSG_LOGIN_RESULT:
        raise Exception(f"Login failed for {username}, got type {rtype}")

    # Get char list
    s.sendall(build_packet(MSG_CHAR_LIST_REQ))
    rtype, rpayload = recv_packet(s, timeout=5)
    if rtype != MSG_CHAR_LIST_RESP:
        raise Exception(f"Char list failed for {username}, got type {rtype}")

    # Parse char_id (if count > 0, use first char, else auto-assign 2000+)
    char_count = rpayload[0] if rpayload else 0
    if char_count > 0:
        char_id = struct.unpack('<I', rpayload[1:5])[0]
    else:
        char_id = 2000  # Auto-assign

    # Select character
    s.sendall(build_packet(MSG_CHAR_SELECT, struct.pack('<I', char_id)))
    rtype, rpayload = recv_packet(s, timeout=5)
    if rtype != MSG_ENTER_GAME:
        raise Exception(f"Enter game failed for {username}, got type {rtype}")

    # Drain all pending packets
    recv_all_available(s, timeout=0.5)

    return s


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
print("  Session 3 Validation Test")
print("  Movement + Broadcast")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # ── S3-POSITION: 이동 후 위치 갱신 ──
    print("--- S3-POSITION: Movement updates position ---")
    print()

    c1 = connect_and_login("s3_pos1")

    # 이동 전 위치 확인
    c1.sendall(build_packet(MSG_POS_QUERY))
    rtype, rpayload = recv_packet(c1)
    pre_x, pre_y, pre_z = parse_pos_response(rpayload)

    test("Initial position query works",
         rtype == MSG_POS_QUERY and pre_x is not None,
         f"type={rtype}, pos=({pre_x}, {pre_y}, {pre_z})")

    # 이동 패킷 전송
    c1.sendall(build_move_packet(100.0, 200.0, 0.0))
    time.sleep(0.3)

    # 이동 후 위치 확인
    c1.sendall(build_packet(MSG_POS_QUERY))
    rtype2, rpayload2 = recv_packet(c1)
    px, py, pz = parse_pos_response(rpayload2)

    test("Position updated after MOVE",
         rtype2 == MSG_POS_QUERY and
         abs(px - 100.0) < 0.01 and abs(py - 200.0) < 0.01,
         f"expected (100, 200, 0), got ({px}, {py}, {pz})")

    # 두 번째 이동
    c1.sendall(build_move_packet(-50.5, 300.25, 10.0))
    time.sleep(0.3)

    c1.sendall(build_packet(MSG_POS_QUERY))
    rtype3, rpayload3 = recv_packet(c1)
    px2, py2, pz2 = parse_pos_response(rpayload3)

    test("Position updated on second MOVE",
         abs(px2 - (-50.5)) < 0.01 and abs(py2 - 300.25) < 0.01 and abs(pz2 - 10.0) < 0.01,
         f"expected (-50.5, 300.25, 10), got ({px2}, {py2}, {pz2})")

    c1.close()
    time.sleep(0.3)
    print()

    # ── S3-BROADCAST: A 이동 → B가 수신 ──
    print("--- S3-BROADCAST: A moves, B receives ---")
    print()

    cA = connect_and_login("s3_bcastA")
    cB = connect_and_login("s3_bcastB")
    time.sleep(0.3)

    # Move both to same area to ensure Interest overlap
    cA.sendall(build_move_packet(500.0, 500.0, 0.0))
    cB.sendall(build_move_packet(501.0, 501.0, 0.0))
    time.sleep(0.5)

    # Drain all pending packets
    recv_all_available(cA, timeout=0.5)
    recv_all_available(cB, timeout=0.5)

    # Now A moves again, B should receive broadcast
    cA.sendall(build_move_packet(510.0, 510.0, 0.0))
    time.sleep(0.5)

    # B가 브로드캐스트 수신
    bcast_type, bcast_payload = try_recv_packet(cB, timeout=2)

    if bcast_type == MSG_MOVE_BROADCAST:
        eid, bx, by, bz = parse_move_broadcast(bcast_payload)
        test("B receives A's MOVE_BROADCAST",
             True,
             f"entity={eid}, pos=({bx}, {by}, {bz})")
        test("Broadcast position matches A's move",
             abs(bx - 510.0) < 0.01 and abs(by - 510.0) < 0.01,
             f"expected (510, 510), got ({bx}, {by})")
    else:
        test("B receives A's MOVE_BROADCAST", False,
             f"expected type={MSG_MOVE_BROADCAST}, got type={bcast_type}")
        test("Broadcast position matches A's move", False, "skipped")

    cA.close()
    cB.close()
    time.sleep(0.3)
    print()

    # ── S3-SELF-NO-ECHO: A 이동 → A에게 브로드캐스트 안 옴 ──
    print("--- S3-SELF-NO-ECHO: Mover doesn't receive own broadcast ---")
    print()

    cSelf = connect_and_login("s3_selfA")
    cOther = connect_and_login("s3_selfB")
    time.sleep(0.3)

    # Move both to same area
    cSelf.sendall(build_move_packet(999.0, 888.0, 0.0))
    cOther.sendall(build_move_packet(1000.0, 888.0, 0.0))
    time.sleep(0.5)

    # Drain
    recv_all_available(cSelf, timeout=0.5)
    recv_all_available(cOther, timeout=0.5)

    # cSelf가 이동
    cSelf.sendall(build_move_packet(1010.0, 900.0, 0.0))
    time.sleep(0.5)

    # cOther는 수신해야 함 (확인용)
    other_type, other_payload = try_recv_packet(cOther, timeout=2)
    test("Other player receives broadcast (control check)",
         other_type == MSG_MOVE_BROADCAST,
         f"type={other_type}")

    # cSelf는 수신하면 안 됨
    self_type, self_payload = try_recv_packet(cSelf, timeout=1)
    test("Mover does NOT receive own broadcast",
         self_type is None,
         f"expected None, got type={self_type}")

    cSelf.close()
    cOther.close()
    time.sleep(0.3)
    print()

    # ── S3-MULTI-MOVE: 3명 동시 이동 ──
    print("--- S3-MULTI-MOVE: 3 players move simultaneously ---")
    print()

    c1 = connect_and_login("s3_m1")
    c2 = connect_and_login("s3_m2")
    c3 = connect_and_login("s3_m3")
    time.sleep(0.3)

    # Move all to same area first
    c1.sendall(build_move_packet(100.0, 100.0, 0.0))
    c2.sendall(build_move_packet(101.0, 101.0, 0.0))
    c3.sendall(build_move_packet(102.0, 102.0, 0.0))
    time.sleep(0.5)

    # Drain
    recv_all_available(c1, timeout=0.5)
    recv_all_available(c2, timeout=0.5)
    recv_all_available(c3, timeout=0.5)

    # 3명 각각 다른 위치로 이동
    c1.sendall(build_move_packet(10.0, 10.0, 0.0))
    c2.sendall(build_move_packet(20.0, 20.0, 0.0))
    c3.sendall(build_move_packet(30.0, 30.0, 0.0))
    time.sleep(0.5)

    # 각 클라이언트가 수신한 브로드캐스트 수집
    pkts1 = recv_all_available(c1, timeout=1)
    pkts2 = recv_all_available(c2, timeout=1)
    pkts3 = recv_all_available(c3, timeout=1)

    # 각각 2개의 MOVE_BROADCAST를 받아야 함 (자기 것 제외)
    bcast1 = [p for p in pkts1 if p[0] == MSG_MOVE_BROADCAST]
    bcast2 = [p for p in pkts2 if p[0] == MSG_MOVE_BROADCAST]
    bcast3 = [p for p in pkts3 if p[0] == MSG_MOVE_BROADCAST]

    test("Player 1 receives 2 broadcasts (from P2 and P3)",
         len(bcast1) == 2,
         f"got {len(bcast1)} broadcasts")

    test("Player 2 receives 2 broadcasts (from P1 and P3)",
         len(bcast2) == 2,
         f"got {len(bcast2)} broadcasts")

    test("Player 3 receives 2 broadcasts (from P1 and P2)",
         len(bcast3) == 2,
         f"got {len(bcast3)} broadcasts")

    # 수신한 브로드캐스트의 좌표 검증
    if len(bcast1) == 2:
        positions = set()
        for _, payload in bcast1:
            _, bx, by, _ = parse_move_broadcast(payload)
            positions.add((round(bx, 1), round(by, 1)))
        test("Player 1 received correct positions",
             (20.0, 20.0) in positions and (30.0, 30.0) in positions,
             f"positions: {positions}")

    # 서버 프로세스 건전성
    test("Server process still running",
         server.poll() is None,
         f"exited with {server.returncode}" if server.poll() is not None else "")

    c1.close()
    c2.close()
    c3.close()

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
    print("  | SESSION 3 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] Position update OK                    |")
    print("  | [O] Broadcast to others OK                |")
    print("  | [O] Self-broadcast blocked OK             |")
    print("  | [O] Multi-player simultaneous move OK     |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 3 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
