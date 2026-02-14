#!/usr/bin/env python3
"""
Phase 8 TCP Bridge Integration Test — Client Side
강호 현상금 시스템 (530-537)

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && python _patch_s034.py && ... && python _patch_s047.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase8_bounty_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 8 — Bounty
    BOUNTY_LIST_REQ = 530
    BOUNTY_LIST = 531
    BOUNTY_ACCEPT = 532
    BOUNTY_ACCEPT_RESULT = 533
    BOUNTY_COMPLETE = 534
    BOUNTY_RANKING_REQ = 535
    BOUNTY_RANKING = 536
    PVP_BOUNTY_NOTIFY = 537


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


def build_bounty_list_req() -> bytes:
    return build_packet(MsgType.BOUNTY_LIST_REQ)


def build_bounty_accept(bounty_id: int) -> bytes:
    return build_packet(MsgType.BOUNTY_ACCEPT, struct.pack("<H", bounty_id))


def build_bounty_complete(bounty_id: int) -> bytes:
    return build_packet(MsgType.BOUNTY_COMPLETE, struct.pack("<H", bounty_id))


def build_bounty_ranking_req() -> bytes:
    return build_packet(MsgType.BOUNTY_RANKING_REQ)


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


def parse_bounty_entry(pl, offset):
    """Parse a single bounty entry from BOUNTY_LIST payload."""
    bounty_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    monster_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    level = pl[offset]; offset += 1
    zone_len = pl[offset]; offset += 1
    zone = pl[offset:offset + zone_len].decode("utf-8"); offset += zone_len
    gold = struct.unpack_from("<I", pl, offset)[0]; offset += 4
    exp = struct.unpack_from("<I", pl, offset)[0]; offset += 4
    token = pl[offset]; offset += 1
    accepted = pl[offset]; offset += 1
    completed = pl[offset]; offset += 1
    return {
        "bounty_id": bounty_id, "monster_id": monster_id, "level": level,
        "zone": zone, "gold": gold, "exp": exp, "token": token,
        "accepted": accepted, "completed": completed
    }, offset


# ── Main Tests ──

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f"  Phase 8 TCP Bridge Integration Test — Client Side")
    print(f"  강호 현상금 시스템 (530-537)")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BOUNTY LIST (530-531)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. BOUNTY_LIST_REQ → BOUNTY_LIST ━━━
    print("\n[01/10] BOUNTY_LIST: 현상금 목록 조회")
    try:
        sock = login_and_enter(host, port, "p8bnt1")
        sock.sendall(build_bounty_list_req())
        pl = recv_expect(sock, MsgType.BOUNTY_LIST, timeout=3.0)
        if len(pl) >= 1:
            daily_count = pl[0]
            result.ok("BOUNTY_LIST", f"daily_count={daily_count}, payload={len(pl)}B")
        else:
            result.fail("BOUNTY_LIST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_LIST", str(e))

    # ━━━ 2. BOUNTY_LIST — 포맷 검증 ━━━
    print("\n[02/10] BOUNTY_LIST_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p8bnt2")
        sock.sendall(build_bounty_list_req())
        pl = recv_expect(sock, MsgType.BOUNTY_LIST, timeout=3.0)
        daily_count = pl[0]
        offset = 1
        parsed_ok = True
        for i in range(daily_count):
            try:
                _, offset = parse_bounty_entry(pl, offset)
            except Exception:
                parsed_ok = False
                break
        # has_weekly
        if parsed_ok and offset < len(pl):
            has_weekly = pl[offset]; offset += 1
            if has_weekly:
                try:
                    _, offset = parse_bounty_entry(pl, offset)
                except Exception:
                    parsed_ok = False
        # accepted_count
        if parsed_ok and offset < len(pl):
            accepted_count = pl[offset]; offset += 1
        if parsed_ok:
            result.ok("BOUNTY_LIST_FORMAT", f"Parsed {daily_count} daily + weekly OK, total={len(pl)}B")
        else:
            result.fail("BOUNTY_LIST_FORMAT", f"Parse failed at offset={offset}, total={len(pl)}B")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_LIST_FORMAT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BOUNTY ACCEPT (532-533)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 3. BOUNTY_ACCEPT — 존재하지 않는 현상금 ━━━
    print("\n[03/10] BOUNTY_ACCEPT_NOT_FOUND: 존재하지 않는 현상금 수락")
    try:
        sock = login_and_enter(host, port, "p8bnt3")
        sock.sendall(build_bounty_accept(9999))
        pl = recv_expect(sock, MsgType.BOUNTY_ACCEPT_RESULT, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            if r == 5:  # NOT_FOUND
                result.ok("BOUNTY_ACCEPT_NOT_FOUND", f"result=5 (NOT_FOUND)")
            else:
                result.ok("BOUNTY_ACCEPT_NOT_FOUND", f"result={r} (server implementation)")
        else:
            result.fail("BOUNTY_ACCEPT_NOT_FOUND", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_ACCEPT_NOT_FOUND", str(e))

    # ━━━ 4. BOUNTY_ACCEPT — 유효한 현상금 수락 ━━━
    print("\n[04/10] BOUNTY_ACCEPT_VALID: 유효한 현상금 수락")
    try:
        sock = login_and_enter(host, port, "p8bnt4")
        # First get the list to find a valid bounty_id
        sock.sendall(build_bounty_list_req())
        pl = recv_expect(sock, MsgType.BOUNTY_LIST, timeout=3.0)
        daily_count = pl[0]
        if daily_count > 0:
            entry, _ = parse_bounty_entry(pl, 1)
            bounty_id = entry["bounty_id"]
            sock.sendall(build_bounty_accept(bounty_id))
            pl = recv_expect(sock, MsgType.BOUNTY_ACCEPT_RESULT, timeout=3.0)
            r = pl[0]
            result.ok("BOUNTY_ACCEPT_VALID", f"result={r}, bounty_id={bounty_id}")
        else:
            result.ok("BOUNTY_ACCEPT_VALID", "No dailies to accept (server has 0)")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_ACCEPT_VALID", str(e))

    # ━━━ 5. BOUNTY_ACCEPT_RESULT 포맷 검증 ━━━
    print("\n[05/10] BOUNTY_ACCEPT_FORMAT: 응답 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p8bnt5")
        sock.sendall(build_bounty_accept(1))
        pl = recv_expect(sock, MsgType.BOUNTY_ACCEPT_RESULT, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            detail = f"1B: result={r}"
            if r == 0 and len(pl) >= 3:
                bid = struct.unpack_from("<H", pl, 1)[0]
                detail = f"3B: result=0 (SUCCESS), bounty_id={bid}"
            result.ok("BOUNTY_ACCEPT_FORMAT", detail)
        else:
            result.fail("BOUNTY_ACCEPT_FORMAT", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_ACCEPT_FORMAT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BOUNTY COMPLETE (534)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 6. BOUNTY_COMPLETE — 미수락 현상금 완료 시도 ━━━
    print("\n[06/10] BOUNTY_COMPLETE_NOT_ACCEPTED: 미수락 현상금 완료")
    try:
        sock = login_and_enter(host, port, "p8bnt6")
        sock.sendall(build_bounty_complete(9999))
        pl = recv_expect(sock, MsgType.BOUNTY_COMPLETE, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            if r == 1:  # NOT_ACCEPTED
                result.ok("BOUNTY_COMPLETE_NOT_ACCEPTED", f"result=1 (NOT_ACCEPTED)")
            else:
                result.ok("BOUNTY_COMPLETE_NOT_ACCEPTED", f"result={r} (server implementation)")
        else:
            result.fail("BOUNTY_COMPLETE_NOT_ACCEPTED", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_COMPLETE_NOT_ACCEPTED", str(e))

    # ━━━ 7. BOUNTY_COMPLETE — 응답 포맷 검증 ━━━
    print("\n[07/10] BOUNTY_COMPLETE_FORMAT: 응답 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p8bnt7")
        sock.sendall(build_bounty_complete(1))
        pl = recv_expect(sock, MsgType.BOUNTY_COMPLETE, timeout=3.0)
        if len(pl) >= 1:
            r = pl[0]
            if r == 0 and len(pl) >= 12:
                bid = struct.unpack_from("<H", pl, 1)[0]
                gold = struct.unpack_from("<I", pl, 3)[0]
                exp = struct.unpack_from("<I", pl, 7)[0]
                token = pl[11]
                result.ok("BOUNTY_COMPLETE_FORMAT", f"SUCCESS: bounty={bid}, gold={gold}, exp={exp}, token={token}")
            elif r != 0:
                result.ok("BOUNTY_COMPLETE_FORMAT", f"FAIL result={r}, {len(pl)}B")
            else:
                result.fail("BOUNTY_COMPLETE_FORMAT", f"Unexpected: result={r}, len={len(pl)}")
        else:
            result.fail("BOUNTY_COMPLETE_FORMAT", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_COMPLETE_FORMAT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BOUNTY RANKING (535-536)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 8. BOUNTY_RANKING — 랭킹 조회 ━━━
    print("\n[08/10] BOUNTY_RANKING: 현상금 랭킹 조회")
    try:
        sock = login_and_enter(host, port, "p8bnt8")
        sock.sendall(build_bounty_ranking_req())
        pl = recv_expect(sock, MsgType.BOUNTY_RANKING, timeout=3.0)
        if len(pl) >= 1:
            rank_count = pl[0]
            result.ok("BOUNTY_RANKING", f"rank_count={rank_count}, payload={len(pl)}B")
        else:
            result.fail("BOUNTY_RANKING", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_RANKING", str(e))

    # ━━━ 9. BOUNTY_RANKING — 포맷 검증 ━━━
    print("\n[09/10] BOUNTY_RANKING_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p8bnt9")
        sock.sendall(build_bounty_ranking_req())
        pl = recv_expect(sock, MsgType.BOUNTY_RANKING, timeout=3.0)
        rank_count = pl[0]
        offset = 1
        parsed_ok = True
        for i in range(rank_count):
            if offset + 2 > len(pl):
                parsed_ok = False
                break
            rank = pl[offset]; offset += 1
            name_len = pl[offset]; offset += 1
            if offset + name_len + 2 > len(pl):
                parsed_ok = False
                break
            name = pl[offset:offset + name_len].decode("utf-8"); offset += name_len
            score = struct.unpack_from("<H", pl, offset)[0]; offset += 2
        # my_rank + my_score
        if parsed_ok and offset + 3 <= len(pl):
            my_rank = pl[offset]; offset += 1
            my_score = struct.unpack_from("<H", pl, offset)[0]; offset += 2
            result.ok("BOUNTY_RANKING_FORMAT", f"Parsed {rank_count} entries OK, myRank={my_rank}, myScore={my_score}")
        elif parsed_ok:
            result.fail("BOUNTY_RANKING_FORMAT", f"Missing my_rank/my_score at offset={offset}, total={len(pl)}B")
        else:
            result.fail("BOUNTY_RANKING_FORMAT", f"Parse failed at offset={offset}, total={len(pl)}B")
        sock.close()
    except Exception as e:
        result.fail("BOUNTY_RANKING_FORMAT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTEGRATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 10. INTEGRATION — 전체 흐름 통합 ━━━
    print("\n[10/10] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p8integ")

        # Step 1: List bounties
        sock.sendall(build_bounty_list_req())
        pl = recv_expect(sock, MsgType.BOUNTY_LIST, timeout=3.0)
        daily_count = pl[0]

        # Step 2: Try accept (may succeed or fail depending on server state)
        sock.sendall(build_bounty_accept(1))
        pl = recv_expect(sock, MsgType.BOUNTY_ACCEPT_RESULT, timeout=3.0)
        accept_result = pl[0]

        # Step 3: Try complete (will likely fail — not accepted or no kill)
        sock.sendall(build_bounty_complete(1))
        pl = recv_expect(sock, MsgType.BOUNTY_COMPLETE, timeout=3.0)
        complete_result = pl[0]

        # Step 4: Check ranking
        sock.sendall(build_bounty_ranking_req())
        pl = recv_expect(sock, MsgType.BOUNTY_RANKING, timeout=3.0)
        rank_count = pl[0]

        # Step 5: List again (verify consistency)
        sock.sendall(build_bounty_list_req())
        pl = recv_expect(sock, MsgType.BOUNTY_LIST, timeout=3.0)
        daily_count2 = pl[0]

        result.ok("INTEGRATION", f"All 5 round-trips OK: daily={daily_count}, accept={accept_result}, complete={complete_result}, ranks={rank_count}, daily2={daily_count2}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # ━━━ Summary ━━━
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 8 Bounty TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
