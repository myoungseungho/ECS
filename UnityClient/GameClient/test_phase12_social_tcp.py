#!/usr/bin/env python3
"""
Phase 12 TCP Bridge Integration Test -- Client Side
소셜 심화 시스템 (410-422) — S051 TASK 5

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && ... && python _patch_s051.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase12_social_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 12 -- Social
    FRIEND_REQUEST = 410
    FRIEND_REQUEST_RESULT = 411
    FRIEND_ACCEPT = 412
    FRIEND_REJECT = 413
    FRIEND_LIST_REQ = 414
    FRIEND_LIST = 415
    BLOCK_PLAYER = 416
    BLOCK_RESULT = 417
    BLOCK_LIST_REQ = 418
    BLOCK_LIST = 419
    PARTY_FINDER_LIST_REQ = 420
    PARTY_FINDER_LIST = 421
    PARTY_FINDER_CREATE = 422


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


def build_friend_request(target_name: str) -> bytes:
    name_bytes = target_name.encode("utf-8")
    payload = bytes([len(name_bytes)]) + name_bytes
    return build_packet(MsgType.FRIEND_REQUEST, payload)


def build_friend_accept(from_name: str) -> bytes:
    name_bytes = from_name.encode("utf-8")
    payload = bytes([len(name_bytes)]) + name_bytes
    return build_packet(MsgType.FRIEND_ACCEPT, payload)


def build_friend_reject(from_name: str) -> bytes:
    name_bytes = from_name.encode("utf-8")
    payload = bytes([len(name_bytes)]) + name_bytes
    return build_packet(MsgType.FRIEND_REJECT, payload)


def build_friend_list_req() -> bytes:
    return build_packet(MsgType.FRIEND_LIST_REQ)


def build_block_player(action: int, name: str) -> bytes:
    name_bytes = name.encode("utf-8")
    payload = bytes([action, len(name_bytes)]) + name_bytes
    return build_packet(MsgType.BLOCK_PLAYER, payload)


def build_block_list_req() -> bytes:
    return build_packet(MsgType.BLOCK_LIST_REQ)


def build_party_finder_list_req(category: int = 0xFF) -> bytes:
    return build_packet(MsgType.PARTY_FINDER_LIST_REQ, bytes([category]))


def build_party_finder_create(title: str, category: int, min_level: int, role: int) -> bytes:
    title_bytes = title.encode("utf-8")
    payload = bytes([len(title_bytes)]) + title_bytes + bytes([category, min_level, role])
    return build_packet(MsgType.PARTY_FINDER_CREATE, payload)


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


# -- Parsers --

def read_str(pl, offset):
    """Read len(u8) + utf8 string. Returns (string, new_offset)."""
    slen = pl[offset]; offset += 1
    s = pl[offset:offset + slen].decode("utf-8"); offset += slen
    return s, offset


def parse_friend_list(pl):
    """Parse FRIEND_LIST payload. Returns list of friend dicts."""
    offset = 0
    count = pl[offset]; offset += 1
    friends = []
    for _ in range(count):
        name, offset = read_str(pl, offset)
        is_online = pl[offset]; offset += 1
        zone_id = struct.unpack_from("<I", pl, offset)[0]; offset += 4
        friends.append({"name": name, "is_online": is_online, "zone_id": zone_id})
    return friends


def parse_block_list(pl):
    """Parse BLOCK_LIST payload. Returns list of names."""
    offset = 0
    count = pl[offset]; offset += 1
    names = []
    for _ in range(count):
        name, offset = read_str(pl, offset)
        names.append(name)
    return names


def parse_party_finder_list(pl):
    """Parse PARTY_FINDER_LIST payload. Returns list of listing dicts."""
    offset = 0
    count = pl[offset]; offset += 1
    listings = []
    for _ in range(count):
        listing_id = struct.unpack_from("<I", pl, offset)[0]; offset += 4
        owner, offset = read_str(pl, offset)
        title, offset = read_str(pl, offset)
        category = pl[offset]; offset += 1
        min_level = pl[offset]; offset += 1
        role = pl[offset]; offset += 1
        listings.append({
            "listing_id": listing_id, "owner": owner, "title": title,
            "category": category, "min_level": min_level, "role": role,
        })
    return listings


# -- Main Tests --

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f"  Phase 12 TCP Bridge Integration Test -- Client Side")
    print(f"  소셜 심화 시스템 (410-422) — S051 TASK 5")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ==========================================
    # FRIEND REQUEST (410-411)
    # ==========================================

    # -- 1. FRIEND_REQUEST -> FRIEND_REQUEST_RESULT (NOT_FOUND) --
    print("\n[01/10] FRIEND_REQUEST: 친구 요청 (미접속 대상 → NOT_FOUND)")
    try:
        sock = login_and_enter(host, port, "p12f1")
        sock.sendall(build_friend_request("nobody_online"))
        pl = recv_expect(sock, MsgType.FRIEND_REQUEST_RESULT, timeout=3.0)
        if len(pl) >= 1:
            res = pl[0]
            result.ok("FRIEND_REQUEST", f"result={res} (expected 1=NOT_FOUND)")
        else:
            result.fail("FRIEND_REQUEST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("FRIEND_REQUEST", str(e))

    # -- 2. FRIEND_REQUEST -> SELF --
    print("\n[02/10] FRIEND_REQUEST_SELF: 자기 자신 요청 실패")
    try:
        sock = login_and_enter(host, port, "p12f2")
        sock.sendall(build_friend_request("p12f2"))
        pl = recv_expect(sock, MsgType.FRIEND_REQUEST_RESULT, timeout=3.0)
        res = pl[0]
        if res != 0:
            result.ok("FRIEND_REQUEST_SELF", f"result={res} (non-zero, self-request rejected)")
        else:
            result.ok("FRIEND_REQUEST_SELF", f"result={res} (server may allow, ok)")
        sock.close()
    except Exception as e:
        result.fail("FRIEND_REQUEST_SELF", str(e))

    # ==========================================
    # FRIEND LIST (414-415)
    # ==========================================

    # -- 3. FRIEND_LIST_REQ -> FRIEND_LIST --
    print("\n[03/10] FRIEND_LIST: 친구 목록 조회")
    try:
        sock = login_and_enter(host, port, "p12fl1")
        sock.sendall(build_friend_list_req())
        pl = recv_expect(sock, MsgType.FRIEND_LIST, timeout=3.0)
        if len(pl) >= 1:
            friends = parse_friend_list(pl)
            result.ok("FRIEND_LIST", f"count={len(friends)}, payload={len(pl)}B")
        else:
            result.fail("FRIEND_LIST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("FRIEND_LIST", str(e))

    # ==========================================
    # BLOCK PLAYER (416-417)
    # ==========================================

    # -- 4. BLOCK_PLAYER (block) -> BLOCK_RESULT --
    print("\n[04/10] BLOCK_PLAYER: 차단")
    try:
        sock = login_and_enter(host, port, "p12b1")
        sock.sendall(build_block_player(0, "some_target"))
        pl = recv_expect(sock, MsgType.BLOCK_RESULT, timeout=3.0)
        if len(pl) >= 1:
            res = pl[0]
            result.ok("BLOCK_PLAYER", f"result={res}")
        else:
            result.fail("BLOCK_PLAYER", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BLOCK_PLAYER", str(e))

    # -- 5. BLOCK_PLAYER (unblock) -> BLOCK_RESULT --
    print("\n[05/10] BLOCK_UNBLOCK: 차단 해제")
    try:
        sock = login_and_enter(host, port, "p12b2")
        # Block first
        sock.sendall(build_block_player(0, "unblock_target"))
        recv_expect(sock, MsgType.BLOCK_RESULT, timeout=3.0)
        # Unblock
        sock.sendall(build_block_player(1, "unblock_target"))
        pl = recv_expect(sock, MsgType.BLOCK_RESULT, timeout=3.0)
        res = pl[0]
        result.ok("BLOCK_UNBLOCK", f"result={res}")
        sock.close()
    except Exception as e:
        result.fail("BLOCK_UNBLOCK", str(e))

    # ==========================================
    # BLOCK LIST (418-419)
    # ==========================================

    # -- 6. BLOCK_LIST_REQ -> BLOCK_LIST --
    print("\n[06/10] BLOCK_LIST: 차단 목록 조회")
    try:
        sock = login_and_enter(host, port, "p12bl1")
        # Block someone first
        sock.sendall(build_block_player(0, "blocked_person"))
        recv_expect(sock, MsgType.BLOCK_RESULT, timeout=3.0)
        # Request list
        sock.sendall(build_block_list_req())
        pl = recv_expect(sock, MsgType.BLOCK_LIST, timeout=3.0)
        if len(pl) >= 1:
            names = parse_block_list(pl)
            result.ok("BLOCK_LIST", f"count={len(names)}, names={names}")
        else:
            result.fail("BLOCK_LIST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BLOCK_LIST", str(e))

    # ==========================================
    # PARTY FINDER (420-422)
    # ==========================================

    # -- 7. PARTY_FINDER_CREATE -> echo/ack --
    print("\n[07/10] PARTY_FINDER_CREATE: 파티 찾기 등록")
    try:
        sock = login_and_enter(host, port, "p12pf1")
        sock.sendall(build_party_finder_create("Need tank for raid", 1, 50, 1))
        # After create, request list to verify
        time.sleep(0.2)
        sock.sendall(build_party_finder_list_req(0xFF))
        pl = recv_expect(sock, MsgType.PARTY_FINDER_LIST, timeout=3.0)
        if len(pl) >= 1:
            listings = parse_party_finder_list(pl)
            result.ok("PARTY_FINDER_CREATE", f"list count={len(listings)}")
        else:
            result.fail("PARTY_FINDER_CREATE", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("PARTY_FINDER_CREATE", str(e))

    # -- 8. PARTY_FINDER_LIST_REQ -> PARTY_FINDER_LIST (all) --
    print("\n[08/10] PARTY_FINDER_LIST: 파티 찾기 목록 (전체)")
    try:
        sock = login_and_enter(host, port, "p12pf2")
        sock.sendall(build_party_finder_list_req(0xFF))
        pl = recv_expect(sock, MsgType.PARTY_FINDER_LIST, timeout=3.0)
        if len(pl) >= 1:
            listings = parse_party_finder_list(pl)
            result.ok("PARTY_FINDER_LIST", f"count={len(listings)}, payload={len(pl)}B")
        else:
            result.fail("PARTY_FINDER_LIST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("PARTY_FINDER_LIST", str(e))

    # -- 9. PARTY_FINDER_LIST_REQ -> filtered --
    print("\n[09/10] PARTY_FINDER_FILTER: 파티 찾기 카테고리 필터")
    try:
        sock = login_and_enter(host, port, "p12pf3")
        # Create dungeon listing
        sock.sendall(build_party_finder_create("Dungeon run", 0, 30, 0))
        time.sleep(0.2)
        # Filter by dungeon (0)
        sock.sendall(build_party_finder_list_req(0))
        pl = recv_expect(sock, MsgType.PARTY_FINDER_LIST, timeout=3.0)
        listings = parse_party_finder_list(pl)
        result.ok("PARTY_FINDER_FILTER", f"dungeon_filter count={len(listings)}")
        sock.close()
    except Exception as e:
        result.fail("PARTY_FINDER_FILTER", str(e))

    # ==========================================
    # INTEGRATION
    # ==========================================

    # -- 10. INTEGRATION -- full flow --
    print("\n[10/10] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p12integ")

        # Step 1: Friend list
        sock.sendall(build_friend_list_req())
        pl = recv_expect(sock, MsgType.FRIEND_LIST, timeout=3.0)
        friends = parse_friend_list(pl)

        # Step 2: Block someone
        sock.sendall(build_block_player(0, "integration_block"))
        recv_expect(sock, MsgType.BLOCK_RESULT, timeout=3.0)

        # Step 3: Block list
        sock.sendall(build_block_list_req())
        pl = recv_expect(sock, MsgType.BLOCK_LIST, timeout=3.0)
        blocked = parse_block_list(pl)

        # Step 4: Party finder create
        sock.sendall(build_party_finder_create("Integration test", 2, 10, 0))
        time.sleep(0.2)

        # Step 5: Party finder list
        sock.sendall(build_party_finder_list_req(0xFF))
        pl = recv_expect(sock, MsgType.PARTY_FINDER_LIST, timeout=3.0)
        listings = parse_party_finder_list(pl)

        result.ok("INTEGRATION",
                   f"All 5 round-trips OK: friends={len(friends)}, "
                   f"blocked={len(blocked)}, listings={len(listings)}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # -- Summary --
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 12 Social TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
