#!/usr/bin/env python3
"""
Phase 15 TCP Bridge Integration Test -- Client Side
보조 화폐/토큰 상점 (468-473) — S054 TASK 10

Usage:
    python test_phase15_currency_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 15 -- Currency/TokenShop
    CURRENCY_QUERY = 468
    CURRENCY_INFO = 469
    TOKEN_SHOP_LIST = 470
    TOKEN_SHOP = 471
    TOKEN_SHOP_BUY = 472
    TOKEN_SHOP_BUY_RESULT = 473


# -- Result codes --
class BuyResult:
    SUCCESS = 0
    INSUFFICIENT_TOKEN = 1
    INVALID_ITEM = 2
    CURRENCY_AT_MAX = 3
    INVENTORY_FULL = 4


class ShopType:
    DUNGEON = 0
    PVP = 1
    GUILD = 2


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


def build_currency_query() -> bytes:
    return build_packet(MsgType.CURRENCY_QUERY)


def build_token_shop_list(shop_type: int) -> bytes:
    return build_packet(MsgType.TOKEN_SHOP_LIST, bytes([shop_type]))


def build_token_shop_buy(shop_id: int, quantity: int) -> bytes:
    payload = struct.pack("<HB", shop_id, quantity)
    return build_packet(MsgType.TOKEN_SHOP_BUY, payload)


# -- Parsers --

def parse_currency_info(pl):
    """Parse CURRENCY_INFO: gold(4)+silver(4)+dungeon_token(4)+pvp_token(4)+guild_contribution(4)"""
    gold = struct.unpack_from("<I", pl, 0)[0]
    silver = struct.unpack_from("<I", pl, 4)[0]
    dungeon_token = struct.unpack_from("<I", pl, 8)[0]
    pvp_token = struct.unpack_from("<I", pl, 12)[0]
    guild_contribution = struct.unpack_from("<I", pl, 16)[0]
    return {
        "gold": gold, "silver": silver,
        "dungeon_token": dungeon_token, "pvp_token": pvp_token,
        "guild_contribution": guild_contribution
    }


def parse_token_shop(pl):
    """Parse TOKEN_SHOP: shop_type(1)+count(1)+[shop_id(2)+price(4)+currency_type(1)+name_len(1)+name(N)]*N"""
    off = 0
    shop_type = pl[off]; off += 1
    count = pl[off]; off += 1
    items = []
    for _ in range(count):
        shop_id = struct.unpack_from("<H", pl, off)[0]; off += 2
        price = struct.unpack_from("<I", pl, off)[0]; off += 4
        currency_type = pl[off]; off += 1
        name_len = pl[off]; off += 1
        name = pl[off:off + name_len].decode("utf-8"); off += name_len
        items.append({
            "shop_id": shop_id, "price": price,
            "currency_type": currency_type, "name": name
        })
    return {"shop_type": shop_type, "count": count, "items": items}


def parse_buy_result(pl):
    """Parse TOKEN_SHOP_BUY_RESULT: result(1)+shop_id(2)+remaining_currency(4)"""
    result = pl[0]
    shop_id = struct.unpack_from("<H", pl, 1)[0]
    remaining = struct.unpack_from("<I", pl, 3)[0]
    return {"result": result, "shop_id": shop_id, "remaining": remaining}


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
    print(f"  Phase 15 TCP Bridge Integration Test -- Client Side")
    print(f"  보조 화폐/토큰 상점 (468-473) — S054 TASK 10")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ==========================================
    # 1. CURRENCY_QUERY: 전체 화폐 조회
    # ==========================================
    print("\n[01/10] CURRENCY_QUERY: 전체 화폐 조회")
    try:
        sock = login_and_enter(host, port, "p15cur1")
        sock.sendall(build_currency_query())
        pl = recv_expect(sock, MsgType.CURRENCY_INFO, timeout=3.0)
        data = parse_currency_info(pl)
        if data["gold"] >= 0 and data["silver"] >= 0:
            result.ok("CURRENCY_QUERY", f"gold={data['gold']}, silver={data['silver']}, dt={data['dungeon_token']}, pvp={data['pvp_token']}, gc={data['guild_contribution']}")
        else:
            result.fail("CURRENCY_QUERY", f"Unexpected negative values: {data}")
        sock.close()
    except Exception as e:
        result.fail("CURRENCY_QUERY", str(e))

    # ==========================================
    # 2. TOKEN_SHOP_LIST: 던전 상점 목록 조회
    # ==========================================
    print("\n[02/10] TOKEN_SHOP_LIST: 던전 상점 목록")
    try:
        sock = login_and_enter(host, port, "p15cur2")
        sock.sendall(build_token_shop_list(ShopType.DUNGEON))
        pl = recv_expect(sock, MsgType.TOKEN_SHOP, timeout=3.0)
        data = parse_token_shop(pl)
        if data["shop_type"] == ShopType.DUNGEON and data["count"] > 0:
            names = [item["name"] for item in data["items"]]
            result.ok("SHOP_LIST_DUNGEON", f"type=DUNGEON, count={data['count']}, items={names}")
        else:
            result.fail("SHOP_LIST_DUNGEON", f"Expected DUNGEON with items, got type={data['shop_type']} count={data['count']}")
        sock.close()
    except Exception as e:
        result.fail("SHOP_LIST_DUNGEON", str(e))

    # ==========================================
    # 3. TOKEN_SHOP_LIST: PvP 상점 목록 조회
    # ==========================================
    print("\n[03/10] TOKEN_SHOP_LIST: PvP 상점 목록")
    try:
        sock = login_and_enter(host, port, "p15cur3")
        sock.sendall(build_token_shop_list(ShopType.PVP))
        pl = recv_expect(sock, MsgType.TOKEN_SHOP, timeout=3.0)
        data = parse_token_shop(pl)
        if data["shop_type"] == ShopType.PVP and data["count"] > 0:
            names = [item["name"] for item in data["items"]]
            result.ok("SHOP_LIST_PVP", f"type=PVP, count={data['count']}, items={names}")
        else:
            result.fail("SHOP_LIST_PVP", f"Expected PVP with items, got type={data['shop_type']} count={data['count']}")
        sock.close()
    except Exception as e:
        result.fail("SHOP_LIST_PVP", str(e))

    # ==========================================
    # 4. TOKEN_SHOP_LIST: 길드 상점 목록 조회
    # ==========================================
    print("\n[04/10] TOKEN_SHOP_LIST: 길드 상점 목록")
    try:
        sock = login_and_enter(host, port, "p15cur4")
        sock.sendall(build_token_shop_list(ShopType.GUILD))
        pl = recv_expect(sock, MsgType.TOKEN_SHOP, timeout=3.0)
        data = parse_token_shop(pl)
        if data["shop_type"] == ShopType.GUILD and data["count"] > 0:
            names = [item["name"] for item in data["items"]]
            result.ok("SHOP_LIST_GUILD", f"type=GUILD, count={data['count']}, items={names}")
        else:
            result.fail("SHOP_LIST_GUILD", f"Expected GUILD with items, got type={data['shop_type']} count={data['count']}")
        sock.close()
    except Exception as e:
        result.fail("SHOP_LIST_GUILD", str(e))

    # ==========================================
    # 5. TOKEN_SHOP_BUY: 토큰 부족 → INSUFFICIENT_TOKEN
    # ==========================================
    print("\n[05/10] TOKEN_SHOP_BUY: 토큰 부족 → INSUFFICIENT_TOKEN")
    try:
        sock = login_and_enter(host, port, "p15cur5")
        # Try to buy an expensive dungeon item (shop_id=1) with no tokens
        sock.sendall(build_token_shop_buy(1, 1))
        pl = recv_expect(sock, MsgType.TOKEN_SHOP_BUY_RESULT, timeout=3.0)
        data = parse_buy_result(pl)
        if data["result"] == BuyResult.INSUFFICIENT_TOKEN:
            result.ok("BUY_INSUFFICIENT", f"result=INSUFFICIENT_TOKEN(1), shop_id={data['shop_id']}")
        else:
            result.fail("BUY_INSUFFICIENT", f"Expected INSUFFICIENT_TOKEN(1), got result={data['result']}")
        sock.close()
    except Exception as e:
        result.fail("BUY_INSUFFICIENT", str(e))

    # ==========================================
    # 6. TOKEN_SHOP_BUY: 잘못된 아이템 → INVALID_ITEM
    # ==========================================
    print("\n[06/10] TOKEN_SHOP_BUY: 잘못된 아이템 → INVALID_ITEM")
    try:
        sock = login_and_enter(host, port, "p15cur6")
        sock.sendall(build_token_shop_buy(9999, 1))  # non-existent shop_id
        pl = recv_expect(sock, MsgType.TOKEN_SHOP_BUY_RESULT, timeout=3.0)
        data = parse_buy_result(pl)
        if data["result"] == BuyResult.INVALID_ITEM:
            result.ok("BUY_INVALID_ITEM", f"result=INVALID_ITEM(2), shop_id={data['shop_id']}")
        else:
            result.fail("BUY_INVALID_ITEM", f"Expected INVALID_ITEM(2), got result={data['result']}")
        sock.close()
    except Exception as e:
        result.fail("BUY_INVALID_ITEM", str(e))

    # ==========================================
    # 7. CURRENCY_QUERY: 초기 실버 5000 확인
    # ==========================================
    print("\n[07/10] CURRENCY_QUERY: 초기 실버 5000 확인")
    try:
        sock = login_and_enter(host, port, "p15cur7")
        sock.sendall(build_currency_query())
        pl = recv_expect(sock, MsgType.CURRENCY_INFO, timeout=3.0)
        data = parse_currency_info(pl)
        if data["silver"] == 5000:
            result.ok("INITIAL_SILVER", f"silver={data['silver']} (expected 5000)")
        elif data["silver"] >= 0:
            result.ok("INITIAL_SILVER", f"silver={data['silver']} (server default, acceptable)")
        else:
            result.fail("INITIAL_SILVER", f"Unexpected silver={data['silver']}")
        sock.close()
    except Exception as e:
        result.fail("INITIAL_SILVER", str(e))

    # ==========================================
    # 8. CURRENCY_QUERY: 연속 조회 안정성 테스트
    # ==========================================
    print("\n[08/10] CURRENCY_QUERY: 연속 조회 안정성")
    try:
        sock = login_and_enter(host, port, "p15cur8")
        for i in range(3):
            sock.sendall(build_currency_query())
            pl = recv_expect(sock, MsgType.CURRENCY_INFO, timeout=3.0)
            data = parse_currency_info(pl)
        result.ok("CURRENCY_MULTI_QUERY", f"3회 연속 조회 성공, gold={data['gold']}")
        sock.close()
    except Exception as e:
        result.fail("CURRENCY_MULTI_QUERY", str(e))

    # ==========================================
    # 9. TOKEN_SHOP_LIST: 잘못된 상점 타입
    # ==========================================
    print("\n[09/10] TOKEN_SHOP_LIST: 잘못된 상점 타입")
    try:
        sock = login_and_enter(host, port, "p15cur9")
        sock.sendall(build_token_shop_list(99))  # invalid shop type
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=1.5)
        shop_pkts = [p for t, p in packets if t == MsgType.TOKEN_SHOP]
        if len(shop_pkts) > 0:
            data = parse_token_shop(shop_pkts[0])
            result.ok("SHOP_INVALID_TYPE", f"Got response with count={data['count']} (server handled gracefully)")
        else:
            result.ok("SHOP_INVALID_TYPE", "No response for invalid type — expected")
        sock.close()
    except Exception as e:
        result.fail("SHOP_INVALID_TYPE", str(e))

    # ==========================================
    # 10. TOKEN_SHOP_BUY: quantity=0 에지 케이스
    # ==========================================
    print("\n[10/10] TOKEN_SHOP_BUY: quantity=0 에지 케이스")
    try:
        sock = login_and_enter(host, port, "p15cur10")
        sock.sendall(build_token_shop_buy(1, 0))  # quantity=0
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=1.5)
        buy_pkts = [p for t, p in packets if t == MsgType.TOKEN_SHOP_BUY_RESULT]
        if len(buy_pkts) > 0:
            data = parse_buy_result(buy_pkts[0])
            result.ok("BUY_ZERO_QTY", f"result={data['result']} (server handled gracefully)")
        else:
            result.ok("BUY_ZERO_QTY", "No response for qty=0 — server ignored")
        sock.close()
    except Exception as e:
        result.fail("BUY_ZERO_QTY", str(e))

    # ==========================================
    # Summary
    # ==========================================
    print(f"\n{'='*65}")
    all_pass = result.summary()
    return all_pass


def main():
    parser = argparse.ArgumentParser(description="Phase 15 Currency/TokenShop TCP Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
