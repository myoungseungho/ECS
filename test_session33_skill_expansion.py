"""Session 33: Skill Expansion Tests — 8 tests
스킬 확장: 21개 스킬, 레벨 시스템, 스킬 포인트

MsgType:
  SKILL_LIST_REQ(150)   C→S: empty
  SKILL_LIST_RESP(151)  S→C: [count(1) {id(4) name(16) cd(4) dmg(4) mp(4) range(4) type(1) skill_level(1) effect(1) min_level(4)}...]
  SKILL_USE(152)        C→S: [skill_id(4) target_entity(8)]
  SKILL_RESULT(153)     S→C: [result(1) skill_id(4) caster(8) target(8) damage(4) target_hp(4)]
  SKILL_LEVEL_UP(260)   C→S: [skill_id(4)]
  SKILL_LEVEL_UP_RESULT(261) S→C: [result(1) skill_id(4) new_level(1) skill_points(4)]
  SKILL_POINT_INFO(262) S→C: [skill_points(4) total_spent(4)]
"""
import socket, struct, time, subprocess, sys, os

PORT = 7777
HEADER = 6

# MsgType IDs
SKILL_LIST_REQ = 150
SKILL_LIST_RESP = 151
SKILL_USE = 152
SKILL_RESULT = 153
SKILL_LEVEL_UP = 260
SKILL_LEVEL_UP_RESULT = 261
SKILL_POINT_INFO = 262
STAT_ADD_EXP = 92
STAT_SYNC = 91

# SkillResult
SK_SUCCESS = 0
SK_SKILL_NOT_FOUND = 1
SK_COOLDOWN = 2
SK_NO_MP = 3
SK_LEVEL_TOO_LOW = 8

# SkillLevelUpResult
SLU_SUCCESS = 0
SLU_NO_SKILL_POINTS = 1
SLU_SKILL_NOT_FOUND = 2
SLU_MAX_LEVEL = 3
SLU_LEVEL_TOO_LOW = 4


