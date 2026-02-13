"""
Session 35: Model C Movement Validation Tests
==============================================
Tests: speed hack detection, zone boundary enforcement,
       invalid coordinate rejection, position correction packets.
"""
import socket, struct, time, subprocess, os, signal, sys

SERVER_EXE = os.path.join(os.path.dirname(__file__), "Servers", "FieldServer", "FieldServer.exe")
HOST, PORT = "127.0.0.1", 7777
HEADER_SIZE = 6

# MsgType IDs
MOVE = 10
MOVE_BROADCAST = 11
POS_QUERY = 12
POSITION_CORRECTION = 15
LOGIN = 60
LOGIN_RESULT = 61
CHAR_LIST_REQ = 62
CHAR_LIST_RESP = 63
CHAR_SELECT = 64
ENTER_GAME = 65
ZONE_ENTER = 30
ZONE_INFO = 31

def build_packet(msg_type, payload=b""):
    length = HEADER_SIZE + len(payload)
    return struct.pack("<IH", length, msg_type) + payload

def recv_packet(sock, timeout=3.0):
    sock.settimeout(timeout)
    try:
        header = b""
        while len(header) < HEADER_SIZE:
            chunk = sock.recv(HEADER_SIZE - len(header))
            if not chunk:
                return None, None
            header += chunk
        length, msg_type = struct.unpack("<IH", header)
        payload_len = length - HEADER_SIZE
        payload = b""
        while len(payload) < payload_len:
            chunk = sock.recv(payload_len - len(payload))
            if not chunk:
                return msg_type, payload
            payload += chunk
        return msg_type, payload
    except socket.timeout:
        return None, None

def recv_specific(sock, target_type, timeout=3.0):
    """특정 MsgType을 받을 때까지 대기"""
    end_time = time.time() + timeout
    while time.time() < end_time:
        remaining = end_time - time.time()
        if remaining <= 0:
            break
        msg_type, payload = recv_packet(sock, timeout=remaining)
        if msg_type == target_type:
            return payload
    return None

def login_and_enter(sock, username="hero", password="pass123", char_id=100):
    """로그인 + 캐릭터 선택 + 게임 진입"""
    uname = username.encode()
    pw = password.encode()
    payload = struct.pack("B", len(uname)) + uname + struct.pack("B", len(pw)) + pw
    sock.sendall(build_packet(LOGIN, payload))
    recv_specific(sock, LOGIN_RESULT)

    sock.sendall(build_packet(CHAR_LIST_REQ))
    recv_specific(sock, CHAR_LIST_RESP)

    sock.sendall(build_packet(CHAR_SELECT, struct.pack("<I", char_id)))
    pl = recv_specific(sock, ENTER_GAME)
    if pl and pl[0] == 0:
        entity = struct.unpack("<Q", pl[1:9])[0]
        return entity
    return None

def enter_zone(sock, zone_id):
    sock.sendall(build_packet(ZONE_ENTER, struct.pack("<i", zone_id)))
    recv_specific(sock, ZONE_INFO)

def send_move(sock, x, y, z, timestamp=None):
    if timestamp is not None:
        payload = struct.pack("<fffI", x, y, z, timestamp)
    else:
        payload = struct.pack("<fff", x, y, z)
    sock.sendall(build_packet(MOVE, payload))

def drain_packets(sock, duration=0.3):
    """짧은 시간 동안 모든 패킷 수신 (버퍼 비우기)"""
    end = time.time() + duration
    packets = []
    while time.time() < end:
        remaining = end - time.time()
        if remaining <= 0:
            break
        msg_type, payload = recv_packet(sock, timeout=remaining)
        if msg_type is not None:
            packets.append((msg_type, payload))
    return packets

def has_correction(packets):
    """POSITION_CORRECTION 패킷이 있는지 확인"""
    return any(t == POSITION_CORRECTION for t, _ in packets)

