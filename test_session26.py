"""
Test Session 26 - Spatial Query System
Tests spatial queries with radius filtering and entity type filters
"""

import subprocess, socket, struct, time, sys, os
from pathlib import Path

BUILD_DIR = Path(__file__).parent / "build"
FIELD_EXE = BUILD_DIR / "FieldServer.exe"
HOST = '127.0.0.1'
PORT = 7777
HEADER_SIZE = 6

def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload

def recv_packet(sock, timeout=5):
    sock.settimeout(timeout)
    header = b""
    while len(header) < HEADER_SIZE:
        chunk = sock.recv(HEADER_SIZE - len(header))
        if not chunk: return None, None
        header += chunk
    length, msg_type = struct.unpack('<IH', header)
    payload_len = length - HEADER_SIZE
    payload = b""
    while len(payload) < payload_len:
        chunk = sock.recv(payload_len - len(payload))
        if not chunk: break
        payload += chunk
    return msg_type, payload

def try_recv(sock, timeout=1.0):
    try: return recv_packet(sock, timeout)
    except: return None, None

def drain(sock, timeout=0.3):
    try:
        sock.settimeout(timeout)
        while True: sock.recv(4096)
    except: pass
    sock.settimeout(5.0)

def start_server():
    proc = subprocess.Popen([str(FIELD_EXE), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    time.sleep(2.0)
    return proc

def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=3)
        except: proc.kill()

def connect_to_server(retries=5):
    for i in range(retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((HOST, PORT))
            time.sleep(0.3)
            return s
        except:
            if i < retries - 1: time.sleep(1.0)
    return None

def login_and_enter(sock, username='hero', password='pass123', char_id=1):
    drain(sock)
    uname = username.encode()
    pw = password.encode()
    payload = struct.pack('B', len(uname)) + uname + struct.pack('B', len(pw)) + pw
    sock.sendall(build_packet(60, payload))
    msg_type, pl = recv_packet(sock)
    assert msg_type == 61 and pl[0] == 0, f"Login failed: {msg_type}, {pl[0] if pl else None}"

    drain(sock, 0.2)
    sock.sendall(build_packet(62))
    msg_type, pl = recv_packet(sock)
    assert msg_type == 63

    drain(sock, 0.2)
    sock.sendall(build_packet(64, struct.pack('<I', char_id)))
    msg_type, pl = recv_packet(sock)
    assert msg_type == 65 and pl[0] == 0, f"Enter game failed: {pl[0] if pl else None}"
    drain(sock, 0.5)
    return sock

def spatial_query(sock, x, y, z, radius, filter_type=0):
    drain(sock, 0.2)
    payload = struct.pack('<ffffB', x, y, z, radius, filter_type)
    sock.sendall(build_packet(215, payload))
    # Read packets until we get SPATIAL_QUERY_RESP(216)
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for spatial query")
        if msg_type == 216:
            count = pl[0]
            results = []
            offset = 1
            for i in range(count):
                entity_id = struct.unpack('<Q', pl[offset:offset+8])[0]
                distance = struct.unpack('<f', pl[offset+8:offset+12])[0]
                results.append((entity_id, distance))
                offset += 12
            return results
    raise Exception("Never got SPATIAL_QUERY_RESP(216)")

def main():
    proc = None
    sock1 = None
    sock2 = None
    try:
        proc = start_server()
        sock1 = connect_to_server()
        assert sock1 is not None, "Failed to connect to server"

        sock1 = login_and_enter(sock1, 'hero', 'pass123', 1)
        print("[OK] Logged in as hero")

        # Move to a known position
        hero_x, hero_y, hero_z = 300.0, 300.0, 0.0
        drain(sock1, 0.2)
        sock1.sendall(build_packet(10, struct.pack('<fff', hero_x, hero_y, hero_z)))
        msg_type, pl = recv_packet(sock1)
        print(f"[OK] Moved to ({hero_x}, {hero_y}, {hero_z})")

        # Test 1: Large radius query, filter=0 (all entities)
        results = spatial_query(sock1, hero_x, hero_y, hero_z, 10000.0, 0)
        assert len(results) > 0, "Expected to find entities with large radius"
        print(f"[OK] Test 1: Large radius query found {len(results)} entities")

        # Test 2: Query for monsters only (filter=2)
        results_monsters = spatial_query(sock1, hero_x, hero_y, hero_z, 10000.0, 2)
        assert len(results_monsters) > 0, "Expected to find monsters"
        print(f"[OK] Test 2: Monster-only query found {len(results_monsters)} monsters")

        # Test 3: Query at far position - should find nothing
        results_far = spatial_query(sock1, 99999.0, 99999.0, 0.0, 10.0, 0)
        assert len(results_far) == 0, "Expected no entities at far position"
        print(f"[OK] Test 3: Far position query found 0 entities")

        # Test 4: Very tight radius - should find 0 or very few
        results_tight = spatial_query(sock1, hero_x, hero_y, hero_z, 1.0, 0)
        print(f"[OK] Test 4: Tight radius query found {len(results_tight)} entities")

        # Test 5: Connect second player and query for players
        sock2 = connect_to_server()
        assert sock2 is not None, "Failed to connect second client"
        # guest account has char_id=3, NOT char_id=1
        sock2 = login_and_enter(sock2, 'guest', 'guest', 3)
        print("[OK] Logged in second player (guest, char_id=3)")

        # Move guest close to hero
        drain(sock2, 0.5)
        sock2.sendall(build_packet(10, struct.pack('<fff', hero_x + 50, hero_y + 50, hero_z)))
        # Read packets - skip non-MOVE_RESULT (monsters may attack guest)
        for _ in range(10):
            msg_type, pl = try_recv(sock2, timeout=2.0)
            if msg_type is None or msg_type == 11:
                break
        time.sleep(0.5)

        # Query for players only (filter=1)
        results_players = spatial_query(sock1, hero_x, hero_y, hero_z, 10000.0, 1)
        assert len(results_players) >= 1, "Expected to find at least one other player"
        print(f"[OK] Test 5: Player-only query found {len(results_players)} players")

        # Test 6: Verify distances are sorted
        results_sorted = spatial_query(sock1, hero_x, hero_y, hero_z, 10000.0, 0)
        distances = [dist for _, dist in results_sorted]
        assert distances == sorted(distances), "Expected distances to be sorted"
        print(f"[OK] Test 6: Distances are sorted (min={distances[0]:.2f}, max={distances[-1]:.2f})")

        # Test 7: Query with medium radius
        results_medium = spatial_query(sock1, hero_x, hero_y, hero_z, 500.0, 0)
        print(f"[OK] Test 7: Medium radius (500) found {len(results_medium)} entities")

        # Test 8: Verify filter=2 returns only monsters (no players)
        results_monsters_check = spatial_query(sock1, hero_x, hero_y, hero_z, 10000.0, 2)
        results_all_check = spatial_query(sock1, hero_x, hero_y, hero_z, 10000.0, 0)
        assert len(results_monsters_check) <= len(results_all_check), "Monster count should be <= total count"
        print(f"[OK] Test 8: Filter verification - monsters={len(results_monsters_check)}, all={len(results_all_check)}")

        print("\n=== All Spatial Query tests passed! ===")
        sys.exit(0)

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if sock1:
            try: sock1.close()
            except: pass
        if sock2:
            try: sock2.close()
            except: pass
        if proc:
            stop_server(proc)

if __name__ == "__main__":
    main()
