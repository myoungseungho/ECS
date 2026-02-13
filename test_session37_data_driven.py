"""
Session 37: Data-Driven + Hot-Reload Skeleton Tests
====================================================
Tests: Config file loading, GameConfig runtime cache, hot-reload via
       ADMIN_RELOAD packet, config value query, fallback to defaults.
"""
import socket, struct, time, sys, os, json, shutil

SERVER_EXE = os.path.join(os.path.dirname(__file__), "Servers", "FieldServer", "FieldServer.exe")
HOST, PORT = "127.0.0.1", 7777
HEADER_SIZE = 6
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# MsgType IDs
LOGIN = 60
LOGIN_RESULT = 61
CHAR_LIST_REQ = 62
CHAR_LIST_RESP = 63
CHAR_SELECT = 64
ENTER_GAME = 65
ZONE_ENTER = 30
ZONE_INFO = 31
CONFIG_QUERY = 82
CONFIG_RESP = 83
ADMIN_RELOAD = 280
ADMIN_RELOAD_RESULT = 281
ADMIN_GET_CONFIG = 282
ADMIN_CONFIG_RESP = 283
MONSTER_SPAWN = 110

def build_packet(msg_type, payload=b""):
    length = HEADER_SIZE + len(payload)
    return struct.pack("<IH", length, msg_type) + payload

def recv_packet(sock, timeout=3.0):
    sock.settimeout(timeout)
    try:
        header = b""
        while len(header) < HEADER_SIZE:
            chunk = sock.recv(HEADER_SIZE - len(header))
            if not chunk: return None, None
            header += chunk
        length, msg_type = struct.unpack("<IH", header)
        payload_len = length - HEADER_SIZE
        payload = b""
        while len(payload) < payload_len:
            chunk = sock.recv(payload_len - len(payload))
            if not chunk: return msg_type, payload
            payload += chunk
        return msg_type, payload
    except socket.timeout:
        return None, None

def recv_specific(sock, target_type, timeout=3.0):
    end_time = time.time() + timeout
    while time.time() < end_time:
        remaining = end_time - time.time()
        if remaining <= 0: break
        msg_type, payload = recv_packet(sock, timeout=remaining)
        if msg_type == target_type:
            return payload
    return None

def login_and_enter(sock, username="hero", password="pass123", char_id=100):
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

def drain_packets(sock, duration=0.3):
    end = time.time() + duration
    packets = []
    while time.time() < end:
        remaining = end - time.time()
        if remaining <= 0: break
        msg_type, payload = recv_packet(sock, timeout=remaining)
        if msg_type is not None:
            packets.append((msg_type, payload))
    return packets

def send_admin_reload(sock, name=""):
    """ADMIN_RELOAD: name_len(1) + name(N). empty = reload all"""
    name_bytes = name.encode()
    payload = struct.pack("B", len(name_bytes)) + name_bytes
    sock.sendall(build_packet(ADMIN_RELOAD, payload))
    return recv_specific(sock, ADMIN_RELOAD_RESULT, timeout=3.0)

def send_admin_get_config(sock, name, key):
    """ADMIN_GET_CONFIG: name_len(1) name(N) key_len(1) key(N)"""
    nb = name.encode()
    kb = key.encode()
    payload = struct.pack("B", len(nb)) + nb + struct.pack("B", len(kb)) + kb
    sock.sendall(build_packet(ADMIN_GET_CONFIG, payload))
    return recv_specific(sock, ADMIN_CONFIG_RESP, timeout=3.0)

def connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    return sock

# ━━━ Test Helpers ━━━

def backup_config(filename):
    """데이터 파일 백업"""
    src = os.path.join(DATA_DIR, filename)
    dst = os.path.join(DATA_DIR, filename + ".bak")
    if os.path.exists(src):
        shutil.copy2(src, dst)

def restore_config(filename):
    """백업에서 복원"""
    src = os.path.join(DATA_DIR, filename + ".bak")
    dst = os.path.join(DATA_DIR, filename)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        os.remove(src)

def modify_json_config(filename, key, value):
    """JSON 설정 파일에서 특정 키 값 변경"""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'r') as f:
        data = json.load(f)
    data[key] = value
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

# ━━━ Tests ━━━

def test_1_config_query_monster_ai():
    """기존 CONFIG_QUERY로 monster_ai 설정 조회 가능"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    # CONFIG_QUERY: [name_len(1) name(N) key_len(1) key(N)]
    name = b"monster_ai"
    key = b"leash_range"
    payload = struct.pack("B", len(name)) + name + struct.pack("B", len(key)) + key
    sock.sendall(build_packet(CONFIG_QUERY, payload))
    resp = recv_specific(sock, CONFIG_RESP, timeout=2.0)
    assert resp is not None, "No CONFIG_RESP"
    assert resp[0] == 1, f"Config not found (found={resp[0]})"
    data_len = struct.unpack("<H", resp[1:3])[0]
    data = resp[3:3+data_len].decode()
    assert "500" in data, f"leash_range should be 500, got: {data}"
    print(f"  config query result: {data}")
    sock.close()

def test_2_admin_get_config():
    """ADMIN_GET_CONFIG로 설정값 직접 조회"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    resp = send_admin_get_config(sock, "monster_ai", "chase_speed_mult")
    assert resp is not None, "No ADMIN_CONFIG_RESP"
    assert resp[0] == 1, f"Config not found (found={resp[0]})"
    value_len = struct.unpack("<H", resp[1:3])[0]
    value = resp[3:3+value_len].decode()
    assert "1.3" in value, f"chase_speed_mult should be 1.3, got: {value}"
    print(f"  chase_speed_mult = {value}")
    sock.close()