def get_correction_pos(packets):
    """POSITION_CORRECTION에서 좌표 추출"""
    for t, p in packets:
        if t == POSITION_CORRECTION and len(p) >= 12:
            x, y, z = struct.unpack("<fff", p[:12])
            return x, y, z
    return None

# ====== Tests ======

def test_normal_move():
    """정상 이동: 검증 통과, 보정 없음"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None, "Login failed"
        enter_zone(sock, 1)
        drain_packets(sock, 0.3)

        # 정상 속도로 이동 (100 units, ~0.5초 대기)
        send_move(sock, 100.0, 100.0, 0.0)
        time.sleep(0.15)
        drain_packets(sock, 0.2)

        send_move(sock, 120.0, 120.0, 0.0)
        time.sleep(0.15)
        packets = drain_packets(sock, 0.3)

        # 정상 이동이므로 POSITION_CORRECTION 없어야 함
        assert not has_correction(packets), "Got unexpected POSITION_CORRECTION for normal move"

        # POS_QUERY로 위치 확인
        sock.sendall(build_packet(POS_QUERY))
        pl = recv_specific(sock, POS_QUERY)
        if pl and len(pl) >= 12:
            x, y, z = struct.unpack("<fff", pl[:12])
            assert abs(x - 120.0) < 1.0, f"X mismatch: {x}"
            assert abs(y - 120.0) < 1.0, f"Y mismatch: {y}"

        print("[PASS] test_normal_move")
    finally:
        sock.close()

def test_speed_hack_detection():
    """스피드핵 감지: 짧은 시간에 큰 거리 이동 → 보정"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None
        enter_zone(sock, 1)
        drain_packets(sock, 0.3)

        # 첫 이동으로 기준점 설정
        send_move(sock, 100.0, 100.0, 0.0)
        time.sleep(0.15)
        drain_packets(sock, 0.2)

        # 0.1초 후 900 units 이동 (= 9000 units/sec, 기본속도 200의 45배)
        time.sleep(0.1)
        send_move(sock, 900.0, 100.0, 0.0)
        packets = drain_packets(sock, 0.5)

        assert has_correction(packets), "Speed hack NOT detected!"
        pos = get_correction_pos(packets)
        assert pos is not None, "No correction position"
        # 보정 위치는 원래 위치(100, 100)에 가까워야 함
        assert abs(pos[0] - 100.0) < 50.0, f"Correction X too far: {pos[0]}"

        print("[PASS] test_speed_hack_detection")
    finally:
        sock.close()

def test_teleport_hack_detection():
    """텔레포트핵 감지: 순간이동 → 보정"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None
        enter_zone(sock, 2)  # Zone 2: 0~2000
        drain_packets(sock, 0.3)

        # 기준점
        send_move(sock, 500.0, 500.0, 0.0)
        time.sleep(0.15)
        drain_packets(sock, 0.2)

        # 즉시 1500 units 텔레포트
        send_move(sock, 500.0, 1999.0, 0.0)
        packets = drain_packets(sock, 0.5)

        assert has_correction(packets), "Teleport hack NOT detected!"
        print("[PASS] test_teleport_hack_detection")
    finally:
        sock.close()

def test_zone_boundary_enforcement():
    """존 경계 이탈: Zone 1은 0~1000, 1500으로 가면 클램프"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None
        enter_zone(sock, 1)  # Zone 1: 0~1000
        drain_packets(sock, 0.3)

        # 기준점 설정 (경계 근처)
        send_move(sock, 950.0, 500.0, 0.0)
        time.sleep(0.5)  # 충분한 시간 대기 (속도 검증 통과)
        drain_packets(sock, 0.2)

        # 존 경계 밖으로 이동 시도
        send_move(sock, 1500.0, 500.0, 0.0)
        packets = drain_packets(sock, 0.5)

        assert has_correction(packets), "Zone boundary NOT enforced!"
        pos = get_correction_pos(packets)
        assert pos is not None
        # 클램프된 좌표는 1000 이하여야 함
        assert pos[0] <= 1000.0, f"Correction X exceeds zone bounds: {pos[0]}"

        print("[PASS] test_zone_boundary_enforcement")
    finally:
        sock.close()

