"""
Session 14: Monster/NPC System Tests
- MonsterComponent: AI state machine (IDLE/ATTACK/DEAD)
- MonsterAISystem: aggro detection, attack, respawn
- PvE combat: player attacks monster, monster attacks player
- Packets: MONSTER_SPAWN(110), MONSTER_RESPAWN(113), reuse ATTACK_RESULT(101), COMBAT_DIED(102)

Monster data (Zone 1):
  Goblin x3: Lv5, HP=100, ATK=15, DEF=5  at (150,150), (250,250), (350,150)
  Wolf   x2: Lv10, HP=200, ATK=25, DEF=10 at (400,300), (300,400)

Player: Warrior_Kim (hero/1): Lv50, ATK=108, DEF=103, HP=1080, zone=1, pos=(100,100)

Combat math:
  Warrior -> Goblin: damage = max(1, 108-5) = 103. HP=100 -> one-hit kill. EXP = 5*10 = 50
  Goblin -> Warrior: damage = max(1, 15-103) = 1 (minimum)
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
    """특정 타입의 패킷이 올 때까지 다른 패킷은 무시"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            msg_type, payload = recv_packet(sock, timeout=remaining)
            if msg_type == expected_type:
                return msg_type, payload
        except (socket.timeout, OSError):
            break
    raise TimeoutError(f"Timed out waiting for msg_type {expected_type}")

def collect_packets(sock, timeout=0.5):
    """소켓에서 timeout 동안 모든 패킷을 수집"""
    packets = []
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            remaining = max(0.01, end_time - time.time())
            msg_type, payload = recv_packet(sock, timeout=remaining)
            packets.append((msg_type, payload))
        except (socket.timeout, OSError):
            break
    return packets

def drain(sock, wait=0.2):
    """소켓 버퍼의 남은 패킷을 모두 소비"""
    sock.settimeout(wait)
    try:
        while True:
            sock.recv(4096)
    except:
        pass
    sock.settimeout(5.0)

def move_near(sock, x, y, z=0.0):
    """플레이어를 특정 위치로 이동 (MOVE 패킷 전송 + 버퍼 정리)"""
    payload = struct.pack('<fff', x, y, z)
    sock.sendall(build_packet(10, payload))  # MOVE
    time.sleep(0.3)  # 서버 처리 대기
    drain(sock, wait=0.3)  # 이동 관련 패킷 + 몬스터 공격 비움

def recv_my_attack_result(sock, my_eid, timeout=5.0):
    """내 공격 결과(ATTACK_RESULT)만 필터링 (몬스터 공격 101 무시)"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            msg_type, payload = recv_packet(sock, timeout=remaining)
            if msg_type == 101:  # ATTACK_RESULT
                r = parse_attack_result(payload)
                if r and r['attacker'] == my_eid:
                    return msg_type, payload
        except (socket.timeout, OSError):
            break
    raise TimeoutError("Timed out waiting for my ATTACK_RESULT")

def recv_monster_respawn_for(sock, target_entity, timeout=10.0):
    """특정 몬스터의 MONSTER_RESPAWN만 필터링 (다른 몬스터 리스폰 무시)"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            msg_type, payload = recv_packet(sock, timeout=remaining)
            if msg_type == 113:  # MONSTER_RESPAWN
                respawn = parse_monster_respawn(payload)
                if respawn and respawn['entity'] == target_entity:
                    return msg_type, payload
        except (socket.timeout, OSError):
            break
    raise TimeoutError(f"Timed out waiting for MONSTER_RESPAWN of entity {target_entity}")

# ━━━ 파싱 헬퍼 ━━━

def parse_monster_spawn(payload):
    """MONSTER_SPAWN: entity(8) monster_id(4) level(4) hp(4) max_hp(4) x(4) y(4) z(4)"""
    if len(payload) < 36:
        return None
    entity = struct.unpack_from('<Q', payload, 0)[0]
    monster_id = struct.unpack_from('<I', payload, 8)[0]
    level = struct.unpack_from('<i', payload, 12)[0]
    hp = struct.unpack_from('<i', payload, 16)[0]
    max_hp = struct.unpack_from('<i', payload, 20)[0]
    x = struct.unpack_from('<f', payload, 24)[0]
    y = struct.unpack_from('<f', payload, 28)[0]
    z = struct.unpack_from('<f', payload, 32)[0]
    return {
        'entity': entity, 'monster_id': monster_id, 'level': level,
        'hp': hp, 'max_hp': max_hp, 'x': x, 'y': y, 'z': z
    }

