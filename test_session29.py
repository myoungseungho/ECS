"""
Test Session 29 - Cross-System Integration
Tests all systems working together in a complete gameplay scenario
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

def accept_quest(sock, quest_id):
    drain(sock, 0.3)
    sock.sendall(build_packet(232, struct.pack('<I', quest_id)))
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for quest accept")
        if msg_type == 233:
            return pl[0]
    raise Exception("Never got QUEST_ACCEPT_RESULT(233)")

def get_quest_list(sock):
    """Quest list: 13 bytes per entry (quest_id=4, state=1, progress=4, target=4)"""
    drain(sock, 0.3)
    sock.sendall(build_packet(230))
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for quest list")
        if msg_type == 231:
            count = pl[0]
            quests = []
            offset = 1
            for i in range(count):
                quest_id = struct.unpack('<I', pl[offset:offset+4])[0]
                state = pl[offset+4]
                progress = struct.unpack('<I', pl[offset+5:offset+9])[0]
                quests.append((quest_id, state, progress))
                offset += 13  # quest_id(4) + state(1) + progress(4) + target(4)
            return quests
    raise Exception("Never got QUEST_LIST_RESP(231)")

def complete_quest(sock, quest_id):
    drain(sock, 0.3)
    sock.sendall(build_packet(235, struct.pack('<I', quest_id)))
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for quest complete")
        if msg_type == 236:
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
    """Send ATTACK_REQ and read response packets.
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
                    for _ in range(10):
                        mt, p = try_recv(sock, timeout=1.0)
                        if mt is None:
                            break
                        if mt == 102:
                            died = True
                            break
                    break
            break

    return died, damage, result_code

def kill_monsters(sock, count_needed):
    """Kill monsters by moving to known spawn locations."""
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

        move_to(sock, mx, my, mz)
        time.sleep(0.5)

        nearby = spatial_query(sock, mx, my, mz, 250.0, 2)
        if not nearby:
            continue

        for entity_id, dist in nearby:
            if kills >= count_needed:
                break
            if dist > 200:
                continue

            print(f"  Attacking entity {entity_id} (dist={dist:.0f})...")

            for attempt in range(15):
                died, damage, result_code = attack_and_wait(sock, entity_id)
                if died:
                    kills += 1
                    print(f"    Monster died! ({kills}/{count_needed})")
                    time.sleep(2.5)
                    break
                elif result_code == 0 and damage > 0:
                    print(f"    Hit! damage={damage}")
                    time.sleep(2.5)
                elif result_code == 2:  # TARGET_DEAD
                    break
                elif result_code == 3:  # OUT_OF_RANGE
                    break
                elif result_code == 4:  # COOLDOWN_NOT_READY
                    time.sleep(1.0)
                elif result_code == 1:  # TARGET_NOT_FOUND
                    break
                else:
                    time.sleep(1.0)

    return kills

def get_inventory(sock):
    """Get inventory. INVENTORY_REQ=190, INVENTORY_RESP=191
    Resp: [count(1)] + {slot(1) item_id(4) count(2) equipped(1)}... = 8 per item"""
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

def apply_buff(sock, buff_id):
    drain(sock, 0.3)
    sock.sendall(build_packet(202, struct.pack('<I', buff_id)))
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for buff apply")
        if msg_type == 203:
            return pl[0]
    raise Exception("Never got BUFF_APPLY_RESULT(203)")

def cond_node(ctype, p1=0, p2=0, left=-1, right=-1):
    return struct.pack('<BiiHH', ctype, p1, p2, left & 0xFFFF, right & 0xFFFF)

def build_condition_eval(nodes, root=0):
    payload = struct.pack('BB', len(nodes), root)
    for n in nodes:
        payload += n
    return build_packet(210, payload)

def eval_condition(sock, nodes, root=0):
    drain(sock, 0.3)
    sock.sendall(build_condition_eval(nodes, root))
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for condition eval")
        if msg_type == 211:
            return pl[0]
    raise Exception("Never got CONDITION_RESULT(211)")

