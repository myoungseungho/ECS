"""
Session 16: Zone Transfer System Tests
- ZONE_TRANSFER_REQ(120): client requests zone change [target_zone_id(4)]
- ZONE_TRANSFER_RESULT(121): server responds [result(1) zone_id(4) x(4) y(4) z(4)]
  result: 0=success, 1=invalid_zone, 2=same_zone
- Zone 1: Goblin x3 + Wolf x2 (spawn at 100,100)
- Zone 2: Orc x2 + Bear x2 (spawn at 500,500)
- Zone 3: empty (spawn at 1000,1000)

Player: Warrior_Kim (hero/pass123): Lv50, zone=1, pos=(100,100)
"""

import socket
import struct
import time
import subprocess
import sys
import os

# ━━━ Network Utils ━━━
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
    """Wait for a specific packet type, discard others."""
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
    """Collect all packets within timeout."""
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
    """Drain all pending packets."""
    sock.settimeout(wait)
    try:
        while True:
            sock.recv(4096)
    except:
        pass
    sock.settimeout(5.0)

# ━━━ Parsing Helpers ━━━

def parse_zone_transfer_result(payload):
    """ZONE_TRANSFER_RESULT: result(1) zone_id(4) x(4) y(4) z(4) = 17 bytes"""
    if len(payload) < 17:
        return None
    return {
        'result': payload[0],
        'zone_id': struct.unpack_from('<i', payload, 1)[0],
        'x': struct.unpack_from('<f', payload, 5)[0],
        'y': struct.unpack_from('<f', payload, 9)[0],
        'z': struct.unpack_from('<f', payload, 13)[0],
    }

