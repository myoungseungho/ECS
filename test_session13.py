"""
Session 13: Combat System Tests
- CombatComponent: 공격 사거리, 쿨타임
- CombatSystem: 쿨타임 감소
- 패킷: ATTACK_REQ(100), ATTACK_RESULT(101), COMBAT_DIED(102), RESPAWN_REQ(103), RESPAWN_RESULT(104)
- 데미지 공식: max(1, attacker.ATK - target.DEF)
- 킬 → EXP 보상, 부활 시스템

캐릭터 스펙:
  Warrior_Kim (hero/1): Lv50, ATK=108, DEF=103, HP=1080, zone=1, pos=(100,100)
  Archer_Park (guest/3): Lv20, ATK=66,  DEF=22,  HP=360,  zone=1, pos=(200,200)
  거리: sqrt((200-100)^2 + (200-100)^2) = ~141.4 (사거리 200 이내)

  Warrior→Archer 데미지: max(1, 108-22) = 86
  Archer→Warrior 데미지: max(1, 66-103) = 1 (최소)
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

def drain(sock, wait=0.2):
    """소켓 버퍼의 남은 패킷을 모두 소비"""
    sock.settimeout(wait)
    try:
        while True:
            sock.recv(4096)
    except:
        pass
    sock.settimeout(5.0)

def recv_my_attack_result(sock, my_eid, timeout=5.0):
    """내 공격 결과(ATTACK_RESULT)만 필터링 (Session 14 몬스터 공격 101 무시)"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            msg_type, payload = recv_packet(sock, timeout=remaining)
            if msg_type == 101:
                r = parse_attack_result(payload)
                if r and r['attacker'] == my_eid:
                    return msg_type, payload
        except (socket.timeout, OSError):
            break
    raise TimeoutError("Timed out waiting for my ATTACK_RESULT")

def connect_and_login(host='127.0.0.1', field_port=7777, username='hero',
                      password='pass123', char_id=1, retries=3):
    """FieldServer 직접 연결 → Login → CharSelect → Channel Join"""
    for attempt in range(retries):
        try:
            fs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            fs.settimeout(5.0)
            fs.connect((host, field_port))

            uname = username.encode()
            pw = password.encode()
            login_payload = bytes([len(uname)]) + uname + bytes([len(pw)]) + pw
            fs.sendall(build_packet(60, login_payload))
            # recv_packet_type: 다른 패킷(APPEAR 등) 무시하고 LOGIN_RESULT만 수신
            msg_type, payload = recv_packet_type(fs, 61, timeout=5.0)
            assert payload[0] == 0, f"Login failed: result={payload[0]}"

            fs.sendall(build_packet(64, struct.pack('<I', char_id)))
            msg_type, payload = recv_packet_type(fs, 65, timeout=5.0)
            assert payload[0] == 0, f"CharSelect failed: result={payload[0]}"
            entity_id = struct.unpack('<Q', payload[1:9])[0]

            # Channel join
            fs.sendall(build_packet(20, struct.pack('<i', 1)))
            msg_type, payload = recv_packet_type(fs, 22, timeout=5.0)

            drain(fs)
            return fs, entity_id
        except Exception as e:
            try: fs.close()
            except: pass
            if attempt < retries - 1:
                time.sleep(1.0)
                continue
            raise

def connect_two_players():
    """Warrior(hero/1) + Archer(guest/3), 둘 다 zone 1, channel 1"""
    sock_a, eid_a = connect_and_login(username='hero', char_id=1)
    sock_b, eid_b = connect_and_login(username='guest', password='guest', char_id=3)
    time.sleep(0.3)
    drain(sock_a)
    drain(sock_b)
    return sock_a, eid_a, sock_b, eid_b

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

# ━━━ 테스트 프레임워크 ━━━
passed = 0
failed = 0
total = 0

def run_test(name, func):
    global passed, failed, total
    total += 1
    time.sleep(1.5)  # IOCP 연결 해제 처리 대기
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

    # FieldServer만 직접 연결 (Gate 불필요)
    # DEVNULL: 파이프 버퍼 풀 방지 (PIPE는 서버 printf가 블로킹됨)
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

