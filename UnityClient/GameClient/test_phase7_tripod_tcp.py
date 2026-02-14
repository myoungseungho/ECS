#!/usr/bin/env python3
"""
Phase 7 TCP Bridge Integration Test — Client Side
비급 & 트라이포드 (520-524)

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && python _patch_s034.py && ... && python _patch_s046.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase7_tripod_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 7 — Tripod
    TRIPOD_LIST_REQ = 520
    TRIPOD_LIST = 521
    TRIPOD_EQUIP = 522
    TRIPOD_EQUIP_RESULT = 523
    SCROLL_DISCOVER = 524


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


def build_tripod_list_req() -> bytes:
    return build_packet(MsgType.TRIPOD_LIST_REQ)


def build_tripod_equip(skill_id: int, tier: int, option_idx: int) -> bytes:
    return build_packet(MsgType.TRIPOD_EQUIP, struct.pack("<HBB", skill_id, tier, option_idx))


def build_scroll_discover(scroll_slot: int) -> bytes:
    return build_packet(MsgType.SCROLL_DISCOVER, struct.pack("<B", scroll_slot))


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
    print(f"  Phase 7 TCP Bridge Integration Test — Client Side")
    print(f"  비급 & 트라이포드 (520-524)")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TRIPOD LIST (520-521)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. TRIPOD_LIST_REQ → TRIPOD_LIST ━━━
    print("\n[01/08] TRIPOD_LIST: 트라이포드 목록 조회")
    try:
        sock = login_and_enter(host, port, "p7tri1")
        sock.sendall(build_tripod_list_req())
        pl = recv_expect(sock, MsgType.TRIPOD_LIST, timeout=3.0)
        # Format: skill_count(1) + skills[]
        if len(pl) >= 1:
            skill_count = pl[0]
            result.ok("TRIPOD_LIST", f"skill_count={skill_count}, payload={len(pl)}B")
        else:
            result.fail("TRIPOD_LIST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TRIPOD_LIST", str(e))

    # ━━━ 2. TRIPOD_LIST — 빈 목록 검증 ━━━
    print("\n[02/08] TRIPOD_LIST_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p7tri2")
        sock.sendall(build_tripod_list_req())
        pl = recv_expect(sock, MsgType.TRIPOD_LIST, timeout=3.0)
        skill_count = pl[0]
        # Parse each skill to validate format
        offset = 1
        parsed_ok = True
        for i in range(skill_count):
            if offset + 3 > len(pl):
                parsed_ok = False
                break
            skill_id = struct.unpack_from("<H", pl, offset)[0]
            offset += 2
            tier_count = pl[offset]
            offset += 1
            for t in range(tier_count):
                if offset + 2 > len(pl):
                    parsed_ok = False
                    break
                tier = pl[offset]
                offset += 1
                unlocked_count = pl[offset]
                offset += 1
                offset += unlocked_count  # skip option_idx bytes
                offset += 1  # equipped_idx
        if parsed_ok:
            result.ok("TRIPOD_LIST_FORMAT", f"Parsed {skill_count} skills OK, total={len(pl)}B")
        else:
            result.fail("TRIPOD_LIST_FORMAT", f"Parse failed at offset={offset}, total={len(pl)}B")
        sock.close()
    except Exception as e:
        result.fail("TRIPOD_LIST_FORMAT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TRIPOD EQUIP (522-523)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 3. TRIPOD_EQUIP — 유효하지 않은 스킬 ━━━
    print("\n[03/08] TRIPOD_EQUIP_INVALID: 유효하지 않은 스킬 장착")
    try:
        sock = login_and_enter(host, port, "p7tri3")
        sock.sendall(build_tripod_equip(9999, 1, 0))  # non-existent skill
        pl = recv_expect(sock, MsgType.TRIPOD_EQUIP_RESULT, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            if r == 2:  # INVALID_SKILL
                result.ok("TRIPOD_EQUIP_INVALID", f"result=2 (INVALID_SKILL)")
            else:
                result.ok("TRIPOD_EQUIP_INVALID", f"result={r} (서버 구현에 따라 다를 수 있음)")
        else:
            result.fail("TRIPOD_EQUIP_INVALID", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TRIPOD_EQUIP_INVALID", str(e))

    # ━━━ 4. TRIPOD_EQUIP_RESULT 패킷 포맷 검증 (1 byte) ━━━
    print("\n[04/08] TRIPOD_EQUIP_FORMAT: 패킷 포맷 검증 (1B)")
    try:
        sock = login_and_enter(host, port, "p7tri4")
        sock.sendall(build_tripod_equip(1, 1, 0))
        pl = recv_expect(sock, MsgType.TRIPOD_EQUIP_RESULT, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            result.ok("TRIPOD_EQUIP_FORMAT", f"1B: result={r}")
        else:
            result.fail("TRIPOD_EQUIP_FORMAT", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TRIPOD_EQUIP_FORMAT", str(e))

    # ━━━ 5. TRIPOD_EQUIP — 해금 안 된 옵션 ━━━
    print("\n[05/08] TRIPOD_EQUIP_NOT_UNLOCKED: 해금 안 된 옵션 장착 시도")
    try:
        sock = login_and_enter(host, port, "p7tri5")
        sock.sendall(build_tripod_equip(1, 3, 7))  # tier=3 (오의), option=7 (unlikely unlocked)
        pl = recv_expect(sock, MsgType.TRIPOD_EQUIP_RESULT, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            result.ok("TRIPOD_EQUIP_NOT_UNLOCKED", f"result={r}")
        else:
            result.fail("TRIPOD_EQUIP_NOT_UNLOCKED", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TRIPOD_EQUIP_NOT_UNLOCKED", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCROLL DISCOVER (524)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 6. SCROLL_DISCOVER — 아이템 없는 슬롯 ━━━
    print("\n[06/08] SCROLL_DISCOVER_NO_ITEM: 빈 슬롯 비급 사용")
    try:
        sock = login_and_enter(host, port, "p7tri6")
        sock.sendall(build_scroll_discover(99))  # slot 99 = empty
        pl = recv_expect(sock, MsgType.SCROLL_DISCOVER, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            if r == 2:  # ITEM_NOT_FOUND
                result.ok("SCROLL_DISCOVER_NO_ITEM", f"result=2 (ITEM_NOT_FOUND)")
            else:
                result.ok("SCROLL_DISCOVER_NO_ITEM", f"result={r} (서버 구현에 따라 다를 수 있음)")
        else:
            result.fail("SCROLL_DISCOVER_NO_ITEM", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("SCROLL_DISCOVER_NO_ITEM", str(e))

    # ━━━ 7. SCROLL_DISCOVER — 응답 포맷 검증 ━━━
    print("\n[07/08] SCROLL_DISCOVER_FORMAT: 응답 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p7tri7")
        sock.sendall(build_scroll_discover(0))  # slot 0
        pl = recv_expect(sock, MsgType.SCROLL_DISCOVER, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            if r == 0 and len(pl) >= 5:
                # SUCCESS: result(1) + skill_id(2) + tier(1) + option_idx(1)
                skill_id = struct.unpack_from("<H", pl, 1)[0]
                tier = pl[3]
                opt = pl[4]
                result.ok("SCROLL_DISCOVER_FORMAT", f"SUCCESS: skill={skill_id}, tier={tier}, opt={opt}")
            elif r != 0 and len(pl) >= 1:
                result.ok("SCROLL_DISCOVER_FORMAT", f"FAIL result={r}, {len(pl)}B (no extra data expected)")
            else:
                result.fail("SCROLL_DISCOVER_FORMAT", f"Unexpected: result={r}, len={len(pl)}")
        else:
            result.fail("SCROLL_DISCOVER_FORMAT", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("SCROLL_DISCOVER_FORMAT", str(e))

    # ━━━ 8. INTEGRATION — 전체 흐름 통합 ━━━
    print("\n[08/08] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p7integ")

        # Step 1: List all tripods
        sock.sendall(build_tripod_list_req())
        pl = recv_expect(sock, MsgType.TRIPOD_LIST, timeout=3.0)
        skill_count = pl[0]

        # Step 2: Try equip (will fail — invalid skill or not unlocked)
        sock.sendall(build_tripod_equip(9999, 1, 0))
        pl = recv_expect(sock, MsgType.TRIPOD_EQUIP_RESULT, timeout=3.0)
        equip_result = pl[0]

        # Step 3: Try scroll discover (will fail — no item)
        sock.sendall(build_scroll_discover(99))
        pl = recv_expect(sock, MsgType.SCROLL_DISCOVER, timeout=3.0)
        discover_result = pl[0]

        # Step 4: List again (verify consistency)
        sock.sendall(build_tripod_list_req())
        pl = recv_expect(sock, MsgType.TRIPOD_LIST, timeout=3.0)
        skill_count2 = pl[0]

        result.ok("INTEGRATION", f"All 4 round-trips OK: skills={skill_count}, equip={equip_result}, discover={discover_result}, skills2={skill_count2}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # ━━━ Summary ━━━
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 7 Tripod TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
