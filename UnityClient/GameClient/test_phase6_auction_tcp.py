#!/usr/bin/env python3
"""
Phase 6 TCP Bridge Integration Test — Client Side
Auction / Exchange (390-397)

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && python _patch_s034.py && ... && python _patch_s044.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase6_auction_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
"""

import argparse
import socket
import struct
import sys
import time

# ── Packet Protocol ──
HEADER_SIZE = 6
MAX_PACKET_SIZE = 8192


class MsgType:
    ECHO = 1
    LOGIN = 60
    LOGIN_RESULT = 61
    CHAR_SELECT = 64
    ENTER_GAME = 65
    STAT_SYNC = 91
    INVENTORY_RESP = 191
    # Phase 6 — Auction
    AUCTION_LIST_REQ = 390
    AUCTION_LIST = 391
    AUCTION_REGISTER = 392
    AUCTION_REGISTER_RESULT = 393
    AUCTION_BUY = 394
    AUCTION_BUY_RESULT = 395
    AUCTION_BID = 396
    AUCTION_BID_RESULT = 397


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


# ── Packet Builders ──

def build_login(username: str, password: str) -> bytes:
    u = username.encode("utf-8")
    p = password.encode("utf-8")
    payload = bytes([len(u)]) + u + bytes([len(p)]) + p
    return build_packet(MsgType.LOGIN, payload)


def build_char_select(char_id: int) -> bytes:
    return build_packet(MsgType.CHAR_SELECT, struct.pack("<I", char_id))


def build_auction_list_req(category: int = 0xFF, page: int = 0, sort_by: int = 0) -> bytes:
    return build_packet(MsgType.AUCTION_LIST_REQ, struct.pack("<BBB", category, page, sort_by))


def build_auction_register(slot_idx: int, count: int, buyout_price: int, category: int) -> bytes:
    return build_packet(MsgType.AUCTION_REGISTER, struct.pack("<BBIB", slot_idx, count, buyout_price, category))


def build_auction_buy(auction_id: int) -> bytes:
    return build_packet(MsgType.AUCTION_BUY, struct.pack("<I", auction_id))


def build_auction_bid(auction_id: int, bid_amount: int) -> bytes:
    return build_packet(MsgType.AUCTION_BID, struct.pack("<II", auction_id, bid_amount))


# ── Test Helpers ──

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str, detail: str = ""):
        self.passed += 1
        mark = "\033[92mPASS\033[0m"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name: str, detail: str = ""):
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        mark = "\033[91mFAIL\033[0m"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

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

    # CHAR_SELECT → triggers ENTER_GAME + burst
    sock.sendall(build_char_select(1))
    time.sleep(0.3)
    t, p = recv_packet(sock, timeout=5.0)
    assert t == MsgType.ENTER_GAME, f"Expected ENTER_GAME, got {msg_name(t)}"

    # Drain initial burst
    recv_all_pending(sock, timeout=1.0)

    return sock


