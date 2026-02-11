"""
Session 8 Validation Test - Ghost Entity System
=================================================

4단계 검증:
  S8-BUILD         : 빌드 성공
  S8-GHOST-CREATE  : 서버 경계 접근 시 Ghost 생성
  S8-GHOST-SYNC    : Ghost 위치 동기화
  S8-GHOST-DESTROY : 경계 이탈 시 Ghost 파괴
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

# -- 패킷 프로토콜 --
HEADER_SIZE = 6
MSG_MOVE = 10
MSG_MOVE_BROADCAST = 11
MSG_APPEAR = 13
MSG_DISAPPEAR = 14
MSG_CHANNEL_JOIN = 20
MSG_ZONE_ENTER = 30
MSG_GHOST_QUERY = 50
MSG_GHOST_INFO = 51
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


def build_ghost_query_packet():
    return build_packet(MSG_GHOST_QUERY)


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


def parse_ghost_info(payload):
    """GHOST_INFO: ghost_count"""
    if len(payload) < 4:
        return None
    return struct.unpack('<i', payload[:4])[0]


def parse_entity_pos(payload):
    """APPEAR/MOVE_BROADCAST: (entity_id, x, y, z)"""
    if len(payload) < 20:
        return None, None, None, None
    eid = struct.unpack('<Q', payload[:8])[0]
    x, y, z = struct.unpack('<fff', payload[8:20])
    return eid, x, y, z


def query_ghost_count(sock):
    """Ghost 수 조회"""
    drain(sock)
    sock.sendall(build_ghost_query_packet())
    time.sleep(0.3)
    pkts = recv_all_available(sock, timeout=1.5)
    info_pkts = [p for p in pkts if p[0] == MSG_GHOST_INFO]
    if info_pkts:
        return parse_ghost_info(info_pkts[0][1])
    return None


# -- 서버 관리 --

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
    recv_all_available(sock, timeout=0.3)


def setup_player_in_zone(zone_id, channel_id):
    """연결 + 존 입장 + 채널 입장 + 초기 패킷 drain"""
    sock = connect()
    sock.sendall(build_zone_enter_packet(zone_id))
    time.sleep(0.5)
    drain(sock)
    sock.sendall(build_channel_join_packet(channel_id))
    time.sleep(0.3)
    drain(sock)
    return sock


# -- 테스트 프레임워크 --

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


# ============================================
print("=" * 60)
print("  Session 8 Validation Test")
print("  Ghost Entity System")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # -- S8-GHOST-CREATE: Ghost 생성 --
    print("--- S8-GHOST-CREATE: Boundary approach -> Ghost creation ---")
    print()

    # B: Zone 2, Channel 1 (스폰 500,500 -> 셀 1,1)
    # A: Zone 1, Channel 1 (스폰 100,100 -> 셀 0,0)
    cB = setup_player_in_zone(2, 1)
    cA = setup_player_in_zone(1, 1)
    time.sleep(0.3)
    drain(cA)
    drain(cB)

    # 초기 상태: Ghost 없음
    gc = query_ghost_count(cA)
    test("Initial ghost count is 0",
         gc == 0,
         f"ghost_count={gc}")

    # A가 경계 근처로 이동 (350 > 300 = 경계)
    cA.sendall(build_move_packet(350.0, 100.0, 0.0))
    time.sleep(0.8)  # GhostSystem 틱 대기

    # Ghost가 생성되었는지 확인
    gc = query_ghost_count(cA)
    test("Ghost created when A enters boundary (count=1)",
         gc == 1,
         f"ghost_count={gc}")

    # B(Zone 2)가 Ghost의 APPEAR를 수신했는지
    # drain 후 ghost_query 패킷은 이미 처리됨, B에게 온 패킷 확인
    # B의 패킷을 다시 확인 (ghost 생성 시점에 APPEAR가 왔을 것)
    # → ghost_query 이전에 이미 왔을 수 있으므로, setup 이후 누적 패킷 확인
    drain(cB)
    # B가 APPEAR를 이미 받았을 수 있음. ghost 생성 시점 패킷은 이미 drain됨
    # 다시 테스트: A를 경계에서 빼고, 다시 넣어서 APPEAR를 직접 캡처

    # -- APPEAR 직접 캡처 테스트 --
    # A를 안전 지역으로 이동 → Ghost 파괴
    cA.sendall(build_move_packet(100.0, 100.0, 0.0))
    time.sleep(0.8)
    drain(cA)
    drain(cB)

    # A를 다시 경계로 → Ghost 재생성 → B에게 APPEAR
    cA.sendall(build_move_packet(350.0, 100.0, 0.0))
    time.sleep(0.8)

    pkts_b = recv_all_available(cB, timeout=1.5)
    appear_b = [p for p in pkts_b if p[0] == MSG_APPEAR]

    test("B receives APPEAR when ghost is created",
         len(appear_b) >= 1,
         f"got {len(appear_b)} APPEAR, types: {[p[0] for p in pkts_b]}")

    if appear_b:
        eid, gx, gy, gz = parse_entity_pos(appear_b[0][1])
        test("Ghost APPEAR position matches A's position (350, 100)",
             gx is not None and abs(gx - 350.0) < 0.01 and abs(gy - 100.0) < 0.01,
             f"pos=({gx}, {gy}, {gz})")

    print()

    # -- S8-GHOST-SYNC: Ghost 위치 동기화 --
    print("--- S8-GHOST-SYNC: Ghost position sync ---")
    print()

    drain(cB)

    # A가 경계 내에서 이동 (400 > 300, 여전히 경계)
    cA.sendall(build_move_packet(400.0, 150.0, 0.0))
    time.sleep(0.8)

    pkts_b2 = recv_all_available(cB, timeout=1.5)
    bcast_b = [p for p in pkts_b2 if p[0] == MSG_MOVE_BROADCAST]

    test("B receives MOVE_BROADCAST when ghost position syncs",
         len(bcast_b) >= 1,
         f"got {len(bcast_b)} MOVE_BROADCAST")

    if bcast_b:
        eid, bx, by, bz = parse_entity_pos(bcast_b[0][1])
        test("Ghost synced position matches A (400, 150)",
             bx is not None and abs(bx - 400.0) < 0.01 and abs(by - 150.0) < 0.01,
             f"pos=({bx}, {by}, {bz})")

    print()

    # -- S8-GHOST-DESTROY: Ghost 파괴 --
    print("--- S8-GHOST-DESTROY: Boundary leave -> Ghost destruction ---")
    print()

    drain(cB)

    # A가 안전 지역으로 이동 (100 < 300, 경계 아님)
    cA.sendall(build_move_packet(100.0, 100.0, 0.0))
    time.sleep(0.8)

    # Ghost가 파괴되었는지 확인
    gc = query_ghost_count(cA)
    test("Ghost destroyed when A leaves boundary (count=0)",
         gc == 0,
         f"ghost_count={gc}")

    # B가 DISAPPEAR를 수신했는지
    pkts_b3 = recv_all_available(cB, timeout=1.5)
    disappear_b = [p for p in pkts_b3 if p[0] == MSG_DISAPPEAR]

    test("B receives DISAPPEAR when ghost is destroyed",
         len(disappear_b) >= 1,
         f"got {len(disappear_b)} DISAPPEAR")

    print()

    # -- Disconnect cleanup --
    print("--- Disconnect cleanup: Ghost auto-destroyed ---")
    print()

    drain(cA)
    drain(cB)

    # A를 다시 경계로 → Ghost 생성
    cA.sendall(build_move_packet(350.0, 100.0, 0.0))
    time.sleep(0.8)

    gc = query_ghost_count(cB)
    test("Ghost re-created when A returns to boundary (count=1)",
         gc == 1,
         f"ghost_count={gc}")

    # A 연결 끊기
    cA.close()
    time.sleep(1.5)  # NetworkSystem이 disconnect 처리 + GhostSystem이 정리

    # B에서 ghost count 조회
    gc = query_ghost_count(cB)
    test("Ghost auto-destroyed after A disconnects (count=0)",
         gc == 0,
         f"ghost_count={gc}")

    print()

    # -- Channel isolation --
    print("--- Channel isolation: Different channel cannot see ghost ---")
    print()

    # C: Zone 2, Channel 2 (다른 채널)
    cC = setup_player_in_zone(2, 2)
    # A2: Zone 1, Channel 1 (새 연결)
    cA2 = setup_player_in_zone(1, 1)
    time.sleep(0.3)
    drain(cA2)
    drain(cB)
    drain(cC)

    # A2를 경계로 → Ghost 생성 (zone 2, channel 1)
    cA2.sendall(build_move_packet(350.0, 100.0, 0.0))
    time.sleep(0.8)

    # B(ch 1)는 APPEAR 수신
    pkts_b4 = recv_all_available(cB, timeout=1.5)
    appear_b4 = [p for p in pkts_b4 if p[0] == MSG_APPEAR]

    test("B (channel 1) sees ghost APPEAR",
         len(appear_b4) >= 1,
         f"got {len(appear_b4)} APPEAR")

    # C(ch 2)는 APPEAR 미수신
    pkts_c = recv_all_available(cC, timeout=1.5)
    appear_c = [p for p in pkts_c if p[0] == MSG_APPEAR]

    test("C (channel 2) does NOT see ghost APPEAR",
         len(appear_c) == 0,
         f"got {len(appear_c)} APPEAR (expected 0)")

    # 서버 건전성
    test("Server process still running",
         server.poll() is None,
         f"exited with {server.returncode}" if server.poll() is not None else "")

    cA2.close()
    cB.close()
    cC.close()

except Exception as e:
    print(f"\n  [ERROR] Exception: {e}")
    import traceback
    traceback.print_exc()
    failed += 1

finally:
    print()
    stop_server(server)

# -- 결과 --
print()
print("=" * 60)
print(f"  Result: {passed}/{total} PASSED, {failed} FAILED")
print()
if failed == 0:
    print("  +-------------------------------------------+")
    print("  | SESSION 8 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] GHOST-CREATE: Boundary detection OK   |")
    print("  | [O] GHOST-SYNC: Position sync OK          |")
    print("  | [O] GHOST-DESTROY: Cleanup OK             |")
    print("  | [O] CHANNEL: Isolation OK                 |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 8 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