def parse_monster_spawn(payload):
    """MONSTER_SPAWN: entity(8) monster_id(4) level(4) hp(4) max_hp(4) x(4) y(4) z(4)"""
    if len(payload) < 36:
        return None
    return {
        'entity': struct.unpack_from('<Q', payload, 0)[0],
        'monster_id': struct.unpack_from('<I', payload, 8)[0],
        'level': struct.unpack_from('<i', payload, 12)[0],
        'hp': struct.unpack_from('<i', payload, 16)[0],
        'max_hp': struct.unpack_from('<i', payload, 20)[0],
        'x': struct.unpack_from('<f', payload, 24)[0],
        'y': struct.unpack_from('<f', payload, 28)[0],
        'z': struct.unpack_from('<f', payload, 32)[0],
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

# ━━━ Connect + Login ━━━

def connect_and_login(port=7777, username='hero', password='pass123', char_id=1):
    """Connect -> Login -> CharSelect -> collect MONSTER_SPAWN packets.
    char_id=0 means use account_id from login result (works for auto-registered accounts)."""
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
    account_id = struct.unpack('<I', payload[1:5])[0]

    # Char Select (auto-registered accounts: char_id == account_id)
    select_id = account_id if char_id == 0 else char_id
    sock.sendall(build_packet(64, struct.pack('<I', select_id)))
    msg_type, payload = recv_packet_type(sock, 65, timeout=5.0)
    assert payload[0] == 0, f"CharSelect failed: result={payload[0]}"
    entity_id = struct.unpack('<Q', payload[1:9])[0]

    # Collect initial packets (MONSTER_SPAWN etc.)
    all_packets = collect_packets(sock, timeout=0.5)
    monsters = []
    for pkt_type, pkt_payload in all_packets:
        if pkt_type == 110:  # MONSTER_SPAWN
            m = parse_monster_spawn(pkt_payload)
            if m:
                monsters.append(m)

    return sock, entity_id, monsters

def send_zone_transfer(sock, target_zone):
    """Send ZONE_TRANSFER_REQ and receive ZONE_TRANSFER_RESULT."""
    payload = struct.pack('<i', target_zone)
    sock.sendall(build_packet(120, payload))  # ZONE_TRANSFER_REQ
    msg_type, resp = recv_packet_type(sock, 121, timeout=5.0)  # ZONE_TRANSFER_RESULT
    return parse_zone_transfer_result(resp)

def collect_monster_spawns(sock, timeout=1.0):
    """Collect MONSTER_SPAWN packets after zone transfer."""
    monsters = []
    packets = collect_packets(sock, timeout=timeout)
    for pkt_type, pkt_payload in packets:
        if pkt_type == 110:  # MONSTER_SPAWN
            m = parse_monster_spawn(pkt_payload)
            if m:
                monsters.append(m)
    return monsters

# ━━━ Test Framework ━━━
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

# ━━━ Server Process ━━━
server_procs = []

def start_servers():
    global server_procs
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')
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

# ━━━ Test 1: Basic Zone Transfer ━━━

def test_zone_transfer_basic():
    """Transfer from zone 1 to zone 2, verify success result."""
    sock, eid, monsters = connect_and_login()
    try:
        # Verify starting zone: should have zone 1 monsters (goblins/wolves)
        zone1_ids = set(m['monster_id'] for m in monsters)
        assert 1 in zone1_ids or 2 in zone1_ids, f"Expected zone 1 monsters, got ids: {zone1_ids}"

        # Transfer to zone 2
        result = send_zone_transfer(sock, 2)
        assert result is not None, "No ZONE_TRANSFER_RESULT received"
        assert result['result'] == 0, f"Expected success(0), got {result['result']}"
        assert result['zone_id'] == 2, f"Expected zone_id=2, got {result['zone_id']}"
    finally:
        sock.close()

# ━━━ Test 2: Position After Transfer ━━━

def test_zone_transfer_position():
    """After transfer to zone 2, position should be zone 2 spawn point (500, 500)."""
    sock, eid, _ = connect_and_login()
    try:
        result = send_zone_transfer(sock, 2)
        assert result['result'] == 0, f"Transfer failed: {result['result']}"
        assert abs(result['x'] - 500.0) < 1.0, f"Expected x=500, got {result['x']}"
        assert abs(result['y'] - 500.0) < 1.0, f"Expected y=500, got {result['y']}"
    finally:
        sock.close()

# ━━━ Test 3: Zone 2 Monsters After Transfer ━━━

def test_zone_transfer_monsters():
    """After transfer to zone 2, receive zone 2 monsters (orcs/bears), NOT goblins."""
    sock, eid, zone1_monsters = connect_and_login()
    try:
        # Zone 1: should have goblins (id=1) and/or wolves (id=2)
        z1_ids = set(m['monster_id'] for m in zone1_monsters)
        assert 1 in z1_ids, f"Zone 1 should have goblins, got ids: {z1_ids}"

        # Transfer to zone 2
        result = send_zone_transfer(sock, 2)
        assert result['result'] == 0, "Transfer failed"

        # Collect zone 2 monsters
        z2_monsters = collect_monster_spawns(sock, timeout=1.0)
        assert len(z2_monsters) >= 4, f"Expected >= 4 zone 2 monsters, got {len(z2_monsters)}"

        z2_ids = set(m['monster_id'] for m in z2_monsters)
        assert 3 in z2_ids, f"Zone 2 should have orcs (id=3), got ids: {z2_ids}"
        assert 4 in z2_ids, f"Zone 2 should have bears (id=4), got ids: {z2_ids}"
        assert 1 not in z2_ids, f"Zone 2 should NOT have goblins (id=1), got ids: {z2_ids}"
    finally:
        sock.close()

# ━━━ Test 4: DISAPPEAR When Player Transfers ━━━

def test_zone_transfer_disappear():
    """Player B in zone 1 should get DISAPPEAR when Player A transfers to zone 2."""
    sock_a, eid_a, _ = connect_and_login(username='hero', char_id=1)
    sock_b, eid_b, _ = connect_and_login(username='hero2', password='pass456', char_id=0)
    try:
        # Move both players close together in zone 1 so they're in each other's interest area
        sock_a.sendall(build_packet(10, struct.pack('<fff', 200.0, 200.0, 0.0)))
        sock_b.sendall(build_packet(10, struct.pack('<fff', 210.0, 210.0, 0.0)))
        time.sleep(0.5)
        drain(sock_a)
        drain(sock_b)

        # Wait for InterestSystem tick to process APPEAR
        time.sleep(0.3)
        drain(sock_a)
        drain(sock_b)

        # Player A transfers to zone 2
        payload = struct.pack('<i', 2)
        sock_a.sendall(build_packet(120, payload))

        # Collect packets on Player B: should see DISAPPEAR for Player A
        time.sleep(0.3)
        b_packets = collect_packets(sock_b, timeout=1.0)
        disappear_entities = []
        for pkt_type, pkt_payload in b_packets:
            if pkt_type == 14:  # DISAPPEAR
                if len(pkt_payload) >= 8:
                    gone_eid = struct.unpack('<Q', pkt_payload[:8])[0]
                    disappear_entities.append(gone_eid)

        assert eid_a in disappear_entities, \
            f"Player B should see DISAPPEAR for Player A ({eid_a}), got: {disappear_entities}"
    finally:
        sock_a.close()
        sock_b.close()

# ━━━ Test 5: Invalid Zone Transfer ━━━

def test_zone_transfer_invalid():
    """Transfer to zone 99 should fail with result=1 (invalid zone)."""
    sock, eid, _ = connect_and_login()
    try:
        result = send_zone_transfer(sock, 99)
        assert result is not None, "No ZONE_TRANSFER_RESULT received"
        assert result['result'] == 1, f"Expected invalid_zone(1), got {result['result']}"
    finally:
        sock.close()

# ━━━ Test 6: Roundtrip Zone Transfer ━━━

def test_zone_transfer_roundtrip():
    """Zone 1 -> Zone 2 -> Zone 1: verify monsters change each time."""
    sock, eid, z1_monsters_initial = connect_and_login()
    try:
        z1_ids = set(m['monster_id'] for m in z1_monsters_initial)
        assert 1 in z1_ids, f"Initial zone 1 should have goblins, got: {z1_ids}"

        # Transfer to zone 2
        result = send_zone_transfer(sock, 2)
        assert result['result'] == 0, "Transfer to zone 2 failed"
        z2_monsters = collect_monster_spawns(sock, timeout=1.0)
        z2_ids = set(m['monster_id'] for m in z2_monsters)
        assert 3 in z2_ids, f"Zone 2 should have orcs, got: {z2_ids}"

        # Transfer back to zone 1
        drain(sock)
        result = send_zone_transfer(sock, 1)
        assert result['result'] == 0, "Transfer back to zone 1 failed"
        z1_monsters_return = collect_monster_spawns(sock, timeout=1.0)
        z1_return_ids = set(m['monster_id'] for m in z1_monsters_return)
        assert 1 in z1_return_ids, f"Zone 1 return should have goblins, got: {z1_return_ids}"
        assert 3 not in z1_return_ids, f"Zone 1 should NOT have orcs, got: {z1_return_ids}"

        # Verify position reset to zone 1 spawn point
        assert abs(result['x'] - 100.0) < 1.0, f"Expected x=100, got {result['x']}"
        assert abs(result['y'] - 100.0) < 1.0, f"Expected y=100, got {result['y']}"
    finally:
        sock.close()

# ━━━ Test 7: Zone Isolation (Cross-Zone Attack) ━━━

def test_zone_isolation():
    """Players in different zones cannot attack each other."""
    sock_a, eid_a, _ = connect_and_login(username='hero', char_id=1)
    sock_b, eid_b, _ = connect_and_login(username='hero2', password='pass456', char_id=0)
    try:
        # Player A stays in zone 1
        sock_a.sendall(build_packet(10, struct.pack('<fff', 200.0, 200.0, 0.0)))
        time.sleep(0.3)
        drain(sock_a)

        # Player B transfers to zone 2
        payload = struct.pack('<i', 2)
        sock_b.sendall(build_packet(120, payload))
        time.sleep(0.5)
        drain(sock_b)

        # Drain Player A socket before attacking (clear monster attack results)
        drain(sock_a, wait=0.5)

        # Player A attacks Player B (cross-zone): should fail
        sock_a.sendall(build_packet(100, struct.pack('<Q', eid_b)))  # ATTACK_REQ

        # Collect attack result - filter by attacker=eid_a (ignore monster attacks on Player A)
        time.sleep(0.5)
        packets_a = collect_packets(sock_a, timeout=1.0)
        my_attack_results = []
        for pkt_type, pkt_payload in packets_a:
            if pkt_type == 101:  # ATTACK_RESULT
                r = parse_attack_result(pkt_payload)
                if r and r['attacker'] == eid_a:
                    my_attack_results.append(r)

        # Player A's own attack should fail (OUT_OF_RANGE=3 due to zone check)
        if my_attack_results:
            for r in my_attack_results:
                assert r['result'] != 0, \
                    f"Cross-zone attack should not succeed, got result={r['result']}"
        # No result for Player A's attack is also acceptable
    finally:
        sock_a.close()
        sock_b.close()

# ━━━ Run ━━━
if __name__ == '__main__':
    print("=" * 50)
    print("  Session 16: Zone Transfer System Tests")
    print("=" * 50)
    print()

    start_servers()

    try:
        print("[1] Basic Transfer")
        run_test("Zone 1->2 transfer success", test_zone_transfer_basic)
        run_test("Position after transfer = zone 2 spawn", test_zone_transfer_position)

        print()
        print("[2] Monster Isolation")
        run_test("Zone 2 monsters (orcs/bears) after transfer", test_zone_transfer_monsters)
        run_test("DISAPPEAR sent to zone 1 players", test_zone_transfer_disappear)

        print()
        print("[3] Edge Cases")
        run_test("Invalid zone (99) rejected", test_zone_transfer_invalid)
        run_test("Roundtrip zone1->zone2->zone1", test_zone_transfer_roundtrip)
        run_test("Cross-zone attack fails", test_zone_isolation)

    finally:
        stop_servers()

    print()
    print("=" * 50)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
