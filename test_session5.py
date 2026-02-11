"""
Session 5 Validation Test - Channel System
============================================

4단계 검증:
  S5-BUILD      : 빌드 성공
  S5-SAME-CH    : 같은 채널 → MOVE_BROADCAST 수신
  S5-DIFF-CH    : 다른 채널 → MOVE_BROADCAST 미수신 (같은 좌표여도!)
  S5-CH-SWITCH  : 채널 이동 → DISAPPEAR/APPEAR 발생
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
MSG_MOVE = 10
MSG_MOVE_BROADCAST = 11
MSG_POS_QUERY = 12
MSG_APPEAR = 13
MSG_DISAPPEAR = 14
MSG_CHANNEL_JOIN = 20
MSG_CHANNEL_INFO = 22
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload


def build_move_packet(x, y, z):
    return build_packet(MSG_MOVE, struct.pack('<fff', x, y, z))


def build_channel_join_packet(channel_id):
    return build_packet(MSG_CHANNEL_JOIN, struct.pack('<i', channel_id))


def recv_packet(sock, timeout=5):
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
    try:
        return recv_packet(sock, timeout)
    except socket.timeout:
        return None, None


def recv_all_available(sock, timeout=1.0):
    packets = []
    while True:
        msg_type, payload = try_recv_packet(sock, timeout)
        if msg_type is None:
            break
        packets.append((msg_type, payload))
        timeout = 0.3
    return packets


def parse_entity_pos(payload):
    """APPEAR/MOVE_BROADCAST: (entity_id, x, y, z)"""
    if len(payload) < 20:
        return None, None, None, None
    eid = struct.unpack('<Q', payload[:8])[0]
    x, y, z = struct.unpack('<fff', payload[8:20])
    return eid, x, y, z


def parse_disappear(payload):
    """DISAPPEAR: entity_id"""
    if len(payload) < 8:
        return None
    return struct.unpack('<Q', payload[:8])[0]


def parse_channel_info(payload):
    """CHANNEL_INFO: channel_id"""
    if len(payload) < 4:
        return None
    return struct.unpack('<i', payload[:4])[0]


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


def drain(sock):
    """소켓의 남은 패킷을 비움"""
    recv_all_available(sock, timeout=0.3)


def setup_player(channel_id, x, y, z):
    """연결 + 채널 입장 + 이동 + 초기 패킷 drain"""
    sock = connect()
    sock.sendall(build_channel_join_packet(channel_id))
    time.sleep(0.3)
    drain(sock)  # CHANNEL_INFO drain
    sock.sendall(build_move_packet(x, y, z))
    time.sleep(0.5)
    drain(sock)  # APPEAR + MOVE_BROADCAST drain
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
print("  Session 5 Validation Test")
print("  Channel System")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # ── CHANNEL_INFO 응답 테스트 ──
    print("--- Channel Join Confirmation ---")
    print()

    cTest = connect()
    cTest.sendall(build_channel_join_packet(1))
    time.sleep(0.3)

    pkts = recv_all_available(cTest, timeout=1.5)
    info_pkts = [p for p in pkts if p[0] == MSG_CHANNEL_INFO]

    test("CHANNEL_INFO response received",
         len(info_pkts) >= 1,
         f"got {len(info_pkts)} CHANNEL_INFO packets")

    if info_pkts:
        ch_id = parse_channel_info(info_pkts[0][1])
        test("CHANNEL_INFO contains correct channel_id (1)",
             ch_id == 1,
             f"channel_id={ch_id}, expected=1")

    cTest.close()
    time.sleep(0.3)
    print()

    # ── S5-SAME-CH: 같은 채널 → MOVE_BROADCAST 수신 ──
    print("--- S5-SAME-CH: Same channel -> broadcast received ---")
    print()

    cA = setup_player(1, 10.0, 10.0, 0.0)
    cB = setup_player(1, 20.0, 20.0, 0.0)
    time.sleep(0.3)
    drain(cA)  # B 셋업 중 발생한 APPEAR 등 정리
    drain(cB)

    # A가 같은 셀 내에서 이동
    cA.sendall(build_move_packet(50.0, 50.0, 0.0))
    time.sleep(0.5)

    pkts_b = recv_all_available(cB, timeout=1.5)
    bcast_b = [p for p in pkts_b if p[0] == MSG_MOVE_BROADCAST]

    test("B receives MOVE_BROADCAST from A (same channel)",
         len(bcast_b) >= 1,
         f"got {len(bcast_b)} broadcasts, all types: {[p[0] for p in pkts_b]}")

    if bcast_b:
        eid, bx, by, bz = parse_entity_pos(bcast_b[0][1])
        test("Broadcast position matches A's move (50,50)",
             abs(bx - 50.0) < 0.01 and abs(by - 50.0) < 0.01,
             f"pos=({bx}, {by})")

    cA.close()
    cB.close()
    time.sleep(0.3)
    print()

    # ── S5-DIFF-CH: 다른 채널 → MOVE_BROADCAST 미수신 ──
    print("--- S5-DIFF-CH: Different channel -> broadcast NOT received ---")
    print()

    cA2 = setup_player(1, 10.0, 10.0, 0.0)
    cC = setup_player(2, 20.0, 20.0, 0.0)  # 같은 좌표지만 다른 채널!
    time.sleep(0.3)
    drain(cA2)
    drain(cC)

    # A가 이동
    cA2.sendall(build_move_packet(50.0, 50.0, 0.0))
    time.sleep(0.5)

    pkts_c = recv_all_available(cC, timeout=1.5)
    bcast_c = [p for p in pkts_c if p[0] == MSG_MOVE_BROADCAST]
    appear_c = [p for p in pkts_c if p[0] == MSG_APPEAR]

    test("C does NOT receive MOVE_BROADCAST from A (different channel)",
         len(bcast_c) == 0,
         f"got {len(bcast_c)} broadcasts (expected 0)")

    test("C does NOT receive APPEAR from A (different channel)",
         len(appear_c) == 0,
         f"got {len(appear_c)} APPEAR (expected 0)")

    cA2.close()
    cC.close()
    time.sleep(0.3)
    print()

    # ── S5-CH-SWITCH: 채널 이동 → DISAPPEAR/APPEAR ──
    print("--- S5-CH-SWITCH: Channel switch -> DISAPPEAR/APPEAR ---")
    print()

    # A: 채널 1, E: 채널 1, D: 채널 2 — 모두 같은 셀(0,0) 근처
    cA3 = setup_player(1, 100.0, 100.0, 0.0)
    cE  = setup_player(1, 150.0, 150.0, 0.0)
    cD  = setup_player(2, 200.0, 200.0, 0.0)
    time.sleep(0.3)
    drain(cA3)
    drain(cE)
    drain(cD)

    # A가 채널 1 → 채널 2로 이동
    cA3.sendall(build_channel_join_packet(2))
    time.sleep(0.5)

    # E는 DISAPPEAR(A) 수신해야 함 (A가 채널1을 떠남)
    pkts_e = recv_all_available(cE, timeout=1.5)
    disappear_e = [p for p in pkts_e if p[0] == MSG_DISAPPEAR]

    test("E receives DISAPPEAR when A switches away from channel 1",
         len(disappear_e) >= 1,
         f"got {len(disappear_e)} DISAPPEAR, all types: {[p[0] for p in pkts_e]}")

    # D는 APPEAR(A) 수신해야 함 (A가 채널2에 합류)
    pkts_d = recv_all_available(cD, timeout=1.5)
    appear_d = [p for p in pkts_d if p[0] == MSG_APPEAR]

    test("D receives APPEAR when A switches to channel 2",
         len(appear_d) >= 1,
         f"got {len(appear_d)} APPEAR, all types: {[p[0] for p in pkts_d]}")

    # A는 CHANNEL_INFO(2) + DISAPPEAR(E) + APPEAR(D) 수신
    pkts_a3 = recv_all_available(cA3, timeout=1.5)
    info_a3 = [p for p in pkts_a3 if p[0] == MSG_CHANNEL_INFO]
    disappear_a3 = [p for p in pkts_a3 if p[0] == MSG_DISAPPEAR]
    appear_a3 = [p for p in pkts_a3 if p[0] == MSG_APPEAR]

    test("A receives CHANNEL_INFO after switch",
         len(info_a3) >= 1,
         f"got {len(info_a3)} CHANNEL_INFO")

    if info_a3:
        ch = parse_channel_info(info_a3[0][1])
        test("A's CHANNEL_INFO confirms channel 2",
             ch == 2,
             f"channel={ch}")

    test("A receives DISAPPEAR (E leaving A's view)",
         len(disappear_a3) >= 1,
         f"got {len(disappear_a3)} DISAPPEAR")

    test("A receives APPEAR (D entering A's view)",
         len(appear_a3) >= 1,
         f"got {len(appear_a3)} APPEAR")

    # ── 채널 전환 후 브로드캐스트 검증 ──
    print()
    print("--- Post-switch broadcast verification ---")
    print()

    drain(cA3)
    drain(cD)
    drain(cE)

    cA3.sendall(build_move_packet(120.0, 120.0, 0.0))
    time.sleep(0.5)

    pkts_d2 = recv_all_available(cD, timeout=1.5)
    bcast_d2 = [p for p in pkts_d2 if p[0] == MSG_MOVE_BROADCAST]

    test("D receives MOVE_BROADCAST from A after channel switch",
         len(bcast_d2) >= 1,
         f"got {len(bcast_d2)} broadcasts")

    pkts_e2 = recv_all_available(cE, timeout=1.5)
    bcast_e2 = [p for p in pkts_e2 if p[0] == MSG_MOVE_BROADCAST]

    test("E does NOT receive MOVE_BROADCAST from A after switch",
         len(bcast_e2) == 0,
         f"got {len(bcast_e2)} broadcasts (expected 0)")

    # 서버 건전성
    test("Server process still running",
         server.poll() is None,
         f"exited with {server.returncode}" if server.poll() is not None else "")

    cA3.close()
    cD.close()
    cE.close()

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
    print("  | SESSION 5 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] CHANNEL_INFO: Join confirmation OK    |")
    print("  | [O] SAME-CH: Same channel broadcast OK   |")
    print("  | [O] DIFF-CH: Cross-channel blocked OK    |")
    print("  | [O] CH-SWITCH: Channel switch OK         |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 5 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
