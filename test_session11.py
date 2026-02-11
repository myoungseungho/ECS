"""
Session 11 Tests: Infrastructure (EventBus + Timer + ConfigLoader)
=================================================================
3개 인프라 시스템 검증:
  1. EventBus - 이벤트 구독/발행/처리
  2. Timer/Scheduler - 시간 기반 로직 + EventBus 연동
  3. ConfigLoader - CSV/JSON 데이터 조회
"""
import subprocess
import socket
import struct
import time
import sys
import os
from pathlib import Path

BUILD = Path(__file__).parent / "build"
FIELD_EXE = BUILD / "FieldServer.exe"
HOST = '127.0.0.1'
PORT = 7777

HEADER = 6
MSG_ECHO            = 1
MSG_LOGIN           = 60
MSG_LOGIN_RESULT    = 61
MSG_CHAR_SELECT     = 64
MSG_ENTER_GAME      = 65
MSG_CHANNEL_JOIN    = 20
MSG_TIMER_ADD       = 80
MSG_TIMER_INFO      = 81
MSG_CONFIG_QUERY    = 82
MSG_CONFIG_RESP     = 83
MSG_EVENT_SUB_COUNT = 84
MSG_STATS           = 99

passed = 0
failed = 0
server_proc = None


def start_server():
    global server_proc
    server_proc = subprocess.Popen(
        [str(FIELD_EXE), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    time.sleep(2)
    if server_proc.poll() is not None:
        print("SERVER FAILED TO START")
        sys.exit(1)


def stop_server():
    global server_proc
    if server_proc and server_proc.poll() is None:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except:
            server_proc.kill()


def bpkt(mt, pl=b""):
    tl = HEADER + len(pl)
    return struct.pack('<IH', tl, mt) + pl


def trecv(sock, to=2.0):
    try:
        sock.settimeout(to)
        hdr = b""
        while len(hdr) < HEADER:
            c = sock.recv(HEADER - len(hdr))
            if not c:
                return None, None
            hdr += c
        ln, mt = struct.unpack('<IH', hdr)
        pl = b""
        pn = ln - HEADER
        while len(pl) < pn:
            c = sock.recv(pn - len(pl))
            if not c:
                return mt, pl
            pl += c
        return mt, pl
    except:
        return None, None


def drain(s, timeout=0.1):
    while True:
        mt, _ = trecv(s, timeout)
        if mt is None:
            break


def login_and_enter(sock):
    """로그인 + 캐릭터 선택 + 게임 진입"""
    # Login
    u, p = b"hero", b"pass123"
    sock.sendall(bpkt(MSG_LOGIN, struct.pack('B', len(u)) + u + struct.pack('B', len(p)) + p))
    mt, pl = trecv(sock)
    assert mt == MSG_LOGIN_RESULT and pl[0] == 0

    # Char select
    drain(sock)
    sock.sendall(bpkt(MSG_CHAR_SELECT, struct.pack('<I', 1)))
    mt, pl = trecv(sock)
    assert mt == MSG_ENTER_GAME and pl[0] == 0

    # Channel
    sock.sendall(bpkt(MSG_CHANNEL_JOIN, struct.pack('<i', 1)))
    time.sleep(0.1)
    drain(sock)


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((HOST, PORT))
    drain(s)
    return s


def test(name, func):
    global passed, failed
    try:
        func()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        print(f"  FAIL  {name}: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EventBus Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_eventbus_subscribers_exist():
    """EventBus에 TEST_EVENT 구독자가 등록되어 있는지"""
    s = connect()
    login_and_enter(s)
    s.sendall(bpkt(MSG_EVENT_SUB_COUNT))
    mt, pl = trecv(s)
    assert mt == MSG_EVENT_SUB_COUNT
    sub_count = struct.unpack('<i', pl[:4])[0]
    assert sub_count >= 1, f"subscribers={sub_count}, expected >= 1"
    s.close()


def test_eventbus_queue_empty_initially():
    """이벤트 큐가 처음에는 비어있는지"""
    s = connect()
    login_and_enter(s)
    s.sendall(bpkt(MSG_EVENT_SUB_COUNT))
    mt, pl = trecv(s)
    queue_size = struct.unpack('<i', pl[4:8])[0]
    assert queue_size == 0, f"queue_size={queue_size}"
    s.close()


def test_eventbus_timer_event_fires():
    """타이머 만료 시 이벤트가 발행되는지 (EventBus + Timer 연동)"""
    s = connect()
    login_and_enter(s)

    # 0.5초 후 만료 타이머 추가
    s.sendall(bpkt(MSG_TIMER_ADD, struct.pack('<iii', 42, 500, 0)))
    time.sleep(1.0)  # 타이머 만료 대기

    # 이벤트 발행 카운터 확인
    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    assert mt == MSG_TIMER_INFO
    total_events = struct.unpack('<i', pl[4:8])[0]
    assert total_events >= 1, f"events_fired={total_events}"
    s.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Timer Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_timer_add():
    """타이머 추가 후 active 카운트 증가"""
    s = connect()
    login_and_enter(s)

    # 긴 타이머 추가 (10초, 만료 안 됨)
    s.sendall(bpkt(MSG_TIMER_ADD, struct.pack('<iii', 100, 10000, 0)))
    time.sleep(0.2)

    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    assert mt == MSG_TIMER_INFO
    active = struct.unpack('<i', pl[:4])[0]
    assert active >= 1, f"active_timers={active}"
    s.close()


def test_timer_oneshot_expires():
    """1회성 타이머가 만료 후 제거되는지"""
    s = connect()
    login_and_enter(s)

    # 0.3초 후 만료 1회성 타이머
    s.sendall(bpkt(MSG_TIMER_ADD, struct.pack('<iii', 200, 300, 0)))
    time.sleep(0.1)

    # 아직 살아있는지
    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    active_before = struct.unpack('<i', pl[:4])[0]

    time.sleep(0.5)  # 만료 대기

    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    active_after = struct.unpack('<i', pl[:4])[0]
    assert active_after < active_before, f"before={active_before}, after={active_after}"
    s.close()


def test_timer_repeating():
    """반복 타이머가 여러 번 이벤트를 발행하는지"""
    s = connect()
    login_and_enter(s)

    # 이벤트 카운터 기준점
    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    events_before = struct.unpack('<i', pl[4:8])[0]

    # 0.2초 간격 반복 타이머 (0.1초 후 시작)
    s.sendall(bpkt(MSG_TIMER_ADD, struct.pack('<iii', 300, 100, 200)))
    time.sleep(1.0)  # ~4-5회 반복 예상

    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    events_after = struct.unpack('<i', pl[4:8])[0]
    fired = events_after - events_before
    assert fired >= 3, f"repeating timer fired {fired} times, expected >= 3"

    # 반복 타이머는 여전히 살아있어야 함
    active = struct.unpack('<i', pl[:4])[0]
    assert active >= 1, f"repeating timer should still be active"
    s.close()


def test_timer_multiple():
    """여러 타이머 동시 추가"""
    s = connect()
    login_and_enter(s)

    # 3개 타이머 동시 추가
    for tid in [501, 502, 503]:
        s.sendall(bpkt(MSG_TIMER_ADD, struct.pack('<iii', tid, 10000, 0)))
    time.sleep(0.3)

    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    active = struct.unpack('<i', pl[:4])[0]
    assert active >= 3, f"active={active}, expected >= 3"
    s.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ConfigLoader Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_config_csv_query_by_id():
    """CSV 테이블에서 id로 검색"""
    s = connect()
    login_and_enter(s)

    table = b"monsters"
    key = b"1"
    payload = struct.pack('B', len(table)) + table + struct.pack('B', len(key)) + key
    s.sendall(bpkt(MSG_CONFIG_QUERY, payload))

    mt, pl = trecv(s)
    assert mt == MSG_CONFIG_RESP
    assert pl[0] == 1, "should find id=1"

    data_len = struct.unpack('<H', pl[1:3])[0]
    data = pl[3:3+data_len].decode()
    # "k=v|k=v" 포맷
    pairs = dict(p.split('=', 1) for p in data.split('|'))
    assert pairs.get('name') == 'Goblin', f"name={pairs.get('name')}"
    assert pairs.get('hp') == '100', f"hp={pairs.get('hp')}"
    s.close()


def test_config_csv_query_dragon():
    """CSV에서 Dragon(id=3) 검색"""
    s = connect()
    login_and_enter(s)

    table = b"monsters"
    key = b"3"
    payload = struct.pack('B', len(table)) + table + struct.pack('B', len(key)) + key
    s.sendall(bpkt(MSG_CONFIG_QUERY, payload))

    mt, pl = trecv(s)
    assert pl[0] == 1
    data_len = struct.unpack('<H', pl[1:3])[0]
    data = pl[3:3+data_len].decode()
    pairs = dict(p.split('=', 1) for p in data.split('|'))
    assert pairs.get('name') == 'Dragon'
    assert pairs.get('hp') == '5000'
    assert pairs.get('attack') == '200'
    s.close()


def test_config_csv_not_found():
    """존재하지 않는 테이블 검색"""
    s = connect()
    login_and_enter(s)

    table = b"nonexistent"
    key = b"1"
    payload = struct.pack('B', len(table)) + table + struct.pack('B', len(key)) + key
    s.sendall(bpkt(MSG_CONFIG_QUERY, payload))

    mt, pl = trecv(s)
    assert mt == MSG_CONFIG_RESP
    assert pl[0] == 0, "should not find nonexistent table"
    s.close()


def test_config_json_query():
    """JSON 설정에서 키 조회"""
    s = connect()
    login_and_enter(s)

    table = b"server"
    key = b"tick_rate"
    payload = struct.pack('B', len(table)) + table + struct.pack('B', len(key)) + key
    s.sendall(bpkt(MSG_CONFIG_QUERY, payload))

    mt, pl = trecv(s)
    assert mt == MSG_CONFIG_RESP
    assert pl[0] == 1, "should find tick_rate"
    data_len = struct.unpack('<H', pl[1:3])[0]
    data = pl[3:3+data_len].decode()
    assert "tick_rate=30" in data, f"data={data}"
    s.close()


def test_config_json_string_value():
    """JSON 문자열 값 조회"""
    s = connect()
    login_and_enter(s)

    table = b"server"
    key = b"server_name"
    payload = struct.pack('B', len(table)) + table + struct.pack('B', len(key)) + key
    s.sendall(bpkt(MSG_CONFIG_QUERY, payload))

    mt, pl = trecv(s)
    assert pl[0] == 1
    data_len = struct.unpack('<H', pl[1:3])[0]
    data = pl[3:3+data_len].decode()
    assert "Field-1" in data, f"data={data}"
    s.close()


def test_config_csv_query_by_name():
    """CSV에서 name으로 검색"""
    s = connect()
    login_and_enter(s)

    table = b"monsters"
    key = b"Wolf"
    payload = struct.pack('B', len(table)) + table + struct.pack('B', len(key)) + key
    s.sendall(bpkt(MSG_CONFIG_QUERY, payload))

    mt, pl = trecv(s)
    assert mt == MSG_CONFIG_RESP
    assert pl[0] == 1
    data_len = struct.unpack('<H', pl[1:3])[0]
    data = pl[3:3+data_len].decode()
    pairs = dict(p.split('=', 1) for p in data.split('|'))
    assert pairs.get('hp') == '200', f"hp={pairs.get('hp')}"
    s.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_echo_still_works():
    """기존 기능이 깨지지 않았는지"""
    s = connect()
    s.sendall(bpkt(MSG_ECHO, b"hello_session11"))
    mt, pl = trecv(s)
    assert mt == MSG_ECHO
    assert pl == b"hello_session11"
    s.close()


def test_full_pipeline_with_timer():
    """전체 파이프라인: Login → Enter → Timer → Event"""
    s = connect()
    login_and_enter(s)

    # 타이머 추가
    s.sendall(bpkt(MSG_TIMER_ADD, struct.pack('<iii', 999, 400, 0)))
    time.sleep(0.7)

    # 타이머 만료 확인
    s.sendall(bpkt(MSG_TIMER_INFO))
    mt, pl = trecv(s)
    assert mt == MSG_TIMER_INFO

    # Config도 동시 확인
    table = b"monsters"
    key = b"2"
    payload = struct.pack('B', len(table)) + table + struct.pack('B', len(key)) + key
    s.sendall(bpkt(MSG_CONFIG_QUERY, payload))
    mt, pl = trecv(s)
    assert mt == MSG_CONFIG_RESP
    assert pl[0] == 1
    s.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("=" * 55)
    print("  Session 11: Infrastructure Tests")
    print("  EventBus + Timer + ConfigLoader")
    print("=" * 55)
    print()

    start_server()

    try:
        print("[EventBus]")
        test("eventbus_subscribers_exist", test_eventbus_subscribers_exist)
        test("eventbus_queue_empty_initially", test_eventbus_queue_empty_initially)
        test("eventbus_timer_event_fires", test_eventbus_timer_event_fires)

        print()
        print("[Timer]")
        test("timer_add", test_timer_add)
        test("timer_oneshot_expires", test_timer_oneshot_expires)
        test("timer_repeating", test_timer_repeating)
        test("timer_multiple", test_timer_multiple)

        print()
        print("[ConfigLoader]")
        test("config_csv_query_by_id", test_config_csv_query_by_id)
        test("config_csv_query_dragon", test_config_csv_query_dragon)
        test("config_csv_not_found", test_config_csv_not_found)
        test("config_json_query", test_config_json_query)
        test("config_json_string_value", test_config_json_string_value)
        test("config_csv_query_by_name", test_config_csv_query_by_name)

        print()
        print("[Integration]")
        test("echo_still_works", test_echo_still_works)
        test("full_pipeline_with_timer", test_full_pipeline_with_timer)

    finally:
        stop_server()

    print()
    print("=" * 55)
    total = passed + failed
    print(f"  Result: {passed}/{total} PASSED" + (f", {failed} FAILED" if failed else ""))
    print("=" * 55)

    sys.exit(0 if failed == 0 else 1)
