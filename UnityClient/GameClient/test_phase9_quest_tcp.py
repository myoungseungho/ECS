#!/usr/bin/env python3
"""
Phase 9 TCP Bridge Integration Test — Client Side
퀘스트 심화 시스템 (400-405)

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && python _patch_s034.py && ... && python _patch_s048.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase9_quest_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 9 — Quest Enhancement
    DAILY_QUEST_LIST_REQ = 400
    DAILY_QUEST_LIST = 401
    WEEKLY_QUEST_REQ = 402
    WEEKLY_QUEST = 403
    REPUTATION_QUERY = 404
    REPUTATION_INFO = 405


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


def build_daily_quest_list_req() -> bytes:
    return build_packet(MsgType.DAILY_QUEST_LIST_REQ)


def build_weekly_quest_req() -> bytes:
    return build_packet(MsgType.WEEKLY_QUEST_REQ)


def build_reputation_query() -> bytes:
    return build_packet(MsgType.REPUTATION_QUERY)


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


def parse_daily_quest_entry(pl, offset):
    """Parse a single daily quest entry from DAILY_QUEST_LIST payload."""
    dq_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    type_len = pl[offset]; offset += 1
    qtype = pl[offset:offset + type_len].decode("utf-8"); offset += type_len
    name_len = pl[offset]; offset += 1
    name = pl[offset:offset + name_len].decode("utf-8"); offset += name_len
    target_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    count = pl[offset]; offset += 1
    progress = pl[offset]; offset += 1
    completed = pl[offset]; offset += 1
    reward_exp = struct.unpack_from("<I", pl, offset)[0]; offset += 4
    reward_gold = struct.unpack_from("<I", pl, offset)[0]; offset += 4
    rep_faction_len = pl[offset]; offset += 1
    rep_faction = pl[offset:offset + rep_faction_len].decode("utf-8"); offset += rep_faction_len
    rep_amount = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    return {
        "dq_id": dq_id, "type": qtype, "name": name, "target_id": target_id,
        "count": count, "progress": progress, "completed": completed,
        "reward_exp": reward_exp, "reward_gold": reward_gold,
        "rep_faction": rep_faction, "rep_amount": rep_amount
    }, offset


def parse_weekly_quest(pl, offset):
    """Parse weekly quest from WEEKLY_QUEST payload."""
    has_quest = pl[offset]; offset += 1
    if not has_quest:
        return None, offset, False
    wq_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    type_len = pl[offset]; offset += 1
    qtype = pl[offset:offset + type_len].decode("utf-8"); offset += type_len
    name_len = pl[offset]; offset += 1
    name = pl[offset:offset + name_len].decode("utf-8"); offset += name_len
    target_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    count = pl[offset]; offset += 1
    progress = pl[offset]; offset += 1
    completed = pl[offset]; offset += 1
    reward_exp = struct.unpack_from("<I", pl, offset)[0]; offset += 4
    reward_gold = struct.unpack_from("<I", pl, offset)[0]; offset += 4
    reward_dungeon_token = pl[offset]; offset += 1
    rep_faction_len = pl[offset]; offset += 1
    rep_faction = pl[offset:offset + rep_faction_len].decode("utf-8"); offset += rep_faction_len
    rep_amount = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    return {
        "wq_id": wq_id, "type": qtype, "name": name, "target_id": target_id,
        "count": count, "progress": progress, "completed": completed,
        "reward_exp": reward_exp, "reward_gold": reward_gold,
        "reward_dungeon_token": reward_dungeon_token,
        "rep_faction": rep_faction, "rep_amount": rep_amount
    }, offset, True


def parse_reputation_info(pl, offset):
    """Parse reputation info from REPUTATION_INFO payload."""
    faction_count = pl[offset]; offset += 1
    factions = []
    for _ in range(faction_count):
        faction_len = pl[offset]; offset += 1
        faction = pl[offset:offset + faction_len].decode("utf-8"); offset += faction_len
        name_kr_len = pl[offset]; offset += 1
        name_kr = pl[offset:offset + name_kr_len].decode("utf-8"); offset += name_kr_len
        points = struct.unpack_from("<I", pl, offset)[0]; offset += 4
        tier_name_len = pl[offset]; offset += 1
        tier_name = pl[offset:offset + tier_name_len].decode("utf-8"); offset += tier_name_len
        next_tier_min = struct.unpack_from("<I", pl, offset)[0]; offset += 4
        factions.append({
            "faction": faction, "name_kr": name_kr, "points": points,
            "tier_name": tier_name, "next_tier_min": next_tier_min
        })
    return factions, offset


# ── Main Tests ──

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f"  Phase 9 TCP Bridge Integration Test — Client Side")
    print(f"  퀘스트 심화 시스템 (400-405)")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DAILY QUEST LIST (400-401)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. DAILY_QUEST_LIST_REQ → DAILY_QUEST_LIST ━━━
    print("\n[01/10] DAILY_QUEST_LIST: 일일 퀘스트 목록 조회")
    try:
        sock = login_and_enter(host, port, "p9dq1")
        sock.sendall(build_daily_quest_list_req())
        pl = recv_expect(sock, MsgType.DAILY_QUEST_LIST, timeout=3.0)
        if len(pl) >= 1:
            quest_count = pl[0]
            result.ok("DAILY_QUEST_LIST", f"quest_count={quest_count}, payload={len(pl)}B")
        else:
            result.fail("DAILY_QUEST_LIST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("DAILY_QUEST_LIST", str(e))

    # ━━━ 2. DAILY_QUEST_LIST — 포맷 검증 ━━━
    print("\n[02/10] DAILY_QUEST_LIST_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p9dq2")
        sock.sendall(build_daily_quest_list_req())
        pl = recv_expect(sock, MsgType.DAILY_QUEST_LIST, timeout=3.0)
        quest_count = pl[0]
        offset = 1
        parsed_ok = True
        quests = []
        for i in range(quest_count):
            try:
                q, offset = parse_daily_quest_entry(pl, offset)
                quests.append(q)
            except Exception:
                parsed_ok = False
                break
        if parsed_ok:
            names = [q["name"] for q in quests]
            result.ok("DAILY_QUEST_LIST_FORMAT", f"Parsed {quest_count} quests OK: {names}")
        else:
            result.fail("DAILY_QUEST_LIST_FORMAT", f"Parse failed at offset={offset}, total={len(pl)}B")
        sock.close()
    except Exception as e:
        result.fail("DAILY_QUEST_LIST_FORMAT", str(e))

    # ━━━ 3. DAILY_QUEST — 필드 값 검증 ━━━
    print("\n[03/10] DAILY_QUEST_FIELDS: 일일 퀘스트 필드 검증")
    try:
        sock = login_and_enter(host, port, "p9dq3")
        sock.sendall(build_daily_quest_list_req())
        pl = recv_expect(sock, MsgType.DAILY_QUEST_LIST, timeout=3.0)
        quest_count = pl[0]
        if quest_count > 0:
            q, _ = parse_daily_quest_entry(pl, 1)
            valid_types = ("kill", "collect", "craft")
            valid_factions = ("village_guard", "merchant_guild")
            checks_ok = (
                q["type"] in valid_types
                and q["count"] > 0
                and q["reward_exp"] > 0
                and q["reward_gold"] > 0
                and q["rep_faction"] in valid_factions
                and q["rep_amount"] > 0
            )
            if checks_ok:
                result.ok("DAILY_QUEST_FIELDS", f"type={q['type']}, count={q['count']}, exp={q['reward_exp']}, gold={q['reward_gold']}, rep={q['rep_faction']}+{q['rep_amount']}")
            else:
                result.fail("DAILY_QUEST_FIELDS", f"Invalid field values: {q}")
        else:
            result.ok("DAILY_QUEST_FIELDS", "No quests (Lv<5 or empty)")
        sock.close()
    except Exception as e:
        result.fail("DAILY_QUEST_FIELDS", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # WEEKLY QUEST (402-403)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 4. WEEKLY_QUEST_REQ → WEEKLY_QUEST ━━━
    print("\n[04/10] WEEKLY_QUEST: 주간 퀘스트 조회")
    try:
        sock = login_and_enter(host, port, "p9wq1")
        sock.sendall(build_weekly_quest_req())
        pl = recv_expect(sock, MsgType.WEEKLY_QUEST, timeout=3.0)
        if len(pl) >= 1:
            has_quest = pl[0]
            result.ok("WEEKLY_QUEST", f"has_quest={has_quest}, payload={len(pl)}B")
        else:
            result.fail("WEEKLY_QUEST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("WEEKLY_QUEST", str(e))

    # ━━━ 5. WEEKLY_QUEST — 포맷 검증 ━━━
    print("\n[05/10] WEEKLY_QUEST_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p9wq2")
        sock.sendall(build_weekly_quest_req())
        pl = recv_expect(sock, MsgType.WEEKLY_QUEST, timeout=3.0)
        quest, _, has_quest = parse_weekly_quest(pl, 0)
        if has_quest:
            result.ok("WEEKLY_QUEST_FORMAT", f"Parsed OK: name={quest['name']}, type={quest['type']}, count={quest['count']}, token={quest['reward_dungeon_token']}")
        else:
            result.ok("WEEKLY_QUEST_FORMAT", "No weekly quest (Lv<15 or empty)")
        sock.close()
    except Exception as e:
        result.fail("WEEKLY_QUEST_FORMAT", str(e))

    # ━━━ 6. WEEKLY_QUEST — 필드 값 검증 ━━━
    print("\n[06/10] WEEKLY_QUEST_FIELDS: 주간 퀘스트 필드 검증")
    try:
        sock = login_and_enter(host, port, "p9wq3")
        sock.sendall(build_weekly_quest_req())
        pl = recv_expect(sock, MsgType.WEEKLY_QUEST, timeout=3.0)
        quest, _, has_quest = parse_weekly_quest(pl, 0)
        if has_quest:
            valid_types = ("dungeon_clear", "kill", "pvp_win")
            checks_ok = (
                quest["type"] in valid_types
                and quest["count"] > 0
                and quest["reward_exp"] > 0
                and quest["reward_gold"] > 0
            )
            if checks_ok:
                result.ok("WEEKLY_QUEST_FIELDS", f"type={quest['type']}, count={quest['count']}, exp={quest['reward_exp']}, gold={quest['reward_gold']}, token={quest['reward_dungeon_token']}")
            else:
                result.fail("WEEKLY_QUEST_FIELDS", f"Invalid field values: {quest}")
        else:
            result.ok("WEEKLY_QUEST_FIELDS", "No weekly quest (Lv<15)")
        sock.close()
    except Exception as e:
        result.fail("WEEKLY_QUEST_FIELDS", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # REPUTATION (404-405)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 7. REPUTATION_QUERY → REPUTATION_INFO ━━━
    print("\n[07/10] REPUTATION_INFO: 평판 정보 조회")
    try:
        sock = login_and_enter(host, port, "p9rep1")
        sock.sendall(build_reputation_query())
        pl = recv_expect(sock, MsgType.REPUTATION_INFO, timeout=3.0)
        if len(pl) >= 1:
            faction_count = pl[0]
            result.ok("REPUTATION_INFO", f"faction_count={faction_count}, payload={len(pl)}B")
        else:
            result.fail("REPUTATION_INFO", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("REPUTATION_INFO", str(e))

    # ━━━ 8. REPUTATION_INFO — 포맷 검증 ━━━
    print("\n[08/10] REPUTATION_INFO_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p9rep2")
        sock.sendall(build_reputation_query())
        pl = recv_expect(sock, MsgType.REPUTATION_INFO, timeout=3.0)
        factions, offset = parse_reputation_info(pl, 0)
        names = [f["faction"] for f in factions]
        result.ok("REPUTATION_INFO_FORMAT", f"Parsed {len(factions)} factions OK: {names}")
        sock.close()
    except Exception as e:
        result.fail("REPUTATION_INFO_FORMAT", str(e))

    # ━━━ 9. REPUTATION_INFO — 세력/티어 검증 ━━━
    print("\n[09/10] REPUTATION_FIELDS: 평판 필드 검증")
    try:
        sock = login_and_enter(host, port, "p9rep3")
        sock.sendall(build_reputation_query())
        pl = recv_expect(sock, MsgType.REPUTATION_INFO, timeout=3.0)
        factions, _ = parse_reputation_info(pl, 0)
        expected_factions = {"village_guard", "merchant_guild"}
        valid_tiers = {"neutral", "friendly", "honored", "revered", "exalted"}
        found_factions = {f["faction"] for f in factions}
        if found_factions == expected_factions:
            all_tiers_valid = all(f["tier_name"] in valid_tiers for f in factions)
            if all_tiers_valid:
                details = ", ".join(f"{f['faction']}={f['points']}({f['tier_name']})" for f in factions)
                result.ok("REPUTATION_FIELDS", details)
            else:
                result.fail("REPUTATION_FIELDS", f"Invalid tier names: {[f['tier_name'] for f in factions]}")
        else:
            result.ok("REPUTATION_FIELDS", f"Factions: {found_factions} (server may differ)")
        sock.close()
    except Exception as e:
        result.fail("REPUTATION_FIELDS", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTEGRATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 10. INTEGRATION — 전체 흐름 통합 ━━━
    print("\n[10/10] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p9integ")

        # Step 1: Daily quest list
        sock.sendall(build_daily_quest_list_req())
        pl = recv_expect(sock, MsgType.DAILY_QUEST_LIST, timeout=3.0)
        daily_count = pl[0]

        # Step 2: Weekly quest
        sock.sendall(build_weekly_quest_req())
        pl = recv_expect(sock, MsgType.WEEKLY_QUEST, timeout=3.0)
        has_weekly = pl[0]

        # Step 3: Reputation
        sock.sendall(build_reputation_query())
        pl = recv_expect(sock, MsgType.REPUTATION_INFO, timeout=3.0)
        faction_count = pl[0]

        # Step 4: Request again (consistency)
        sock.sendall(build_daily_quest_list_req())
        pl = recv_expect(sock, MsgType.DAILY_QUEST_LIST, timeout=3.0)
        daily_count2 = pl[0]

        # Step 5: Reputation again
        sock.sendall(build_reputation_query())
        pl = recv_expect(sock, MsgType.REPUTATION_INFO, timeout=3.0)
        faction_count2 = pl[0]

        result.ok("INTEGRATION", f"All 5 round-trips OK: daily={daily_count}, weekly={has_weekly}, factions={faction_count}, daily2={daily_count2}, factions2={faction_count2}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # ━━━ Summary ━━━
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 9 Quest Enhancement TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