def test_basic_attack():
    """기본 공격: Warrior(ATK=108) → Archer(DEF=22, HP=360), damage=86"""
    sock_a, eid_a, sock_b, eid_b = connect_two_players()
    try:
        # ATTACK_REQ: target = Archer
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))
        msg_type, payload = recv_packet_type(sock_a, 101)
        r = parse_attack_result(payload)
        assert r is not None, "Failed to parse ATTACK_RESULT"
        assert r['result'] == 0, f"Expected SUCCESS(0), got {r['result']}"
        assert r['damage'] == 86, f"Expected damage 86 (108-22), got {r['damage']}"
        assert r['target_hp'] == 274, f"Expected HP 274 (360-86), got {r['target_hp']}"
        assert r['target_max_hp'] == 360, f"Expected max_hp 360, got {r['target_max_hp']}"
        assert r['attacker'] == eid_a, "Attacker ID mismatch"
        assert r['target'] == eid_b, "Target ID mismatch"
    finally:
        sock_a.close()
        sock_b.close()

def test_cooldown_and_range():
    """쿨타임 + 사거리 종합"""
    sock_a, eid_a, sock_b, eid_b = connect_two_players()
    try:
        # 1. 첫 공격 → 성공
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))
        msg_type, payload = recv_my_attack_result(sock_a, eid_a)
        r = parse_attack_result(payload)
        assert r['result'] == 0, f"First attack should succeed, got {r['result']}"

        # 2. 즉시 재공격 → 쿨타임 실패
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))
        msg_type, payload = recv_my_attack_result(sock_a, eid_a)
        r = parse_attack_result(payload)
        assert r['result'] == 4, f"Expected COOLDOWN(4), got {r['result']}"

        # 3. Warrior를 (5000, 5000, 0)으로 이동 + 쿨타임 대기
        sock_a.sendall(build_packet(10, struct.pack('<fff', 5000.0, 5000.0, 0.0)))
        time.sleep(2.0)  # 쿨타임(1.5초) + 서버 처리 여유

        # 4. 사거리 밖 공격 → 실패
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))
        msg_type, payload = recv_my_attack_result(sock_a, eid_a)
        r = parse_attack_result(payload)
        assert r['result'] == 3, f"Expected OUT_OF_RANGE(3), got {r['result']}"
    finally:
        sock_a.close()
        sock_b.close()

def test_kill_and_exp():
    """킬 → EXP 획득 + COMBAT_DIED + 사망 타겟 재공격 불가"""
    sock_a, eid_a, sock_b, eid_b = connect_two_players()
    try:
        # Warrior의 현재 EXP
        sock_a.sendall(build_packet(90))  # STAT_QUERY
        msg_type, payload = recv_packet_type(sock_a, 91)
        before = parse_stat_sync(payload)

        # Archer HP를 2로 낮추기
        # Archer DEF=22, TAKE_DMG(380): actual = max(1, 380-22) = 358, HP = 360-358 = 2
        sock_b.sendall(build_packet(93, struct.pack('<i', 380)))
        msg_type, payload = recv_packet_type(sock_b, 91)
        archer = parse_stat_sync(payload)
        assert archer['hp'] == 2, f"Archer HP should be 2, got {archer['hp']}"

        # Warrior kills Archer (damage=86 > 2)
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))

        # ATTACK_RESULT
        msg_type, payload = recv_packet_type(sock_a, 101)
        r = parse_attack_result(payload)
        assert r['result'] == 0, f"Kill attack should succeed"
        assert r['target_hp'] == 0, f"Target should be dead: HP={r['target_hp']}"

        # COMBAT_DIED (공격자 수신)
        msg_type, payload = recv_packet_type(sock_a, 102)
        dead = struct.unpack('<Q', payload[:8])[0]
        killer = struct.unpack('<Q', payload[8:16])[0]
        assert dead == eid_b, "Dead entity should be Archer"
        assert killer == eid_a, "Killer should be Warrior"

        # STAT_SYNC (Warrior EXP 증가)
        msg_type, payload = recv_packet_type(sock_a, 91)
        after = parse_stat_sync(payload)
        exp_gained = after['exp'] - before['exp']
        # Archer Lv20: EXP = 20 * 10 = 200
        assert exp_gained == 200, f"Expected +200 EXP, got +{exp_gained}"

        # 사망한 타겟 재공격 → TARGET_DEAD
        # (몬스터 공격 101이 섞일 수 있으므로 attacker 필터링)
        time.sleep(1.6)  # 쿨타임 대기
        drain(sock_a, wait=0.3)  # 대기 중 도착한 몬스터 공격 정리
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))
        msg_type, payload = recv_my_attack_result(sock_a, eid_a)
        r = parse_attack_result(payload)
        assert r['result'] == 2, f"Expected TARGET_DEAD(2), got {r['result']}"
    finally:
        sock_a.close()
        sock_b.close()