def start_server():
    p = subprocess.Popen(
        [os.path.join("build", "FieldServer.exe"), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return p


def send(s, msg_type, payload=b""):
    length = HEADER + len(payload)
    s.sendall(struct.pack("<IH", length, msg_type) + payload)


def recv_pkt(s, timeout=2.0):
    s.settimeout(timeout)
    hdr = b""
    while len(hdr) < HEADER:
        hdr += s.recv(HEADER - len(hdr))
    length, msg_type = struct.unpack("<IH", hdr)
    payload = b""
    remaining = length - HEADER
    while len(payload) < remaining:
        payload += s.recv(remaining - len(payload))
    return msg_type, payload


def connect_and_login(username="tester"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", PORT))
    uname = username.encode()
    pw = b"pass"
    send(s, 60, bytes([len(uname)]) + uname + bytes([len(pw)]) + pw)
    recv_pkt(s)
    send(s, 62)
    _, cl = recv_pkt(s)
    char_id = struct.unpack_from("<I", cl, 1)[0] if cl[0] > 0 else 2000
    send(s, 64, struct.pack("<I", char_id))
    _, eg = recv_pkt(s)
    entity = struct.unpack_from("<Q", eg, 1)[0]
    drain(s)
    return s, entity


def drain(s, timeout=0.3):
    pkts = []
    try:
        s.settimeout(timeout)
        while True:
            pkts.append(recv_pkt(s, timeout))
    except:
        pass
    return pkts


def recv_specific(s, target_type, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            remaining = max(0.1, deadline - time.time())
            t, p = recv_pkt(s, remaining)
            if t == target_type:
                return t, p
        except:
            break
    return None, None


def parse_skill_list(payload):
    """Parse SKILL_LIST_RESP: count(1) {id(4)+name(16)+cd(4)+dmg(4)+mp(4)+range(4)+type(1)+level(1)+effect(1)+min_level(4)}..."""
    count = payload[0]
    skills = []
    per_skill = 43
    for i in range(count):
        off = 1 + i * per_skill
        skill_id = struct.unpack_from("<i", payload, off)[0]
        name = payload[off+4:off+20].split(b'\x00')[0].decode('ascii', errors='replace')
        cd_ms = struct.unpack_from("<i", payload, off+20)[0]
        dmg = struct.unpack_from("<i", payload, off+24)[0]
        mp = struct.unpack_from("<i", payload, off+28)[0]
        range_v = struct.unpack_from("<i", payload, off+32)[0]
        job_class = payload[off+36]
        skill_level = payload[off+37]
        effect = payload[off+38]
        min_level = struct.unpack_from("<i", payload, off+39)[0]
        skills.append({
            "id": skill_id, "name": name, "cd": cd_ms, "dmg": dmg,
            "mp": mp, "range": range_v, "job": job_class,
            "level": skill_level, "effect": effect, "min_level": min_level
        })
    return skills


def parse_skill_result(payload):
    """SKILL_RESULT: result(1) skill_id(4) caster(8) target(8) damage(4) target_hp(4)"""
    result = payload[0]
    skill_id = struct.unpack_from("<i", payload, 1)[0]
    caster = struct.unpack_from("<Q", payload, 5)[0]
    target = struct.unpack_from("<Q", payload, 13)[0]
    damage = struct.unpack_from("<i", payload, 21)[0]
    target_hp = struct.unpack_from("<i", payload, 25)[0]
    return result, skill_id, caster, target, damage, target_hp


def parse_level_up_result(payload):
    """SKILL_LEVEL_UP_RESULT: result(1) skill_id(4) new_level(1) skill_points(4)"""
    result = payload[0]
    skill_id = struct.unpack_from("<i", payload, 1)[0]
    new_level = payload[5]
    skill_points = struct.unpack_from("<i", payload, 6)[0]
    return result, skill_id, new_level, skill_points


# ━━━ Tests ━━━

def test_expanded_skill_list():
    """Test 1: 확장된 스킬 목록 확인 — 전사는 공용+전사 스킬 수신"""
    s, e = connect_and_login("skill1")
    send(s, SKILL_LIST_REQ)
    t, p = recv_specific(s, SKILL_LIST_RESP)
    assert t == SKILL_LIST_RESP, "Should receive SKILL_LIST_RESP"
    skills = parse_skill_list(p)

    # hero 계정의 Warrior_Kim은 Lv50 전사
    # 공용 스킬 (min_level 충족): BasicAttack(1), Heal(2), Dash(5), Provoke(10) = 4개
    # 전사 스킬 (min_level 충족 Lv50): Slash(1), ShieldBash(5), PowerStrike(10), Whirlwind(15), Warcry(20) = 5개
    # 총 9개 (모두 min_level <= 50)
    skill_ids = [s["id"] for s in skills]
    assert 1 in skill_ids, "BasicAttack should be available"
    assert 10 in skill_ids, "Slash should be available"
    assert 14 in skill_ids, "Warcry should be available for Lv50 warrior"
    assert 13 in skill_ids, "Whirlwind should be available"
    assert 30 not in skill_ids, "Fireball(mage) should NOT be in warrior list"
    assert 20 not in skill_ids, "ArrowShot(archer) should NOT be in warrior list"

    # 확장 필드 검증
    basic = next(s for s in skills if s["id"] == 1)
    assert basic["effect"] == 0, f"BasicAttack effect should be DAMAGE(0), got {basic['effect']}"
    assert basic["min_level"] == 1, f"BasicAttack min_level should be 1, got {basic['min_level']}"
    assert basic["level"] == 0, f"BasicAttack should be unlearned (level 0), got {basic['level']}"

    s.close()
    print(f"  PASS: Warrior skill list has {len(skills)} skills with expanded fields")


def test_skill_level_up():
    """Test 2: 스킬 레벨업 — 포인트 소모 + 레벨 증가"""
    s, e = connect_and_login("skill2")
    # Warrior_Kim Lv50 → 50 스킬 포인트 보유

    # Slash(10) 레벨업
    send(s, SKILL_LEVEL_UP, struct.pack("<i", 10))
    t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
    assert t == SKILL_LEVEL_UP_RESULT
    result, skill_id, new_level, sp = parse_level_up_result(p)
    assert result == SLU_SUCCESS, f"Expected SUCCESS, got {result}"
    assert skill_id == 10
    assert new_level == 1, f"Expected level 1, got {new_level}"
    assert sp == 49, f"Expected 49 points remaining, got {sp}"

    # 한번 더 레벨업 → level 2
    send(s, SKILL_LEVEL_UP, struct.pack("<i", 10))
    t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
    result, skill_id, new_level, sp = parse_level_up_result(p)
    assert result == SLU_SUCCESS
    assert new_level == 2, f"Expected level 2, got {new_level}"
    assert sp == 48, f"Expected 48 points remaining, got {sp}"

    s.close()
    print(f"  PASS: Slash leveled to 2, points 50→48")


def test_skill_level_up_no_points():
    """Test 3: 포인트 없이 레벨업 시도 → NO_SKILL_POINTS"""
    s, e = connect_and_login("skill3")

    # guest 계정 Archer_Park Lv20 → 20 포인트
    # 20포인트 모두 소진
    for i in range(20):
        send(s, SKILL_LEVEL_UP, struct.pack("<i", 1))  # BasicAttack 반복 (max lv5)
        t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
        result, _, new_level, sp = parse_level_up_result(p)
        if result != SLU_SUCCESS:
            # 만렙 도달 시 다른 스킬로 전환
            send(s, SKILL_LEVEL_UP, struct.pack("<i", 20))  # ArrowShot
            t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
            result, _, _, sp = parse_level_up_result(p)

    # 포인트 0일 때 레벨업 시도
    send(s, SKILL_LEVEL_UP, struct.pack("<i", 2))  # Heal
    t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
    result, _, _, sp = parse_level_up_result(p)
    assert result == SLU_NO_SKILL_POINTS, f"Expected NO_SKILL_POINTS(1), got {result}"
    assert sp == 0, f"Expected 0 points, got {sp}"

    s.close()
    print(f"  PASS: no skill points → NO_SKILL_POINTS error")


def test_skill_max_level():
    """Test 4: 만렙 스킬 레벨업 시도 → MAX_LEVEL"""
    s, e = connect_and_login("skill4")
    # Lv50 → 50 포인트. BasicAttack 5번 레벨업하면 만렙

    for i in range(5):
        send(s, SKILL_LEVEL_UP, struct.pack("<i", 1))
        t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
        result, _, new_level, sp = parse_level_up_result(p)
        assert result == SLU_SUCCESS, f"Level {i+1} should succeed"

    # 6번째 시도 → 만렙
    send(s, SKILL_LEVEL_UP, struct.pack("<i", 1))
    t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
    result, _, new_level, sp = parse_level_up_result(p)
    assert result == SLU_MAX_LEVEL, f"Expected MAX_LEVEL(3), got {result}"
    assert new_level == 5, f"Should still be level 5"

    s.close()
    print(f"  PASS: skill at max level 5 → MAX_LEVEL error")


def test_skill_level_reflected_in_list():
    """Test 5: 레벨업 후 스킬 목록에 레벨이 반영되는지 확인"""
    s, e = connect_and_login("skill5")

    # Slash(10) 3번 레벨업
    for i in range(3):
        send(s, SKILL_LEVEL_UP, struct.pack("<i", 10))
        recv_specific(s, SKILL_LEVEL_UP_RESULT)

    # 스킬 목록 조회
    send(s, SKILL_LIST_REQ)
    t, p = recv_specific(s, SKILL_LIST_RESP)
    skills = parse_skill_list(p)
    slash = next((s for s in skills if s["id"] == 10), None)
    assert slash is not None, "Slash should be in list"
    assert slash["level"] == 3, f"Slash should be level 3, got {slash['level']}"

    s.close()
    print(f"  PASS: Slash level 3 reflected in SKILL_LIST_RESP")


def test_level_scaling_damage():
    """Test 6: 스킬 레벨에 따른 데미지 스케일링 검증"""
    s, e = connect_and_login("skill6")
    drain(s)

    # 몬스터 스폰 대기 후 SPATIAL_QUERY로 찾기
    # 대신 entity 0으로 자기 자신 대상... 아니면 스킬 사용 결과로 간접 확인

    # Heal(2)로 테스트: 자힐이니까 target=self
    # 먼저 데미지를 받아서 HP를 줄이자
    send(s, 93, struct.pack("<i", 500))  # STAT_TAKE_DMG: 500 raw damage
    drain(s, 0.3)

    # 레벨업 없이 Heal 사용 → 기본 힐량
    send(s, SKILL_USE, struct.pack("<iQ", 2, e))  # Heal on self
    t, p = recv_specific(s, SKILL_RESULT)
    assert t == SKILL_RESULT
    result1, _, _, _, heal1, _ = parse_skill_result(p)
    assert result1 == SK_SUCCESS, f"Heal should succeed, got {result1}"

    # Heal 쿨다운 대기 (5초... 너무 길다)
    # 대신 새로운 접속으로 테스트
    s.close()

    # 새로운 캐릭터로 Heal lv3 테스트
    s2, e2 = connect_and_login("skill6b")
    drain(s2)

    # Heal 3번 레벨업
    for i in range(3):
        send(s2, SKILL_LEVEL_UP, struct.pack("<i", 2))
        recv_specific(s2, SKILL_LEVEL_UP_RESULT)

    # 데미지 받기
    send(s2, 93, struct.pack("<i", 500))
    drain(s2, 0.3)

    # Heal 사용 (lv3 = 1.4x 스케일링)
    send(s2, SKILL_USE, struct.pack("<iQ", 2, e2))
    t2, p2 = recv_specific(s2, SKILL_RESULT)
    result2, _, _, _, heal2, _ = parse_skill_result(p2)
    assert result2 == SK_SUCCESS

    # lv3 힐량 > lv0 힐량 (1.4x vs 1.0x)
    assert heal2 > heal1, f"Lv3 heal ({heal2}) should be > Lv0 heal ({heal1})"

    s2.close()
    print(f"  PASS: Heal lv0={heal1}, lv3={heal2} — level scaling works!")


def test_nonexistent_skill_level_up():
    """Test 7: 존재하지 않는 스킬 레벨업 → SKILL_NOT_FOUND"""
    s, e = connect_and_login("skill7")
    send(s, SKILL_LEVEL_UP, struct.pack("<i", 999))
    t, p = recv_specific(s, SKILL_LEVEL_UP_RESULT)
    assert t == SKILL_LEVEL_UP_RESULT
    result, skill_id, _, _ = parse_level_up_result(p)
    assert result == SLU_SKILL_NOT_FOUND, f"Expected SKILL_NOT_FOUND(2), got {result}"
    assert skill_id == 999
    s.close()
    print(f"  PASS: nonexistent skill → SKILL_NOT_FOUND")


def test_self_buff_skill():
    """Test 8: 자기 버프 스킬 (Warcry) 사용 확인"""
    s, e = connect_and_login("skill8")
    drain(s)

    # 먼저 스탯 확인
    send(s, 90)  # STAT_QUERY
    t, p = recv_specific(s, STAT_SYNC)
    atk_before = struct.unpack_from("<i", p, 20)[0]  # atk at offset 20

    # Warcry(14) 사용 (자기 버프: ATK +20%)
    send(s, SKILL_USE, struct.pack("<iQ", 14, e))
    t, p = recv_specific(s, SKILL_RESULT)
    assert t == SKILL_RESULT
    result, _, _, _, buff_amount, _ = parse_skill_result(p)
    assert result == SK_SUCCESS, f"Warcry should succeed, got {result}"
    assert buff_amount > 0, f"Buff amount should be > 0, got {buff_amount}"

    # 스탯 확인 — ATK 증가
    drain(s, 0.2)
    send(s, 90)  # STAT_QUERY
    t, p = recv_specific(s, STAT_SYNC)
    atk_after = struct.unpack_from("<i", p, 20)[0]
    assert atk_after > atk_before, f"ATK should increase after Warcry: {atk_before}→{atk_after}"

    s.close()
    print(f"  PASS: Warcry ATK buff: {atk_before}→{atk_after} (+{buff_amount})")


# ━━━ Runner ━━━

def main():
    server = None
    if "--no-server" not in sys.argv:
        server = start_server()
        print(f"Server started (PID={server.pid})")

    tests = [
        test_expanded_skill_list,
        test_skill_level_up,
        test_skill_level_up_no_points,
        test_skill_max_level,
        test_skill_level_reflected_in_list,
        test_level_scaling_damage,
        test_nonexistent_skill_level_up,
        test_self_buff_skill,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            print(f"\n{test.__doc__}")
            test()
            passed += 1
        except Exception as ex:
            failed += 1
            print(f"  FAIL: {ex}")

    print(f"\n{'='*50}")
    print(f"Session 33 Skill Expansion: {passed}/{len(tests)} passed, {failed} failed")

    if server:
        server.terminate()
        server.wait(timeout=5)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
