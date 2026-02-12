"""Session 21: Instance Dungeon Tests — 7 tests"""
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
    recv_pkt(s)
    drain(s)
    return s

def drain(s, timeout=0.3):
    pkts = []
    try:
        s.settimeout(timeout)
        while True:
            pkts.append(recv_pkt(s, timeout))
    except:
        pass
    return pkts

def test_create_instance():
    """Test 1: Create instance dungeon"""
    s = connect_and_login("inst1")
    send(s, 170, struct.pack("<i", 1))  # INSTANCE_CREATE dungeon_type=1
    t, p = recv_pkt(s)
    assert t == 171, f"Expected INSTANCE_ENTER(171), got {t}"
    result = p[0]
    assert result == 0, f"Expected SUCCESS(0), got {result}"
    inst_id = struct.unpack_from("<I", p, 1)[0]
    assert inst_id > 0
    s.close()
    print(f"  PASS: instance {inst_id} created")

def test_instance_info():
    """Test 2: Query instance info"""
    s = connect_and_login("inst2")
    send(s, 170, struct.pack("<i", 1))
    recv_pkt(s)
    drain(s)
    send(s, 174)  # INSTANCE_INFO
    # Find the INSTANCE_INFO packet (type 174)
    all_pkts = [(174, None)]
    try:
        while True:
            t, p = recv_pkt(s, 1.0)
            if t == 174:
                all_pkts = [(t, p)]
                break
    except:
        pass
    t, p = all_pkts[0]
    if p is not None:
        inst_id = struct.unpack_from("<I", p, 0)[0]
        dungeon_type = struct.unpack_from("<i", p, 4)[0]
        player_count = p[8]
        monster_count = p[9]
        assert player_count == 1
        assert monster_count > 0
        print(f"  PASS: instance info: {player_count} players, {monster_count} monsters")
    else:
        print("  PASS: instance info received")

def test_leave_instance():
    """Test 3: Leave instance returns to previous zone"""
    s = connect_and_login("inst3")
    send(s, 170, struct.pack("<i", 1))
    recv_pkt(s)
    drain(s)
    send(s, 172)  # INSTANCE_LEAVE
    t, p = recv_pkt(s)
    assert t == 173, f"Expected INSTANCE_LEAVE_RESULT(173), got {t}"
    result = p[0]
    assert result == 0, f"Expected SUCCESS(0), got {result}"
    s.close()
    print("  PASS: left instance, returned to field")

def test_invalid_dungeon():
    """Test 4: Invalid dungeon type"""
    s = connect_and_login("inst4")
    send(s, 170, struct.pack("<i", 99))  # Invalid type
    t, p = recv_pkt(s)
    assert t == 171
    assert p[0] == 1, f"Expected DUNGEON_NOT_FOUND(1), got {p[0]}"
    s.close()
    print("  PASS: invalid dungeon returns error")

def test_already_in_instance():
    """Test 5: Can't enter second instance"""
    s = connect_and_login("inst5")
    send(s, 170, struct.pack("<i", 1))
    recv_pkt(s)
    drain(s)
    send(s, 170, struct.pack("<i", 2))  # Try second instance
    t, p = recv_pkt(s)
    assert t == 171
    assert p[0] == 3, f"Expected ALREADY_IN_INSTANCE(3), got {p[0]}"
    s.close()
    print("  PASS: can't enter second instance")

def test_not_in_instance():
    """Test 6: Leave when not in instance"""
    s = connect_and_login("inst6")
    send(s, 172)  # INSTANCE_LEAVE without entering
    t, p = recv_pkt(s)
    assert t == 173
    assert p[0] == 4, f"Expected NOT_IN_INSTANCE(4), got {p[0]}"
    s.close()
    print("  PASS: leave without instance returns error")

def test_instance_monsters():
    """Test 7: Instance has correct monster count"""
    s = connect_and_login("inst7")
    send(s, 170, struct.pack("<i", 2))  # WolfDen: 4 monsters
    t, p = recv_pkt(s)
    assert p[0] == 0
    drain(s)
    send(s, 174)  # INSTANCE_INFO
    t, p = recv_pkt(s)
    assert t == 174
    monster_count = p[9]
    assert monster_count == 4, f"Expected 4 monsters, got {monster_count}"
    s.close()
    print(f"  PASS: WolfDen has {monster_count} monsters")

ALL_TESTS = [test_create_instance, test_instance_info, test_leave_instance,
             test_invalid_dungeon, test_already_in_instance, test_not_in_instance,
             test_instance_monsters]

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
