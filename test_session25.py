"""
Test Session 25 - Condition Engine
Tests condition evaluation system with various node types and logical operators
"""

import subprocess, socket, struct, time, sys, os
from pathlib import Path

BUILD_DIR = Path(__file__).parent / "build"
FIELD_EXE = BUILD_DIR / "FieldServer.exe"
HOST = '127.0.0.1'
PORT = 7777
HEADER_SIZE = 6

# Hero character data (from LoginComponents.h pre-registered account):
# char_id=1, name="Warrior_Kim", level=50, job=0(Warrior), zone=1
HERO_LEVEL = 50
HERO_ZONE = 1
HERO_JOB = 0

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

def cond_node(ctype, p1=0, p2=0, left=-1, right=-1):
    return struct.pack('<BiiHH', ctype, p1, p2, left & 0xFFFF, right & 0xFFFF)

def build_condition_eval(nodes, root=0):
    payload = struct.pack('BB', len(nodes), root)
    for n in nodes:
        payload += n
    return build_packet(210, payload)

def test_condition(sock, nodes, root=0, expected=None, test_name=""):
    drain(sock, 0.5)
    sock.sendall(build_condition_eval(nodes, root))
    # Read packets until we get CONDITION_RESULT(211), skip others
    attempts = 0
    while attempts < 20:
        msg_type, pl = recv_packet(sock, timeout=3)
        if msg_type is None:
            raise Exception(f"{test_name}: No response from server")
        if msg_type == 211:
            break
        attempts += 1
    assert msg_type == 211, f"{test_name}: Expected CONDITION_RESULT(211), got {msg_type}"
    result = pl[0]
    if expected is not None:
        assert result == expected, f"{test_name}: Expected {expected}, got {result}"
    print(f"[OK] {test_name}: result={result}")
    return result

def main():
    proc = None
    sock = None
    try:
        proc = start_server()
        sock = connect_to_server()
        assert sock is not None, "Failed to connect to server"

        sock = login_and_enter(sock, 'hero', 'pass123', 1)
        print(f"[OK] Logged in as hero (level {HERO_LEVEL}, job={HERO_JOB}, zone={HERO_ZONE})")

        # Test 1: ALWAYS_TRUE
        test_condition(sock, [cond_node(0)], 0, 1, "ALWAYS_TRUE")

        # Test 2: ALWAYS_FALSE
        test_condition(sock, [cond_node(1)], 0, 0, "ALWAYS_FALSE")

        # Test 3: LEVEL_GE(50) - hero is level 50, should be true
        test_condition(sock, [cond_node(20, HERO_LEVEL)], 0, 1, f"LEVEL_GE({HERO_LEVEL})")

        # Test 4: LEVEL_GE(51) - hero is level 50, should be false
        test_condition(sock, [cond_node(20, HERO_LEVEL + 1)], 0, 0, f"LEVEL_GE({HERO_LEVEL + 1})")

        # Test 5: LEVEL_GE(10) - hero is level 50, should be true
        test_condition(sock, [cond_node(20, 10)], 0, 1, "LEVEL_GE(10)")

        # Test 6: IN_ZONE(1) - hero is in zone 1
        test_condition(sock, [cond_node(40, HERO_ZONE)], 0, 1, f"IN_ZONE({HERO_ZONE})")

        # Test 7: IN_ZONE(5) - hero is not in zone 5
        test_condition(sock, [cond_node(40, 5)], 0, 0, "IN_ZONE(5)")

        # Test 8: AND(LEVEL_GE(50), IN_ZONE(1)) - both true
        nodes = [
            cond_node(10, 0, 0, 1, 2),       # AND at index 0
            cond_node(20, HERO_LEVEL),        # LEVEL_GE(50) at index 1
            cond_node(40, HERO_ZONE)          # IN_ZONE(1) at index 2
        ]
        test_condition(sock, nodes, 0, 1, f"AND(LEVEL_GE({HERO_LEVEL}), IN_ZONE({HERO_ZONE}))")

        # Test 9: AND(LEVEL_GE(51), IN_ZONE(1)) - first false
        nodes = [
            cond_node(10, 0, 0, 1, 2),       # AND at index 0
            cond_node(20, HERO_LEVEL + 1),    # LEVEL_GE(51) at index 1
            cond_node(40, HERO_ZONE)          # IN_ZONE(1) at index 2
        ]
        test_condition(sock, nodes, 0, 0, f"AND(LEVEL_GE({HERO_LEVEL + 1}), IN_ZONE({HERO_ZONE}))")

        # Test 10: OR(LEVEL_GE(51), IN_ZONE(1)) - second true
        nodes = [
            cond_node(11, 0, 0, 1, 2),       # OR at index 0
            cond_node(20, HERO_LEVEL + 1),    # LEVEL_GE(51) at index 1
            cond_node(40, HERO_ZONE)          # IN_ZONE(1) at index 2
        ]
        test_condition(sock, nodes, 0, 1, f"OR(LEVEL_GE({HERO_LEVEL + 1}), IN_ZONE({HERO_ZONE}))")

        # Test 11: NOT(IN_ZONE(5)) - hero not in zone 5
        nodes = [
            cond_node(12, 0, 0, 1, -1),  # NOT at index 0
            cond_node(40, 5)              # IN_ZONE(5) at index 1
        ]
        test_condition(sock, nodes, 0, 1, "NOT(IN_ZONE(5))")

        # Test 12: Complex - AND(LEVEL_GE(5), OR(HAS_ITEM(1), IN_ZONE(1)))
        nodes = [
            cond_node(10, 0, 0, 1, 2),  # AND at index 0
            cond_node(20, 5),            # LEVEL_GE(5) at index 1
            cond_node(11, 0, 0, 3, 4),  # OR at index 2
            cond_node(30, 1),            # HAS_ITEM(1) at index 3
            cond_node(40, HERO_ZONE)     # IN_ZONE(1) at index 4
        ]
        test_condition(sock, nodes, 0, 1, "Complex: AND(LEVEL_GE(5), OR(HAS_ITEM(1), IN_ZONE(1)))")

        # Test 13: CLASS_EQ(0) - hero is Warrior (job=0)
        test_condition(sock, [cond_node(60, HERO_JOB)], 0, 1, f"CLASS_EQ({HERO_JOB})")

        # Test 14: CLASS_EQ(2) - hero is not Mage (job=2)
        test_condition(sock, [cond_node(60, 2)], 0, 0, "CLASS_EQ(2)")

        # Test 15: Apply buff and check HAS_BUFF(1)
        print("Applying buff 1...")
        drain(sock, 0.5)
        sock.sendall(build_packet(202, struct.pack('<I', 1)))  # BUFF_APPLY_REQ
        # Skip non-buff-result packets
        for _ in range(20):
            msg_type, pl = recv_packet(sock)
            if msg_type == 203: break
        assert msg_type == 203, f"Expected BUFF_APPLY_RESULT(203), got {msg_type}"
        assert pl[0] == 0, f"Buff apply failed: {pl[0]}"
        print("[OK] Buff applied")

        test_condition(sock, [cond_node(31, 1)], 0, 1, "HAS_BUFF(1) after applying buff")

        # Test 16: HAS_BUFF(99) - non-existent buff
        test_condition(sock, [cond_node(31, 99)], 0, 0, "HAS_BUFF(99) - no such buff")

        print("\n=== All Condition Engine tests passed! ===")
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
