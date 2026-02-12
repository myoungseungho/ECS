"""
Test Session 27 - Loot/Drop Table System
Tests loot rolling with various drop tables and statistical verification
"""

import subprocess, socket, struct, time, sys, os
from pathlib import Path
from collections import Counter

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

def roll_loot(sock, table_id):
    drain(sock, 0.2)
    payload = struct.pack('<I', table_id)
    sock.sendall(build_packet(220, payload))
    msg_type, pl = recv_packet(sock)
    assert msg_type == 221, f"Expected LOOT_RESULT(221), got {msg_type}"

    count = pl[0]
    items = []
    offset = 1
    for i in range(count):
        item_id = struct.unpack('<I', pl[offset:offset+4])[0]
        item_count = struct.unpack('<H', pl[offset+4:offset+6])[0]
        items.append((item_id, item_count))
        offset += 6

    return items

def main():
    proc = None
    sock = None
    try:
        proc = start_server()
        sock = connect_to_server()
        assert sock is not None, "Failed to connect to server"

        sock = login_and_enter(sock, 'hero', 'pass123', 1)
        print("[OK] Logged in as hero")

        # Test 1: Roll table 1 (BasicMonster) - should return 0 or 1 items
        items = roll_loot(sock, 1)
        assert len(items) <= 1, f"Table 1 should have 0-1 items, got {len(items)}"
        print(f"[OK] Test 1: Table 1 (BasicMonster) rolled {len(items)} items")

        # Test 2: Roll table 3 (BossMonster) - should always have item 11
        items = roll_loot(sock, 3)
        item_ids = [item[0] for item in items]
        assert 11 in item_ids, "Table 3 should always contain guaranteed item 11"
        print(f"[OK] Test 2: Table 3 (BossMonster) contains guaranteed item 11")

        # Test 3: Roll table 3 - count should be >= 1 (guaranteed + rolls)
        items = roll_loot(sock, 3)
        assert len(items) >= 1, "Table 3 should have at least 1 item (guaranteed)"
        print(f"[OK] Test 3: Table 3 rolled {len(items)} items (>= 1)")

        # Test 4: Roll invalid table 99 - should return 0 items
        items = roll_loot(sock, 99)
        assert len(items) == 0, f"Invalid table should return 0 items, got {len(items)}"
        print(f"[OK] Test 4: Invalid table 99 returned 0 items")

        # Test 5: Roll table 1 many times - statistical check
        print("Rolling table 1 fifty times for statistical verification...")
        all_items = []
        for i in range(50):
            items = roll_loot(sock, 1)
            for item in items:
                all_items.append(item[0])
            time.sleep(0.05)  # Small delay to avoid overwhelming server

        item_counts = Counter(all_items)
        assert 1 in item_counts or 2 in item_counts, "Expected to see items 1 or 2 after 50 rolls"
        print(f"[OK] Test 5: Table 1 statistical results: {dict(item_counts)}")

        # Test 6: Roll table 2 (EliteMonster) - 2 rolls, so 0-2 items
        items = roll_loot(sock, 2)
        assert len(items) <= 2, f"Table 2 should have 0-2 items, got {len(items)}"
        print(f"[OK] Test 6: Table 2 (EliteMonster) rolled {len(items)} items (0-2 expected)")

        # Test 7: Roll table 4 (TreasureChest) - 1 roll
        items = roll_loot(sock, 4)
        assert len(items) <= 1, f"Table 4 should have 0-1 items, got {len(items)}"
        print(f"[OK] Test 7: Table 4 (TreasureChest) rolled {len(items)} items")

        # Test 8: Verify table 3 always has at least the guaranteed item
        print("Rolling table 3 ten times to verify guaranteed drop...")
        all_contain_11 = True
        for i in range(10):
            items = roll_loot(sock, 3)
            item_ids = [item[0] for item in items]
            if 11 not in item_ids:
                all_contain_11 = False
                break
            time.sleep(0.05)

        assert all_contain_11, "All table 3 rolls should contain item 11"
        print(f"[OK] Test 8: All 10 rolls of table 3 contained guaranteed item 11")

        print("\n=== All Loot/Drop Table tests passed! ===")
        sys.exit(0)

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if sock:
            try: sock.close()
            except: pass
        if proc:
            stop_server(proc)

if __name__ == "__main__":
    main()