def test_invalid_coordinates():
    """비정상 좌표(NaN, 극값) → 보정"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None
        drain_packets(sock, 0.3)

        # 정상 이동으로 기준점
        send_move(sock, 50.0, 50.0, 0.0)
        time.sleep(0.15)
        drain_packets(sock, 0.2)

        # NaN 전송
        nan_bytes = struct.pack("<f", float('nan'))
        payload = nan_bytes + struct.pack("<ff", 50.0, 0.0)
        sock.sendall(build_packet(MOVE, payload))
        packets = drain_packets(sock, 0.5)

        assert has_correction(packets), "NaN coordinates NOT rejected!"

        print("[PASS] test_invalid_coordinates")
    finally:
        sock.close()

def test_extreme_coordinates():
    """극단적 좌표값 (±99999) → 보정"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None
        drain_packets(sock, 0.3)

        send_move(sock, 50.0, 50.0, 0.0)
        time.sleep(0.15)
        drain_packets(sock, 0.2)

        # 범위 초과 좌표
        send_move(sock, 99999.0, 99999.0, 0.0)
        packets = drain_packets(sock, 0.5)

        assert has_correction(packets), "Extreme coordinates NOT rejected!"

        print("[PASS] test_extreme_coordinates")
    finally:
        sock.close()

def test_move_with_timestamp():
    """Model C 형식: timestamp 포함 이동 (16바이트)"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None
        enter_zone(sock, 1)
        drain_packets(sock, 0.3)

        # timestamp 포함 정상 이동
        ts = int(time.time() * 1000) & 0xFFFFFFFF
        send_move(sock, 100.0, 100.0, 0.0, timestamp=ts)
        time.sleep(0.15)

        send_move(sock, 110.0, 110.0, 0.0, timestamp=ts + 100)
        packets = drain_packets(sock, 0.3)

        assert not has_correction(packets), "Normal move with timestamp got correction!"

        # 위치 확인
        sock.sendall(build_packet(POS_QUERY))
        pl = recv_specific(sock, POS_QUERY)
        if pl and len(pl) >= 12:
            x, y, z = struct.unpack("<fff", pl[:12])
            assert abs(x - 110.0) < 1.0

        print("[PASS] test_move_with_timestamp")
    finally:
        sock.close()

def test_normal_speed_no_false_positive():
    """정상 속도 이동이 오탐되지 않는지 확인"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    try:
        entity = login_and_enter(sock)
        assert entity is not None
        enter_zone(sock, 2)
        drain_packets(sock, 0.3)

        # 기준점
        send_move(sock, 500.0, 500.0, 0.0)
        time.sleep(0.2)
        drain_packets(sock, 0.2)

        # base_speed=200, 1초 대기 후 150 units 이동 (= 150 units/sec < 200)
        corrections = 0
        x, y = 500.0, 500.0
        for i in range(5):
            time.sleep(0.3)
            x += 30.0  # 30 units per 0.3sec = 100 units/sec
            y += 10.0
            send_move(sock, x, y, 0.0)
            packets = drain_packets(sock, 0.15)
            if has_correction(packets):
                corrections += 1

        assert corrections == 0, f"False positive: {corrections} corrections for normal speed"

        print("[PASS] test_normal_speed_no_false_positive")
    finally:
        sock.close()

# ====== Main ======

def main():
    tests = [
        test_normal_move,
        test_speed_hack_detection,
        test_teleport_hack_detection,
        test_zone_boundary_enforcement,
        test_invalid_coordinates,
        test_extreme_coordinates,
        test_move_with_timestamp,
        test_normal_speed_no_false_positive,
    ]

    passed = 0
    failed = 0
    errors = []

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"  {test.__name__}: {e}")
            print(f"[FAIL] {test.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Session 35 Movement Validation: {passed} passed, {failed} failed")
    if errors:
        print("Failures:")
        for e in errors:
            print(e)
    print(f"{'='*50}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
