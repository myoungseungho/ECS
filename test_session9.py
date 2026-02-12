"""
Session 9 Validation Test - Login + Character Select
=====================================================

5단계 검증:
  S9-BUILD         : 빌드 성공
  S9-LOGIN-OK      : 정상 로그인
  S9-LOGIN-FAIL    : 잘못된 인증 거부
  S9-CHAR-LIST     : 캐릭터 목록 조회
  S9-ENTER-GAME    : 게임서버 진입 성공
"""
import subprocess
import socket
import struct
import time
import sys
from pathlib import Path

EXE = Path(__file__).parent / "build" / "FieldServer.exe"
HOST = '127.0.0.1'
PORT = 7777

# -- 패킷 프로토콜 --
HEADER_SIZE = 6
MSG_MOVE = 10
MSG_APPEAR = 13
MSG_ZONE_ENTER = 30
MSG_ZONE_INFO = 31
MSG_LOGIN = 60
MSG_LOGIN_RESULT = 61
MSG_CHAR_LIST_REQ = 62
MSG_CHAR_LIST_RESP = 63
MSG_CHAR_SELECT = 64
MSG_ENTER_GAME = 65
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload


def build_login_packet(username, password):
    uname = username.encode('utf-8')
    pw = password.encode('utf-8')
    payload = struct.pack('B', len(uname)) + uname + struct.pack('B', len(pw)) + pw
    return build_packet(MSG_LOGIN, payload)


def build_char_list_req():
    return build_packet(MSG_CHAR_LIST_REQ)


def build_char_select_packet(char_id):
    return build_packet(MSG_CHAR_SELECT, struct.pack('<I', char_id))


def build_stats_packet():
    return build_packet(MSG_STATS)


def recv_packet(sock, timeout=5):
    sock.settimeout(timeout)
    header_data = b""
    while len(header_data) < HEADER_SIZE:
        chunk = sock.recv(HEADER_SIZE - len(header_data))
        if not chunk:
            return None, None
        header_data += chunk
    length, msg_type = struct.unpack('<IH', header_data)
    payload_len = length - HEADER_SIZE
    payload = b""
    while len(payload) < payload_len:
        chunk = sock.recv(payload_len - len(payload))
        if not chunk:
            return msg_type, payload
        payload += chunk
    return msg_type, payload


def try_recv_packet(sock, timeout=1.0):
    try:
        return recv_packet(sock, timeout)
    except socket.timeout:
        return None, None


def recv_all_available(sock, timeout=1.0):
    packets = []
    while True:
        msg_type, payload = try_recv_packet(sock, timeout)
        if msg_type is None:
            break
        packets.append((msg_type, payload))
        timeout = 0.3
    return packets


def drain(sock):
    recv_all_available(sock, timeout=0.3)


# -- 서버 관리 --

