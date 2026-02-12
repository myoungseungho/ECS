"""
Session 1 Validation Test (Session 2+ compatible)
===================================================
ECS + IOCP 시스템 검증 - 패킷 프로토콜 사용 버전

3단계 검증:
  Level 1: ECS 내부 상태 확인 (STATS 패킷)
  Level 2: Entity 생명주기 (접속->생성, 접속해제->파괴)
  Level 3: 멀티 클라이언트 독립성
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

# 패킷 프로토콜
HEADER_SIZE = 6
MSG_ECHO = 1
MSG_PING = 2
MSG_STATS = 99


def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    header = struct.pack('<IH', total_len, msg_type)
    return header + payload


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


# ── Utility ──

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


def send_echo(sock, data):
    """ECHO 패킷 전송 후 응답 수신"""
    if isinstance(data, str):
        data = data.encode()
    sock.sendall(build_packet(MSG_ECHO, data))
    rtype, rpayload = recv_packet(sock)
    return rpayload


def get_stats(sock):
    """STATS 패킷으로 ECS 내부 상태 조회"""
    sock.sendall(build_packet(MSG_STATS, b""))
    rtype, rpayload = recv_packet(sock)
    if rtype != MSG_STATS or not rpayload:
        return {}
    text = rpayload.decode('utf-8')
    result = {}
    for part in text.split('|'):
        if '=' in part:
            k, v = part.split('=', 1)
            result[k] = int(v)
    return result


# ── Test framework ──

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


# ════════════════════════════════════════════
print("=" * 60)
print("  Session 1 Validation Test")
print("  ECS + IOCP System Verification")
print("=" * 60)
print()

server = start_server()
print(f"Server started (PID: {server.pid})")
print()

try:
    # ── Level 1: ECS Internal State ──
    print("--- Level 1: ECS Internal State ---")
    print("  (STATS packet -> ECS World internals)")
    print()

    c1 = connect()
    stats = get_stats(c1)

    # Establish baseline (includes monsters + this 1 connection)
    baseline = stats.get('entity_count', 0)

    test("Entity count baseline established",
         baseline > 0,
         f"baseline={baseline} (includes monsters + 1 player)")

    test("SessionComponent attached",
         stats.get('has_session_comp') == 1,
         f"got {stats.get('has_session_comp')}")

    test("RecvBufferComponent attached",
         stats.get('has_recv_comp') == 1,
         f"got {stats.get('has_recv_comp')}")

    # Echo still works
    resp = send_echo(c1, b"hello_ecs")
    test("Echo via packet protocol",
         resp == b"hello_ecs",
         f"got {resp}")

    c1.close()
    time.sleep(0.5)
    print()

    # ── Level 2: Entity Lifecycle ──
    print("--- Level 2: Entity Lifecycle ---")
    print("  (connect -> Entity create, disconnect -> Entity destroy)")
    print()

    c2a = connect()
    c2b = connect()
    time.sleep(0.3)

    stats_2 = get_stats(c2a)
    current_count = stats_2.get('entity_count', 0)
    test("2 connections -> Entity count = baseline+1",
         current_count == baseline + 1,
         f"expected {baseline + 1}, got {current_count}")

    c2b.close()
    time.sleep(0.5)

    stats_after = get_stats(c2a)
    after_count = stats_after.get('entity_count', 0)
    test("1 disconnect -> Entity count = baseline",
         after_count == baseline,
         f"expected {baseline}, got {after_count}")

    c2c = connect()
    time.sleep(0.3)
    stats_rejoin = get_stats(c2a)
    rejoin_count = stats_rejoin.get('entity_count', 0)
    test("Reconnect -> Entity count = baseline+1",
         rejoin_count == baseline + 1,
         f"expected {baseline + 1}, got {rejoin_count}")

    c2a.close()
    c2c.close()
    time.sleep(0.5)
    print()

    # ── Level 3: Multi-client Independence ──
    print("--- Level 3: Multi-client Independence ---")
    print("  (5 clients, independent echo, partial disconnect)")
    print()

    clients = []
    for i in range(5):
        clients.append(connect())
    time.sleep(0.3)

    stats_5 = get_stats(clients[0])
    count_5 = stats_5.get('entity_count', 0)
    test("5 connections -> Entity count = baseline+4",
         count_5 == baseline + 4,
         f"expected {baseline + 4}, got {count_5}")

    # Independent echo
    echo_ok = True
    for i, c in enumerate(clients):
        msg = f"client_{i}".encode()
        resp = send_echo(c, msg)
        if resp != msg:
            echo_ok = False
    test("5 clients independent echo",
         echo_ok)

    # Partial disconnect
    clients[1].close()
    clients[3].close()
    time.sleep(0.5)

    stats_3 = get_stats(clients[0])
    count_3 = stats_3.get('entity_count', 0)
    test("2 disconnects -> Entity count = baseline+2",
         count_3 == baseline + 2,
         f"expected {baseline + 2}, got {count_3}")

    remaining_ok = True
    for i in [0, 2, 4]:
        msg = f"alive_{i}".encode()
        try:
            resp = send_echo(clients[i], msg)
            if resp != msg:
                remaining_ok = False
        except:
            remaining_ok = False
    test("Remaining 3 clients echo OK",
         remaining_ok)

    for c in clients:
        try:
            c.close()
        except:
            pass
    time.sleep(0.5)

    # Clean reconnect
    c_final = connect()
    stats_final = get_stats(c_final)
    final_count = stats_final.get('entity_count', 0)
    test("Full disconnect + reconnect -> Entity count = baseline",
         final_count == baseline,
         f"expected {baseline}, got {final_count}")
    c_final.close()

except Exception as e:
    print(f"\n  [ERROR] Exception: {e}")
    import traceback
    traceback.print_exc()
    failed += 1

finally:
    print()
    stop_server(server)

# ── Result ──
print()
print("=" * 60)
print(f"  Result: {passed}/{total} PASSED, {failed} FAILED")
print()
if failed == 0:
    print("  +-------------------------------------------+")
    print("  | SESSION 1 VALIDATION: ALL TESTS PASSED    |")
    print("  |                                           |")
    print("  | [O] ECS internal state OK                 |")
    print("  | [O] Entity lifecycle OK                   |")
    print("  | [O] Multi-client independence OK          |")
    print("  +-------------------------------------------+")
else:
    print("  +-------------------------------------------+")
    print("  | SESSION 1 VALIDATION: SOME TESTS FAILED   |")
    print("  +-------------------------------------------+")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
