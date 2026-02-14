#!/usr/bin/env python3
"""
Phase 14 TCP Bridge Integration Test -- Client Side
전장/길드전/PvP시즌 (430-435) — S053 TASK 6

Usage:
    python test_phase14_battleground_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 14 -- Battleground/GuildWar
    BATTLEGROUND_QUEUE = 430
    BATTLEGROUND_STATUS = 431
    BATTLEGROUND_SCORE = 432
    BATTLEGROUND_SCORE_UPDATE = 433
    GUILD_WAR_DECLARE = 434
    GUILD_WAR_STATUS = 435


# -- Status enums --
class BGStatus:
    QUEUED = 0
    MATCH_FOUND = 1
    CANCELLED = 2
    ALREADY_IN_MATCH = 3
    INVALID_MODE = 4


class GWStatus:
    WAR_DECLARED = 0
    WAR_STARTED = 1
    WAR_REJECTED = 2
    NO_GUILD = 3
    TOO_FEW_MEMBERS = 4
    ALREADY_AT_WAR = 5
    PENDING_INFO = 6
    NO_WAR = 7


class GWAction:
    DECLARE = 0
    ACCEPT = 1
    REJECT = 2
    QUERY = 3


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


def build_bg_queue(action: int, mode: int) -> bytes:
    """action: 0=enqueue, 1=cancel; mode: 0=capture_point, 1=payload"""
    return build_packet(MsgType.BATTLEGROUND_QUEUE, bytes([action, mode]))


def build_bg_score(action: int, point_index: int) -> bytes:
    return build_packet(MsgType.BATTLEGROUND_SCORE, bytes([action, point_index]))


def build_gw_declare(action: int, target_guild_id: int) -> bytes:
    payload = bytes([action]) + struct.pack("<I", target_guild_id)
    return build_packet(MsgType.GUILD_WAR_DECLARE, payload)


# -- Parsers --

def parse_bg_status(pl):
    """Parse BATTLEGROUND_STATUS: status(1)+match_id(4)+mode(1)+team(1)+queue_count(1)"""
    status = pl[0]
    match_id = struct.unpack_from("<I", pl, 1)[0]
    mode = pl[5]
    team = pl[6]
    queue_count = pl[7]
    return {
        "status": status, "match_id": match_id,
        "mode": mode, "team": team, "queue_count": queue_count
    }


def parse_bg_score_update(pl):
    """Parse BATTLEGROUND_SCORE_UPDATE: mode(1)+red_score(4)+blue_score(4)+time(4)"""
    mode = pl[0]
    red_score = struct.unpack_from("<I", pl, 1)[0]
    blue_score = struct.unpack_from("<I", pl, 5)[0]
    time_remaining = struct.unpack_from("<I", pl, 9)[0]
    return {
        "mode": mode, "red_score": red_score,
        "blue_score": blue_score, "time": time_remaining
    }


def parse_gw_status(pl):
    """Parse GUILD_WAR_STATUS: status(1)+war_id(4)+guild_a(4)+guild_b(4)+crystal_hp_a(4)+crystal_hp_b(4)+time(4)"""
    status = pl[0]
    war_id = struct.unpack_from("<I", pl, 1)[0]
    guild_a = struct.unpack_from("<I", pl, 5)[0]
    guild_b = struct.unpack_from("<I", pl, 9)[0]
    crystal_hp_a = struct.unpack_from("<I", pl, 13)[0]
    crystal_hp_b = struct.unpack_from("<I", pl, 17)[0]
    time_remaining = struct.unpack_from("<I", pl, 21)[0]
    return {
        "status": status, "war_id": war_id,
        "guild_a": guild_a, "guild_b": guild_b,
        "crystal_hp_a": crystal_hp_a, "crystal_hp_b": crystal_hp_b,
        "time": time_remaining
    }


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
    print(f"  Phase 14 TCP Bridge Integration Test -- Client Side")
    print(f"  전장/길드전/PvP시즌 (430-435) — S053 TASK 6")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ==========================================
    # 1. BG_QUEUE: 거점 점령 큐 등록 → QUEUED
    # ==========================================
    print("\n[01/10] BG_QUEUE: 거점 점령 큐 등록 → QUEUED")
    try:
        sock = login_and_enter(host, port, "p14bg1")
        sock.sendall(build_bg_queue(0, 0))  # action=0(enqueue), mode=0(capture_point)
        pl = recv_expect(sock, MsgType.BATTLEGROUND_STATUS, timeout=3.0)
        data = parse_bg_status(pl)
        if data["status"] == BGStatus.QUEUED:
            result.ok("BG_QUEUE_CAPTURE", f"status=QUEUED, mode={data['mode']}, count={data['queue_count']}")
        else:
            result.fail("BG_QUEUE_CAPTURE", f"Expected QUEUED(0), got status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("BG_QUEUE_CAPTURE", str(e))

    # ==========================================
    # 2. BG_QUEUE: 큐 취소 → CANCELLED
    # ==========================================
    print("\n[02/10] BG_QUEUE: 큐 취소 → CANCELLED")
    try:
        sock = login_and_enter(host, port, "p14bg2")
        # First enqueue
        sock.sendall(build_bg_queue(0, 0))
        pl = recv_expect(sock, MsgType.BATTLEGROUND_STATUS, timeout=3.0)
        data = parse_bg_status(pl)
        assert data["status"] == BGStatus.QUEUED, f"Pre-condition: expected QUEUED, got {data['status']}"

        # Then cancel
        sock.sendall(build_bg_queue(1, 0))
        pl = recv_expect(sock, MsgType.BATTLEGROUND_STATUS, timeout=3.0)
        data = parse_bg_status(pl)
        if data["status"] == BGStatus.CANCELLED:
            result.ok("BG_QUEUE_CANCEL", f"status=CANCELLED")
        else:
            result.fail("BG_QUEUE_CANCEL", f"Expected CANCELLED(2), got status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("BG_QUEUE_CANCEL", str(e))

    # ==========================================
    # 3. BG_QUEUE: 잘못된 모드 → INVALID_MODE
    # ==========================================
    print("\n[03/10] BG_QUEUE: 잘못된 모드 → INVALID_MODE")
    try:
        sock = login_and_enter(host, port, "p14bg3")
        sock.sendall(build_bg_queue(0, 99))  # invalid mode
        pl = recv_expect(sock, MsgType.BATTLEGROUND_STATUS, timeout=3.0)
        data = parse_bg_status(pl)
        if data["status"] == BGStatus.INVALID_MODE:
            result.ok("BG_INVALID_MODE", f"status=INVALID_MODE(4)")
        else:
            result.fail("BG_INVALID_MODE", f"Expected INVALID_MODE(4), got status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("BG_INVALID_MODE", str(e))

    # ==========================================
    # 4. BG_QUEUE: 수레 호위 모드 큐 → QUEUED
    # ==========================================
    print("\n[04/10] BG_QUEUE: 수레 호위 큐 → QUEUED")
    try:
        sock = login_and_enter(host, port, "p14bg4")
        sock.sendall(build_bg_queue(0, 1))  # mode=1(payload)
        pl = recv_expect(sock, MsgType.BATTLEGROUND_STATUS, timeout=3.0)
        data = parse_bg_status(pl)
        if data["status"] == BGStatus.QUEUED and data["mode"] == 1:
            result.ok("BG_QUEUE_PAYLOAD", f"status=QUEUED, mode=payload(1)")
        else:
            result.fail("BG_QUEUE_PAYLOAD", f"Expected QUEUED+mode=1, got status={data['status']} mode={data['mode']}")
        sock.close()
    except Exception as e:
        result.fail("BG_QUEUE_PAYLOAD", str(e))

    # ==========================================
    # 5. BG_SCORE: 매치 없이 점수 조회 → 빈/기본 응답
    # ==========================================
    print("\n[05/10] BG_SCORE: 매치 없이 점수 조회")
    try:
        sock = login_and_enter(host, port, "p14bg5")
        sock.sendall(build_bg_score(0, 0))
        # Might get a score update with zeros or no response
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=1.5)
        score_pkts = [p for t, p in packets if t == MsgType.BATTLEGROUND_SCORE_UPDATE]
        if len(score_pkts) > 0:
            data = parse_bg_score_update(score_pkts[0])
            result.ok("BG_SCORE_NO_MATCH", f"red={data['red_score']}, blue={data['blue_score']}, time={data['time']}")
        else:
            result.ok("BG_SCORE_NO_MATCH", "No score response (not in match) — expected")
        sock.close()
    except Exception as e:
        result.fail("BG_SCORE_NO_MATCH", str(e))

    # ==========================================
    # 6. GW_DECLARE: 길드 없이 선언 → NO_GUILD
    # ==========================================
    print("\n[06/10] GW_DECLARE: 길드 없이 선언 → NO_GUILD")
    try:
        sock = login_and_enter(host, port, "p14gw1")
        sock.sendall(build_gw_declare(GWAction.DECLARE, 999))
        pl = recv_expect(sock, MsgType.GUILD_WAR_STATUS, timeout=3.0)
        data = parse_gw_status(pl)
        if data["status"] == GWStatus.NO_GUILD:
            result.ok("GW_DECLARE_NO_GUILD", f"status=NO_GUILD(3)")
        else:
            result.fail("GW_DECLARE_NO_GUILD", f"Expected NO_GUILD(3), got status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("GW_DECLARE_NO_GUILD", str(e))

    # ==========================================
    # 7. GW_QUERY: 전쟁 없이 상태 조회 → NO_WAR
    # ==========================================
    print("\n[07/10] GW_QUERY: 전쟁 없이 상태 조회 → NO_WAR")
    try:
        sock = login_and_enter(host, port, "p14gw2")
        sock.sendall(build_gw_declare(GWAction.QUERY, 0))
        pl = recv_expect(sock, MsgType.GUILD_WAR_STATUS, timeout=3.0)
        data = parse_gw_status(pl)
        if data["status"] == GWStatus.NO_WAR:
            result.ok("GW_QUERY_NO_WAR", f"status=NO_WAR(7)")
        else:
            result.fail("GW_QUERY_NO_WAR", f"Expected NO_WAR(7), got status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("GW_QUERY_NO_WAR", str(e))

    # ==========================================
    # 8. GW_ACCEPT: 전쟁 없이 수락 → NO_WAR
    # ==========================================
    print("\n[08/10] GW_ACCEPT: 전쟁 없이 수락 → NO_WAR")
    try:
        sock = login_and_enter(host, port, "p14gw3")
        sock.sendall(build_gw_declare(GWAction.ACCEPT, 0))
        pl = recv_expect(sock, MsgType.GUILD_WAR_STATUS, timeout=3.0)
        data = parse_gw_status(pl)
        if data["status"] in (GWStatus.NO_WAR, GWStatus.NO_GUILD):
            result.ok("GW_ACCEPT_NO_WAR", f"status={data['status']} (NO_WAR or NO_GUILD)")
        else:
            result.fail("GW_ACCEPT_NO_WAR", f"Expected NO_WAR(7) or NO_GUILD(3), got status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("GW_ACCEPT_NO_WAR", str(e))

    # ==========================================
    # 9. GW_REJECT: 전쟁 없이 거절 → NO_WAR
    # ==========================================
    print("\n[09/10] GW_REJECT: 전쟁 없이 거절 → NO_WAR")
    try:
        sock = login_and_enter(host, port, "p14gw4")
        sock.sendall(build_gw_declare(GWAction.REJECT, 0))
        pl = recv_expect(sock, MsgType.GUILD_WAR_STATUS, timeout=3.0)
        data = parse_gw_status(pl)
        if data["status"] in (GWStatus.NO_WAR, GWStatus.NO_GUILD):
            result.ok("GW_REJECT_NO_WAR", f"status={data['status']} (NO_WAR or NO_GUILD)")
        else:
            result.fail("GW_REJECT_NO_WAR", f"Expected NO_WAR(7) or NO_GUILD(3), got status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("GW_REJECT_NO_WAR", str(e))

    # ==========================================
    # 10. BG_QUEUE: 이중 큐 등록 → ALREADY_IN_MATCH or QUEUED
    # ==========================================
    print("\n[10/10] BG_QUEUE: 이중 큐 등록 체크")
    try:
        sock = login_and_enter(host, port, "p14bg6")
        # First enqueue
        sock.sendall(build_bg_queue(0, 0))
        pl = recv_expect(sock, MsgType.BATTLEGROUND_STATUS, timeout=3.0)
        data = parse_bg_status(pl)
        assert data["status"] == BGStatus.QUEUED, f"Pre-condition failed: {data['status']}"

        # Second enqueue (same mode)
        sock.sendall(build_bg_queue(0, 0))
        pl = recv_expect(sock, MsgType.BATTLEGROUND_STATUS, timeout=3.0)
        data = parse_bg_status(pl)
        if data["status"] in (BGStatus.ALREADY_IN_MATCH, BGStatus.QUEUED):
            result.ok("BG_DOUBLE_QUEUE", f"status={data['status']} (ALREADY or re-QUEUED)")
        else:
            result.fail("BG_DOUBLE_QUEUE", f"Unexpected status={data['status']}")
        sock.close()
    except Exception as e:
        result.fail("BG_DOUBLE_QUEUE", str(e))

    # ==========================================
    # Summary
    # ==========================================
    print(f"\n{'='*65}")
    all_pass = result.summary()
    return all_pass


def main():
    parser = argparse.ArgumentParser(description="Phase 14 Battleground/GuildWar TCP Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