# ── Main Tests ──

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f"  Phase 6 TCP Bridge Integration Test — Client Side")
    print(f"  Auction / Exchange (390-397)")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AUCTION LIST (390-391)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. AUCTION_LIST_REQ → AUCTION_LIST (전체 카테고리) ━━━
    print("\n[01/08] AUCTION_LIST: 전체 카테고리 목록 조회")
    try:
        sock = login_and_enter(host, port, "p6auc1")
        sock.sendall(build_auction_list_req(0xFF, 0, 0))
        pl = recv_expect(sock, MsgType.AUCTION_LIST, timeout=3.0)
        # Format: H:total_count + B:total_pages + B:page + B:item_count + items[]
        if len(pl) >= 5:
            total_count = struct.unpack_from("<H", pl, 0)[0]
            total_pages = pl[2]
            page = pl[3]
            item_count = pl[4]
            result.ok("AUCTION_LIST", f"total={total_count}, pages={total_pages}, page={page}, items={item_count}")
        else:
            result.fail("AUCTION_LIST", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("AUCTION_LIST", str(e))

    # ━━━ 2. AUCTION_LIST — 카테고리 필터 ━━━
    print("\n[02/08] AUCTION_LIST_FILTER: 카테고리 필터링 (무기)")
    try:
        sock = login_and_enter(host, port, "p6auc2")
        sock.sendall(build_auction_list_req(0, 0, 0))  # category=0 (무기)
        pl = recv_expect(sock, MsgType.AUCTION_LIST, timeout=3.0)
        if len(pl) >= 5:
            total_count = struct.unpack_from("<H", pl, 0)[0]
            item_count = pl[4]
            result.ok("AUCTION_LIST_FILTER", f"weapon_count={total_count}, page_items={item_count}")
        else:
            result.fail("AUCTION_LIST_FILTER", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("AUCTION_LIST_FILTER", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AUCTION REGISTER (392-393)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 3. AUCTION_REGISTER — 등록 시도 (아이템 없음) ━━━
    print("\n[03/08] AUCTION_REGISTER_NO_ITEM: 빈 슬롯 등록 실패")
    try:
        sock = login_and_enter(host, port, "p6auc3")
        sock.sendall(build_auction_register(99, 1, 1000, 0))  # slot 99 = empty
        pl = recv_expect(sock, MsgType.AUCTION_REGISTER_RESULT, timeout=3.0)
        # Format: B:result + I:auction_id
        if len(pl) >= 5:
            r = pl[0]
            auction_id = struct.unpack_from("<I", pl, 1)[0]
            if r == 2:  # no_item
                result.ok("AUCTION_REGISTER_NO_ITEM", f"result=2 (NO_ITEM), auction_id={auction_id}")
            else:
                result.fail("AUCTION_REGISTER_NO_ITEM", f"Expected result=2 (NO_ITEM), got {r}")
        else:
            result.fail("AUCTION_REGISTER_NO_ITEM", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("AUCTION_REGISTER_NO_ITEM", str(e))

    # ━━━ 4. AUCTION_REGISTER_RESULT 패킷 포맷 검증 ━━━
    print("\n[04/08] AUCTION_REGISTER_FORMAT: 패킷 포맷 검증 (5 bytes)")
    try:
        sock = login_and_enter(host, port, "p6auc4")
        sock.sendall(build_auction_register(0, 1, 500, 0))
        pl = recv_expect(sock, MsgType.AUCTION_REGISTER_RESULT, timeout=3.0)
        if len(pl) >= 5:
            r = pl[0]
            aid = struct.unpack_from("<I", pl, 1)[0]
            result.ok("AUCTION_REGISTER_FORMAT", f"5B: result={r}, auction_id={aid}")
        else:
            result.fail("AUCTION_REGISTER_FORMAT", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("AUCTION_REGISTER_FORMAT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AUCTION BUY (394-395)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 5. AUCTION_BUY — 존재하지 않는 경매 ━━━
    print("\n[05/08] AUCTION_BUY_NOT_FOUND: 존재하지 않는 경매 구매")
    try:
        sock = login_and_enter(host, port, "p6auc5")
        sock.sendall(build_auction_buy(99999))  # non-existent auction
        pl = recv_expect(sock, MsgType.AUCTION_BUY_RESULT, timeout=3.0)
        if len(pl) >= 5:
            r = pl[0]
            aid = struct.unpack_from("<I", pl, 1)[0]
            if r == 1:  # not_found
                result.ok("AUCTION_BUY_NOT_FOUND", f"result=1 (NOT_FOUND), auction_id={aid}")
            else:
                result.fail("AUCTION_BUY_NOT_FOUND", f"Expected result=1 (NOT_FOUND), got {r}")
        else:
            result.fail("AUCTION_BUY_NOT_FOUND", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("AUCTION_BUY_NOT_FOUND", str(e))

    # ━━━ 6. AUCTION_BUY_RESULT 패킷 포맷 검증 ━━━
    print("\n[06/08] AUCTION_BUY_FORMAT: 패킷 포맷 검증 (5 bytes)")
    try:
        sock = login_and_enter(host, port, "p6auc6")
        sock.sendall(build_auction_buy(1))
        pl = recv_expect(sock, MsgType.AUCTION_BUY_RESULT, timeout=3.0)
        if len(pl) >= 5:
            r = pl[0]
            aid = struct.unpack_from("<I", pl, 1)[0]
            result.ok("AUCTION_BUY_FORMAT", f"5B: result={r}, auction_id={aid}")
        else:
            result.fail("AUCTION_BUY_FORMAT", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("AUCTION_BUY_FORMAT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AUCTION BID (396-397)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 7. AUCTION_BID — 존재하지 않는 경매 ━━━
    print("\n[07/08] AUCTION_BID_NOT_FOUND: 존재하지 않는 경매 입찰")
    try:
        sock = login_and_enter(host, port, "p6auc7")
        sock.sendall(build_auction_bid(99999, 500))
        pl = recv_expect(sock, MsgType.AUCTION_BID_RESULT, timeout=3.0)
        if len(pl) >= 5:
            r = pl[0]
            aid = struct.unpack_from("<I", pl, 1)[0]
            if r == 1:  # not_found
                result.ok("AUCTION_BID_NOT_FOUND", f"result=1 (NOT_FOUND), auction_id={aid}")
            else:
                result.fail("AUCTION_BID_NOT_FOUND", f"Expected result=1 (NOT_FOUND), got {r}")
        else:
            result.fail("AUCTION_BID_NOT_FOUND", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("AUCTION_BID_NOT_FOUND", str(e))

    # ━━━ 8. INTEGRATION — 전체 흐름 통합 ━━━
    print("\n[08/08] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p6integ")

        # Step 1: List all auctions
        sock.sendall(build_auction_list_req(0xFF, 0, 0))
        pl = recv_expect(sock, MsgType.AUCTION_LIST, timeout=3.0)
        total = struct.unpack_from("<H", pl, 0)[0]

        # Step 2: Try register (will fail — no item)
        sock.sendall(build_auction_register(0, 1, 1000, 0))
        pl = recv_expect(sock, MsgType.AUCTION_REGISTER_RESULT, timeout=3.0)
        reg_result = pl[0]

        # Step 3: Try buy non-existent
        sock.sendall(build_auction_buy(99999))
        pl = recv_expect(sock, MsgType.AUCTION_BUY_RESULT, timeout=3.0)
        buy_result = pl[0]

        # Step 4: Try bid on non-existent
        sock.sendall(build_auction_bid(99999, 100))
        pl = recv_expect(sock, MsgType.AUCTION_BID_RESULT, timeout=3.0)
        bid_result = pl[0]

        result.ok("INTEGRATION", f"All 4 round-trips OK: list_total={total}, reg={reg_result}, buy={buy_result}, bid={bid_result}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # ━━━ Summary ━━━
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 6 Auction TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
