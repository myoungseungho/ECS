"""
Test Session 28 - Quest System
Tests quest acceptance, progress tracking, completion, and prerequisites
"""

import subprocess, socket, struct, time, sys, os
from pathlib import Path

BUILD_DIR = Path(__file__).parent / "build"
FIELD_EXE = BUILD_DIR / "FieldServer.exe"
HOST = '127.0.0.1'
PORT = 7777
HEADER_SIZE = 6

# ATTACK_RESULT payload format (29 bytes):
# [0]     result (uint8_t) - AttackResult enum
# [1:9]   attacker (uint64_t)
# [9:17]  target (uint64_t)
# [17:21] damage (int32_t)
# [21:25] target_hp (int32_t)
# [25:29] target_max_hp (int32_t)
#
# AttackResult enum:
# SUCCESS=0, TARGET_NOT_FOUND=1, TARGET_DEAD=2, OUT_OF_RANGE=3,
# COOLDOWN_NOT_READY=4, ATTACKER_DEAD=5, SELF_ATTACK=6

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

def move_to(sock, x, y, z):
    drain(sock, 0.3)
    sock.sendall(build_packet(10, struct.pack('<fff', x, y, z)))
    for _ in range(10):
        msg_type, pl = try_recv(sock, timeout=2.0)
        if msg_type is None or msg_type == 11:
            break
    time.sleep(0.3)

def get_quest_list(sock):
    """Get quest list. Returns list of (quest_id, state, progress)."""
    drain(sock, 0.3)
    sock.sendall(build_packet(230))  # QUEST_LIST_REQ
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for quest list")
        if msg_type == 231:  # QUEST_LIST_RESP
            count = pl[0]
            quests = []
            offset = 1
            for i in range(count):
                quest_id = struct.unpack('<I', pl[offset:offset+4])[0]
                state = pl[offset+4]
                progress = struct.unpack('<I', pl[offset+5:offset+9])[0]
                # target is at offset+9:offset+13 (4 bytes) - skip it
                quests.append((quest_id, state, progress))
                offset += 13  # quest_id(4) + state(1) + progress(4) + target(4)
            return quests
    raise Exception("Never got QUEST_LIST_RESP(231)")

def accept_quest(sock, quest_id):
    drain(sock, 0.3)
    payload = struct.pack('<I', quest_id)
    sock.sendall(build_packet(232, payload))  # QUEST_ACCEPT
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for quest accept")
        if msg_type == 233:  # QUEST_ACCEPT_RESULT
            return pl[0]
    raise Exception("Never got QUEST_ACCEPT_RESULT(233)")

def complete_quest(sock, quest_id):
    drain(sock, 0.3)
    payload = struct.pack('<I', quest_id)
    sock.sendall(build_packet(235, payload))  # QUEST_COMPLETE
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for quest complete")
        if msg_type == 236:  # QUEST_COMPLETE_RESULT
            return pl[0]
    raise Exception("Never got QUEST_COMPLETE_RESULT(236)")

def spatial_query(sock, x, y, z, radius, filter_type=2):
    drain(sock, 0.3)
    payload = struct.pack('<ffffB', x, y, z, radius, filter_type)
    sock.sendall(build_packet(215, payload))
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

def attack_and_wait(sock, target_id):
    """Send ATTACK_REQ and read all response packets.
    Returns (died:bool, damage:int, result_code:int)"""
    drain(sock, 0.3)
    sock.sendall(build_packet(100, struct.pack('<Q', target_id)))

    died = False
    damage = 0
    result_code = -1

    for _ in range(20):
        msg_type, pl = try_recv(sock, timeout=2.0)
        if msg_type is None:
            break
        if msg_type == 102:  # COMBAT_DIED
            died = True
            break
        elif msg_type == 101:  # ATTACK_RESULT (29 bytes)
            if pl and len(pl) >= 29:
                result_code = pl[0]
                damage = struct.unpack('<i', pl[17:21])[0]
                target_hp = struct.unpack('<i', pl[21:25])[0]
                if result_code == 0 and target_hp <= 0:
                    # Monster should die, COMBAT_DIED should follow
                    for _ in range(10):
                        mt, p = try_recv(sock, timeout=1.0)
                        if mt is None:
                            break
                        if mt == 102:
                            died = True
                            break
                    break
            break
        # Skip STAT_SYNC(91) and other packets

    return died, damage, result_code

def kill_monsters(sock, count_needed):
    """Kill monsters by moving to known spawn locations.
    Zone 1 monster spawns: (200,200), (400,300), (300,500), (100,400), (500,100)"""
    monster_positions = [
        (200.0, 200.0, 0.0),
        (400.0, 300.0, 0.0),
        (300.0, 500.0, 0.0),
        (100.0, 400.0, 0.0),
        (500.0, 100.0, 0.0),
    ]

    kills = 0
    for pos_idx, (mx, my, mz) in enumerate(monster_positions):
        if kills >= count_needed:
            break

        # Move hero near monster spawn
        move_to(sock, mx, my, mz)
        time.sleep(0.5)

        # Find nearby monsters (within attack range 200)
        nearby = spatial_query(sock, mx, my, mz, 250.0, 2)
        if not nearby:
            print(f"  No monsters near ({mx}, {my})")
            continue

        for entity_id, dist in nearby:
            if kills >= count_needed:
                break
            if dist > 200:
                continue

            print(f"  Attacking entity {entity_id} (dist={dist:.0f})...")

            # Attack with cooldown handling
            for attempt in range(15):
                died, damage, result_code = attack_and_wait(sock, entity_id)
                if died:
                    kills += 1
                    print(f"    Monster died! ({kills}/{count_needed})")
                    # Wait for cooldown after kill
                    time.sleep(2.5)
                    break
                elif result_code == 0 and damage > 0:
                    print(f"    Hit! damage={damage}")
                    time.sleep(2.5)  # Wait for cooldown
                elif result_code == 2:  # TARGET_DEAD
                    print(f"    Target already dead")
                    break
                elif result_code == 3:  # OUT_OF_RANGE
                    print(f"    Out of range")
                    break
                elif result_code == 4:  # COOLDOWN_NOT_READY
                    time.sleep(1.0)  # Wait for cooldown
                elif result_code == 1:  # TARGET_NOT_FOUND
                    break
                else:
                    time.sleep(1.0)

    return kills

