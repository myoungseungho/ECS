"""
Session 7 Validation Test - Handoff System
============================================

3단계 검증:
  S7-BUILD        : 빌드 성공
  S7-SERIALIZE    : Component 직렬화/역직렬화
  S7-HANDOFF      : 서버 간 이관 시뮬레이션
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
MSG_HANDOFF_REQUEST = 40
MSG_HANDOFF_DATA = 41
MSG_HANDOFF_RESTORE = 42
MSG_HANDOFF_RESULT = 43
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


def build_handoff_request_packet():
    return build_packet(MSG_HANDOFF_REQUEST)


def build_handoff_restore_packet(serialized_data):
    return build_packet(MSG_HANDOFF_RESTORE, serialized_data)


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


def parse_handoff_result(payload):
    """HANDOFF_RESULT: (zone_id, channel_id, x, y, z)"""
    if len(payload) < 20:
        return None, None, None, None, None
    zone = struct.unpack('<i', payload[:4])[0]
    ch = struct.unpack('<i', payload[4:8])[0]
    x, y, z = struct.unpack('<fff', payload[8:20])
    return zone, ch, x, y, z


def parse_serialized_data(data):
    """직렬화 데이터 파싱: {type_id: (data_size, raw_bytes)}"""
    if len(data) < 2:
        return 0, {}
    count = struct.unpack('<H', data[:2])[0]
    offset = 2
    components = {}
    for _ in range(count):
        if offset + 4 > len(data):
            break
        type_id, data_size = struct.unpack('<HH', data[offset:offset+4])
        offset += 4
        if offset + data_size > len(data):
            break
        components[type_id] = (data_size, data[offset:offset+data_size])
        offset += data_size
    return count, components


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
print("  Session 7 Validation Test")
print("  Handoff System")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # -- S7-SERIALIZE: 직렬화 데이터 검증 --
    print("--- S7-SERIALIZE: Serialization format verification ---")
    print()

    # A: 맵1 채널1 위치(150, 250, 0)
    cA = setup_player_in_zone(1, 1)
    cA.sendall(build_move_packet(150.0, 250.0, 0.0))
    time.sleep(0.5)
    drain(cA)

    # 핸드오프 요청 → HANDOFF_DATA 수신
    cA.sendall(build_handoff_request_packet())
    time.sleep(0.5)

    pkts = recv_all_available(cA, timeout=1.5)
    data_pkts = [p for p in pkts if p[0] == MSG_HANDOFF_DATA]

    test("HANDOFF_DATA received after HANDOFF_REQUEST",
         len(data_pkts) >= 1,
         f"got {len(data_pkts)} HANDOFF_DATA packets")

    serialized_bytes = b""
    if data_pkts:
        serialized_bytes = data_pkts[0][1]
        count, components = parse_serialized_data(serialized_bytes)

        test("Serialized data contains 3 components (Position, Zone, Channel)",
             count == 3,
             f"count={count}, expected=3")

        # Position (type=1, 12 bytes)
        if 1 in components:
            psize, pdata = components[1]
            test("Position component size is 12 bytes",
                 psize == 12,
                 f"size={psize}")

            if psize >= 12:
                px, py, pz = struct.unpack('<fff', pdata[:12])
                test("Position values match (150, 250, 0)",
                     abs(px - 150.0) < 0.01 and abs(py - 250.0) < 0.01 and abs(pz) < 0.01,
                     f"pos=({px}, {py}, {pz})")
        else:
            test("Position component present in serialized data", False, "type_id=1 not found")
            test("Position values match", False, "skipped")

        # Zone (type=2, 4 bytes)
        if 2 in components:
            zsize, zdata = components[2]
            zone_val = struct.unpack('<i', zdata[:4])[0]
            test("Zone value matches (1)",
                 zone_val == 1,
                 f"zone={zone_val}")
        else:
            test("Zone component present in serialized data", False, "type_id=2 not found")

        # Channel (type=3, 4 bytes)
        if 3 in components:
            csize, cdata = components[3]
            ch_val = struct.unpack('<i', cdata[:4])[0]
            test("Channel value matches (1)",
                 ch_val == 1,
                 f"channel={ch_val}")
        else:
            test("Channel component present in serialized data", False, "type_id=3 not found")

    cA.close()
    time.sleep(0.3)
    print()

    # -- S7-HANDOFF: 핸드오프 시뮬레이션 --
    print("--- S7-HANDOFF: Handoff simulation (request + restore) ---")
    print()

    # B: 맵2 채널1 (이웃 역할 - 복원 후 APPEAR 확인용)
    # A: 맵2 채널1 위치(550, 550, 0) → 핸드오프 → 복원
    cB = setup_player_in_zone(2, 1)
    cA2 = setup_player_in_zone(2, 1)
    cA2.sendall(build_move_packet(550.0, 550.0, 0.0))
    time.sleep(0.5)
    drain(cA2)
    drain(cB)

    # A가 핸드오프 요청
    cA2.sendall(build_handoff_request_packet())
    time.sleep(0.5)

    # A는 HANDOFF_DATA 수신
    pkts_a = recv_all_available(cA2, timeout=1.5)
    data_a = [p for p in pkts_a if p[0] == MSG_HANDOFF_DATA]

    test("A receives HANDOFF_DATA",
         len(data_a) >= 1,
         f"got {len(data_a)}")

    # B는 DISAPPEAR 수신
    pkts_b = recv_all_available(cB, timeout=1.5)
    disappear_b = [p for p in pkts_b if p[0] == MSG_DISAPPEAR]

    test("B receives DISAPPEAR when A does handoff",
         len(disappear_b) >= 1,
         f"got {len(disappear_b)} DISAPPEAR")

    # A가 직렬화 데이터로 복원 (같은 연결에서 시뮬레이션)
    if data_a:
        restore_data = data_a[0][1]
        drain(cA2)
        drain(cB)

        cA2.sendall(build_handoff_restore_packet(restore_data))
        time.sleep(1.0)  # InterestSystem 틱 대기

        # A는 HANDOFF_RESULT 수신
        pkts_a2 = recv_all_available(cA2, timeout=1.5)
        result_a = [p for p in pkts_a2 if p[0] == MSG_HANDOFF_RESULT]

        test("A receives HANDOFF_RESULT after restore",
             len(result_a) >= 1,
             f"got {len(result_a)}")

        if result_a:
            zone, ch, rx, ry, rz = parse_handoff_result(result_a[0][1])
            test("Restored zone matches original (2)",
                 zone == 2,
                 f"zone={zone}")
            test("Restored channel matches original (1)",
                 ch == 1,
                 f"channel={ch}")
            test("Restored position matches original (550, 550, 0)",
                 rx is not None and abs(rx - 550.0) < 0.01 and abs(ry - 550.0) < 0.01,
                 f"pos=({rx}, {ry}, {rz})")

        # B는 APPEAR 수신 (InterestSystem이 다음 틱에)
        pkts_b2 = recv_all_available(cB, timeout=1.5)
        appear_b = [p for p in pkts_b2 if p[0] == MSG_APPEAR]

        test("B receives APPEAR after A restores",
             len(appear_b) >= 1,
             f"got {len(appear_b)} APPEAR, types: {[p[0] for p in pkts_b2]}")

        # 복원 후 POS_QUERY로 위치 확인
        drain(cA2)
        cA2.sendall(build_pos_query_packet())
        time.sleep(0.3)
        pkts_pos = recv_all_available(cA2, timeout=1.5)
        pos_pkts = [p for p in pkts_pos if p[0] == MSG_POS_QUERY]

        if pos_pkts:
            qx, qy, qz = struct.unpack('<fff', pos_pkts[0][1][:12])
            test("POS_QUERY confirms restored position",
                 abs(qx - 550.0) < 0.01 and abs(qy - 550.0) < 0.01,
                 f"pos=({qx}, {qy}, {qz})")
        else:
            test("POS_QUERY confirms restored position", False, "no response")

    print()

    # -- 복원 후 브로드캐스트 동작 확인 --
    print("--- Post-restore broadcast verification ---")
    print()

    drain(cA2)
    drain(cB)

    # A가 복원 후 이동 → B가 MOVE_BROADCAST 수신해야 함
    cA2.sendall(build_move_packet(600.0, 600.0, 0.0))
    time.sleep(0.5)

    pkts_b3 = recv_all_available(cB, timeout=1.5)
    bcast_b = [p for p in pkts_b3 if p[0] == MSG_MOVE_BROADCAST]

    test("B receives MOVE_BROADCAST from A after restore",
         len(bcast_b) >= 1,
         f"got {len(bcast_b)} broadcasts")

    # 서버 건전성
    test("Server process still running",
         server.poll() is None,
         f"exited with {server.returncode}" if server.poll() is not None else "")

    cA2.close()
    cB.close()

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
    print("  | SESSION 7 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] SERIALIZE: Data format OK             |")
    print("  | [O] HANDOFF: Request + Restore OK         |")
    print("  | [O] NEIGHBOR: DISAPPEAR/APPEAR OK         |")
    print("  | [O] POST-RESTORE: Broadcast OK            |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 7 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