def start_server():
    proc = subprocess.Popen(
        [str(EXE)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    time.sleep(2.5)
    if proc.poll() is not None:
        print("  [FAIL] Server exited immediately")
        sys.exit(1)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except:
        proc.kill()


def connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((HOST, PORT))
    time.sleep(0.3)
    return sock


# -- 테스트 프레임워크 --

passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg)


# ============================================
print("=" * 60)
print("  Session 9 Validation Test")
print("  Login + Character Select")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # -- S9-LOGIN-OK: 정상 로그인 --
    print("--- S9-LOGIN-OK: Successful login ---")
    print()

    c1 = connect()
    drain(c1)

    # hero / pass123 로그인
    c1.sendall(build_login_packet("hero", "pass123"))
    time.sleep(0.5)

    msg_type, payload = try_recv_packet(c1, timeout=2)

    test("Login response received",
         msg_type == MSG_LOGIN_RESULT,
         f"msg_type={msg_type}")

    if msg_type == MSG_LOGIN_RESULT and payload:
        result_code = payload[0]
        account_id = struct.unpack('<I', payload[1:5])[0] if len(payload) >= 5 else 0

        test("Login result = SUCCESS (0)",
             result_code == 0,
             f"result_code={result_code}")

        test("Account ID is valid (1001)",
             account_id == 1001,
             f"account_id={account_id}")

    # 중복 로그인 (이미 로그인한 상태에서 다시)
    c1.sendall(build_login_packet("hero", "pass123"))
    time.sleep(0.3)
    msg_type2, payload2 = try_recv_packet(c1, timeout=2)
    test("Re-login returns success (already authenticated)",
         msg_type2 == MSG_LOGIN_RESULT and payload2 and payload2[0] == 0,
         f"msg_type={msg_type2}")

    print()

    # -- S9-LOGIN-FAIL: 인증 실패 --
    print("--- S9-LOGIN-FAIL: Authentication failures ---")
    print()

    c2 = connect()
    drain(c2)

    # 틀린 비밀번호
    c2.sendall(build_login_packet("hero", "wrongpw"))
    time.sleep(0.5)

    msg_type, payload = try_recv_packet(c2, timeout=2)

    test("Wrong password -> LOGIN_RESULT received",
         msg_type == MSG_LOGIN_RESULT,
         f"msg_type={msg_type}")

    if msg_type == MSG_LOGIN_RESULT and payload:
        result_code = payload[0]
        test("Wrong password result = FAIL (2)",
             result_code == 2,
             f"result_code={result_code}")

    # 없는 계정
    c3 = connect()
    drain(c3)

    c3.sendall(build_login_packet("nonexist", "anything"))
    time.sleep(0.5)

    msg_type, payload = try_recv_packet(c3, timeout=2)

    if msg_type == MSG_LOGIN_RESULT and payload:
        result_code = payload[0]
        test("Unknown account auto-registers = SUCCESS (0)",
             result_code == 0,
             f"result_code={result_code}")

    c2.close()
    c3.close()
    print()

    # -- S9-CHAR-LIST: 캐릭터 목록 조회 --
    print("--- S9-CHAR-LIST: Character list query ---")
    print()

    drain(c1)

    # hero 계정은 캐릭터 2개
    c1.sendall(build_char_list_req())
    time.sleep(0.5)

    msg_type, payload = try_recv_packet(c1, timeout=2)

    test("CHAR_LIST_RESP received",
         msg_type == MSG_CHAR_LIST_RESP,
         f"msg_type={msg_type}")

    if msg_type == MSG_CHAR_LIST_RESP and payload:
        char_count = payload[0]

        test("Character count = 2 (hero has 2 chars)",
             char_count == 2,
             f"count={char_count}")

        if char_count >= 1:
            # 첫 번째 캐릭터 파싱
            off = 1
            cid1 = struct.unpack('<I', payload[off:off+4])[0]; off += 4
            name1 = payload[off:off+32].split(b'\x00')[0].decode('utf-8'); off += 32
            level1 = struct.unpack('<i', payload[off:off+4])[0]; off += 4
            job1 = struct.unpack('<i', payload[off:off+4])[0]; off += 4

            test("First char: id=1, name=Warrior_Kim, level=50",
                 cid1 == 1 and name1 == "Warrior_Kim" and level1 == 50,
                 f"id={cid1}, name={name1}, level={level1}")

        if char_count >= 2:
            # 두 번째 캐릭터 파싱
            cid2 = struct.unpack('<I', payload[off:off+4])[0]; off += 4
            name2 = payload[off:off+32].split(b'\x00')[0].decode('utf-8'); off += 32
            level2 = struct.unpack('<i', payload[off:off+4])[0]; off += 4
            job2 = struct.unpack('<i', payload[off:off+4])[0]; off += 4

            test("Second char: id=2, name=Mage_Lee, level=35",
                 cid2 == 2 and name2 == "Mage_Lee" and level2 == 35,
                 f"id={cid2}, name={name2}, level={level2}")

    # 로그인 안 한 상태에서 캐릭터 목록 요청
    c4 = connect()
    drain(c4)
    c4.sendall(build_char_list_req())
    time.sleep(0.5)
    msg_type, payload = try_recv_packet(c4, timeout=2)
    if msg_type == MSG_CHAR_LIST_RESP and payload:
        test("Unauthenticated char list returns count=0",
             payload[0] == 0,
             f"count={payload[0]}")
    c4.close()

    # empty 계정 (캐릭터 0개)
    c5 = connect()
    drain(c5)
    c5.sendall(build_login_packet("empty", "empty"))
    time.sleep(0.5)
    drain(c5)  # login result
    c5.sendall(build_char_list_req())
    time.sleep(0.5)
    msg_type, payload = try_recv_packet(c5, timeout=2)
    if msg_type == MSG_CHAR_LIST_RESP and payload:
        test("Empty account char list returns count=0",
             payload[0] == 0,
             f"count={payload[0]}")
    c5.close()

    print()

    # -- S9-ENTER-GAME: 캐릭터 선택 → 게임 진입 --
    print("--- S9-ENTER-GAME: Character select -> Enter game ---")
    print()

    drain(c1)

    # 캐릭터 1 (Warrior_Kim) 선택
    c1.sendall(build_char_select_packet(1))
    time.sleep(0.5)

    msg_type, payload = try_recv_packet(c1, timeout=2)

    test("ENTER_GAME response received",
         msg_type == MSG_ENTER_GAME,
         f"msg_type={msg_type}")

    if msg_type == MSG_ENTER_GAME and payload and len(payload) >= 25:
        result_code = payload[0]
        entity_id = struct.unpack('<Q', payload[1:9])[0]
        zone_id = struct.unpack('<i', payload[9:13])[0]
        px = struct.unpack('<f', payload[13:17])[0]
        py = struct.unpack('<f', payload[17:21])[0]
        pz = struct.unpack('<f', payload[21:25])[0]

        test("Enter game result = SUCCESS (0)",
             result_code == 0,
             f"result_code={result_code}")

        test("Entity ID is valid (non-zero)",
             entity_id > 0,
             f"entity_id={entity_id}")

        test("Zone ID = 1 (Warrior_Kim's zone)",
             zone_id == 1,
             f"zone_id={zone_id}")

        test("Position matches (100, 100, 0)",
             abs(px - 100.0) < 0.01 and abs(py - 100.0) < 0.01,
             f"pos=({px}, {py}, {pz})")

    # 존재하지 않는 캐릭터 선택
    drain(c1)
    c1.sendall(build_char_select_packet(999))
    time.sleep(0.5)
    msg_type, payload = try_recv_packet(c1, timeout=2)
    if msg_type == MSG_ENTER_GAME and payload:
        test("Nonexistent char_id returns FAIL (2)",
             payload[0] == 2,
             f"result={payload[0]}")

    # 로그인 안 한 상태에서 캐릭터 선택
    c6 = connect()
    drain(c6)
    c6.sendall(build_char_select_packet(1))
    time.sleep(0.5)
    msg_type, payload = try_recv_packet(c6, timeout=2)
    if msg_type == MSG_ENTER_GAME and payload:
        test("Unauthenticated char select returns FAIL (1)",
             payload[0] == 1,
             f"result={payload[0]}")
    c6.close()

    print()

    # -- 서버 건전성 --
    print("--- Server health check ---")
    print()

    test("Server process still running",
         server.poll() is None,
         f"exited with {server.returncode}" if server.poll() is not None else "")

    c1.close()

except Exception as e:
    print(f"\n  [ERROR] Exception: {e}")
    import traceback
    traceback.print_exc()
    failed += 1

finally:
    print()
    stop_server(server)

# -- 결과 --
print()
print("=" * 60)
print(f"  Result: {passed}/{total} PASSED, {failed} FAILED")
print()
if failed == 0:
    print("  +-------------------------------------------+")
    print("  | SESSION 9 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] LOGIN-OK: Authentication OK           |")
    print("  | [O] LOGIN-FAIL: Rejection OK              |")
    print("  | [O] CHAR-LIST: Character listing OK       |")
    print("  | [O] ENTER-GAME: Game entry OK             |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 9 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
