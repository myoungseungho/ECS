"""
Session 10 Validation Test - Gate Server (Load Balancing)
=========================================================

5단계 검증:
  S10-BUILD        : 빌드 성공 (FieldServer + GateServer)
  S10-GATE-CONNECT : 게이트 서버 접속
  S10-ROUTE        : 게임서버 라우팅
  S10-BALANCE      : 로드밸런싱 동작
  S10-FULL-PIPE    : 전체 파이프라인 (Gate -> Login -> CharSelect -> Game)
"""
import subprocess
import socket
import struct
import time
import sys
from pathlib import Path

BUILD_DIR = Path(__file__).parent / "build"
FIELD_EXE = BUILD_DIR / "FieldServer.exe"
GATE_EXE = BUILD_DIR / "GateServer.exe"

HOST = '127.0.0.1'
GATE_PORT = 8888
FIELD_PORT_1 = 7777
FIELD_PORT_2 = 7778

# -- 패킷 프로토콜 --
HEADER_SIZE = 6
MSG_ECHO = 1
MSG_MOVE = 10
MSG_MOVE_BROADCAST = 11
MSG_LOGIN = 60
MSG_LOGIN_RESULT = 61
MSG_CHAR_LIST_REQ = 62
MSG_CHAR_LIST_RESP = 63
MSG_CHAR_SELECT = 64
MSG_ENTER_GAME = 65
MSG_GATE_ROUTE_REQ = 70
MSG_GATE_ROUTE_RESP = 71
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload


def build_login_packet(username, password):
    uname = username.encode('utf-8')
    pw = password.encode('utf-8')
    payload = struct.pack('B', len(uname)) + uname + struct.pack('B', len(pw)) + pw
    return build_packet(MSG_LOGIN, payload)


def build_gate_route_req():
    return build_packet(MSG_GATE_ROUTE_REQ)


def build_char_list_req():
    return build_packet(MSG_CHAR_LIST_REQ)


def build_char_select_packet(char_id):
    return build_packet(MSG_CHAR_SELECT, struct.pack('<I', char_id))


def build_move_packet(x, y, z):
    return build_packet(MSG_MOVE, struct.pack('<fff', x, y, z))


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