def parse_attack_result(payload):
    """ATTACK_RESULT: result(1) attacker(8) target(8) damage(4) target_hp(4) target_max_hp(4)"""
    if len(payload) < 29:
        return None
    return {
        'result': payload[0],
        'attacker': struct.unpack('<Q', payload[1:9])[0],
        'target': struct.unpack('<Q', payload[9:17])[0],
        'damage': struct.unpack('<i', payload[17:21])[0],
        'target_hp': struct.unpack('<i', payload[21:25])[0],
        'target_max_hp': struct.unpack('<i', payload[25:29])[0],
    }

def parse_stat_sync(payload):
    """STAT_SYNC: level(4) hp(4) max_hp(4) mp(4) max_mp(4) atk(4) def(4) exp(4) exp_next(4)"""
    if len(payload) < 36:
        return None
    vals = struct.unpack('<iiiiiiiii', payload[:36])
    return {
        'level': vals[0], 'hp': vals[1], 'max_hp': vals[2],
        'mp': vals[3], 'max_mp': vals[4],
        'attack': vals[5], 'defense': vals[6],
        'exp': vals[7], 'exp_to_next': vals[8],
    }

def parse_monster_respawn(payload):
    """MONSTER_RESPAWN: entity(8) hp(4) max_hp(4) x(4) y(4) z(4)"""
    if len(payload) < 28:
        return None
    entity = struct.unpack_from('<Q', payload, 0)[0]
    hp = struct.unpack_from('<i', payload, 8)[0]
    max_hp = struct.unpack_from('<i', payload, 12)[0]
    x = struct.unpack_from('<f', payload, 16)[0]
    y = struct.unpack_from('<f', payload, 20)[0]
    z = struct.unpack_from('<f', payload, 24)[0]
    return {'entity': entity, 'hp': hp, 'max_hp': max_hp, 'x': x, 'y': y, 'z': z}

# ━━━ 연결 + 로그인 ━━━