def test_edge_cases():
    """자기 공격 불가 + 존재하지 않는 타겟"""
    sock, eid = connect_and_login()
    try:
        # 자기 자신 공격
        sock.sendall(build_packet(100, struct.pack('<Q', eid)))
        msg_type, payload = recv_my_attack_result(sock, eid)
        r = parse_attack_result(payload)
        assert r['result'] == 6, f"Self: expected SELF_ATTACK(6), got {r['result']}"

        # 존재하지 않는 타겟
        sock.sendall(build_packet(100, struct.pack('<Q', 99999)))
        msg_type, payload = recv_my_attack_result(sock, eid)
        r = parse_attack_result(payload)
        assert r['result'] == 1, f"Nonexist: expected TARGET_NOT_FOUND(1), got {r['result']}"
    finally:
        sock.close()

def test_dead_attacker():
    """죽은 상태에서 공격 불가"""
    sock_a, eid_a, sock_b, eid_b = connect_two_players()
    try:
        # Warrior 자살 (STAT_TAKE_DMG 999999)
        sock_a.sendall(build_packet(93, struct.pack('<i', 999999)))
        msg_type, payload = recv_packet_type(sock_a, 91)
        stats = parse_stat_sync(payload)
        assert stats['hp'] == 0, f"Warrior should be dead, HP={stats['hp']}"

        # 죽은 Warrior가 Archer 공격 시도
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))
        msg_type, payload = recv_my_attack_result(sock_a, eid_a)
        r = parse_attack_result(payload)
        assert r['result'] == 5, f"Expected ATTACKER_DEAD(5), got {r['result']}"
    finally:
        sock_a.close()
        sock_b.close()

def test_respawn():
    """죽은 후 부활 → HP/MP 전회복 + 위치 초기화"""
    sock, eid = connect_and_login()
    try:
        # 스탯 확인
        sock.sendall(build_packet(90))
        msg_type, payload = recv_packet_type(sock, 91)
        before = parse_stat_sync(payload)

        # 살아있는 상태에서 부활 시도 → 실패
        sock.sendall(build_packet(103))  # RESPAWN_REQ
        msg_type, payload = recv_packet_type(sock, 104)
        assert payload[0] == 1, f"Expected NOT_DEAD(1), got {payload[0]}"

        # 자살
        sock.sendall(build_packet(93, struct.pack('<i', 999999)))
        msg_type, payload = recv_packet_type(sock, 91)
        dead = parse_stat_sync(payload)
        assert dead['hp'] == 0, "Should be dead"

        # 부활
        sock.sendall(build_packet(103))
        msg_type, payload = recv_packet_type(sock, 104)
        assert payload[0] == 0, f"Expected SUCCESS(0), got {payload[0]}"

        hp = struct.unpack('<i', payload[1:5])[0]
        mp = struct.unpack('<i', payload[5:9])[0]
        x = struct.unpack('<f', payload[9:13])[0]
        y = struct.unpack('<f', payload[13:17])[0]

        assert hp == before['max_hp'], f"HP should be max: {hp} vs {before['max_hp']}"
        assert mp == before['max_mp'], f"MP should be max: {mp} vs {before['max_mp']}"
        assert x == 100.0, f"Spawn x should be 100, got {x}"
        assert y == 100.0, f"Spawn y should be 100, got {y}"

        # 부활 후 스탯 동기화 확인
        msg_type, payload = recv_packet_type(sock, 91)
        alive = parse_stat_sync(payload)
        assert alive['hp'] == before['max_hp'], f"After respawn HP: {alive['hp']}"
    finally:
        sock.close()

# ━━━ 실행 ━━━
if __name__ == '__main__':
    print("=" * 50)
    print("  Session 13: Combat System Tests")
    print("=" * 50)
    print()

    start_servers()

    try:
        print("[1] Basic Combat")
        run_test("Basic attack (damage formula)", test_basic_attack)
        run_test("Cooldown + range check", test_cooldown_and_range)

        print()
        print("[2] Kill & Death")
        run_test("Kill -> EXP + attack dead fails", test_kill_and_exp)
        run_test("Dead attacker can't attack", test_dead_attacker)

        print()
        print("[3] Edge Cases & Respawn")
        run_test("Self-attack + nonexistent target", test_edge_cases)
        run_test("Respawn after death", test_respawn)

    finally:
        stop_servers()

    print()
    print("=" * 50)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