def start_field_server(port):
    proc = subprocess.Popen(
        [str(FIELD_EXE), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    return proc


def start_gate_server(field_ports):
    args = [str(GATE_EXE)] + [str(p) for p in field_ports]
    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    return proc


def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except:
            proc.kill()


def connect(port, host=HOST):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((host, port))
    time.sleep(0.3)
    return sock


def parse_route_resp(payload):
    """GATE_ROUTE_RESP: result(1) port(2) ip_len(1) ip(N)"""
    if not payload or len(payload) < 4:
        return None, None, None
    result = payload[0]
    port = struct.unpack('<H', payload[1:3])[0]
    ip_len = payload[3]
    ip = payload[4:4+ip_len].decode('utf-8') if len(payload) >= 4 + ip_len else ""
    return result, port, ip


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
print("  Session 10 Validation Test")
print("  Gate Server (Load Balancing)")
print("=" * 60)
print()

# 서버 시작: FieldServer x2 + GateServer x1
field1 = start_field_server(FIELD_PORT_1)
field2 = start_field_server(FIELD_PORT_2)
time.sleep(2.5)

gate = start_gate_server([FIELD_PORT_1, FIELD_PORT_2])
time.sleep(2.0)

test("FieldServer 1 started", field1.poll() is None,
     f"exited {field1.returncode}" if field1.poll() is not None else "")
test("FieldServer 2 started", field2.poll() is None,
     f"exited {field2.returncode}" if field2.poll() is not None else "")
test("GateServer started", gate.poll() is None,
     f"exited {gate.returncode}" if gate.poll() is not None else "")

print()

try:
    # -- S10-GATE-CONNECT: 게이트 서버 접속 --
    print("--- S10-GATE-CONNECT: Gate server connection ---")
    print()

    gc = connect(GATE_PORT)
    test("TCP connect to gate server (port 8888)", gc is not None)
    gc.close()

    print()

    # -- S10-ROUTE: 게임서버 라우팅 --
    print("--- S10-ROUTE: Game server routing ---")
    print()

    gc = connect(GATE_PORT)
    drain(gc)

    gc.sendall(build_gate_route_req())
    time.sleep(0.5)

    msg_type, payload = try_recv_packet(gc, timeout=2)

    test("GATE_ROUTE_RESP received",
         msg_type == MSG_GATE_ROUTE_RESP,
         f"msg_type={msg_type}")

    routed_port = None
    routed_ip = None
    if msg_type == MSG_GATE_ROUTE_RESP and payload:
        result, port, ip = parse_route_resp(payload)

        test("Route result = SUCCESS (0)",
             result == 0,
             f"result={result}")

        test("Routed port is valid (7777 or 7778)",
             port in [FIELD_PORT_1, FIELD_PORT_2],
             f"port={port}")

        test("Routed IP is 127.0.0.1",
             ip == "127.0.0.1",
             f"ip={ip}")

        routed_port = port
        routed_ip = ip

    gc.close()

    # 라우팅 받은 게임서버에 실제 접속 가능한지
    if routed_port:
        fc = connect(routed_port)
        # ECHO로 동작 확인
        fc.sendall(build_packet(MSG_ECHO, b"hello"))
        time.sleep(0.3)
        msg_type, payload = try_recv_packet(fc, timeout=2)
        test("Routed game server responds to ECHO",
             msg_type == MSG_ECHO and payload == b"hello",
             f"msg_type={msg_type}, payload={payload}")
        fc.close()

    print()

    # -- S10-BALANCE: 로드밸런싱 --
    print("--- S10-BALANCE: Load balancing (10 clients) ---")
    print()

    port_counts = {FIELD_PORT_1: 0, FIELD_PORT_2: 0}

    for i in range(10):
        gc = connect(GATE_PORT)
        drain(gc)
        gc.sendall(build_gate_route_req())
        time.sleep(0.3)
        msg_type, payload = try_recv_packet(gc, timeout=2)
        if msg_type == MSG_GATE_ROUTE_RESP and payload:
            result, port, ip = parse_route_resp(payload)
            if result == 0 and port in port_counts:
                port_counts[port] += 1
        gc.close()

    count_1 = port_counts[FIELD_PORT_1]
    count_2 = port_counts[FIELD_PORT_2]

    test(f"10 clients routed total (got {count_1}+{count_2})",
         count_1 + count_2 == 10,
         f"7777={count_1}, 7778={count_2}")

    test(f"Load balanced: 7777={count_1}, 7778={count_2} (each 3~7)",
         3 <= count_1 <= 7 and 3 <= count_2 <= 7,
         f"7777={count_1}, 7778={count_2}")

    test("Both servers received clients",
         count_1 > 0 and count_2 > 0,
         f"7777={count_1}, 7778={count_2}")

    print()

    # -- S10-FULL-PIPE: 전체 파이프라인 --
    print("--- S10-FULL-PIPE: Full pipeline (Gate -> Login -> Game) ---")
    print()

    # Step 1: Gate에서 서버 배정
    gc = connect(GATE_PORT)
    drain(gc)
    gc.sendall(build_gate_route_req())
    time.sleep(0.3)
    msg_type, payload = try_recv_packet(gc, timeout=2)
    result, game_port, game_ip = parse_route_resp(payload) if msg_type == MSG_GATE_ROUTE_RESP else (None, None, None)
    gc.close()

    test("Step 1: Gate routing OK",
         result == 0 and game_port is not None,
         f"result={result}, port={game_port}")

    if game_port:
        # Step 2: 게임서버 접속 + 로그인
        fc = connect(game_port)
        drain(fc)

        fc.sendall(build_login_packet("hero", "pass123"))
        time.sleep(0.5)
        msg_type, payload = try_recv_packet(fc, timeout=2)
        login_ok = msg_type == MSG_LOGIN_RESULT and payload and payload[0] == 0

        test("Step 2: Login OK on game server",
             login_ok,
             f"msg_type={msg_type}")

        # Step 3: 캐릭터 목록
        drain(fc)
        fc.sendall(build_char_list_req())
        time.sleep(0.5)
        msg_type, payload = try_recv_packet(fc, timeout=2)
        charlist_ok = msg_type == MSG_CHAR_LIST_RESP and payload and payload[0] >= 1

        test("Step 3: Character list received",
             charlist_ok,
             f"msg_type={msg_type}, count={payload[0] if payload else 0}")

        # Step 4: 캐릭터 선택 → 게임 진입
        drain(fc)
        fc.sendall(build_char_select_packet(1))
        time.sleep(0.5)
        msg_type, payload = try_recv_packet(fc, timeout=2)
        enter_ok = msg_type == MSG_ENTER_GAME and payload and payload[0] == 0

        test("Step 4: Enter game OK",
             enter_ok,
             f"msg_type={msg_type}")

        # Step 5: 게임 내 이동
        drain(fc)
        fc.sendall(build_move_packet(200.0, 300.0, 0.0))
        time.sleep(0.5)
        # 이동은 응답이 없지만 (브로드캐스트), STATS로 Entity 존재 확인
        fc.sendall(build_packet(MSG_STATS))
        time.sleep(0.3)
        pkts = recv_all_available(fc, timeout=1.5)
        stats_pkts = [p for p in pkts if p[0] == MSG_STATS]
        has_pos = False
        if stats_pkts:
            stats_str = stats_pkts[0][1].decode('utf-8', errors='replace')
            has_pos = "has_position_comp=1" in stats_str

        test("Step 5: Move + STATS shows position component",
             has_pos,
             f"stats={stats_str if stats_pkts else 'none'}")

        fc.close()

    print()

    # -- 서버 건전성 --
    print("--- Server health check ---")
    print()

    test("FieldServer 1 still running",
         field1.poll() is None,
         f"exited {field1.returncode}" if field1.poll() is not None else "")
    test("FieldServer 2 still running",
         field2.poll() is None,
         f"exited {field2.returncode}" if field2.poll() is not None else "")
    test("GateServer still running",
         gate.poll() is None,
         f"exited {gate.returncode}" if gate.poll() is not None else "")

except Exception as e:
    print(f"\n  [ERROR] Exception: {e}")
    import traceback
    traceback.print_exc()
    failed += 1

finally:
    print()
    stop_server(gate)
    stop_server(field1)
    stop_server(field2)

# -- 결과 --
print()
print("=" * 60)
print(f"  Result: {passed}/{total} PASSED, {failed} FAILED")
print()
if failed == 0:
    print("  +-------------------------------------------+")
    print("  | SESSION 10 VALIDATION: ALL TESTS PASSED   |")
    print("  |                                           |")
    print("  | [O] GATE-CONNECT: Gate connection OK      |")
    print("  | [O] ROUTE: Server routing OK              |")
    print("  | [O] BALANCE: Load balancing OK            |")
    print("  | [O] FULL-PIPE: Full pipeline OK           |")
    print("  |                                           |")
    print("  | ========================================= |")
    print("  | PROJECT COMPLETE! All 10 sessions done!   |")
    print("  | ========================================= |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 10 VALIDATION: SOME TESTS FAILED  |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
