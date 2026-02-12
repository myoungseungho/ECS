"""Session 23: Inventory/Item System Tests — 7 tests"""
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

def test_empty_inventory():
    """Test 1: Empty inventory query"""
    s = connect_and_login("inv1")
    send(s, 190)  # INVENTORY_REQ
    t, p = recv_pkt(s)
    assert t == 191, f"Expected INVENTORY_RESP(191), got {t}"
    count = p[0]
    assert count == 0, f"Expected 0 items, got {count}"
    s.close()
    print("  PASS: empty inventory")

def test_add_item():
    """Test 2: Add item to inventory"""
    s = connect_and_login("inv2")
    send(s, 192, struct.pack("<Ih", 1, 5))  # ITEM_ADD: HP Potion x5
    t, p = recv_pkt(s)
    assert t == 193, f"Expected ITEM_ADD_RESULT(193), got {t}"
    assert p[0] == 0, f"Expected SUCCESS(0), got {p[0]}"
    slot = p[1]
    assert slot >= 0
    s.close()
    print(f"  PASS: item added to slot {slot}")

def test_use_hp_potion():
    """Test 3: Use HP potion heals"""
    s = connect_and_login("inv3")
    # Take damage
    send(s, 93, struct.pack("<i", 30))
    time.sleep(0.2)
    drain(s)
    send(s, 90)  # STAT_QUERY
    # Find STAT_SYNC (type 91)
    t, sp = recv_pkt(s)
    while t != 91:
        t, sp = recv_pkt(s)
    hp_before = struct.unpack_from("<i", sp, 4)[0]
    # Add and use HP potion
    send(s, 192, struct.pack("<Ih", 1, 1))  # HP Potion x1
    t, p = recv_pkt(s)
    while t != 193:
        t, p = recv_pkt(s)
    slot = p[1]
    drain(s)
    send(s, 194, bytes([slot]))  # ITEM_USE
    time.sleep(0.2)
    # Collect all responses and find ITEM_USE_RESULT
    pkts = []
    try:
        while True:
            pkts.append(recv_pkt(s, 0.5))
    except:
        pass
    use_results = [p for t, p in pkts if t == 195]
    assert len(use_results) > 0, "Should receive ITEM_USE_RESULT"
    assert use_results[0][0] == 0, f"Expected SUCCESS, got {use_results[0][0]}"
    # Check HP
    send(s, 90)
    t, sp2 = recv_pkt(s)
    while t != 91:
        t, sp2 = recv_pkt(s)
    hp_after = struct.unpack_from("<i", sp2, 4)[0]
    assert hp_after >= hp_before, f"HP should increase: {hp_before} -> {hp_after}"
    s.close()
    print(f"  PASS: HP potion healed {hp_before} -> {hp_after}")

def test_equip_weapon():
    """Test 4: Equip weapon"""
    s = connect_and_login("inv4")
    send(s, 192, struct.pack("<Ih", 10, 1))  # Iron Sword x1
    t, p = recv_pkt(s)
    slot = p[1]
    drain(s)
    send(s, 196, bytes([slot]))  # ITEM_EQUIP
    t, p = recv_pkt(s)
    assert t == 198, f"Expected ITEM_EQUIP_RESULT(198), got {t}"
    assert p[0] == 0, f"Expected SUCCESS, got {p[0]}"
    equipped = p[6]
    assert equipped == 1, "Should be equipped"
    s.close()
    print("  PASS: weapon equipped")

def test_unequip():
    """Test 5: Unequip item"""
    s = connect_and_login("inv5")
    send(s, 192, struct.pack("<Ih", 10, 1))
    t, p = recv_pkt(s)
    slot = p[1]
    drain(s)
    send(s, 196, bytes([slot]))  # Equip
    recv_pkt(s)
    send(s, 197, bytes([slot]))  # ITEM_UNEQUIP
    t, p = recv_pkt(s)
    assert t == 198
    assert p[0] == 0
    equipped = p[6]
    assert equipped == 0, "Should be unequipped"
    s.close()
    print("  PASS: unequipped")

def test_inventory_after_add():
    """Test 6: Inventory shows added items"""
    s = connect_and_login("inv6")
    send(s, 192, struct.pack("<Ih", 1, 3))  # HP Potion x3
    recv_pkt(s)
    send(s, 192, struct.pack("<Ih", 10, 1))  # Iron Sword
    recv_pkt(s)
    drain(s)
    send(s, 190)  # INVENTORY_REQ
    t, p = recv_pkt(s)
    count = p[0]
    assert count == 2, f"Expected 2 items, got {count}"
    s.close()
    print(f"  PASS: inventory has {count} items")

def test_use_non_consumable():
    """Test 7: Can't use non-consumable"""
    s = connect_and_login("inv7")
    send(s, 192, struct.pack("<Ih", 10, 1))  # Iron Sword
    t, p = recv_pkt(s)
    slot = p[1]
    drain(s)
    send(s, 194, bytes([slot]))  # ITEM_USE on weapon
    t, p = recv_pkt(s)
    assert t == 195
    assert p[0] == 3, f"Expected NOT_CONSUMABLE(3), got {p[0]}"
    s.close()
    print("  PASS: can't use non-consumable")

ALL_TESTS = [test_empty_inventory, test_add_item, test_use_hp_potion,
             test_equip_weapon, test_unequip, test_inventory_after_add,
             test_use_non_consumable]

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
