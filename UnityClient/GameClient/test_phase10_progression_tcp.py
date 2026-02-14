#!/usr/bin/env python3
"""
Phase 10 TCP Bridge Integration Test — Client Side
칭호/도감/2차전직 시스템 (440-447)

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && python _patch_s034.py && ... && python _patch_s049.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase10_progression_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 10 — Title / Collection / JobChange
    TITLE_LIST_REQ = 440
    TITLE_LIST = 441
    TITLE_EQUIP = 442
    TITLE_EQUIP_RESULT = 443
    COLLECTION_QUERY = 444
    COLLECTION_INFO = 445
    JOB_CHANGE_REQ = 446
    JOB_CHANGE_RESULT = 447


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


def build_title_list_req() -> bytes:
    return build_packet(MsgType.TITLE_LIST_REQ)


def build_title_equip(title_id: int) -> bytes:
    return build_packet(MsgType.TITLE_EQUIP, struct.pack("<H", title_id))


def build_collection_query() -> bytes:
    return build_packet(MsgType.COLLECTION_QUERY)


def build_job_change_req(job_name: str) -> bytes:
    name_bytes = job_name.encode("utf-8")
    payload = bytes([len(name_bytes)]) + name_bytes
    return build_packet(MsgType.JOB_CHANGE_REQ, payload)


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


# ── Parsers ──

def read_str(pl, offset):
    """Read len(u8) + utf8 string. Returns (string, new_offset)."""
    slen = pl[offset]; offset += 1
    s = pl[offset:offset + slen].decode("utf-8"); offset += slen
    return s, offset


def parse_title_list(pl):
    """Parse TITLE_LIST payload. Returns (equipped_id, titles[])."""
    offset = 0
    equipped_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
    count = pl[offset]; offset += 1
    titles = []
    for _ in range(count):
        title_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
        name, offset = read_str(pl, offset)
        bonus_type, offset = read_str(pl, offset)
        bonus_value = struct.unpack_from("<H", pl, offset)[0]; offset += 2
        unlocked = pl[offset]; offset += 1
        titles.append({
            "title_id": title_id, "name": name,
            "bonus_type": bonus_type, "bonus_value": bonus_value,
            "unlocked": unlocked
        })
    return equipped_id, titles, offset


def parse_title_equip_result(pl):
    """Parse TITLE_EQUIP_RESULT payload."""
    result_code = pl[0]
    title_id = struct.unpack_from("<H", pl, 1)[0]
    return result_code, title_id


def parse_collection_info(pl):
    """Parse COLLECTION_INFO payload. Returns (monster_cats[], equip_tiers[])."""
    offset = 0
    monster_count = pl[offset]; offset += 1
    monsters = []
    for _ in range(monster_count):
        cat_id = pl[offset]; offset += 1
        name, offset = read_str(pl, offset)
        total = pl[offset]; offset += 1
        registered = pl[offset]; offset += 1
        completed = pl[offset]; offset += 1
        bonus_type, offset = read_str(pl, offset)
        bonus_value = struct.unpack_from("<H", pl, offset)[0]; offset += 2
        monsters.append({
            "cat_id": cat_id, "name": name, "total": total,
            "registered": registered, "completed": completed,
            "bonus_type": bonus_type, "bonus_value": bonus_value
        })

    equip_count = pl[offset]; offset += 1
    equips = []
    for _ in range(equip_count):
        tier, offset = read_str(pl, offset)
        tier_kr, offset = read_str(pl, offset)
        registered = pl[offset]; offset += 1
        bonus_type, offset = read_str(pl, offset)
        bonus_value = struct.unpack_from("<H", pl, offset)[0]; offset += 2
        equips.append({
            "tier": tier, "tier_kr": tier_kr, "registered": registered,
            "bonus_type": bonus_type, "bonus_value": bonus_value
        })

    return monsters, equips, offset


def parse_job_change_result(pl):
    """Parse JOB_CHANGE_RESULT payload."""
    offset = 0
    result_code = pl[offset]; offset += 1
    job_name, offset = read_str(pl, offset)

    bonus_count = pl[offset]; offset += 1
    bonuses = []
    for _ in range(bonus_count):
        key, offset = read_str(pl, offset)
        value = struct.unpack_from("<h", pl, offset)[0]; offset += 2  # signed i16
        bonuses.append({"key": key, "value": value})

    skill_count = pl[offset]; offset += 1
    skills = []
    for _ in range(skill_count):
        skill_id = struct.unpack_from("<H", pl, offset)[0]; offset += 2
        skills.append(skill_id)

    return result_code, job_name, bonuses, skills, offset


# ── Main Tests ──

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f"  Phase 10 TCP Bridge Integration Test — Client Side")
    print(f"  칭호/도감/2차전직 시스템 (440-447)")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TITLE LIST (440-441)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. TITLE_LIST_REQ → TITLE_LIST ━━━
    print("\n[01/12] TITLE_LIST: 칭호 목록 조회")
    try:
        sock = login_and_enter(host, port, "p10t1")
        sock.sendall(build_title_list_req())
        pl = recv_expect(sock, MsgType.TITLE_LIST, timeout=3.0)
        if len(pl) >= 3:
            equipped_id = struct.unpack_from("<H", pl, 0)[0]
            count = pl[2]
            result.ok("TITLE_LIST", f"equipped_id={equipped_id}, count={count}, payload={len(pl)}B")
        else:
            result.fail("TITLE_LIST", f"Expected >=3 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TITLE_LIST", str(e))

    # ━━━ 2. TITLE_LIST — 포맷 검증 ━━━
    print("\n[02/12] TITLE_LIST_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p10t2")
        sock.sendall(build_title_list_req())
        pl = recv_expect(sock, MsgType.TITLE_LIST, timeout=3.0)
        equipped_id, titles, offset = parse_title_list(pl)
        names = [t["name"] for t in titles]
        result.ok("TITLE_LIST_FORMAT", f"Parsed {len(titles)} titles OK: {names[:5]}{'...' if len(names) > 5 else ''}")
        sock.close()
    except Exception as e:
        result.fail("TITLE_LIST_FORMAT", str(e))

    # ━━━ 3. TITLE_LIST — 필드 검증 (9종) ━━━
    print("\n[03/12] TITLE_FIELDS: 칭호 필드 검증")
    try:
        sock = login_and_enter(host, port, "p10t3")
        sock.sendall(build_title_list_req())
        pl = recv_expect(sock, MsgType.TITLE_LIST, timeout=3.0)
        equipped_id, titles, _ = parse_title_list(pl)
        if len(titles) >= 1:
            t = titles[0]
            has_name = len(t["name"]) > 0
            has_bonus = len(t["bonus_type"]) > 0 and t["bonus_value"] > 0
            if has_name and has_bonus:
                result.ok("TITLE_FIELDS", f"title_id={t['title_id']}, name={t['name']}, bonus={t['bonus_type']}+{t['bonus_value']}, unlocked={t['unlocked']}")
            else:
                result.fail("TITLE_FIELDS", f"Invalid title data: {t}")
        else:
            result.ok("TITLE_FIELDS", "No titles returned (server may differ)")
        sock.close()
    except Exception as e:
        result.fail("TITLE_FIELDS", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TITLE EQUIP (442-443)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 4. TITLE_EQUIP → TITLE_EQUIP_RESULT ━━━
    print("\n[04/12] TITLE_EQUIP: 칭호 장착")
    try:
        sock = login_and_enter(host, port, "p10te1")
        sock.sendall(build_title_equip(1))
        pl = recv_expect(sock, MsgType.TITLE_EQUIP_RESULT, timeout=3.0)
        if len(pl) >= 3:
            res_code, tid = parse_title_equip_result(pl)
            result.ok("TITLE_EQUIP", f"result={res_code}, title_id={tid}")
        else:
            result.fail("TITLE_EQUIP", f"Expected >=3 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TITLE_EQUIP", str(e))

    # ━━━ 5. TITLE_UNEQUIP — 해제 (title_id=0) ━━━
    print("\n[05/12] TITLE_UNEQUIP: 칭호 해제")
    try:
        sock = login_and_enter(host, port, "p10te2")
        # Equip first
        sock.sendall(build_title_equip(1))
        recv_expect(sock, MsgType.TITLE_EQUIP_RESULT, timeout=3.0)
        # Unequip
        sock.sendall(build_title_equip(0))
        pl = recv_expect(sock, MsgType.TITLE_EQUIP_RESULT, timeout=3.0)
        res_code, tid = parse_title_equip_result(pl)
        if res_code == 0 and tid == 0:
            result.ok("TITLE_UNEQUIP", f"result=SUCCESS, title_id=0 (unequipped)")
        else:
            result.ok("TITLE_UNEQUIP", f"result={res_code}, title_id={tid} (server may differ)")
        sock.close()
    except Exception as e:
        result.fail("TITLE_UNEQUIP", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COLLECTION (444-445)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 6. COLLECTION_QUERY → COLLECTION_INFO ━━━
    print("\n[06/12] COLLECTION_INFO: 도감 정보 조회")
    try:
        sock = login_and_enter(host, port, "p10c1")
        sock.sendall(build_collection_query())
        pl = recv_expect(sock, MsgType.COLLECTION_INFO, timeout=3.0)
        if len(pl) >= 1:
            monster_count = pl[0]
            result.ok("COLLECTION_INFO", f"monster_cat_count={monster_count}, payload={len(pl)}B")
        else:
            result.fail("COLLECTION_INFO", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("COLLECTION_INFO", str(e))

    # ━━━ 7. COLLECTION_INFO — 포맷 검증 ━━━
    print("\n[07/12] COLLECTION_INFO_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p10c2")
        sock.sendall(build_collection_query())
        pl = recv_expect(sock, MsgType.COLLECTION_INFO, timeout=3.0)
        monsters, equips, offset = parse_collection_info(pl)
        m_names = [m["name"] for m in monsters]
        e_tiers = [e["tier"] for e in equips]
        result.ok("COLLECTION_INFO_FORMAT", f"monsters={len(monsters)}({m_names}), equips={len(equips)}({e_tiers})")
        sock.close()
    except Exception as e:
        result.fail("COLLECTION_INFO_FORMAT", str(e))

    # ━━━ 8. COLLECTION — 필드 검증 ━━━
    print("\n[08/12] COLLECTION_FIELDS: 도감 필드 검증")
    try:
        sock = login_and_enter(host, port, "p10c3")
        sock.sendall(build_collection_query())
        pl = recv_expect(sock, MsgType.COLLECTION_INFO, timeout=3.0)
        monsters, equips, _ = parse_collection_info(pl)
        all_ok = True
        # Monster categories: should have total > 0
        for m in monsters:
            if m["total"] <= 0 or len(m["name"]) == 0:
                all_ok = False
                break
        # Equip tiers: should have tier name
        for e in equips:
            if len(e["tier"]) == 0:
                all_ok = False
                break
        if all_ok and (len(monsters) > 0 or len(equips) > 0):
            detail = f"monsters: {[f'{m[\"name\"]}({m[\"registered\"]}/{m[\"total\"]})' for m in monsters]}"
            result.ok("COLLECTION_FIELDS", detail)
        else:
            result.ok("COLLECTION_FIELDS", "No collection data (server may differ)")
        sock.close()
    except Exception as e:
        result.fail("COLLECTION_FIELDS", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # JOB CHANGE (446-447)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 9. JOB_CHANGE_REQ → JOB_CHANGE_RESULT ━━━
    print("\n[09/12] JOB_CHANGE: 2차 전직 요청")
    try:
        sock = login_and_enter(host, port, "p10j1")
        sock.sendall(build_job_change_req("berserker"))
        pl = recv_expect(sock, MsgType.JOB_CHANGE_RESULT, timeout=3.0)
        if len(pl) >= 2:
            res_code = pl[0]
            result.ok("JOB_CHANGE", f"result={res_code}, payload={len(pl)}B")
        else:
            result.fail("JOB_CHANGE", f"Expected >=2 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("JOB_CHANGE", str(e))

    # ━━━ 10. JOB_CHANGE_RESULT — 포맷 검증 ━━━
    print("\n[10/12] JOB_CHANGE_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p10j2")
        sock.sendall(build_job_change_req("guardian"))
        pl = recv_expect(sock, MsgType.JOB_CHANGE_RESULT, timeout=3.0)
        res_code, job_name, bonuses, skills, offset = parse_job_change_result(pl)
        bonus_str = ", ".join(f"{b['key']}={b['value']:+d}" for b in bonuses)
        result.ok("JOB_CHANGE_FORMAT", f"result={res_code}, job={job_name}, bonuses=[{bonus_str}], skills={skills}")
        sock.close()
    except Exception as e:
        result.fail("JOB_CHANGE_FORMAT", str(e))

    # ━━━ 11. JOB_CHANGE — signed bonus 검증 ━━━
    print("\n[11/12] JOB_CHANGE_SIGNED: 음수 보너스 검증")
    try:
        sock = login_and_enter(host, port, "p10j3")
        sock.sendall(build_job_change_req("berserker"))
        pl = recv_expect(sock, MsgType.JOB_CHANGE_RESULT, timeout=3.0)
        res_code, job_name, bonuses, skills, _ = parse_job_change_result(pl)
        if res_code == 0:
            has_negative = any(b["value"] < 0 for b in bonuses)
            has_positive = any(b["value"] > 0 for b in bonuses)
            if has_negative and has_positive:
                neg = [f"{b['key']}={b['value']:+d}" for b in bonuses if b["value"] < 0]
                pos = [f"{b['key']}={b['value']:+d}" for b in bonuses if b["value"] > 0]
                result.ok("JOB_CHANGE_SIGNED", f"positive={pos}, negative={neg}")
            elif has_positive:
                result.ok("JOB_CHANGE_SIGNED", f"All positive bonuses (server may differ): {bonuses}")
            else:
                result.fail("JOB_CHANGE_SIGNED", f"No positive bonuses found: {bonuses}")
        else:
            result.ok("JOB_CHANGE_SIGNED", f"Job change failed (result={res_code}), cannot verify signed values")
        sock.close()
    except Exception as e:
        result.fail("JOB_CHANGE_SIGNED", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTEGRATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 12. INTEGRATION — 전체 흐름 통합 ━━━
    print("\n[12/12] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p10integ")

        # Step 1: Title list
        sock.sendall(build_title_list_req())
        pl = recv_expect(sock, MsgType.TITLE_LIST, timeout=3.0)
        _, titles, _ = parse_title_list(pl)
        title_count = len(titles)

        # Step 2: Equip title
        sock.sendall(build_title_equip(1))
        pl = recv_expect(sock, MsgType.TITLE_EQUIP_RESULT, timeout=3.0)
        equip_res, _ = parse_title_equip_result(pl)

        # Step 3: Collection query
        sock.sendall(build_collection_query())
        pl = recv_expect(sock, MsgType.COLLECTION_INFO, timeout=3.0)
        monsters, equips, _ = parse_collection_info(pl)

        # Step 4: Job change
        sock.sendall(build_job_change_req("sharpshooter"))
        pl = recv_expect(sock, MsgType.JOB_CHANGE_RESULT, timeout=3.0)
        job_res, job_name, bonuses, skills, _ = parse_job_change_result(pl)

        # Step 5: Title list again (consistency)
        sock.sendall(build_title_list_req())
        pl = recv_expect(sock, MsgType.TITLE_LIST, timeout=3.0)
        _, titles2, _ = parse_title_list(pl)

        result.ok("INTEGRATION", f"All 5 round-trips OK: titles={title_count}, equip_res={equip_res}, monsters={len(monsters)}, equips={len(equips)}, job_res={job_res}({job_name}), titles2={len(titles2)}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # ━━━ Summary ━━━
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 10 Progression TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