def connect_and_login(port=7777, username='hero', password='pass123', char_id=1):
    """FieldServer 직접 연결 -> Login -> CharSelect -> 몬스터 스폰 수집"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(('127.0.0.1', port))

    # Login
    uname = username.encode()
    pw = password.encode()
    login_payload = bytes([len(uname)]) + uname + bytes([len(pw)]) + pw
    sock.sendall(build_packet(60, login_payload))
    msg_type, payload = recv_packet_type(sock, 61, timeout=5.0)
    assert payload[0] == 0, f"Login failed: result={payload[0]}"

    # Char Select
    sock.sendall(build_packet(64, struct.pack('<I', char_id)))
    msg_type, payload = recv_packet_type(sock, 65, timeout=5.0)
    assert payload[0] == 0, f"CharSelect failed: result={payload[0]}"
    entity_id = struct.unpack('<Q', payload[1:9])[0]

    # Collect all pending packets (MONSTER_SPAWN + possible monster attacks)
    all_packets = collect_packets(sock, timeout=0.5)
    monsters = []
    for pkt_type, pkt_payload in all_packets:
        if pkt_type == 110:  # MONSTER_SPAWN
            m = parse_monster_spawn(pkt_payload)
            if m:
                monsters.append(m)

    return sock, entity_id, monsters

# ━━━ 테스트 프레임워크 ━━━
passed = 0
failed = 0
total = 0

def run_test(name, func):
    global passed, failed, total
    total += 1
    time.sleep(1.0)
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

    if not os.path.exists(field_exe):
        print(f"ERROR: {field_exe} not found. Build first!")
        sys.exit(1)

    p1 = subprocess.Popen([field_exe, '7777'], cwd=build_dir,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server_procs = [p1]
    time.sleep(1.5)

def stop_servers():
    for p in server_procs:
        try:
            p.terminate()
            p.wait(timeout=3)
        except:
            p.kill()

# ━━━ 테스트 구현 ━━━

def test_monster_spawn():
    """로그인 후 zone 1의 몬스터 5마리 MONSTER_SPAWN 수신 확인"""
    sock, player_eid, monsters = connect_and_login()
    try:
        assert len(monsters) == 5, f"Expected 5 monsters in zone 1, got {len(monsters)}"

        # 고블린 3마리 (monster_id=1)
        goblins = [m for m in monsters if m['monster_id'] == 1]
        assert len(goblins) == 3, f"Expected 3 goblins, got {len(goblins)}"
        for g in goblins:
            assert g['level'] == 5, f"Goblin level should be 5, got {g['level']}"
            assert g['hp'] == 100, f"Goblin HP should be 100, got {g['hp']}"
            assert g['max_hp'] == 100, f"Goblin max_hp should be 100, got {g['max_hp']}"

        # 늑대 2마리 (monster_id=2)
        wolves = [m for m in monsters if m['monster_id'] == 2]
        assert len(wolves) == 2, f"Expected 2 wolves, got {len(wolves)}"
        for w in wolves:
            assert w['level'] == 10, f"Wolf level should be 10, got {w['level']}"
            assert w['hp'] == 200, f"Wolf HP should be 200, got {w['hp']}"
    finally:
        sock.close()

def test_kill_monster():
    """고블린 공격 -> 원킬 + EXP 보상"""
    sock, player_eid, monsters = connect_and_login()
    try:
        # 가장 가까운 고블린 (150,150) 찾기
        goblins = [m for m in monsters if m['monster_id'] == 1]
        assert len(goblins) > 0, "No goblins found"
        target_goblin = None
        for g in goblins:
            if abs(g['x'] - 150.0) < 1.0 and abs(g['y'] - 150.0) < 1.0:
                target_goblin = g
                break
        if target_goblin is None:
            target_goblin = goblins[0]

        # 타겟 근처로 이동 (공격 범위 내 보장)
        move_near(sock, target_goblin['x'] + 30, target_goblin['y'])

        # 현재 EXP 확인
        sock.sendall(build_packet(90))  # STAT_QUERY
        _, payload = recv_packet_type(sock, 91)
        before = parse_stat_sync(payload)

        # 공격 (몬스터 공격 101 필터링)
        sock.sendall(build_packet(100, struct.pack('<Q', target_goblin['entity'])))
        _, payload = recv_my_attack_result(sock, player_eid, timeout=3.0)
        r = parse_attack_result(payload)
        assert r is not None, "Failed to parse ATTACK_RESULT"
        assert r['result'] == 0, f"Expected SUCCESS(0), got {r['result']}"
        assert r['damage'] == 103, f"Expected damage 103 (108-5), got {r['damage']}"
        assert r['target_hp'] == 0, f"Goblin should be dead, HP={r['target_hp']}"

        # COMBAT_DIED
        _, payload = recv_packet_type(sock, 102, timeout=3.0)
        dead = struct.unpack('<Q', payload[:8])[0]
        killer = struct.unpack('<Q', payload[8:16])[0]
        assert dead == target_goblin['entity'], f"Dead should be goblin"
        assert killer == player_eid, f"Killer should be player"

        # STAT_SYNC (EXP 증가)
        _, payload = recv_packet_type(sock, 91, timeout=3.0)
        after = parse_stat_sync(payload)
        exp_gained = after['exp'] - before['exp']
        assert exp_gained == 50, f"Expected +50 EXP (Goblin Lv5*10), got +{exp_gained}"
    finally:
        sock.close()

def test_dead_monster_attack():
    """죽은 몬스터 재공격 -> TARGET_DEAD"""
    sock, player_eid, monsters = connect_and_login()
    try:
        goblins = [m for m in monsters if m['monster_id'] == 1]
        assert len(goblins) > 0, "No alive goblins found"
        target = goblins[0]

        # 타겟 근처로 이동 (공격 범위 내 보장)
        move_near(sock, target['x'] + 30, target['y'])

        # 고블린 킬 (몬스터 공격 101 필터링)
        sock.sendall(build_packet(100, struct.pack('<Q', target['entity'])))
        _, payload = recv_my_attack_result(sock, player_eid)
        r = parse_attack_result(payload)
        assert r['result'] == 0 and r['target_hp'] == 0, \
            f"Failed to kill goblin: result={r['result']}, hp={r['target_hp']}"

        # COMBAT_DIED 수신
        recv_packet_type(sock, 102)

        # 나머지 패킷 정리 (STAT_SYNC 등)
        drain(sock, wait=0.3)

        # 죽은 고블린 재공격 (TARGET_DEAD 체크는 쿨타임보다 우선)
        sock.sendall(build_packet(100, struct.pack('<Q', target['entity'])))
        _, payload = recv_my_attack_result(sock, player_eid, timeout=3.0)
        r = parse_attack_result(payload)
        assert r['result'] == 2, f"Expected TARGET_DEAD(2), got {r['result']}"
    finally:
        sock.close()

def test_monster_respawn():
    """몬스터 킬 후 리스폰 대기 -> MONSTER_RESPAWN 수신"""
    sock, player_eid, monsters = connect_and_login()
    try:
        goblins = [m for m in monsters if m['monster_id'] == 1]
        assert len(goblins) > 0, "No alive goblins found"
        target = goblins[0]

        # 타겟 근처로 이동 (공격 범위 내 보장)
        move_near(sock, target['x'] + 30, target['y'])

        # 고블린 킬 (몬스터 공격 101 필터링)
        sock.sendall(build_packet(100, struct.pack('<Q', target['entity'])))
        _, payload = recv_my_attack_result(sock, player_eid)
        r = parse_attack_result(payload)
        assert r['result'] == 0, f"Kill failed: result={r['result']}"

        # COMBAT_DIED 수신
        recv_packet_type(sock, 102)

        # 리스폰 대기 (고블린 respawn_time=5.0초)
        # 이전 테스트에서 죽은 다른 몬스터의 리스폰이 먼저 올 수 있으므로 entity 필터링
        _, payload = recv_monster_respawn_for(sock, target['entity'], timeout=10.0)
        respawn = parse_monster_respawn(payload)
        assert respawn is not None, "Failed to parse MONSTER_RESPAWN"
        assert respawn['hp'] == 100, f"Respawned HP should be 100, got {respawn['hp']}"
        assert respawn['max_hp'] == 100, f"Respawned max_hp should be 100, got {respawn['max_hp']}"
    finally:
        sock.close()

def test_monster_aggro():
    """몬스터 어그로 -> 플레이어 공격 감지"""
    sock, player_eid, monsters = connect_and_login()
    try:
        monster_eids = [m['entity'] for m in monsters]

        # 몬스터의 첫 공격은 connect_and_login의 collect_packets에서 소비됨
        # 다음 공격 대기 (쿨타임 2.0초)
        _, payload = recv_packet_type(sock, 101, timeout=4.0)
        r = parse_attack_result(payload)
        assert r is not None, "Failed to parse ATTACK_RESULT from monster"
        assert r['result'] == 0, f"Monster attack should succeed, got {r['result']}"
        assert r['attacker'] in monster_eids, f"Attacker {r['attacker']} not a monster"
        assert r['target'] == player_eid, "Target should be the player"
        assert r['damage'] == 1, f"Goblin->Warrior damage should be 1, got {r['damage']}"
    finally:
        sock.close()

def test_kill_after_respawn():
    """몬스터 킬 -> 리스폰 -> 다시 킬 -> EXP 재획득"""
    sock, player_eid, monsters = connect_and_login()
    try:
        goblins = [m for m in monsters if m['monster_id'] == 1]
        assert len(goblins) > 0, "No alive goblins found"
        target = goblins[0]

        # 타겟 근처로 이동
        move_near(sock, target['x'] + 30, target['y'])

        # 현재 EXP
        sock.sendall(build_packet(90))
        _, payload = recv_packet_type(sock, 91)
        before = parse_stat_sync(payload)

        # 첫 킬 (몬스터 공격 101 필터링)
        sock.sendall(build_packet(100, struct.pack('<Q', target['entity'])))
        recv_my_attack_result(sock, player_eid)  # ATTACK_RESULT
        recv_packet_type(sock, 102)  # COMBAT_DIED
        recv_packet_type(sock, 91)   # STAT_SYNC (EXP +50)

        # 리스폰 대기 (다른 몬스터 리스폰 필터링)
        _, payload = recv_monster_respawn_for(sock, target['entity'], timeout=10.0)
        respawn = parse_monster_respawn(payload)
        assert respawn['entity'] == target['entity'], "Wrong entity respawned"
        assert respawn['hp'] == 100, "Respawned HP should be full"

        # 쿨타임 대기 후 재킬
        time.sleep(0.5)
        drain(sock)  # 중간에 받은 몬스터 공격 등 비움

        sock.sendall(build_packet(100, struct.pack('<Q', target['entity'])))
        _, payload = recv_my_attack_result(sock, player_eid)
        r = parse_attack_result(payload)
        assert r['result'] == 0, f"Second kill attack should succeed, got {r['result']}"
        assert r['target_hp'] == 0, f"Goblin should die again, HP={r['target_hp']}"

        # 두 번째 킬 EXP 확인
        recv_packet_type(sock, 102)  # COMBAT_DIED
        _, payload = recv_packet_type(sock, 91)  # STAT_SYNC
        after = parse_stat_sync(payload)

        total_exp = after['exp'] - before['exp']
        assert total_exp == 100, f"Expected +100 total EXP (2 kills * 50), got +{total_exp}"
    finally:
        sock.close()

# ━━━ 실행 ━━━
if __name__ == '__main__':
    print("=" * 50)
    print("  Session 14: Monster/NPC System Tests")
    print("=" * 50)
    print()

    start_servers()

    try:
        print("[1] Monster Spawning")
        run_test("Monster spawn verification (5 in zone 1)", test_monster_spawn)

        print()
        print("[2] PvE Combat")
        run_test("Kill goblin (one-hit, EXP=50)", test_kill_monster)
        run_test("Attack dead monster -> TARGET_DEAD", test_dead_monster_attack)

        print()
        print("[3] Respawn & Aggro")
        run_test("Monster respawn after death", test_monster_respawn)
        run_test("Monster aggro attacks player", test_monster_aggro)

        print()
        print("[4] Advanced")
        run_test("Kill -> respawn -> kill again (EXP x2)", test_kill_after_respawn)

    finally:
        stop_servers()

    print()
    print("=" * 50)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