def get_inventory(sock):
    """Get inventory. Returns list of (item_id, quantity).
    Protocol: INVENTORY_REQ=190, INVENTORY_RESP=191
    Resp format: [count(1)] + {slot(1) item_id(4) count(2) equipped(1)}... = 8 per item"""
    drain(sock, 0.5)
    sock.sendall(build_packet(190))  # INVENTORY_REQ
    for _ in range(30):
        msg_type, pl = try_recv(sock, timeout=3.0)
        if msg_type is None:
            break
        if msg_type == 191:  # INVENTORY_RESP
            count = pl[0]
            items = []
            offset = 1
            for i in range(count):
                slot = pl[offset]
                item_id = struct.unpack('<I', pl[offset+1:offset+5])[0]
                quantity = struct.unpack('<H', pl[offset+5:offset+7])[0]
                equipped = pl[offset+7]
                items.append((item_id, quantity))
                offset += 8
            return items
    return None

def main():
    proc = None
    sock = None
    try:
        proc = start_server()
        sock = connect_to_server()
        assert sock is not None, "Failed to connect to server"

        sock = login_and_enter(sock, 'hero', 'pass123', 1)
        print("[OK] Logged in as hero")

        # Test 1: QUEST_LIST initially should be empty
        quests = get_quest_list(sock)
        assert len(quests) == 0, f"Expected 0 quests initially, got {len(quests)}"
        print(f"[OK] Test 1: Initial quest list is empty")

        # Test 2: Accept quest 1 (Beginner Hunt)
        result = accept_quest(sock, 1)
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        print(f"[OK] Test 2: Quest 1 accepted successfully")

        # Test 3: Accept quest 1 again - should fail with ALREADY_ACCEPTED
        result = accept_quest(sock, 1)
        assert result == 2, f"Expected ALREADY_ACCEPTED(2), got {result}"
        print(f"[OK] Test 3: Quest 1 already accepted (error code 2)")

        # Test 4: QUEST_LIST should show quest 1 with state ACCEPTED(1)
        quests = get_quest_list(sock)
        assert len(quests) == 1, f"Expected 1 quest, got {len(quests)}"
        quest_id, state, progress = quests[0]
        assert quest_id == 1 and state == 1, f"Expected quest 1 state ACCEPTED(1), got {state}"
        print(f"[OK] Test 4: Quest list shows quest 1 in ACCEPTED state")

        # Test 5: Try to accept quest 5 (requires quest 1 completion)
        result = accept_quest(sock, 5)
        assert result == 4, f"Expected PREREQUISITE_NOT_MET(4), got {result}"
        print(f"[OK] Test 5: Quest 5 prerequisite not met (error code 4)")

        # Test 6: Accept invalid quest 99
        result = accept_quest(sock, 99)
        assert result == 1, f"Expected QUEST_NOT_FOUND(1), got {result}"
        print(f"[OK] Test 6: Invalid quest 99 not found (error code 1)")

        # Test 7: Try to complete quest 1 without progress - should fail
        result = complete_quest(sock, 1)
        assert result == 6, f"Expected NOT_COMPLETE(6), got {result}"
        print(f"[OK] Test 7: Cannot complete quest without progress (error code 6)")

        # Test 8: Kill monsters to progress quest
        print("Killing monsters for quest...")
        kills = kill_monsters(sock, 3)
        assert kills >= 3, f"Only killed {kills} monsters, need 3"
        print(f"[OK] Test 8: Killed 3 monsters")

        # Test 9: Check quest state is now COMPLETE(3)
        time.sleep(0.5)
        quests = get_quest_list(sock)
        quest_id, state, progress = quests[0]
        assert state == 3, f"Expected quest state COMPLETE(3), got {state}"
        print(f"[OK] Test 9: Quest 1 is now COMPLETE (progress={progress})")

        # Test 10: Complete quest 1 - should succeed and give rewards
        result = complete_quest(sock, 1)
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        print(f"[OK] Test 10: Quest 1 completed successfully (100 EXP + 3 HP Potions)")

        # Test 11: Quest list should show REWARDED(4)
        quests = get_quest_list(sock)
        quest_id, state, progress = quests[0]
        assert state == 4, f"Expected quest state REWARDED(4), got {state}"
        print(f"[OK] Test 11: Quest 1 is now REWARDED")

        # Test 12: Check inventory for HP Potions (item_id=1)
        # Move away from monster spawns to reduce combat packet noise
        move_to(sock, 1500.0, 1500.0, 0.0)
        time.sleep(1.0)

        items = get_inventory(sock)
        assert items is not None, "Expected INVENTORY_RESP(191), never received"
        has_potion = any(item_id == 1 for item_id, _ in items)
        assert has_potion, "Expected HP Potion in inventory after quest reward"
        potion_qty = next(qty for item_id, qty in items if item_id == 1)
        print(f"[OK] Test 12: Inventory has HP Potion x{potion_qty}")

        print("\n=== All Quest System tests passed! ===")
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
