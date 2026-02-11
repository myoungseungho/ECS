"""
Session 12: Stats System Tests
- StatsComponent: HP/MP/Attack/Defense/Level/EXP
- StatsSystem: HP/MP 자연회복
- 패킷: STAT_QUERY(90), STAT_SYNC(91), STAT_ADD_EXP(92), STAT_TAKE_DMG(93), STAT_HEAL(94)
- 레벨업, 데미지(방어력 적용), 힐, 사망 판정
"""

import socket
import struct
import time
import subprocess
import sys
import os

# ━━━ 네트워크 유틸 ━━━
HEADER_SIZE = 6

def build_packet(msg_type, payload=b''):
    total = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total, msg_type) + payload

def recv_packet(sock, timeout=3.0):
    sock.settimeout(timeout)
    header = b''
    while len(header) < 4:
        chunk = sock.recv(4 - len(header))
        if not chunk:
            raise ConnectionError("Connection closed")
        header += chunk
    total_len = struct.unpack('<I', header)[0]
    remaining = total_len - 4
    data = b''
    while len(data) < remaining:
        chunk = sock.recv(remaining - len(data))
        if not chunk:
            raise ConnectionError("Connection closed")
        data += chunk
    msg_type = struct.unpack('<H', data[:2])[0]
    payload = data[2:]
    return msg_type, payload