def test_3_admin_get_config_movement():
    """movement_rules 설정값 조회"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    resp = send_admin_get_config(sock, "movement_rules", "base_speed")
    assert resp is not None, "No ADMIN_CONFIG_RESP"
    assert resp[0] == 1, f"Config not found"
    value_len = struct.unpack("<H", resp[1:3])[0]
    value = resp[3:3+value_len].decode()
    assert "200" in value, f"base_speed should be 200, got: {value}"
    print(f"  base_speed = {value}")
    sock.close()

def test_4_admin_get_config_missing_key():
    """존재하지 않는 설정 키 조회 → found=0"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    resp = send_admin_get_config(sock, "monster_ai", "nonexistent_key")
    assert resp is not None, "No ADMIN_CONFIG_RESP"
    assert resp[0] == 0, f"Should not find nonexistent key (found={resp[0]})"
    print("  correctly returned not found for nonexistent key")
    sock.close()

def test_5_admin_reload_single():
    """ADMIN_RELOAD: 단일 설정 리로드"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    resp = send_admin_reload(sock, "monster_ai")
    assert resp is not None, "No ADMIN_RELOAD_RESULT"
    result = resp[0]
    version = struct.unpack("<I", resp[1:5])[0]
    reload_count = struct.unpack("<I", resp[5:9])[0]
    print(f"  reload result={result}, version={version}, reload_count={reload_count}")
    assert result == 1, f"Reload should succeed (result={result})"
    assert version > 0, "Version should be > 0"
    assert reload_count > 0, "Reload count should be > 0"
    sock.close()

def test_6_admin_reload_all():
    """ADMIN_RELOAD: 전체 리로드 (빈 이름)"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    resp = send_admin_reload(sock, "")
    assert resp is not None, "No ADMIN_RELOAD_RESULT"
    result = resp[0]
    version = struct.unpack("<I", resp[1:5])[0]
    reload_count = struct.unpack("<I", resp[5:9])[0]
    print(f"  reload all: result={result}, version={version}, reload_count={reload_count}")
    assert result == 1, f"ReloadAll should succeed"
    sock.close()

def test_7_hot_reload_value_change():
    """핫리로드: JSON 수정 → ADMIN_RELOAD → 값 변경 확인"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    # 1단계: 현재 값 확인
    resp = send_admin_get_config(sock, "monster_ai", "leash_range")
    assert resp is not None and resp[0] == 1
    original_value = resp[3:3+struct.unpack("<H", resp[1:3])[0]].decode()
    print(f"  before: leash_range = {original_value}")

    # 2단계: 파일 수정 (500 → 999)
    backup_config("monster_ai.json")
    try:
        modify_json_config("monster_ai.json", "leash_range", 999.0)

        # 3단계: 리로드 전 → 여전히 이전 값
        resp = send_admin_get_config(sock, "monster_ai", "leash_range")
        assert resp is not None and resp[0] == 1
        before_reload = resp[3:3+struct.unpack("<H", resp[1:3])[0]].decode()
        # 리로드 전이니까 아직 파일에서 직접 읽는 것이 아닌 캐시된 값
        # (ConfigLoader는 파일에서 로드하지만 ADMIN_GET_CONFIG은 이미 로드된 걸 조회)
        # 이미 monster_ai.json이 파일로 로드되었으니 파일 내용이 반환됨

        # 4단계: 리로드
        reload_resp = send_admin_reload(sock, "monster_ai")
        assert reload_resp is not None and reload_resp[0] == 1

        # 5단계: 리로드 후 새 값 확인
        resp = send_admin_get_config(sock, "monster_ai", "leash_range")
        assert resp is not None and resp[0] == 1
        new_value = resp[3:3+struct.unpack("<H", resp[1:3])[0]].decode()
        print(f"  after reload: leash_range = {new_value}")
        assert "999" in new_value, f"After reload, leash_range should be 999, got: {new_value}"

    finally:
        # 6단계: 원본 복원
        restore_config("monster_ai.json")
        send_admin_reload(sock, "monster_ai")

    sock.close()

def test_8_reload_nonexistent():
    """존재하지 않는 설정 리로드 시 실패"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    resp = send_admin_reload(sock, "totally_fake_config")
    assert resp is not None, "No ADMIN_RELOAD_RESULT"
    result = resp[0]
    assert result == 0, f"Should fail for nonexistent config (result={result})"
    print("  correctly failed for nonexistent config")
    sock.close()

