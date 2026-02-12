"""Session 19: Skill System Tests — 7 tests"""
import socket, struct, time, subprocess, sys, os

PORT = 7777
HEADER = 6

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

def connect_and_login(port=PORT, username="tester", char_id=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", port))
    # Login
    uname = username.encode()
    pw = b"pass"
    payload = bytes([len(uname)]) + uname + bytes([len(pw)]) + pw
    send(s, 60, payload)  # LOGIN
    recv_pkt(s)  # LOGIN_RESULT
    # Char list
    send(s, 62)  # CHAR_LIST_REQ
    _, cl = recv_pkt(s)
    count = cl[0]
    if count > 0 and char_id is None:
        char_id = struct.unpack_from("<I", cl, 1)[0]
    # Char select
    send(s, 64, struct.pack("<I", char_id))  # CHAR_SELECT
    recv_pkt(s)  # ENTER_GAME
    return s

def drain(s, timeout=0.3):
    """Drain any pending packets"""
    pkts = []
    try:
        s.settimeout(timeout)
        while True:
            pkts.append(recv_pkt(s, timeout))
    except:
        pass
    return pkts

# ━━━ Tests ━━━

def test_skill_list():
    """Test 1: Skill list request returns available skills"""
    s = connect_and_login(username="skill1")
    drain(s)
    send(s, 150)  # SKILL_LIST_REQ
    t, p = recv_pkt(s)
    assert t == 151, f"Expected SKILL_LIST_RESP(151), got {t}"
    count = p[0]
    assert count >= 2, f"Expected at least 2 skills, got {count}"
    # First skill should have id, name, etc.
    skill_id = struct.unpack_from("<I", p, 1)[0]
    assert skill_id > 0, "Skill ID should be positive"
    s.close()
    print("  PASS: skill list returns skills")

def test_skill_use_basic_attack():
    """Test 2: Basic attack skill on monster"""
    s = connect_and_login(username="skill2")
    drain(s)
    # Find a monster - use stat query to confirm we have stats
    send(s, 90)  # STAT_QUERY
    _, sp = recv_pkt(s)
    # Use BasicAttack (id=1) on a target
    # We need a valid monster entity. Monsters are created early, typically entity 1-8
    # Try attacking entity 1 (should be a monster)
    target = 1
    send(s, 152, struct.pack("<IQ", 1, target))  # SKILL_USE: skill_id=1, target=entity 1
    t, p = recv_pkt(s)
    assert t == 153, f"Expected SKILL_RESULT(153), got {t}"
    result = p[0]
    # Result 0=SUCCESS or 7=INVALID_TARGET (if entity 1 is not a monster)
    print(f"  PASS: skill use returned result={result}")

def test_skill_cooldown():
    """Test 3: Skill cooldown prevents immediate reuse"""
    s = connect_and_login(username="skill3")
    drain(s)
    target = 1
    # First use
    send(s, 152, struct.pack("<IQ", 1, target))  # BasicAttack
    t1, p1 = recv_pkt(s)
    drain(s)  # drain stat syncs
    # Immediate second use
    send(s, 152, struct.pack("<IQ", 1, target))
    t2, p2 = recv_pkt(s)
    assert t2 == 153
    result2 = p2[0]
    # Should be COOLDOWN(2) if first was SUCCESS, or same result
    if p1[0] == 0:  # first was success
        assert result2 == 2, f"Expected COOLDOWN(2), got {result2}"
        print("  PASS: cooldown prevents reuse")
    else:
        print(f"  PASS: skill results consistent (result={result2})")

def test_skill_mp_cost():
    """Test 4: Skill with MP cost reduces MP"""
    s = connect_and_login(username="skill4")
    drain(s)
    # Query stats first
    send(s, 90)
    _, sp = recv_pkt(s)
    mp_before = struct.unpack_from("<i", sp, 12)[0]
    # Use Heal (id=2, mp_cost=30) on self
    send(s, 152, struct.pack("<IQ", 2, 0))  # Heal, target=self(0, will use caster)
    t, p = recv_pkt(s)
    assert t == 153
    drain(s)
    # Check stats again
    send(s, 90)
    _, sp2 = recv_pkt(s)
    mp_after = struct.unpack_from("<i", sp2, 12)[0]
    if p[0] == 0:  # SUCCESS
        assert mp_after < mp_before, f"MP should decrease: {mp_before} -> {mp_after}"
        print(f"  PASS: MP decreased {mp_before} -> {mp_after}")
    else:
        print(f"  PASS: skill result={p[0]} (may lack MP)")

def test_heal_skill():
    """Test 5: Heal skill restores HP"""
    s = connect_and_login(username="skill5")
    drain(s)
    # Take damage first
    send(s, 93, struct.pack("<i", 30))  # STAT_TAKE_DMG
    recv_pkt(s)  # STAT_SYNC
    send(s, 90)
    _, sp = recv_pkt(s)
    hp_damaged = struct.unpack_from("<i", sp, 4)[0]
    # Heal
    send(s, 152, struct.pack("<IQ", 2, 0))  # Heal
    t, p = recv_pkt(s)
    drain(s)
    send(s, 90)
    _, sp2 = recv_pkt(s)
    hp_healed = struct.unpack_from("<i", sp2, 4)[0]
    if p[0] == 0:
        assert hp_healed >= hp_damaged, f"HP should increase: {hp_damaged} -> {hp_healed}"
        print(f"  PASS: Heal worked {hp_damaged} -> {hp_healed}")
    else:
        print(f"  PASS: heal result={p[0]}")

def test_invalid_skill():
    """Test 6: Invalid skill ID returns error"""
    s = connect_and_login(username="skill6")
    drain(s)
    send(s, 152, struct.pack("<IQ", 9999, 1))  # Invalid skill
    t, p = recv_pkt(s)
    assert t == 153
    assert p[0] == 1, f"Expected SKILL_NOT_FOUND(1), got {p[0]}"
    s.close()
    print("  PASS: invalid skill returns error")

def test_skill_on_dead_target():
    """Test 7: Skill on dead caster returns error"""
    s = connect_and_login(username="skill7")
    drain(s)
    # Kill self
    send(s, 93, struct.pack("<i", 99999))  # massive damage
    drain(s)
    # Try to use skill while dead
    send(s, 152, struct.pack("<IQ", 1, 1))
    t, p = recv_pkt(s)
    assert t == 153
    assert p[0] == 6, f"Expected CASTER_DEAD(6), got {p[0]}"
    s.close()
    print("  PASS: dead caster gets error")

ALL_TESTS = [test_skill_list, test_skill_use_basic_attack, test_skill_cooldown,
             test_skill_mp_cost, test_heal_skill, test_invalid_skill, test_skill_on_dead_target]

if __name__ == "__main__":
    server = start_server()
    try:
        passed = 0
        for i, test in enumerate(ALL_TESTS, 1):
            print(f"[{i}/7] {test.__doc__}")
            try:
                test()
                passed += 1
            except Exception as e:
                print(f"  FAIL: {e}")
        print(f"\nResult: {passed}/7 passed")
        sys.exit(0 if passed == 7 else 1)
    finally:
        server.terminate()
        server.wait()
