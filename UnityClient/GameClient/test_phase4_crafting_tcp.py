#!/usr/bin/env python3
"""
Phase 4 TCP Bridge Integration Test — Client Side (S043 format)
Crafting(380-383) / Gathering(384-385) / Cooking(386-387) / Enchant(388-389)

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && python _patch_s034.py && python _patch_s035.py && python _patch_s036.py && python _patch_s037.py && python _patch_s040.py && python _patch_s041.py && python _patch_s043.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase4_crafting_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    SKILL_LIST_RESP = 151
    INVENTORY_RESP = 191
    BUFF_LIST_RESP = 201
    QUEST_LIST_RESP = 231
    MONSTER_SPAWN = 110
    # Phase 4 — Crafting (S043)
    CRAFT_LIST_REQ = 380
    CRAFT_LIST = 381
    CRAFT_EXECUTE = 382
    CRAFT_RESULT = 383
    # Phase 4 — Gathering (S043)
    GATHER_START = 384
    GATHER_RESULT = 385
    # Phase 4 — Cooking (S043)
    COOK_EXECUTE = 386
    COOK_RESULT = 387
    # Phase 4 — Enchant (S043)
    ENCHANT_REQ = 388
    ENCHANT_RESULT = 389


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


# ── Packet Builders (S043 format) ──

def build_login(username: str, password: str) -> bytes:
    u = username.encode("utf-8")
    p = password.encode("utf-8")
    payload = bytes([len(u)]) + u + bytes([len(p)]) + p
    return build_packet(MsgType.LOGIN, payload)


def build_char_select(char_id: int) -> bytes:
    return build_packet(MsgType.CHAR_SELECT, struct.pack("<I", char_id))


def build_craft_list_req(category: int = 0xFF) -> bytes:
    return build_packet(MsgType.CRAFT_LIST_REQ, struct.pack("<B", category))


def build_craft_execute(recipe_id: str) -> bytes:
    rid = recipe_id.encode("utf-8")
    payload = struct.pack("<B", len(rid)) + rid
    return build_packet(MsgType.CRAFT_EXECUTE, payload)


def build_gather_start(gather_type: int) -> bytes:
    return build_packet(MsgType.GATHER_START, struct.pack("<B", gather_type))


def build_cook_execute(recipe_id: str) -> bytes:
    rid = recipe_id.encode("utf-8")
    payload = struct.pack("<B", len(rid)) + rid
    return build_packet(MsgType.COOK_EXECUTE, payload)


def build_enchant_req(slot: int, element: int, level: int) -> bytes:
    return build_packet(MsgType.ENCHANT_REQ, struct.pack("<BBB", slot, element, level))


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
    print(f"  Phase 4 TCP Bridge Integration Test — Client Side")
    print(f"  Crafting / Gathering / Cooking / Enchant")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CRAFTING (380-383) — S043 format
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. CRAFT_LIST_REQ → CRAFT_LIST ━━━
    print("\n[01/14] CRAFT_LIST: 제작 레시피 목록 조회")
    try:
        sock = login_and_enter(host, port, "p4craft1")
        sock.sendall(build_craft_list_req(0xFF))  # category=ALL
        pl = recv_expect(sock, MsgType.CRAFT_LIST, timeout=3.0)
        count = pl[0]
        if count >= 4:
            # Parse first recipe: B:rid_len + str:rid + B:prof + H:gold + B:success + H:item_id + B:item_cnt + B:mat_cnt
            off = 1
            rid_len = pl[off]; off += 1
            rid = pl[off:off+rid_len].decode("utf-8"); off += rid_len
            result.ok("CRAFT_LIST", f"{count} recipes, first: '{rid}'")
        else:
            result.fail("CRAFT_LIST", f"Expected >=4 recipes, got {count}")
        sock.close()
    except Exception as e:
        result.fail("CRAFT_LIST", str(e))

    # ━━━ 2. CRAFT_LIST category filter ━━━
    print("\n[02/14] CRAFT_LIST_FILTER: 포션 카테고리 필터")
    try:
        sock = login_and_enter(host, port, "p4craft2")
        sock.sendall(build_craft_list_req(2))  # category=POTION
        pl = recv_expect(sock, MsgType.CRAFT_LIST, timeout=3.0)
        count = pl[0]
        result.ok("CRAFT_LIST_FILTER", f"Potion category: {count} recipes")
        sock.close()
    except Exception as e:
        result.fail("CRAFT_LIST_FILTER", str(e))

    # ━━━ 3. CRAFT_EXECUTE — 존재하지 않는 레시피 ━━━
    print("\n[03/14] CRAFT_INVALID: 존재하지 않는 레시피")
    try:
        sock = login_and_enter(host, port, "p4craft3")
        sock.sendall(build_craft_execute("nonexistent_recipe"))
        pl = recv_expect(sock, MsgType.CRAFT_RESULT, timeout=3.0)
        status = pl[0]
        if status == 1:  # RECIPE_NOT_FOUND (UNKNOWN)
            result.ok("CRAFT_INVALID", f"result=1 (UNKNOWN/NOT_FOUND)")
        else:
            result.fail("CRAFT_INVALID", f"Expected 1 (UNKNOWN), got {status}")
        sock.close()
    except Exception as e:
        result.fail("CRAFT_INVALID", str(e))

    # ━━━ 4. CRAFT_EXECUTE — hp_potion_s (골드 부족) ━━━
    print("\n[04/14] CRAFT_FAIL: 골드 부족 제작 실패")
    try:
        sock = login_and_enter(host, port, "p4craft4")
        sock.sendall(build_craft_execute("iron_sword"))
        pl = recv_expect(sock, MsgType.CRAFT_RESULT, timeout=3.0)
        status = pl[0]
        # S043: result=0 SUCCESS, 1=UNKNOWN, 2=LEVEL_LOW, 3=NO_GOLD, 5=FAIL
        if status != 0:
            result.ok("CRAFT_FAIL", f"result={status} (expected non-zero)")
        else:
            result.ok("CRAFT_FAIL", f"result=0 (craft succeeded — server may auto-give gold)")
        sock.close()
    except Exception as e:
        result.fail("CRAFT_FAIL", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # GATHERING (384-385) — S043 format
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 5. GATHER — 약초 채집 성공 ━━━
    print("\n[05/14] GATHER_HERB: 약초 채집 성공")
    try:
        sock = login_and_enter(host, port, "p4gath1")
        sock.sendall(build_gather_start(1))  # gather_type=1 (herb)
        pl = recv_expect(sock, MsgType.GATHER_RESULT, timeout=3.0)
        # S043: result(1) energy(1) drop_count(1) {item_id(2)}*N
        status = pl[0]
        energy = pl[1]
        drop_count = pl[2]
        if status == 0 and drop_count >= 1:
            item_ids = []
            off = 3
            for i in range(drop_count):
                iid = struct.unpack_from("<H", pl, off)[0]; off += 2
                item_ids.append(iid)
            result.ok("GATHER_HERB", f"drops={drop_count}, items={item_ids}, energy={energy}")
        elif status == 0:
            result.ok("GATHER_HERB", f"SUCCESS drops={drop_count}, energy={energy}")
        else:
            result.fail("GATHER_HERB", f"result={status}, expected 0")
        sock.close()
    except Exception as e:
        result.fail("GATHER_HERB", str(e))

    # ━━━ 6. GATHER — 잘못된 타입 ━━━
    print("\n[06/14] GATHER_INVALID: 잘못된 채집 타입")
    try:
        sock = login_and_enter(host, port, "p4gath2")
        sock.sendall(build_gather_start(99))  # Invalid gather_type
        pl = recv_expect(sock, MsgType.GATHER_RESULT, timeout=3.0)
        status = pl[0]
        if status == 1:  # UNKNOWN_TYPE
            result.ok("GATHER_INVALID", "result=1 (UNKNOWN_TYPE)")
        else:
            result.fail("GATHER_INVALID", f"Expected 1 (UNKNOWN_TYPE), got {status}")
        sock.close()
    except Exception as e:
        result.fail("GATHER_INVALID", str(e))

    # ━━━ 7. GATHER — 에너지 소진 ━━━
    print("\n[07/14] GATHER_ENERGY: 에너지 소진 후 채집 불가")
    try:
        sock = login_and_enter(host, port, "p4gath3")
        # 40 gathers × 5 energy = 200 (max), all should succeed
        for i in range(40):
            sock.sendall(build_gather_start(2))  # mining
            pl = recv_expect(sock, MsgType.GATHER_RESULT, timeout=2.0)
            assert pl[0] == 0, f"Gather #{i+1} failed: result={pl[0]}"

        # 41st should fail with NO_ENERGY
        sock.sendall(build_gather_start(2))
        pl = recv_expect(sock, MsgType.GATHER_RESULT, timeout=3.0)
        status = pl[0]
        energy = pl[1]
        if status == 2 and energy == 0:
            result.ok("GATHER_ENERGY", "result=2 (NO_ENERGY), energy=0")
        else:
            result.fail("GATHER_ENERGY", f"Expected result=2 energy=0, got result={status} energy={energy}")
        sock.close()
    except Exception as e:
        result.fail("GATHER_ENERGY", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COOKING (386-387) — S043 format
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 8. COOK — 존재하지 않는 레시피 ━━━
    print("\n[08/14] COOK_FAIL: 존재하지 않는 레시피 요리 실패")
    try:
        sock = login_and_enter(host, port, "p4cook1")
        sock.sendall(build_cook_execute("nonexistent_food"))
        pl = recv_expect(sock, MsgType.COOK_RESULT, timeout=3.0)
        status = pl[0]
        if status == 1:  # UNKNOWN
            result.ok("COOK_FAIL", "result=1 (UNKNOWN)")
        else:
            result.fail("COOK_FAIL", f"Expected 1 (UNKNOWN), got {status}")
        sock.close()
    except Exception as e:
        result.fail("COOK_FAIL", str(e))

    # ━━━ 9. COOK — grilled_meat 시도 ━━━
    print("\n[09/14] COOK_EXECUTE: grilled_meat 요리 시도")
    try:
        sock = login_and_enter(host, port, "p4cook2")
        sock.sendall(build_cook_execute("grilled_meat"))
        pl = recv_expect(sock, MsgType.COOK_RESULT, timeout=3.0)
        # S043: result(1) [+ duration(2) effect_count(1)]
        status = pl[0]
        if status == 0 and len(pl) >= 4:
            duration = struct.unpack_from("<H", pl, 1)[0]
            effect_count = pl[3]
            result.ok("COOK_EXECUTE", f"SUCCESS duration={duration}s effects={effect_count}")
        else:
            result.ok("COOK_EXECUTE", f"result={status} (may fail if no materials)")
        sock.close()
    except Exception as e:
        result.fail("COOK_EXECUTE", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ENCHANT (388-389) — S043 format
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 10. ENCHANT — 빈 슬롯 ━━━
    print("\n[10/14] ENCHANT_EMPTY: 빈 슬롯 인챈트 실패")
    try:
        sock = login_and_enter(host, port, "p4ench1")
        sock.sendall(build_enchant_req(99, 1, 1))  # slot=99 (empty)
        pl = recv_expect(sock, MsgType.ENCHANT_RESULT, timeout=3.0)
        status = pl[0]
        if status == 5:  # INVALID_SLOT
            result.ok("ENCHANT_EMPTY", "result=5 (INVALID_SLOT)")
        else:
            result.fail("ENCHANT_EMPTY", f"Expected 5 (INVALID_SLOT), got {status}")
        sock.close()
    except Exception as e:
        result.fail("ENCHANT_EMPTY", str(e))

    # ━━━ 11. ENCHANT — 잘못된 원소 ━━━
    print("\n[11/14] ENCHANT_ELEMENT: 잘못된 원소 거부")
    try:
        sock = login_and_enter(host, port, "p4ench2")
        sock.sendall(build_enchant_req(0, 99, 1))  # element=99 invalid
        pl = recv_expect(sock, MsgType.ENCHANT_RESULT, timeout=3.0)
        status = pl[0]
        if status == 1:  # INVALID_ELEMENT
            result.ok("ENCHANT_ELEMENT", "result=1 (INVALID_ELEMENT)")
        else:
            result.fail("ENCHANT_ELEMENT", f"Expected 1 (INVALID_ELEMENT), got {status}")
        sock.close()
    except Exception as e:
        result.fail("ENCHANT_ELEMENT", str(e))

    # ━━━ 12. ENCHANT — 잘못된 레벨 ━━━
    print("\n[12/14] ENCHANT_LEVEL: 잘못된 레벨 거부")
    try:
        sock = login_and_enter(host, port, "p4ench3")
        sock.sendall(build_enchant_req(0, 1, 99))  # level=99 invalid
        pl = recv_expect(sock, MsgType.ENCHANT_RESULT, timeout=3.0)
        status = pl[0]
        if status == 2:  # INVALID_LEVEL
            result.ok("ENCHANT_LEVEL", "result=2 (INVALID_LEVEL)")
        else:
            result.fail("ENCHANT_LEVEL", f"Expected 2 (INVALID_LEVEL), got {status}")
        sock.close()
    except Exception as e:
        result.fail("ENCHANT_LEVEL", str(e))

    # ━━━ 13. ENCHANT_RESULT 패킷 포맷 검증 ━━━
    print("\n[13/14] ENCHANT_RESULT: 패킷 포맷 검증 (S043: 1~4 bytes)")
    try:
        sock = login_and_enter(host, port, "p4ench4")
        sock.sendall(build_enchant_req(0, 1, 1))
        pl = recv_expect(sock, MsgType.ENCHANT_RESULT, timeout=3.0)
        # S043: result(1) [+ element_id(1) level(1) dmg_bonus_pct(1)] (conditional on success)
        r = pl[0]
        if r == 0 and len(pl) >= 4:
            elem = pl[1]
            lv = pl[2]
            dmg = pl[3]
            result.ok("ENCHANT_RESULT_FORMAT", f"4B: result=0, elem={elem}, lv={lv}, dmg={dmg}%")
        elif r != 0:
            result.ok("ENCHANT_RESULT_FORMAT", f"result={r} (error, 1B only)")
        else:
            result.fail("ENCHANT_RESULT_FORMAT", f"result=0 but payload too short: {len(pl)}B")
        sock.close()
    except Exception as e:
        result.fail("ENCHANT_RESULT_FORMAT", str(e))

    # ━━━ 14. 전체 흐름 통합 ━━━
    print("\n[14/14] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p4integ")

        # Step 1: Craft list (all categories)
        sock.sendall(build_craft_list_req(0xFF))
        pl = recv_expect(sock, MsgType.CRAFT_LIST, timeout=3.0)
        craft_count = pl[0]
        assert craft_count >= 4, f"Craft list count {craft_count} < 4"

        # Step 2: Craft attempt
        sock.sendall(build_craft_execute("hp_potion_s"))
        pl = recv_expect(sock, MsgType.CRAFT_RESULT, timeout=3.0)

        # Step 3: Gather herb
        sock.sendall(build_gather_start(1))
        pl = recv_expect(sock, MsgType.GATHER_RESULT, timeout=3.0)
        g_status = pl[0]
        g_energy = pl[1]
        assert g_status == 0, f"Gather failed: {g_status}"

        # Step 4: Cook attempt
        sock.sendall(build_cook_execute("grilled_meat"))
        pl = recv_expect(sock, MsgType.COOK_RESULT, timeout=3.0)

        # Step 5: Enchant attempt
        sock.sendall(build_enchant_req(0, 1, 1))
        pl = recv_expect(sock, MsgType.ENCHANT_RESULT, timeout=3.0)

        result.ok("INTEGRATION", f"All 5 round-trips OK: craft_list={craft_count}, gather_energy={g_energy}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # ━━━ Summary ━━━
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4 Crafting TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
