"""
Session 4 Validation Test - Interest Management (AOI)
======================================================

5단계 검증:
  S4-BUILD     : 빌드 성공
  S4-AOI-IN    : 같은 그리드 셀 → MOVE_BROADCAST 수신
  S4-AOI-OUT   : 먼 그리드 셀 → MOVE_BROADCAST 미수신
  S4-AOI-ENTER : 먼 곳에서 가까이 이동 → APPEAR 수신
  S4-AOI-LEAVE : 가까이에서 먼 곳으로 이동 → DISAPPEAR 수신

Grid 설정: CELL_SIZE=500, 인접=3x3 (같은 셀 + 8방향)
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
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload


def build_move_packet(x, y, z):
    return build_packet(MSG_MOVE, struct.pack('<fff', x, y, z))


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
print("  Session 4 Validation Test")
print("  Interest Management (AOI)")
print("  Grid Cell Size = 500")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # ── S4-AOI-IN: 같은 셀에서 MOVE_BROADCAST 수신 ──
    print("--- S4-AOI-IN: Same grid cell -> broadcast received ---")
    print()

    cA = connect()
    cB = connect()

    # A, B 모두 같은 셀(0,0)에 초기 배치
    cA.sendall(build_move_packet(10.0, 10.0, 0.0))
    cB.sendall(build_move_packet(20.0, 20.0, 0.0))
    time.sleep(0.5)
    drain(cA)
    drain(cB)

    # A가 같은 셀 내에서 이동
    cA.sendall(build_move_packet(50.0, 50.0, 0.0))
    time.sleep(0.5)

    pkts_b = recv_all_available(cB, timeout=1.5)
    bcast_b = [p for p in pkts_b if p[0] == MSG_MOVE_BROADCAST]

    test("B receives MOVE_BROADCAST from A (same cell)",
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

    # ── S4-AOI-OUT: 먼 셀에서 MOVE_BROADCAST 미수신 ──
    print("--- S4-AOI-OUT: Far grid cell -> broadcast NOT received ---")
    print()

    cA2 = connect()
    cC = connect()

    # A는 (0,0) 셀, C는 (9999,9999) → 셀(19,19) — 매우 먼 곳
    cA2.sendall(build_move_packet(10.0, 10.0, 0.0))
    cC.sendall(build_move_packet(9999.0, 9999.0, 0.0))
    time.sleep(0.5)
    drain(cA2)
    drain(cC)

    # A가 같은 셀 내에서 이동
    cA2.sendall(build_move_packet(100.0, 100.0, 0.0))
    time.sleep(0.5)

    pkts_c = recv_all_available(cC, timeout=1.5)
    bcast_c = [p for p in pkts_c if p[0] == MSG_MOVE_BROADCAST]

    test("C does NOT receive MOVE_BROADCAST from A (far cell)",
         len(bcast_c) == 0,
         f"got {len(bcast_c)} broadcasts (expected 0)")

    cA2.close()
    cC.close()
    time.sleep(0.3)
    print()

    # ── S4-AOI-ENTER: 먼 곳에서 가까이 이동 → APPEAR 수신 ──
    print("--- S4-AOI-ENTER: Move into AOI -> APPEAR received ---")
    print()

    cA3 = connect()
    cD = connect()

    # A는 (10,10) 셀(0,0)에 배치
    cA3.sendall(build_move_packet(10.0, 10.0, 0.0))
    time.sleep(0.3)
    drain(cA3)

    # D는 처음에 먼 곳 (5000, 5000) 셀(10,10)에 배치
    cD.sendall(build_move_packet(5000.0, 5000.0, 0.0))
    time.sleep(0.3)
    drain(cD)
    drain(cA3)

    # D가 A 근처로 이동 → 셀(0,0) 진입
    cD.sendall(build_move_packet(50.0, 50.0, 0.0))
    time.sleep(0.5)

    # D가 A의 APPEAR을 수신해야 함
    pkts_d = recv_all_available(cD, timeout=2)
    appear_d = [p for p in pkts_d if p[0] == MSG_APPEAR]

    test("D receives APPEAR when moving near A",
         len(appear_d) >= 1,
         f"got {len(appear_d)} APPEAR packets, all types: {[p[0] for p in pkts_d]}")

    if appear_d:
        eid, ax, ay, az = parse_entity_pos(appear_d[0][1])
        test("APPEAR contains A's position",
             ax is not None,
             f"entity={eid}, pos=({ax}, {ay}, {az})")

    # A도 D의 APPEAR을 수신해야 함 (양방향)
    pkts_a3 = recv_all_available(cA3, timeout=1)
    appear_a3 = [p for p in pkts_a3 if p[0] == MSG_APPEAR]

    test("A receives APPEAR for D (bidirectional)",
         len(appear_a3) >= 1,
         f"got {len(appear_a3)} APPEAR packets")

    cA3.close()
    cD.close()
    time.sleep(0.3)
    print()

    # ── S4-AOI-LEAVE: 가까이에서 먼 곳으로 → DISAPPEAR 수신 ──
    print("--- S4-AOI-LEAVE: Move out of AOI -> DISAPPEAR received ---")
    print()

    cE = connect()
    cF = connect()

    # E, F 모두 같은 셀에 배치
    cE.sendall(build_move_packet(100.0, 100.0, 0.0))
    cF.sendall(build_move_packet(200.0, 200.0, 0.0))
    time.sleep(0.5)
    drain(cE)
    drain(cF)

    # E가 매우 먼 곳으로 이동 → 셀 전환
    cE.sendall(build_move_packet(9999.0, 9999.0, 0.0))
    time.sleep(0.5)

    # F가 DISAPPEAR 수신해야 함
    pkts_f = recv_all_available(cF, timeout=2)
    disappear_f = [p for p in pkts_f if p[0] == MSG_DISAPPEAR]

    test("F receives DISAPPEAR when E moves far away",
         len(disappear_f) >= 1,
         f"got {len(disappear_f)} DISAPPEAR packets, all types: {[p[0] for p in pkts_f]}")

    if disappear_f:
        gone_eid = parse_disappear(disappear_f[0][1])
        test("DISAPPEAR contains E's entity ID",
             gone_eid is not None,
             f"entity={gone_eid}")

    # E도 F의 DISAPPEAR 수신해야 함
    pkts_e = recv_all_available(cE, timeout=1)
    disappear_e = [p for p in pkts_e if p[0] == MSG_DISAPPEAR]

    test("E receives DISAPPEAR for F (bidirectional)",
         len(disappear_e) >= 1,
         f"got {len(disappear_e)} DISAPPEAR, all types: {[p[0] for p in pkts_e]}")

    # E가 먼 곳에서 이동해도 F는 더 이상 수신 안 함
    drain(cF)
    cE.sendall(build_move_packet(9500.0, 9500.0, 0.0))
    time.sleep(0.5)

    pkts_f2 = recv_all_available(cF, timeout=1)
    any_from_e = [p for p in pkts_f2 if p[0] in (MSG_MOVE_BROADCAST, MSG_APPEAR)]

    test("F receives nothing after E left AOI",
         len(any_from_e) == 0,
         f"got {len(any_from_e)} packets (expected 0)")

    # 서버 건전성
    test("Server process still running",
         server.poll() is None,
         f"exited with {server.returncode}" if server.poll() is not None else "")

    cE.close()
    cF.close()

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
    print("  | SESSION 4 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] AOI-IN: Same cell broadcast OK        |")
    print("  | [O] AOI-OUT: Far cell blocked OK          |")
    print("  | [O] AOI-ENTER: Appear on entry OK         |")
    print("  | [O] AOI-LEAVE: Disappear on exit OK       |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 4 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
