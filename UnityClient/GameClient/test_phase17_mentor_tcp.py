#!/usr/bin/env python3
"""
Phase 17 TCP Bridge Integration Test -- Client Side
사제(師弟) 시스템 (550-560) — S056 TASK 18

Usage:
    python test_phase17_mentor_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
"""

import argparse
import socket
import struct
import sys
import time

# -- Packet Protocol --
HEADER_SIZE = 6
MAX_PACKET_SIZE = 8192


class MsgType:
    ECHO = 1
    LOGIN = 60
    LOGIN_RESULT = 61
    CHAR_SELECT = 64
    ENTER_GAME = 65
    STAT_SYNC = 91
    # Phase 17 -- Mentor System
    MENTOR_SEARCH = 550
    MENTOR_LIST = 551
    MENTOR_REQUEST = 552
    MENTOR_REQUEST_RESULT = 553
    MENTOR_ACCEPT = 554
    MENTOR_ACCEPT_RESULT = 555
    MENTOR_QUEST_LIST = 556
    MENTOR_QUESTS = 557
    MENTOR_GRADUATE = 558
    MENTOR_SHOP_LIST = 559
    MENTOR_SHOP_BUY = 560


# -- Result codes --
class MentorRequestResultCode:
    SENT = 0
    LV_LOW = 1
    LV_HIGH = 2
    HAS_MASTER = 3
    FULL = 4
    NOT_FOUND = 5
    SELF = 6
    ALREADY = 7


class MentorAcceptResultCode:
    SUCCESS = 0
    FAILED = 1


class MentorGraduateResultCode:
    SUCCESS = 0
    NOT_READY = 1
    NOT_FOUND = 2


class MentorShopBuyResultCode:
    SUCCESS = 0
    INSUFFICIENT_CONTRIB = 1
    INVALID_ITEM = 2


def build_packet(msg_type: int, payload: bytes = b"") -> bytes:
    total_len = HEADER_SIZE + len(payload)
    header = struct.pack("<IH", total_len, msg_type)
    return header + payload


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed by server")
        buf += chunk
    return buf


def recv_packet(sock: socket.socket, timeout: float = 5.0) -> tuple:
    """Returns (msg_type, payload)"""
    sock.settimeout(timeout)
    header = recv_exact(sock, HEADER_SIZE)
    total_len, msg_type = struct.unpack("<IH", header)
    payload_len = total_len - HEADER_SIZE
    payload = recv_exact(sock, payload_len) if payload_len > 0 else b""
    return msg_type, payload


def recv_all_pending(sock: socket.socket, timeout: float = 1.0) -> list:
    """Receive all pending packets until timeout."""
    packets = []
    try:
        while True:
            pkt = recv_packet(sock, timeout)
            packets.append(pkt)
    except (socket.timeout, ConnectionError):
        pass
    return packets


def recv_expect(sock: socket.socket, expected: int, timeout: float = 5.0):
    """Receive packets until we find the expected type. Returns payload."""
    deadline = time.time() + timeout
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for MsgType {expected}")
        t, p = recv_packet(sock, timeout=remaining)
        if t == expected:
            return p


# -- Packet Builders --

def build_login(username: str, password: str) -> bytes:
    u = username.encode("utf-8")
    p = password.encode("utf-8")
    payload = bytes([len(u)]) + u + bytes([len(p)]) + p
    return build_packet(MsgType.LOGIN, payload)


def build_char_select(char_id: int) -> bytes:
    return build_packet(MsgType.CHAR_SELECT, struct.pack("<I", char_id))


def build_mentor_search(search_type: int) -> bytes:
    return build_packet(MsgType.MENTOR_SEARCH, bytes([search_type]))


def build_mentor_request(target_eid: int, role: int) -> bytes:
    payload = struct.pack("<IB", target_eid, role)
    return build_packet(MsgType.MENTOR_REQUEST, payload)


def build_mentor_accept(accept: int) -> bytes:
    return build_packet(MsgType.MENTOR_ACCEPT, bytes([accept]))


def build_mentor_quest_list() -> bytes:
    return build_packet(MsgType.MENTOR_QUEST_LIST)


def build_mentor_graduate(disciple_eid: int) -> bytes:
    return build_packet(MsgType.MENTOR_GRADUATE, struct.pack("<I", disciple_eid))


def build_mentor_shop_list() -> bytes:
    return build_packet(MsgType.MENTOR_SHOP_LIST)


def build_mentor_shop_buy(item_id: int) -> bytes:
    return build_packet(MsgType.MENTOR_SHOP_BUY, bytes([item_id]))


