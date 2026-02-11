"""
Session 6 Validation Test - Zone (Map) System
==============================================

4단계 검증:
  S6-BUILD        : 빌드 성공
  S6-ZONE-ISOLATE : 다른 맵 → 브로드캐스트 격리
  S6-ZONE-TRANSFER: 맵 전환 → DISAPPEAR/APPEAR
  S6-SPAWN        : 스폰 포인트 배정
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
MSG_ZONE_ENTER = 30
MSG_ZONE_INFO = 31
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload


def build_move_packet(x, y, z):
    return build_packet(MSG_MOVE, struct.pack('<fff', x, y, z))


def build_channel_join_packet(channel_id):
    return build_packet(MSG_CHANNEL_JOIN, struct.pack('<i', channel_id))


def build_zone_enter_packet(zone_id):
    return build_packet(MSG_ZONE_ENTER, struct.pack('<i', zone_id))


def build_pos_query_packet():
    return build_packet(MSG_POS_QUERY)


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


def parse_zone_info(payload):
    """ZONE_INFO: zone_id"""
    if len(payload) < 4:
        return None
    return struct.unpack('<i', payload[:4])[0]


def parse_pos_query(payload):
    """POS_QUERY response: (x, y, z)"""
    if len(payload) < 12:
        return None, None, None
    return struct.unpack('<fff', payload[:12])


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


def setup_player_in_zone(zone_id, channel_id):
    """연결 + 존 입장 + 채널 입장 + 초기 패킷 drain

    순서:
      1. ZONE_ENTER → 스폰 포인트로 위치, dirty=true
      2. 틱 대기 → InterestSystem이 GridCellComponent 생성
      3. CHANNEL_JOIN → 같은 존+채널의 기존 Entity와 APPEAR
    """
    sock = connect()

    # 존 입장 (스폰 포인트로 위치 설정 + dirty)
    sock.sendall(build_zone_enter_packet(zone_id))
    time.sleep(0.5)  # InterestSystem이 GridCellComponent 생성하도록 대기
    drain(sock)  # ZONE_INFO drain

    # 채널 입장
    sock.sendall(build_channel_join_packet(channel_id))
    time.sleep(0.3)
    drain(sock)  # CHANNEL_INFO + APPEAR drain

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
print("  Session 6 Validation Test")
print("  Zone (Map) System")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # ── ZONE_INFO 응답 테스트 ──
    print("--- Zone Enter Confirmation ---")
    print()

    zTest = connect()
    zTest.sendall(build_zone_enter_packet(1))
    time.sleep(0.3)

    pkts = recv_all_available(zTest, timeout=1.5)
    info_pkts = [p for p in pkts if p[0] == MSG_ZONE_INFO]

    test("ZONE_INFO response received",
         len(info_pkts) >= 1,
         f"got {len(info_pkts)} ZONE_INFO packets")

    if info_pkts:
        z_id = parse_zone_info(info_pkts[0][1])
        test("ZONE_INFO contains correct zone_id (1)",
             z_id == 1,
             f"zone_id={z_id}, expected=1")

    zTest.close()
    time.sleep(0.3)
    print()

    # ── S6-ZONE-ISOLATE: 다른 맵은 서로 격리 ──
    print("--- S6-ZONE-ISOLATE: Different zone -> broadcast blocked ---")
    print()

    # A: 맵1 채널1, C: 맵1 채널1 (같은 맵), B: 맵2 채널1 (다른 맵)
    # 맵1 스폰: (100,100) = cell(0,0)
    # 맵2 스폰: (500,500) = cell(1,1)
    # cell(0,0)과 cell(1,1)은 인접 셀 → 존 필터 없으면 보임!
    cA = setup_player_in_zone(1, 1)
    cC = setup_player_in_zone(1, 1)
    cB = setup_player_in_zone(2, 1)
    time.sleep(0.3)
    drain(cA)
    drain(cB)
    drain(cC)

    # A가 같은 셀 내에서 이동
    cA.sendall(build_move_packet(150.0, 150.0, 0.0))
    time.sleep(0.5)

    # C(같은 맵)는 MOVE_BROADCAST 수신해야 함
    pkts_c = recv_all_available(cC, timeout=1.5)
    bcast_c = [p for p in pkts_c if p[0] == MSG_MOVE_BROADCAST]

    test("C receives MOVE_BROADCAST from A (same zone)",
         len(bcast_c) >= 1,
         f"got {len(bcast_c)} broadcasts")

    # B(다른 맵)는 MOVE_BROADCAST 수신하면 안 됨
    pkts_b = recv_all_available(cB, timeout=1.5)
    bcast_b = [p for p in pkts_b if p[0] == MSG_MOVE_BROADCAST]
    appear_b = [p for p in pkts_b if p[0] == MSG_APPEAR]

    test("B does NOT receive MOVE_BROADCAST from A (different zone)",
         len(bcast_b) == 0,
         f"got {len(bcast_b)} broadcasts (expected 0)")

    test("B does NOT receive APPEAR from A (different zone)",
         len(appear_b) == 0,
         f"got {len(appear_b)} APPEAR (expected 0)")

    cA.close()
    cB.close()
    cC.close()
    time.sleep(0.3)
    print()

    # ── S6-ZONE-TRANSFER: 맵 전환 → DISAPPEAR/APPEAR ──
    print("--- S6-ZONE-TRANSFER: Zone transfer -> DISAPPEAR/APPEAR ---")
    print()

    # C: 맵1 채널1, B: 맵2 채널1, A: 맵1 채널1
    # A가 맵1→맵2로 전환하면:
    #   C(맵1)에게 DISAPPEAR(A)
    #   B(맵2)에게 APPEAR(A) (InterestSystem이 다음 틱에)
    cC2 = setup_player_in_zone(1, 1)
    cB2 = setup_player_in_zone(2, 1)
    cA2 = setup_player_in_zone(1, 1)
    time.sleep(0.3)
    drain(cA2)
    drain(cB2)
    drain(cC2)

    # A가 맵1 → 맵2로 전환
    cA2.sendall(build_zone_enter_packet(2))
    time.sleep(1.0)  # 핸들러(DISAPPEAR) + 같은 틱 InterestSystem(APPEAR)

    # C(맵1)는 DISAPPEAR(A) 수신해야 함
    pkts_c2 = recv_all_available(cC2, timeout=1.5)
    disappear_c2 = [p for p in pkts_c2 if p[0] == MSG_DISAPPEAR]

    test("C receives DISAPPEAR when A transfers away from zone 1",
         len(disappear_c2) >= 1,
         f"got {len(disappear_c2)} DISAPPEAR, all types: {[p[0] for p in pkts_c2]}")

    # B(맵2)는 APPEAR(A) 수신해야 함 (InterestSystem → 같은 틱)
    pkts_b2 = recv_all_available(cB2, timeout=1.5)
    appear_b2 = [p for p in pkts_b2 if p[0] == MSG_APPEAR]

    test("B receives APPEAR when A transfers to zone 2",
         len(appear_b2) >= 1,
         f"got {len(appear_b2)} APPEAR, all types: {[p[0] for p in pkts_b2]}")

    # A는 ZONE_INFO(2) + DISAPPEAR(C) + APPEAR(B) 수신
    pkts_a2 = recv_all_available(cA2, timeout=1.5)
    info_a2 = [p for p in pkts_a2 if p[0] == MSG_ZONE_INFO]
    disappear_a2 = [p for p in pkts_a2 if p[0] == MSG_DISAPPEAR]
    appear_a2 = [p for p in pkts_a2 if p[0] == MSG_APPEAR]

    test("A receives ZONE_INFO after zone transfer",
         len(info_a2) >= 1,
         f"got {len(info_a2)} ZONE_INFO")

    if info_a2:
        z = parse_zone_info(info_a2[0][1])
        test("A's ZONE_INFO confirms zone 2",
             z == 2,
             f"zone={z}")

    test("A receives DISAPPEAR (C leaving A's view)",
         len(disappear_a2) >= 1,
         f"got {len(disappear_a2)} DISAPPEAR")

    test("A receives APPEAR (B entering A's view)",
         len(appear_a2) >= 1,
         f"got {len(appear_a2)} APPEAR")
    print()

    # ── S6-SPAWN: 스폰 포인트 검증 ──
    print("--- S6-SPAWN: Spawn point verification ---")
    print()

    # A의 위치를 POS_QUERY로 확인 (맵2 스폰: 500, 500)
    drain(cA2)
    cA2.sendall(build_pos_query_packet())
    time.sleep(0.3)

    pkts_pos = recv_all_available(cA2, timeout=1.5)
    pos_pkts = [p for p in pkts_pos if p[0] == MSG_POS_QUERY]

    test("POS_QUERY response received after zone transfer",
         len(pos_pkts) >= 1,
         f"got {len(pos_pkts)} POS_QUERY responses")

    if pos_pkts:
        px, py, pz = parse_pos_query(pos_pkts[0][1])
        test("Position matches zone 2 spawn point (500, 500)",
             px is not None and abs(px - 500.0) < 0.01 and abs(py - 500.0) < 0.01,
             f"pos=({px}, {py}, {pz}), expected=(500, 500, 0)")
    print()

    # ── 전환 후 브로드캐스트 검증 ──
    print("--- Post-transfer broadcast verification ---")
    print()

    drain(cA2)
    drain(cB2)
    drain(cC2)

    # A가 맵2에서 이동
    cA2.sendall(build_move_packet(550.0, 550.0, 0.0))
    time.sleep(0.5)

    pkts_b3 = recv_all_available(cB2, timeout=1.5)
    bcast_b3 = [p for p in pkts_b3 if p[0] == MSG_MOVE_BROADCAST]

    test("B receives MOVE_BROADCAST from A after zone transfer",
         len(bcast_b3) >= 1,
         f"got {len(bcast_b3)} broadcasts")

    pkts_c3 = recv_all_available(cC2, timeout=1.5)
    bcast_c3 = [p for p in pkts_c3 if p[0] == MSG_MOVE_BROADCAST]

    test("C does NOT receive MOVE_BROADCAST from A after transfer",
         len(bcast_c3) == 0,
         f"got {len(bcast_c3)} broadcasts (expected 0)")

    # 서버 건전성
    test("Server process still running",
         server.poll() is None,
         f"exited with {server.returncode}" if server.poll() is not None else "")

    cA2.close()
    cB2.close()
    cC2.close()

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
    print("  | SESSION 6 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] ZONE_INFO: Enter confirmation OK      |")
    print("  | [O] ISOLATE: Zone isolation OK            |")
    print("  | [O] TRANSFER: Zone transfer OK            |")
    print("  | [O] SPAWN: Spawn point OK                 |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 6 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
