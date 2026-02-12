"""Session 20: Party System Tests — 7 tests"""
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

def test_party_create():
    """Test 1: Create party"""
    s, e = connect_and_login("party1")
    send(s, 160)  # PARTY_CREATE
    t, p = recv_pkt(s)
    assert t == 164, f"Expected PARTY_INFO(164), got {t}"
    result = p[0]
    assert result == 0, f"Expected SUCCESS(0), got {result}"
    party_id = struct.unpack_from("<I", p, 1)[0]
    assert party_id > 0
    count = p[13]
    assert count == 1, f"Expected 1 member, got {count}"
    s.close()
    print(f"  PASS: party {party_id} created with 1 member")

def test_party_invite():
    """Test 2: Invite another player"""
    s1, e1 = connect_and_login("party2a")
    s2, e2 = connect_and_login("party2b")
    # Player 1 creates party
    send(s1, 160)
    t, p = recv_pkt(s1)
    party_id = struct.unpack_from("<I", p, 1)[0]
    # Player 1 invites player 2
    send(s1, 161, struct.pack("<Q", e2))  # PARTY_INVITE
    # Both should receive PARTY_INFO
    drain(s1, 0.5)
    pkts = drain(s2, 0.5)
    got_info = any(t == 164 for t, _ in pkts)
    assert got_info, "Player 2 should receive PARTY_INFO"
    s1.close(); s2.close()
    print(f"  PASS: invite works, both notified")

def test_party_leave():
    """Test 3: Leave party"""
    s1, e1 = connect_and_login("party3a")
    s2, e2 = connect_and_login("party3b")
    send(s1, 160)
    recv_pkt(s1)
    send(s1, 161, struct.pack("<Q", e2))
    drain(s1); drain(s2)
    # Player 2 leaves
    send(s2, 163)  # PARTY_LEAVE
    t, p = recv_pkt(s2)
    assert t == 164
    result = p[0]
    assert result == 3, f"Expected NOT_IN_PARTY(3) after leave, got {result}"
    s1.close(); s2.close()
    print("  PASS: leave party works")

def test_party_kick():
    """Test 4: Kick member"""
    s1, e1 = connect_and_login("party4a")
    s2, e2 = connect_and_login("party4b")
    send(s1, 160)
    recv_pkt(s1)
    send(s1, 161, struct.pack("<Q", e2))
    drain(s1); drain(s2)
    # Leader kicks player 2
    send(s1, 165, struct.pack("<Q", e2))  # PARTY_KICK
    drain(s1)
    pkts = drain(s2)
    got_kicked = any(t == 164 and p[0] == 3 for t, p in pkts)  # NOT_IN_PARTY
    assert got_kicked, "Kicked player should receive NOT_IN_PARTY"
    s1.close(); s2.close()
    print("  PASS: kick works")

def test_party_full():
    """Test 5: Party max 4 members"""
    players = []
    for i in range(5):
        s, e = connect_and_login(f"party5_{i}")
        players.append((s, e))
    # First player creates party
    send(players[0][0], 160)
    recv_pkt(players[0][0])
    # Invite 3 more (total 4), drain all existing members each time
    for i in range(1, 4):
        send(players[0][0], 161, struct.pack("<Q", players[i][1]))
        time.sleep(0.2)
        for j in range(i + 1):
            drain(players[j][0])
    # Try to invite 5th
    send(players[0][0], 161, struct.pack("<Q", players[4][1]))
    t, p = recv_pkt(players[0][0])
    assert t == 164
    result = p[0]
    assert result == 2, f"Expected PARTY_FULL(2), got {result}"
    for s, _ in players: s.close()
    print("  PASS: party full at 4")

def test_already_in_party():
    """Test 6: Can't create party while in one"""
    s, e = connect_and_login("party6")
    send(s, 160)
    recv_pkt(s)
    send(s, 160)  # Try again
    t, p = recv_pkt(s)
    assert t == 164
    result = p[0]
    assert result == 1, f"Expected ALREADY_IN_PARTY(1), got {result}"
    s.close()
    print("  PASS: can't create while in party")

def test_leader_transfer():
    """Test 7: Leader leaves, new leader assigned"""
    s1, e1 = connect_and_login("party7a")
    s2, e2 = connect_and_login("party7b")
    send(s1, 160)
    recv_pkt(s1)
    send(s1, 161, struct.pack("<Q", e2))
    drain(s1); drain(s2)
    # Leader leaves
    send(s1, 163)
    drain(s1)
    # Player 2 should now be leader
    pkts = drain(s2, 0.5)
    got_info = False
    for t, p in pkts:
        if t == 164 and p[0] == 0:
            leader = struct.unpack_from("<Q", p, 5)[0]
            assert leader == e2, f"New leader should be {e2}, got {leader}"
            got_info = True
    assert got_info, "Player 2 should receive updated party info"
    s1.close(); s2.close()
    print("  PASS: leader transferred on leave")

ALL_TESTS = [test_party_create, test_party_invite, test_party_leave,
             test_party_kick, test_party_full, test_already_in_party, test_leader_transfer]

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