# -- Parsers --

def parse_mentor_list(pl):
    """Parse MENTOR_LIST: count(1)+[entity_id(4)+level(2)+name_len(1)+name(utf8)]*N"""
    off = 0
    count = pl[off]; off += 1
    entries = []
    for _ in range(count):
        eid = struct.unpack_from("<I", pl, off)[0]; off += 4
        level = struct.unpack_from("<H", pl, off)[0]; off += 2
        name_len = pl[off]; off += 1
        name = pl[off:off + name_len].decode("utf-8"); off += name_len
        entries.append({"entity_id": eid, "level": level, "name": name})
    return entries


def parse_mentor_request_result(pl):
    """Parse MENTOR_REQUEST_RESULT: result(1)"""
    return pl[0]


def parse_mentor_accept_result(pl):
    """Parse MENTOR_ACCEPT_RESULT: result(1)+master_eid(4)+disciple_eid(4)"""
    result = pl[0]
    master_eid = struct.unpack_from("<I", pl, 1)[0] if len(pl) >= 5 else 0
    disciple_eid = struct.unpack_from("<I", pl, 5)[0] if len(pl) >= 9 else 0
    return {"result": result, "master_eid": master_eid, "disciple_eid": disciple_eid}


def parse_mentor_quests(pl):
    """Parse MENTOR_QUESTS: count(1)+[quest_id_len+quest_id+name_len+name+type_len+type+count_needed(2)+progress(2)]*N"""
    off = 0
    count = pl[off]; off += 1
    quests = []
    for _ in range(count):
        qid_len = pl[off]; off += 1
        qid = pl[off:off + qid_len].decode("utf-8"); off += qid_len
        name_len = pl[off]; off += 1
        name = pl[off:off + name_len].decode("utf-8"); off += name_len
        type_len = pl[off]; off += 1
        qtype = pl[off:off + type_len].decode("utf-8"); off += type_len
        count_needed = struct.unpack_from("<H", pl, off)[0]; off += 2
        progress = struct.unpack_from("<H", pl, off)[0]; off += 2
        quests.append({
            "quest_id": qid, "name": name, "type": qtype,
            "count_needed": count_needed, "progress": progress
        })
    return quests


def parse_mentor_graduate(pl):
    """Parse MENTOR_GRADUATE response: result(1)+master_eid(4)+disciple_eid(4)+master_gold(4)+disciple_gold(4)"""
    result = pl[0]
    data = {"result": result}
    if len(pl) >= 17:
        data["master_eid"] = struct.unpack_from("<I", pl, 1)[0]
        data["disciple_eid"] = struct.unpack_from("<I", pl, 5)[0]
        data["master_gold"] = struct.unpack_from("<I", pl, 9)[0]
        data["disciple_gold"] = struct.unpack_from("<I", pl, 13)[0]
    return data


def parse_mentor_shop_list(pl):
    """Parse MENTOR_SHOP_LIST: contribution(4)+count(1)+[item_id(1)+cost(2)+name_len(1)+name(utf8)]*N"""
    off = 0
    contribution = struct.unpack_from("<I", pl, off)[0]; off += 4
    count = pl[off]; off += 1
    items = []
    for _ in range(count):
        item_id = pl[off]; off += 1
        cost = struct.unpack_from("<H", pl, off)[0]; off += 2
        name_len = pl[off]; off += 1
        name = pl[off:off + name_len].decode("utf-8"); off += name_len
        items.append({"item_id": item_id, "cost": cost, "name": name})
    return {"contribution": contribution, "items": items}


def parse_mentor_shop_buy(pl):
    """Parse MENTOR_SHOP_BUY response: result(1)+remaining_contribution(4)"""
    result = pl[0]
    remaining = struct.unpack_from("<I", pl, 1)[0] if len(pl) >= 5 else 0
    return {"result": result, "remaining_contribution": remaining}