def recv_packet_type(sock, expected_type, timeout=5.0):
    """특정 타입의 패킷이 올 때까지 다른 패킷은 무시 (APPEAR 등)"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            msg_type, payload = recv_packet(sock, timeout=remaining)
            if msg_type == expected_type:
                return msg_type, payload
            # APPEAR(13), DISAPPEAR(14), MOVE_BROADCAST(11) 등은 무시
        except (socket.timeout, OSError):
            break
    raise TimeoutError(f"Timed out waiting for msg_type {expected_type}")

def connect_and_login(host='127.0.0.1', gate_port=8888, username='hero', password='pass123', char_id=1, retries=3):
    """Gate → Field → Login → CharSelect → InGame, returns (sock, entity_id)"""
    last_err = None
    for attempt in range(retries):
        try:
            # Gate
            gs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            gs.settimeout(5.0)
            gs.connect((host, gate_port))
            gs.sendall(build_packet(70))  # GATE_ROUTE_REQ
            msg_type, payload = recv_packet(gs, timeout=5.0)
            assert msg_type == 71, f"Expected GATE_ROUTE_RESP(71), got {msg_type}"
            result = payload[0]
            assert result == 0, f"Gate route failed: {result}"
            port = struct.unpack('<H', payload[1:3])[0]
            ip_len = payload[3]
            ip = payload[4:4+ip_len].decode()
            gs.close()
            time.sleep(0.05)

            # Field
            fs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            fs.settimeout(5.0)
            fs.connect((ip, port))

            # Login
            uname = username.encode()
            pw = password.encode()
            login_payload = bytes([len(uname)]) + uname + bytes([len(pw)]) + pw
            fs.sendall(build_packet(60, login_payload))
            msg_type, payload = recv_packet(fs, timeout=5.0)
            assert msg_type == 61, f"Expected LOGIN_RESULT(61), got {msg_type}"
            assert payload[0] == 0, f"Login failed: {payload[0]}"

            # CharSelect
            fs.sendall(build_packet(64, struct.pack('<I', char_id)))
            msg_type, payload = recv_packet(fs, timeout=5.0)
            assert msg_type == 65, f"Expected ENTER_GAME(65), got {msg_type}"
            assert payload[0] == 0, f"Enter game failed: {payload[0]}"
            entity_id = struct.unpack('<Q', payload[1:9])[0]

            # Channel join
            fs.sendall(build_packet(20, struct.pack('<i', 1)))
            msg_type, payload = recv_packet_type(fs, 22, timeout=5.0)

            # 채널 진입 후 APPEAR 패킷 drain
            time.sleep(0.15)
            fs.settimeout(0.2)
            try:
                while True:
                    fs.recv(4096)
            except:
                pass
            fs.settimeout(5.0)

            return fs, entity_id

        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(0.5)
            try:
                gs.close()
            except:
                pass

    raise last_err

def parse_stat_sync(payload):
    """STAT_SYNC 페이로드 파싱 → dict"""
    if len(payload) < 36:
        return None
    vals = struct.unpack('<iiiiiiiii', payload[:36])
    return {
        'level': vals[0],
        'hp': vals[1],
        'max_hp': vals[2],
        'mp': vals[3],
        'max_mp': vals[4],
        'attack': vals[5],
        'defense': vals[6],
        'exp': vals[7],
        'exp_to_next': vals[8],
    }

# ━━━ 테스트 ━━━
passed = 0
failed = 0
total = 0

def run_test(name, func):
    global passed, failed, total
    total += 1
    time.sleep(0.2)  # 테스트 간 서버 정리 시간
    try:
        func()
        passed += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name}: {e}")

# ━━━ 서버 프로세스 ━━━
server_procs = []

def start_servers():
    global server_procs
    build_dir = os.path.join(os.path.dirname(__file__), 'build')
    field_exe = os.path.join(build_dir, 'FieldServer.exe')
    gate_exe = os.path.join(build_dir, 'GateServer.exe')

    if not os.path.exists(field_exe):
        print(f"ERROR: {field_exe} not found. Build first!")
        sys.exit(1)

    p1 = subprocess.Popen([field_exe, '7777'], cwd=build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2 = subprocess.Popen([field_exe, '7778'], cwd=build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p3 = subprocess.Popen([gate_exe, '7777', '7778'], cwd=build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    server_procs = [p1, p2, p3]
    time.sleep(1.5)  # 서버 시작 대기

def stop_servers():
    for p in server_procs:
        try:
            p.terminate()
            p.wait(timeout=3)
        except:
            p.kill()

# ━━━ 테스트 구현 ━━━

def test_stat_query_after_login():
    """STAT_QUERY: 로그인 후 스탯 조회"""
    sock, eid = connect_and_login()
    try:
        sock.sendall(build_packet(90))  # STAT_QUERY
        msg_type, payload = recv_packet_type(sock, 91)
        assert msg_type == 91, f"Expected STAT_SYNC(91), got {msg_type}"
        stats = parse_stat_sync(payload)
        assert stats is not None, "Failed to parse stat sync"
        assert stats['level'] == 50, f"Expected level 50, got {stats['level']}"
        assert stats['hp'] > 0, f"HP should be > 0, got {stats['hp']}"
        assert stats['max_hp'] > 0, f"max_hp should be > 0"
        assert stats['attack'] > 0, f"attack should be > 0"
        assert stats['defense'] > 0, f"defense should be > 0"
    finally:
        sock.close()

def test_warrior_stats_formula():
    """전사(Warrior_Kim Lv50) 스탯 공식 검증"""
    sock, eid = connect_and_login(username='hero', char_id=1)
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats = parse_stat_sync(payload)
        # Warrior Lv50: max_hp = 80 + 50*20 = 1080
        assert stats['max_hp'] == 1080, f"Warrior Lv50 max_hp: expected 1080, got {stats['max_hp']}"
        # hp should equal max_hp (freshly created)
        assert stats['hp'] == stats['max_hp'], f"HP should be full: {stats['hp']} != {stats['max_hp']}"
        # attack = 8 + 50*2 = 108
        assert stats['attack'] == 108, f"Warrior Lv50 atk: expected 108, got {stats['attack']}"
        # defense = 3 + 50*2 = 103
        assert stats['defense'] == 103, f"Warrior Lv50 def: expected 103, got {stats['defense']}"
    finally:
        sock.close()

def test_mage_stats_formula():
    """마법사(Mage_Lee Lv35) 스탯 공식 검증"""
    sock, eid = connect_and_login(username='hero', char_id=2)
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats = parse_stat_sync(payload)
        # Mage Lv35: max_hp = 50 + 35*10 = 400
        assert stats['max_hp'] == 400, f"Mage Lv35 max_hp: expected 400, got {stats['max_hp']}"
        # max_mp = 60 + 35*12 = 480
        assert stats['max_mp'] == 480, f"Mage Lv35 max_mp: expected 480, got {stats['max_mp']}"
        # attack = 5 + 35*4 = 145
        assert stats['attack'] == 145, f"Mage Lv35 atk: expected 145, got {stats['attack']}"
        # defense = 1 + 35*1 = 36
        assert stats['defense'] == 36, f"Mage Lv35 def: expected 36, got {stats['defense']}"
    finally:
        sock.close()

def test_archer_stats_formula():
    """궁수(Archer_Park Lv20) 스탯 공식 검증"""
    sock, eid = connect_and_login(username='guest', password='guest', char_id=3)
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats = parse_stat_sync(payload)
        # Archer Lv20: max_hp = 60 + 20*15 = 360
        assert stats['max_hp'] == 360, f"Archer Lv20 max_hp: expected 360, got {stats['max_hp']}"
        # max_mp = 40 + 20*8 = 200
        assert stats['max_mp'] == 200, f"Archer Lv20 max_mp: expected 200, got {stats['max_mp']}"
        # attack = 6 + 20*3 = 66
        assert stats['attack'] == 66, f"Archer Lv20 atk: expected 66, got {stats['attack']}"
    finally:
        sock.close()

def test_take_damage():
    """STAT_TAKE_DMG: 데미지 처리 (방어력 적용)"""
    sock, eid = connect_and_login()
    try:
        # 먼저 스탯 확인
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_before = parse_stat_sync(payload)

        # 200 데미지 (Warrior Lv50 def=103, 실제 데미지 = max(1, 200-103) = 97)
        sock.sendall(build_packet(93, struct.pack('<i', 200)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_after = parse_stat_sync(payload)

        expected_hp = stats_before['hp'] - max(1, 200 - stats_before['defense'])
        assert stats_after['hp'] == expected_hp, \
            f"HP after damage: expected {expected_hp}, got {stats_after['hp']}"
    finally:
        sock.close()

def test_damage_minimum_one():
    """데미지 최소 1 보장 (방어력 > 공격력이어도)"""
    sock, eid = connect_and_login()  # Warrior def=103
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_before = parse_stat_sync(payload)

        # 1 데미지 (def=103이므로 원래는 -102지만 최소 1)
        sock.sendall(build_packet(93, struct.pack('<i', 1)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_after = parse_stat_sync(payload)

        assert stats_after['hp'] == stats_before['hp'] - 1, \
            f"Min damage should be 1: {stats_before['hp']} -> {stats_after['hp']}"
    finally:
        sock.close()

def test_heal():
    """STAT_HEAL: 힐 처리"""
    sock, eid = connect_and_login()
    try:
        # 먼저 데미지를 줘서 HP를 깎음
        sock.sendall(build_packet(93, struct.pack('<i', 500)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_damaged = parse_stat_sync(payload)
        assert stats_damaged['hp'] < stats_damaged['max_hp'], "Should be damaged"

        # 100 힐
        sock.sendall(build_packet(94, struct.pack('<i', 100)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_healed = parse_stat_sync(payload)

        assert stats_healed['hp'] == stats_damaged['hp'] + 100, \
            f"HP after heal: expected {stats_damaged['hp'] + 100}, got {stats_healed['hp']}"
    finally:
        sock.close()

def test_heal_no_overheal():
    """힐로 max_hp 초과 불가"""
    sock, eid = connect_and_login()
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats = parse_stat_sync(payload)
        assert stats['hp'] == stats['max_hp'], "Should be full HP"

        # 9999 힐 (이미 풀피)
        sock.sendall(build_packet(94, struct.pack('<i', 9999)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_after = parse_stat_sync(payload)

        assert stats_after['hp'] == stats_after['max_hp'], \
            f"HP should not exceed max: {stats_after['hp']} > {stats_after['max_hp']}"
    finally:
        sock.close()

def test_add_exp_no_levelup():
    """EXP 추가 (레벨업 안 되는 양) + exp_to_next 공식 + 필드 완전성 + 지속성"""
    sock, eid = connect_and_login()
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_before = parse_stat_sync(payload)

        # --- exp_to_next 공식: level^2 * 10 + 100 ---
        expected_etn = 50 * 50 * 10 + 100  # 25100
        assert stats_before['exp_to_next'] == expected_etn, \
            f"exp_to_next: expected {expected_etn}, got {stats_before['exp_to_next']}"

        # --- STAT_SYNC 전체 필드 완전성 ---
        assert len(payload) >= 36, f"STAT_SYNC should be >= 36 bytes, got {len(payload)}"
        for key, val in stats_before.items():
            assert val >= 0, f"{key} should be >= 0, got {val}"

        # 10 EXP (Lv50 exp_to_next = 25100, 10으로는 안 오름)
        sock.sendall(build_packet(92, struct.pack('<i', 10)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_after = parse_stat_sync(payload)

        assert stats_after['level'] == stats_before['level'], \
            f"Level should stay same: {stats_before['level']} -> {stats_after['level']}"
        assert stats_after['exp'] == stats_before['exp'] + 10, \
            f"EXP: expected {stats_before['exp'] + 10}, got {stats_after['exp']}"

        # --- 스탯 지속성: 재조회 시 동일 ---
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_requery = parse_stat_sync(payload)
        diff = abs(stats_after['exp'] - stats_requery['exp'])
        assert diff == 0, \
            f"EXP should persist: {stats_after['exp']} vs {stats_requery['exp']}"
    finally:
        sock.close()

def test_level_up():
    """EXP 추가로 레벨업"""
    # Archer Lv20 사용 (exp_to_next가 더 낮음: 20*20*10+100 = 4100)
    sock, eid = connect_and_login(username='guest', password='guest', char_id=3)
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_before = parse_stat_sync(payload)
        assert stats_before['level'] == 20

        # 4200 EXP (4100 필요 → 레벨 21로)
        sock.sendall(build_packet(92, struct.pack('<i', 4200)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_after = parse_stat_sync(payload)

        assert stats_after['level'] == 21, \
            f"Expected level 21, got {stats_after['level']}"
        # 레벨업 시 스탯 재계산됨
        assert stats_after['max_hp'] > stats_before['max_hp'], \
            f"max_hp should increase: {stats_before['max_hp']} -> {stats_after['max_hp']}"
        # 레벨업 시 HP 전회복
        assert stats_after['hp'] == stats_after['max_hp'], \
            f"HP should be full after levelup: {stats_after['hp']} != {stats_after['max_hp']}"
    finally:
        sock.close()

def test_multi_level_up():
    """대량 EXP로 다중 레벨업"""
    sock, eid = connect_and_login(username='guest', password='guest', char_id=3)
    try:
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_before = parse_stat_sync(payload)
        assert stats_before['level'] == 20

        # 엄청 많은 EXP (Lv20→21 4100, 21→22 4510, 22→23 4940 ... 대충 50000이면 여러번)
        sock.sendall(build_packet(92, struct.pack('<i', 50000)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats_after = parse_stat_sync(payload)

        assert stats_after['level'] > 21, \
            f"Expected multiple levelups from 20, got {stats_after['level']}"
    finally:
        sock.close()

def test_death_by_damage():
    """큰 데미지로 사망 (HP=0)"""
    sock, eid = connect_and_login()
    try:
        # Warrior Lv50: max_hp=1080, def=103
        # 999999 데미지로 확실히 죽임
        sock.sendall(build_packet(93, struct.pack('<i', 999999)))
        msg_type, payload = recv_packet_type(sock, 91)
        stats = parse_stat_sync(payload)

        assert stats['hp'] == 0, f"Should be dead: HP={stats['hp']}"
    finally:
        sock.close()


# ━━━ 실행 ━━━
if __name__ == '__main__':
    print("=" * 50)
    print("  Session 12: Stats System Tests")
    print("=" * 50)
    print()

    start_servers()

    try:
        print("[1] Stats Query & Formula Tests")
        run_test("STAT_QUERY after login", test_stat_query_after_login)
        run_test("Warrior(Lv50) stats formula", test_warrior_stats_formula)
        run_test("Mage(Lv35) stats formula", test_mage_stats_formula)
        run_test("Archer(Lv20) stats formula", test_archer_stats_formula)

        print()
        print("[2] Damage & Heal Tests")
        run_test("Take damage (defense applied)", test_take_damage)
        run_test("Minimum 1 damage", test_damage_minimum_one)
        run_test("Heal", test_heal)
        run_test("No overheal", test_heal_no_overheal)
        run_test("Death by massive damage", test_death_by_damage)

        print()
        print("[3] EXP & Level Up Tests")
        run_test("Add EXP (no levelup)", test_add_exp_no_levelup)
        run_test("Level up", test_level_up)
        run_test("Multi level up", test_multi_level_up)

    finally:
        stop_servers()

    print()
    print("=" * 50)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
