"""Session 24: Buff/Debuff System Tests — 7 tests"""
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

def test_apply_buff():
    """Test 1: Apply buff"""
    s = connect_and_login("buff1")
    send(s, 202, struct.pack("<i", 1))  # BUFF_APPLY: Strength
    t, p = recv_pkt(s)
    assert t == 203, f"Expected BUFF_RESULT(203), got {t}"
    assert p[0] == 0, f"Expected SUCCESS(0), got {p[0]}"
    buff_id = struct.unpack_from("<i", p, 1)[0]
    assert buff_id == 1
    stacks = p[5]
    assert stacks == 1
    s.close()
    print("  PASS: buff applied")

def test_buff_list():
    """Test 2: Buff list shows active buffs"""
    s = connect_and_login("buff2")
    send(s, 202, struct.pack("<i", 1))  # Strength
    recv_pkt(s)
    send(s, 202, struct.pack("<i", 2))  # IronSkin
    recv_pkt(s)
    drain(s)
    send(s, 200)  # BUFF_LIST_REQ
    t, p = recv_pkt(s)
    assert t == 201, f"Expected BUFF_LIST_RESP(201), got {t}"
    count = p[0]
    assert count == 2, f"Expected 2 buffs, got {count}"
    s.close()
    print(f"  PASS: {count} active buffs")

def test_remove_buff():
    """Test 3: Remove buff"""
    s = connect_and_login("buff3")
    send(s, 202, struct.pack("<i", 1))  # Apply
    recv_pkt(s)
    send(s, 204, struct.pack("<i", 1))  # BUFF_REMOVE
    t, p = recv_pkt(s)
    assert t == 205, f"Expected BUFF_REMOVE_RESP(205), got {t}"
    assert p[0] == 0
    # Verify list is empty
    drain(s)
    send(s, 200)
    t, p = recv_pkt(s)
    assert p[0] == 0, f"Expected 0 buffs after remove, got {p[0]}"
    s.close()
    print("  PASS: buff removed")

def test_buff_stacking():
    """Test 4: Poison stacks (max 3)"""
    s = connect_and_login("buff4")
    for i in range(4):
        send(s, 202, struct.pack("<i", 5))  # Poison (max_stacks=3)
        t, p = recv_pkt(s)
    stacks = p[5]
    assert stacks == 3, f"Expected 3 stacks (max), got {stacks}"
    s.close()
    print(f"  PASS: poison capped at {stacks} stacks")

def test_invalid_buff():
    """Test 5: Invalid buff ID"""
    s = connect_and_login("buff5")
    send(s, 202, struct.pack("<i", 999))  # Invalid
    t, p = recv_pkt(s)
    assert t == 203
    assert p[0] == 1, f"Expected BUFF_NOT_FOUND(1), got {p[0]}"
    s.close()
    print("  PASS: invalid buff returns error")

def test_buff_duration():
    """Test 6: Buff has correct duration"""
    s = connect_and_login("buff6")
    send(s, 202, struct.pack("<i", 1))  # Strength (10000ms)
    t, p = recv_pkt(s)
    duration = struct.unpack_from("<i", p, 6)[0]
    assert duration == 10000, f"Expected 10000ms duration, got {duration}"
    s.close()
    print(f"  PASS: buff duration = {duration}ms")

def test_multiple_buff_types():
    """Test 7: Multiple different buff types"""
    s = connect_and_login("buff7")
    for bid in [1, 2, 3, 4, 5, 6]:
        send(s, 202, struct.pack("<i", bid))
        recv_pkt(s)
    drain(s)
    send(s, 200)  # BUFF_LIST
    t, p = recv_pkt(s)
    count = p[0]
    assert count == 6, f"Expected 6 different buffs, got {count}"
    s.close()
    print(f"  PASS: {count} different buff types active")

ALL_TESTS = [test_apply_buff, test_buff_list, test_remove_buff,
             test_buff_stacking, test_invalid_buff, test_buff_duration,
             test_multiple_buff_types]

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