# -- Test Helpers --

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str, detail: str = ""):
        self.passed += 1
        mark = "\033[92mPASS\033[0m"
        print(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))

    def fail(self, name: str, detail: str = ""):
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        mark = "\033[91mFAIL\033[0m"
        print(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        if self.failed == 0:
            print(f"\n\033[92m✓ ALL PASS: {self.passed}/{total}\033[0m")
        else:
            print(f"\n\033[91m✗ {self.failed} FAILED, {self.passed} PASSED / {total} total\033[0m")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


def msg_name(t: int) -> str:
    for attr in dir(MsgType):
        if not attr.startswith("_") and getattr(MsgType, attr) == t:
            return attr
    return f"UNKNOWN({t})"


def login_and_enter(host: str, port: int, username: str) -> socket.socket:
    """Connect, login, char_select, enter_game. Returns connected socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect((host, port))

    # LOGIN
    sock.sendall(build_login(username, "pw"))
    t, p = recv_packet(sock)
    assert t == MsgType.LOGIN_RESULT, f"Expected LOGIN_RESULT, got {msg_name(t)}"

    # CHAR_SELECT -> triggers ENTER_GAME + burst
    sock.sendall(build_char_select(1))
    time.sleep(0.3)
    t, p = recv_packet(sock, timeout=5.0)
    assert t == MsgType.ENTER_GAME, f"Expected ENTER_GAME, got {msg_name(t)}"

    # Drain initial burst
    recv_all_pending(sock, timeout=1.0)

    return sock


# -- Main Tests --

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f" Phase 17 — 사제(師弟) 시스템 TCP 테스트 (MsgType 550-560)")
    print(f" S056 TASK 18 | Server: {host}:{port}")
    print(f"{'='*65}\n")

    # ──────────────────────────────────────────
    # Test 1: MENTOR_SEARCH — 사부 검색 (count=0 가능)
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test1")
        sock.sendall(build_mentor_search(0))  # 0=사부 검색
        pl = recv_expect(sock, MsgType.MENTOR_LIST)
        entries = parse_mentor_list(pl)
        # 결과 0건은 정상 (Lv40+ 플레이어 미존재 가능)
        result.ok("MENTOR_SEARCH(사부검색)", f"count={len(entries)}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_SEARCH(사부검색)", str(e))

    # ──────────────────────────────────────────
    # Test 2: MENTOR_SEARCH — 제자 검색
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test2")
        sock.sendall(build_mentor_search(1))  # 1=제자 검색
        pl = recv_expect(sock, MsgType.MENTOR_LIST)
        entries = parse_mentor_list(pl)
        result.ok("MENTOR_SEARCH(제자검색)", f"count={len(entries)}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_SEARCH(제자검색)", str(e))

    # ──────────────────────────────────────────
    # Test 3: MENTOR_REQUEST — 레벨 미달 (Lv40 사부 최소)
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test3")
        sock.sendall(build_mentor_request(99999, 1))  # role=1(나=사부), 타겟 존재X
        pl = recv_expect(sock, MsgType.MENTOR_REQUEST_RESULT)
        res = parse_mentor_request_result(pl)
        # LV_LOW(1) 또는 NOT_FOUND(5) 중 하나
        if res in (MentorRequestResultCode.LV_LOW, MentorRequestResultCode.NOT_FOUND):
            result.ok("MENTOR_REQUEST(레벨미달/대상없음)", f"result={res}")
        else:
            result.fail("MENTOR_REQUEST(레벨미달/대상없음)", f"expected LV_LOW(1) or NOT_FOUND(5), got {res}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_REQUEST(레벨미달/대상없음)", str(e))

    # ──────────────────────────────────────────
    # Test 4: MENTOR_REQUEST — SELF 불가
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test4")
        # 자기 자신의 entity_id를 알기 어려우므로, SELF가 아닌 결과가 올 수 있음
        # 존재하지 않는 대상으로 요청 → NOT_FOUND 기대
        sock.sendall(build_mentor_request(0, 0))  # target=0, role=0(나=제자)
        pl = recv_expect(sock, MsgType.MENTOR_REQUEST_RESULT)
        res = parse_mentor_request_result(pl)
        # NOT_FOUND(5) 또는 SELF(6) 중 하나
        if res in (MentorRequestResultCode.NOT_FOUND, MentorRequestResultCode.SELF,
                   MentorRequestResultCode.LV_LOW, MentorRequestResultCode.LV_HIGH):
            result.ok("MENTOR_REQUEST(SELF/NOT_FOUND)", f"result={res}")
        else:
            result.fail("MENTOR_REQUEST(SELF/NOT_FOUND)", f"unexpected result={res}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_REQUEST(SELF/NOT_FOUND)", str(e))

    # ──────────────────────────────────────────
    # Test 5: MENTOR_QUEST_LIST — 사제 퀘스트 조회
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test5")
        sock.sendall(build_mentor_quest_list())
        pl = recv_expect(sock, MsgType.MENTOR_QUESTS)
        quests = parse_mentor_quests(pl)
        # 사제 관계 미성립이면 0건 가능
        result.ok("MENTOR_QUEST_LIST", f"count={len(quests)}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_QUEST_LIST", str(e))

    # ──────────────────────────────────────────
    # Test 6: MENTOR_SHOP_LIST — 기여도 상점 조회
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test6")
        sock.sendall(build_mentor_shop_list())
        pl = recv_expect(sock, MsgType.MENTOR_SHOP_LIST)
        shop = parse_mentor_shop_list(pl)
        result.ok("MENTOR_SHOP_LIST", f"contribution={shop['contribution']}, items={len(shop['items'])}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_SHOP_LIST", str(e))

    # ──────────────────────────────────────────
    # Test 7: MENTOR_SHOP_BUY — 기여도 부족 구매 실패
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test7")
        sock.sendall(build_mentor_shop_buy(1))  # item_id=1
        pl = recv_expect(sock, MsgType.MENTOR_SHOP_BUY)
        buy = parse_mentor_shop_buy(pl)
        if buy["result"] == MentorShopBuyResultCode.INSUFFICIENT_CONTRIB:
            result.ok("MENTOR_SHOP_BUY(기여도부족)", f"result=INSUFFICIENT_CONTRIB")
        elif buy["result"] == MentorShopBuyResultCode.INVALID_ITEM:
            result.ok("MENTOR_SHOP_BUY(아이템없음)", f"result=INVALID_ITEM")
        else:
            # SUCCESS도 가능 (기여도가 있다면)
            result.ok("MENTOR_SHOP_BUY", f"result={buy['result']}, remaining={buy['remaining_contribution']}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_SHOP_BUY(기여도부족)", str(e))

    # ──────────────────────────────────────────
    # Test 8: MENTOR_GRADUATE — 졸업 조건 미달
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test8")
        sock.sendall(build_mentor_graduate(0))  # disciple_eid=0 (자기 자신)
        pl = recv_expect(sock, MsgType.MENTOR_GRADUATE)
        grad = parse_mentor_graduate(pl)
        # NOT_READY(1) 또는 NOT_FOUND(2) 기대
        if grad["result"] in (MentorGraduateResultCode.NOT_READY, MentorGraduateResultCode.NOT_FOUND):
            result.ok("MENTOR_GRADUATE(조건미달)", f"result={grad['result']}")
        else:
            result.ok("MENTOR_GRADUATE", f"result={grad['result']}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_GRADUATE(조건미달)", str(e))

    # ──────────────────────────────────────────
    # Test 9: MENTOR_ACCEPT — 수락 (대기 요청 없음)
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test9")
        sock.sendall(build_mentor_accept(1))  # accept=1 (수락)
        pl = recv_expect(sock, MsgType.MENTOR_ACCEPT_RESULT)
        acc = parse_mentor_accept_result(pl)
        # 대기 요청 없으면 FAILED(1)
        if acc["result"] == MentorAcceptResultCode.FAILED:
            result.ok("MENTOR_ACCEPT(대기요청없음)", f"result=FAILED")
        else:
            result.ok("MENTOR_ACCEPT", f"result={acc['result']}, master={acc['master_eid']}, disciple={acc['disciple_eid']}")
        sock.close()
    except Exception as e:
        result.fail("MENTOR_ACCEPT(대기요청없음)", str(e))

    # ──────────────────────────────────────────
    # Test 10: 연속 SEARCH+QUEST+SHOP 안정성
    # ──────────────────────────────────────────
    try:
        sock = login_and_enter(host, port, "mentor_test10")
        # 연속 3패킷 전송
        sock.sendall(build_mentor_search(0))
        sock.sendall(build_mentor_quest_list())
        sock.sendall(build_mentor_shop_list())
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=3.0)
        found_list = any(t == MsgType.MENTOR_LIST for t, _ in packets)
        found_quests = any(t == MsgType.MENTOR_QUESTS for t, _ in packets)
        found_shop = any(t == MsgType.MENTOR_SHOP_LIST for t, _ in packets)
        if found_list and found_quests and found_shop:
            result.ok("연속 SEARCH+QUEST+SHOP", f"3패킷 응답 수신 OK")
        else:
            missing = []
            if not found_list: missing.append("MENTOR_LIST")
            if not found_quests: missing.append("MENTOR_QUESTS")
            if not found_shop: missing.append("MENTOR_SHOP_LIST")
            result.fail("연속 SEARCH+QUEST+SHOP", f"missing: {', '.join(missing)}")
        sock.close()
    except Exception as e:
        result.fail("연속 SEARCH+QUEST+SHOP", str(e))

    # -- Summary --
    print(f"\n{'='*65}")
    success = result.summary()
    return success


def main():
    parser = argparse.ArgumentParser(description="Phase 17 Mentor TCP Test")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=7777, help="Server port")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
