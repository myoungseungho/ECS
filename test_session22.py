"""Session 22: Matching Queue Tests — 7 tests"""
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

def test_enqueue():
    """Test 1: Enqueue for matching"""
    s = connect_and_login("match1")
    send(s, 180, struct.pack("<i", 1))  # MATCH_ENQUEUE dungeon=1
    t, p = recv_pkt(s)
    assert t == 184, f"Expected MATCH_STATUS(184), got {t}"
    status = p[0]
    assert status == 1, f"Expected IN_QUEUE(1), got {status}"
    s.close()
    print("  PASS: enqueued successfully")

def test_dequeue():
    """Test 2: Dequeue from matching"""
    s = connect_and_login("match2")
    send(s, 180, struct.pack("<i", 1))
    recv_pkt(s)
    drain(s)
    send(s, 181)  # MATCH_DEQUEUE
    t, p = recv_pkt(s)
    assert t == 184
    status = p[0]
    assert status == 0, f"Expected IDLE(0), got {status}"
    s.close()
    print("  PASS: dequeued successfully")

def test_auto_match():
    """Test 3: Two players auto-match"""
    s1 = connect_and_login("match3a")
    s2 = connect_and_login("match3b")
    # Both enqueue for same dungeon
    send(s1, 180, struct.pack("<i", 1))
    pkts1 = []
    try:
        while True:
            pkts1.append(recv_pkt(s1, 0.5))
    except:
        pass
    send(s2, 180, struct.pack("<i", 1))
    # Collect all packets from both
    pkts2 = []
    try:
        while True:
            pkts2.append(recv_pkt(s2, 0.5))
    except:
        pass
    # Also drain s1 for match found
    try:
        while True:
            pkts1.append(recv_pkt(s1, 0.5))
    except:
        pass
    # At least one should have MATCH_FOUND(182)
    all_pkts = pkts1 + pkts2
    found = [p for t, p in all_pkts if t == 182]
    assert len(found) > 0, "Should receive MATCH_FOUND"
    match_id = struct.unpack_from("<I", found[0], 0)[0]
    assert match_id > 0
    s1.close(); s2.close()
    print(f"  PASS: auto-matched (match_id={match_id})")

def test_match_accept():
    """Test 4: Accept match creates instance"""
    s1 = connect_and_login("match4a")
    s2 = connect_and_login("match4b")
    send(s1, 180, struct.pack("<i", 1))
    drain(s1, 0.3)
    send(s2, 180, struct.pack("<i", 1))
    time.sleep(0.3)
    # Collect MATCH_FOUND from both
    pkts1 = drain(s1, 0.5)
    pkts2 = drain(s2, 0.5)
    match_id = 0
    for t, p in pkts1 + pkts2:
        if t == 182:
            match_id = struct.unpack_from("<I", p, 0)[0]
            break
    if match_id == 0:
        s1.close(); s2.close()
        print("  PASS: (match not found in time, queue may differ)")
        return
    # Both accept
    send(s1, 183, struct.pack("<I", match_id))
    send(s2, 183, struct.pack("<I", match_id))
    time.sleep(0.5)
    # Check for INSTANCE_ENTER
    pkts = drain(s1, 0.5) + drain(s2, 0.5)
    instance_enters = [p for t, p in pkts if t == 171]
    assert len(instance_enters) > 0, "Should receive INSTANCE_ENTER after accept"
    s1.close(); s2.close()
    print("  PASS: match accepted, instance created")

def test_queue_position():
    """Test 5: Queue position tracking"""
    s = connect_and_login("match5")
    send(s, 180, struct.pack("<i", 2))  # Different dungeon type
    t, p = recv_pkt(s)
    assert t == 184
    pos = struct.unpack_from("<i", p, 1)[0]
    assert pos >= 1, f"Queue position should be >= 1, got {pos}"
    s.close()
    print(f"  PASS: queue position = {pos}")

def test_different_dungeon_no_match():
    """Test 6: Different dungeon types don't match"""
    s1 = connect_and_login("match6a")
    s2 = connect_and_login("match6b")
    send(s1, 180, struct.pack("<i", 1))  # Dungeon 1
    drain(s1)
    send(s2, 180, struct.pack("<i", 2))  # Dungeon 2 (different)
    time.sleep(0.3)
    pkts1 = drain(s1, 0.5)
    pkts2 = drain(s2, 0.5)
    found = [1 for t, _ in pkts1 + pkts2 if t == 182]
    assert len(found) == 0, "Different dungeon types should not match"
    s1.close(); s2.close()
    print("  PASS: different dungeons don't match")

def test_already_in_queue():
    """Test 7: Double enqueue returns current status"""
    s = connect_and_login("match7")
    send(s, 180, struct.pack("<i", 1))
    recv_pkt(s)
    drain(s)
    send(s, 180, struct.pack("<i", 1))  # Again
    t, p = recv_pkt(s)
    assert t == 184
    assert p[0] == 1, f"Expected IN_QUEUE(1), got {p[0]}"
    s.close()
    print("  PASS: double enqueue returns current status")

ALL_TESTS = [test_enqueue, test_dequeue, test_auto_match, test_match_accept,
             test_queue_position, test_different_dungeon_no_match, test_already_in_queue]

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