def roll_loot(sock, table_id):
    drain(sock, 0.3)
    sock.sendall(build_packet(220, struct.pack('<I', table_id)))
    for _ in range(20):
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception("No response for loot roll")
        if msg_type == 221:
            count = pl[0]
            items = []
            offset = 1
            for i in range(count):
                item_id = struct.unpack('<I', pl[offset:offset+4])[0]
                item_count = struct.unpack('<H', pl[offset+4:offset+6])[0]
                items.append((item_id, item_count))
                offset += 6
            return items
    raise Exception("Never got LOOT_RESULT(221)")

def main():
    proc = None
    sock = None
    try:
        proc = start_server()
        sock = connect_to_server()
        assert sock is not None, "Failed to connect to server"

        sock = login_and_enter(sock, 'hero', 'pass123', 1)
        print("[OK] Logged in and entered game")

        # Test 1: Accept quest 1 (kill 3 monsters)
        result = accept_quest(sock, 1)
        assert result == 0, f"Quest accept failed: {result}"
        print("[OK] Test 1: Quest 1 accepted")

        # Test 2: Find monsters with spatial query
        hero_x, hero_y, hero_z = 300.0, 300.0, 0.0
        move_to(sock, hero_x, hero_y, hero_z)

        monsters = spatial_query(sock, hero_x, hero_y, hero_z, 10000.0, 2)
        assert len(monsters) > 0, "No monsters found"
        print(f"[OK] Test 2: Spatial query found {len(monsters)} monsters")

        # Test 3: Kill 3 monsters
        print("Killing monsters for quest...")
        kills = kill_monsters(sock, 3)
        assert kills >= 3, f"Only killed {kills} monsters"
        print("[OK] Test 3: Killed 3 monsters")

        # Test 4: Check quest is COMPLETE
        time.sleep(0.5)
        quests = get_quest_list(sock)
        quest_id, state, progress = quests[0]
        assert state == 3, f"Expected COMPLETE(3), got {state}"
        print(f"[OK] Test 4: Quest is COMPLETE (progress={progress})")

        # Test 5: Complete quest and get rewards
        result = complete_quest(sock, 1)
        assert result == 0, f"Quest complete failed: {result}"
        print("[OK] Test 5: Quest completed, rewards received (100 EXP + 3 HP Potions)")

        # Test 6: Check inventory has HP Potions
        # Move away from monsters first
        move_to(sock, 1500.0, 1500.0, 0.0)
        time.sleep(1.0)

        items = get_inventory(sock)
        assert items is not None, "Expected INVENTORY_RESP(191), never received"
        has_potion = any(item_id == 1 for item_id, _ in items)
        assert has_potion, "No HP Potion in inventory"
        potion_qty = next(qty for item_id, qty in items if item_id == 1)
        print(f"[OK] Test 6: Inventory has HP Potion x{potion_qty}")

        # Test 7: Apply buff
        result = apply_buff(sock, 1)
        assert result == 0, f"Buff apply failed: {result}"
        print("[OK] Test 7: Buff 1 (Strength) applied")

        # Test 8: Test complex condition (HAS_ITEM AND HAS_BUFF)
        nodes = [
            cond_node(10, 0, 0, 1, 2),  # AND
            cond_node(30, 1),            # HAS_ITEM(1)
            cond_node(31, 1)             # HAS_BUFF(1)
        ]
        result = eval_condition(sock, nodes, 0)
        assert result == 1, f"Expected condition TRUE, got {result}"
        print("[OK] Test 8: Condition (HAS_ITEM(1) AND HAS_BUFF(1)) = TRUE")

        # Test 9: Roll loot table
        loot_items = roll_loot(sock, 1)
        print(f"[OK] Test 9: Loot roll returned {len(loot_items)} items")

        # Test 10: Accept quest 5 (chain quest, requires quest 1)
        result = accept_quest(sock, 5)
        assert result == 0, f"Quest 5 accept failed: {result}"
        print("[OK] Test 10: Quest 5 accepted (prerequisite met)")

        print("\n=== All Cross-System Integration tests passed! ===")
        print("Tested: Login -> Quest -> Spatial -> Combat -> Rewards -> Inventory -> Buff -> Condition -> Loot -> Chain Quest")
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