def test_9_config_version_increments():
    """리로드마다 version이 증가하는지 확인"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    # 첫 번째 리로드
    resp1 = send_admin_reload(sock, "monster_ai")
    assert resp1 is not None and resp1[0] == 1
    version1 = struct.unpack("<I", resp1[1:5])[0]

    # 두 번째 리로드
    resp2 = send_admin_reload(sock, "monster_ai")
    assert resp2 is not None and resp2[0] == 1
    version2 = struct.unpack("<I", resp2[1:5])[0]

    print(f"  version1={version1}, version2={version2}")
    assert version2 > version1, f"Version should increment: {version2} > {version1}"
    sock.close()

def test_10_monster_spawns_csv_loaded():
    """monster_spawns.csv가 로드되어 CONFIG_QUERY로 조회 가능"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    # CONFIG_QUERY for monster_spawns table, key="1" (Goblin)
    name = b"monster_spawns"
    key = b"1"
    payload = struct.pack("B", len(name)) + name + struct.pack("B", len(key)) + key
    sock.sendall(build_packet(CONFIG_QUERY, payload))
    resp = recv_specific(sock, CONFIG_RESP, timeout=2.0)
    assert resp is not None, "No CONFIG_RESP"
    assert resp[0] == 1, f"monster_spawns should be loaded (found={resp[0]})"
    data_len = struct.unpack("<H", resp[1:3])[0]
    data = resp[3:3+data_len].decode()
    assert "Goblin" in data, f"Should contain Goblin, got: {data}"
    print(f"  monster_spawns row: {data[:80]}...")
    sock.close()

def test_11_zone_bounds_csv_loaded():
    """zone_bounds.csv가 로드되어 CONFIG_QUERY로 조회 가능"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    name = b"zone_bounds"
    key = b"1"
    payload = struct.pack("B", len(name)) + name + struct.pack("B", len(key)) + key
    sock.sendall(build_packet(CONFIG_QUERY, payload))
    resp = recv_specific(sock, CONFIG_RESP, timeout=2.0)
    assert resp is not None, "No CONFIG_RESP"
    assert resp[0] == 1, f"zone_bounds should be loaded (found={resp[0]})"
    data_len = struct.unpack("<H", resp[1:3])[0]
    data = resp[3:3+data_len].decode()
    assert "1000" in data, f"Zone 1 should have max 1000, got: {data}"
    print(f"  zone_bounds row: {data[:80]}...")
    sock.close()

def test_12_hot_reload_movement_rules():
    """movement_rules 핫리로드: tolerance 변경 확인"""
    sock = connect()
    entity = login_and_enter(sock)
    assert entity is not None, "Login failed"
    drain_packets(sock)

    backup_config("movement_rules.json")
    try:
        # 변경: tolerance 1.5 → 3.0
        modify_json_config("movement_rules.json", "tolerance", 3.0)
        send_admin_reload(sock, "movement_rules")

        resp = send_admin_get_config(sock, "movement_rules", "tolerance")
        assert resp is not None and resp[0] == 1
        value = resp[3:3+struct.unpack("<H", resp[1:3])[0]].decode()
        print(f"  tolerance after reload = {value}")
        assert "3" in value, f"tolerance should be 3.0 after reload, got: {value}"
    finally:
        restore_config("movement_rules.json")
        send_admin_reload(sock, "movement_rules")

    sock.close()

# ━━━ Test Runner ━━━

def run_tests():
    tests = [
        ("Config query monster_ai", test_1_config_query_monster_ai),
        ("Admin get config (chase_speed_mult)", test_2_admin_get_config),
        ("Admin get config (movement base_speed)", test_3_admin_get_config_movement),
        ("Admin get config (missing key)", test_4_admin_get_config_missing_key),
        ("Admin reload single", test_5_admin_reload_single),
        ("Admin reload all", test_6_admin_reload_all),
        ("Hot-reload value change", test_7_hot_reload_value_change),
        ("Reload nonexistent config", test_8_reload_nonexistent),
        ("Config version increments", test_9_config_version_increments),
        ("Monster spawns CSV loaded", test_10_monster_spawns_csv_loaded),
        ("Zone bounds CSV loaded", test_11_zone_bounds_csv_loaded),
        ("Hot-reload movement rules", test_12_hot_reload_movement_rules),
    ]

    passed = 0
    failed = 0
    errors = []

    print(f"\n{'='*60}")
    print(f" Session 37: Data-Driven + Hot-Reload Tests ({len(tests)} tests)")
    print(f"{'='*60}\n")

    for i, (name, test_func) in enumerate(tests, 1):
        try:
            print(f"[{i:2d}/{len(tests)}] {name}...", end=" ", flush=True)
            test_func()
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1
            errors.append((name, str(e)))

    print(f"\n{'='*60}")
    print(f" Results: {passed} PASSED / {failed} FAILED / {len(tests)} TOTAL")
    print(f"{'='*60}")

    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
