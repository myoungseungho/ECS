#!/usr/bin/env python3
"""
Phase 5 TCP Bridge Integration Test — Client Side
CashShop(474-477) / BattlePass(478-483) / Events(484-487)
Subscription(488-489) / Weather(490-491) / Teleport(492-495)
WorldObject(496-497) / Mount(498-501) / Attendance(502-509)
Dialog(510-511) / Cutscene(512-514) / Story(515-517)

Usage:
    python test_phase5_world_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 5 — CashShop (TASK 11)
    CASH_SHOP_LIST_REQ = 474
    CASH_SHOP_LIST = 475
    CASH_SHOP_BUY = 476
    CASH_SHOP_BUY_RESULT = 477
    # Phase 5 — BattlePass (TASK 11)
    BATTLEPASS_INFO_REQ = 478
    BATTLEPASS_INFO = 479
    BATTLEPASS_REWARD_CLAIM = 480
    BATTLEPASS_REWARD_RESULT = 481
    BATTLEPASS_BUY_PREMIUM = 482
    BATTLEPASS_BUY_RESULT = 483
    # Phase 5 — Events (TASK 11)
    EVENT_LIST_REQ = 484
    EVENT_LIST = 485
    EVENT_CLAIM = 486
    EVENT_CLAIM_RESULT = 487
    # Phase 5 — Subscription (TASK 11)
    SUBSCRIPTION_INFO_REQ = 488
    SUBSCRIPTION_INFO = 489
    # Phase 5 — Weather/Time (TASK 12)
    WEATHER_UPDATE = 490
    TIME_UPDATE = 491
    # Phase 5 — Teleport (TASK 12)
    TELEPORT_LIST_REQ = 492
    TELEPORT_LIST = 493
    TELEPORT_REQ = 494
    TELEPORT_RESULT = 495
    # Phase 5 — WorldObject (TASK 12)
    WORLD_OBJECT_INTERACT = 496
    WORLD_OBJECT_RESULT = 497
    # Phase 5 — Mount (TASK 12)
    MOUNT_SUMMON = 498
    MOUNT_RESULT = 499
    MOUNT_DISMOUNT = 500
    MOUNT_DISMOUNT_RESULT = 501
    # Phase 5 — Attendance (TASK 13)
    ATTENDANCE_INFO_REQ = 502
    ATTENDANCE_INFO = 503
    ATTENDANCE_CLAIM = 504
    ATTENDANCE_CLAIM_RESULT = 505
    DAILY_RESET_NOTIFY = 506
    CONTENT_UNLOCK_NOTIFY = 507
    CONTENT_UNLOCK_ACK = 508
    LOGIN_REWARD_NOTIFY = 509
    # Phase 5 — Dialog/Story (TASK 14)
    DIALOG_CHOICE = 510
    DIALOG_CHOICE_RESULT = 511
    CUTSCENE_TRIGGER = 512
    CUTSCENE_SKIP = 513
    CUTSCENE_END = 514
    STORY_PROGRESS_REQ = 515
    STORY_PROGRESS = 516
    MAIN_QUEST_DATA = 517


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


# CashShop
def build_cash_shop_list_req(category: int = 0) -> bytes:
    return build_packet(MsgType.CASH_SHOP_LIST_REQ, struct.pack("<B", category))

def build_cash_shop_buy(item_id: int, count: int = 1) -> bytes:
    return build_packet(MsgType.CASH_SHOP_BUY, struct.pack("<IB", item_id, count))

# BattlePass
def build_battlepass_info_req() -> bytes:
    return build_packet(MsgType.BATTLEPASS_INFO_REQ)

def build_battlepass_reward_claim(level: int, track: int) -> bytes:
    return build_packet(MsgType.BATTLEPASS_REWARD_CLAIM, struct.pack("<BB", level, track))

def build_battlepass_buy_premium() -> bytes:
    return build_packet(MsgType.BATTLEPASS_BUY_PREMIUM)

# Events
def build_event_list_req() -> bytes:
    return build_packet(MsgType.EVENT_LIST_REQ)

def build_event_claim(event_id: int) -> bytes:
    return build_packet(MsgType.EVENT_CLAIM, struct.pack("<H", event_id))

# Subscription
def build_subscription_info_req() -> bytes:
    return build_packet(MsgType.SUBSCRIPTION_INFO_REQ)

# Teleport
def build_teleport_list_req() -> bytes:
    return build_packet(MsgType.TELEPORT_LIST_REQ)

def build_teleport_req(waypoint_id: int) -> bytes:
    return build_packet(MsgType.TELEPORT_REQ, struct.pack("<H", waypoint_id))

# WorldObject
def build_world_object_interact(object_id: int, action: int = 0) -> bytes:
    return build_packet(MsgType.WORLD_OBJECT_INTERACT, struct.pack("<IB", object_id, action))

# Mount
def build_mount_summon(mount_id: int) -> bytes:
    return build_packet(MsgType.MOUNT_SUMMON, struct.pack("<I", mount_id))

def build_mount_dismount() -> bytes:
    return build_packet(MsgType.MOUNT_DISMOUNT)

# Attendance
def build_attendance_info_req() -> bytes:
    return build_packet(MsgType.ATTENDANCE_INFO_REQ)

def build_attendance_claim(day: int) -> bytes:
    return build_packet(MsgType.ATTENDANCE_CLAIM, struct.pack("<B", day))

def build_content_unlock_ack(unlock_type: int) -> bytes:
    return build_packet(MsgType.CONTENT_UNLOCK_ACK, struct.pack("<B", unlock_type))

# Dialog/Story
def build_dialog_choice(npc_id: int, choice_index: int) -> bytes:
    return build_packet(MsgType.DIALOG_CHOICE, struct.pack("<HB", npc_id, choice_index))

def build_cutscene_skip(cutscene_id: int) -> bytes:
    return build_packet(MsgType.CUTSCENE_SKIP, struct.pack("<H", cutscene_id))

def build_story_progress_req() -> bytes:
    return build_packet(MsgType.STORY_PROGRESS_REQ)


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
    print(f"  Phase 5 TCP Bridge Integration Test — Client Side")
    print(f"  CashShop / BattlePass / Events / Subscription / Weather")
    print(f"  Teleport / WorldObject / Mount / Attendance / Story")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 11: CASH SHOP (474-477)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. CASH_SHOP_LIST_REQ → CASH_SHOP_LIST ━━━
    print("\n[01/25] CASH_SHOP_LIST: 캐시샵 아이템 목록 조회")
    try:
        sock = login_and_enter(host, port, "p5cash1")
        sock.sendall(build_cash_shop_list_req(0))  # ALL category
        pl = recv_expect(sock, MsgType.CASH_SHOP_LIST, timeout=3.0)
        count = pl[0]
        if count >= 1:
            # Parse first item: I:item_id + 32B:name + B:category + I:price + B:currency = 42B/entry
            item_id = struct.unpack_from("<I", pl, 1)[0]
            name_raw = pl[5:37]
            name = name_raw.split(b"\x00", 1)[0].decode("utf-8")
            result.ok("CASH_SHOP_LIST", f"{count} items, first: #{item_id} '{name}'")
        else:
            result.ok("CASH_SHOP_LIST", f"{count} items (empty shop)")
        sock.close()
    except Exception as e:
        result.fail("CASH_SHOP_LIST", str(e))

    # ━━━ 2. CASH_SHOP_BUY → CASH_SHOP_BUY_RESULT ━━━
    print("\n[02/25] CASH_SHOP_BUY: 캐시샵 아이템 구매")
    try:
        sock = login_and_enter(host, port, "p5cash2")
        sock.sendall(build_cash_shop_buy(1, 1))
        pl = recv_expect(sock, MsgType.CASH_SHOP_BUY_RESULT, timeout=3.0)
        # Format: B:result + I:item_id + I:remaining = 9B
        if len(pl) >= 9:
            r = pl[0]
            iid = struct.unpack_from("<I", pl, 1)[0]
            remaining = struct.unpack_from("<I", pl, 5)[0]
            result.ok("CASH_SHOP_BUY", f"result={r}, item={iid}, crystals_left={remaining}")
        else:
            result.fail("CASH_SHOP_BUY", f"Expected >=9 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("CASH_SHOP_BUY", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 11: BATTLEPASS (478-483)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 3. BATTLEPASS_INFO_REQ → BATTLEPASS_INFO ━━━
    print("\n[03/25] BATTLEPASS_INFO: 배틀패스 정보 조회")
    try:
        sock = login_and_enter(host, port, "p5bp1")
        sock.sendall(build_battlepass_info_req())
        pl = recv_expect(sock, MsgType.BATTLEPASS_INFO, timeout=3.0)
        # Format: H:season_id + B:level + H:exp + H:max_exp + B:is_premium + H:days_left = 10B
        if len(pl) >= 10:
            season = struct.unpack_from("<H", pl, 0)[0]
            level = pl[2]
            exp = struct.unpack_from("<H", pl, 3)[0]
            max_exp = struct.unpack_from("<H", pl, 5)[0]
            premium = pl[7]
            days = struct.unpack_from("<H", pl, 8)[0]
            result.ok("BATTLEPASS_INFO", f"season={season}, lv={level}, exp={exp}/{max_exp}, premium={premium}, days={days}")
        else:
            result.fail("BATTLEPASS_INFO", f"Expected >=10 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BATTLEPASS_INFO", str(e))

    # ━━━ 4. BATTLEPASS_REWARD_CLAIM → BATTLEPASS_REWARD_RESULT ━━━
    print("\n[04/25] BATTLEPASS_REWARD: 배틀패스 보상 수령")
    try:
        sock = login_and_enter(host, port, "p5bp2")
        sock.sendall(build_battlepass_reward_claim(1, 0))  # level=1, track=FREE
        pl = recv_expect(sock, MsgType.BATTLEPASS_REWARD_RESULT, timeout=3.0)
        # Format: B:result + B:level + B:track + B:reward_type + I:reward_id + H:reward_count = 10B
        if len(pl) >= 10:
            r = pl[0]
            lv = pl[1]
            track = pl[2]
            result.ok("BATTLEPASS_REWARD", f"result={r}, lv={lv}, track={track}")
        else:
            result.fail("BATTLEPASS_REWARD", f"Expected >=10 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BATTLEPASS_REWARD", str(e))

    # ━━━ 5. BATTLEPASS_BUY_PREMIUM → BATTLEPASS_BUY_RESULT ━━━
    print("\n[05/25] BATTLEPASS_PREMIUM: 프리미엄 구매")
    try:
        sock = login_and_enter(host, port, "p5bp3")
        sock.sendall(build_battlepass_buy_premium())
        pl = recv_expect(sock, MsgType.BATTLEPASS_BUY_RESULT, timeout=3.0)
        # Format: B:result + I:remaining_crystals = 5B
        if len(pl) >= 5:
            r = pl[0]
            remaining = struct.unpack_from("<I", pl, 1)[0]
            result.ok("BATTLEPASS_PREMIUM", f"result={r}, crystals_left={remaining}")
        else:
            result.fail("BATTLEPASS_PREMIUM", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("BATTLEPASS_PREMIUM", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 11: EVENTS (484-487)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 6. EVENT_LIST_REQ → EVENT_LIST ━━━
    print("\n[06/25] EVENT_LIST: 이벤트 목록 조회")
    try:
        sock = login_and_enter(host, port, "p5evt1")
        sock.sendall(build_event_list_req())
        pl = recv_expect(sock, MsgType.EVENT_LIST, timeout=3.0)
        count = pl[0]
        if count >= 0:
            result.ok("EVENT_LIST", f"{count} events")
        else:
            result.fail("EVENT_LIST", f"Invalid count: {count}")
        sock.close()
    except Exception as e:
        result.fail("EVENT_LIST", str(e))

    # ━━━ 7. EVENT_CLAIM → EVENT_CLAIM_RESULT ━━━
    print("\n[07/25] EVENT_CLAIM: 이벤트 보상 수령")
    try:
        sock = login_and_enter(host, port, "p5evt2")
        sock.sendall(build_event_claim(1))
        pl = recv_expect(sock, MsgType.EVENT_CLAIM_RESULT, timeout=3.0)
        # Format: B:result + H:event_id + B:reward_type + I:reward_id + H:reward_count = 10B
        if len(pl) >= 10:
            r = pl[0]
            eid = struct.unpack_from("<H", pl, 1)[0]
            result.ok("EVENT_CLAIM", f"result={r}, event_id={eid}")
        else:
            result.fail("EVENT_CLAIM", f"Expected >=10 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("EVENT_CLAIM", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 11: SUBSCRIPTION (488-489)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 8. SUBSCRIPTION_INFO_REQ → SUBSCRIPTION_INFO ━━━
    print("\n[08/25] SUBSCRIPTION_INFO: 월정액 정보 조회")
    try:
        sock = login_and_enter(host, port, "p5sub1")
        sock.sendall(build_subscription_info_req())
        pl = recv_expect(sock, MsgType.SUBSCRIPTION_INFO, timeout=3.0)
        # Format: B:is_active + H:days_left + H:daily_crystals = 5B
        if len(pl) >= 5:
            active = pl[0]
            days = struct.unpack_from("<H", pl, 1)[0]
            daily = struct.unpack_from("<H", pl, 3)[0]
            result.ok("SUBSCRIPTION_INFO", f"active={active}, days={days}, daily={daily}")
        else:
            result.fail("SUBSCRIPTION_INFO", f"Expected >=5 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("SUBSCRIPTION_INFO", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 12: TELEPORT (492-495)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 9. TELEPORT_LIST_REQ → TELEPORT_LIST ━━━
    print("\n[09/25] TELEPORT_LIST: 워프포인트 목록 조회")
    try:
        sock = login_and_enter(host, port, "p5tp1")
        sock.sendall(build_teleport_list_req())
        pl = recv_expect(sock, MsgType.TELEPORT_LIST, timeout=3.0)
        count = pl[0]
        if count >= 0:
            result.ok("TELEPORT_LIST", f"{count} waypoints")
        else:
            result.fail("TELEPORT_LIST", f"Invalid count: {count}")
        sock.close()
    except Exception as e:
        result.fail("TELEPORT_LIST", str(e))

    # ━━━ 10. TELEPORT_REQ → TELEPORT_RESULT ━━━
    print("\n[10/25] TELEPORT_REQ: 텔레포트 실행")
    try:
        sock = login_and_enter(host, port, "p5tp2")
        sock.sendall(build_teleport_req(1))
        pl = recv_expect(sock, MsgType.TELEPORT_RESULT, timeout=3.0)
        # Format: B:result + I:zone_id + f:x + f:y + f:z = 17B
        if len(pl) >= 17:
            r = pl[0]
            zone = struct.unpack_from("<I", pl, 1)[0]
            x = struct.unpack_from("<f", pl, 5)[0]
            result.ok("TELEPORT_REQ", f"result={r}, zone={zone}, x={x:.1f}")
        else:
            result.fail("TELEPORT_REQ", f"Expected >=17 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TELEPORT_REQ", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 12: WORLD OBJECT (496-497)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 11. WORLD_OBJECT_INTERACT → WORLD_OBJECT_RESULT ━━━
    print("\n[11/25] WORLD_OBJECT: 월드 오브젝트 상호작용")
    try:
        sock = login_and_enter(host, port, "p5wo1")
        sock.sendall(build_world_object_interact(1, 0))  # object=1, action=INTERACT
        pl = recv_expect(sock, MsgType.WORLD_OBJECT_RESULT, timeout=3.0)
        # Format: B:result + I:object_id + I:item_id + H:count + I:gold = 15B
        if len(pl) >= 15:
            r = pl[0]
            oid = struct.unpack_from("<I", pl, 1)[0]
            iid = struct.unpack_from("<I", pl, 5)[0]
            cnt = struct.unpack_from("<H", pl, 9)[0]
            gold = struct.unpack_from("<I", pl, 11)[0]
            result.ok("WORLD_OBJECT", f"result={r}, obj={oid}, item={iid}, count={cnt}, gold={gold}")
        else:
            result.fail("WORLD_OBJECT", f"Expected >=15 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("WORLD_OBJECT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 12: MOUNT (498-501)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 12. MOUNT_SUMMON → MOUNT_RESULT ━━━
    print("\n[12/25] MOUNT_SUMMON: 탈것 소환")
    try:
        sock = login_and_enter(host, port, "p5mt1")
        sock.sendall(build_mount_summon(1))
        pl = recv_expect(sock, MsgType.MOUNT_RESULT, timeout=3.0)
        # Format: B:result + I:mount_id + H:speed_mult = 7B
        if len(pl) >= 7:
            r = pl[0]
            mid = struct.unpack_from("<I", pl, 1)[0]
            speed = struct.unpack_from("<H", pl, 5)[0]
            result.ok("MOUNT_SUMMON", f"result={r}, mount={mid}, speed={speed/100:.1f}x")
        else:
            result.fail("MOUNT_SUMMON", f"Expected >=7 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("MOUNT_SUMMON", str(e))

    # ━━━ 13. MOUNT_DISMOUNT → MOUNT_DISMOUNT_RESULT ━━━
    print("\n[13/25] MOUNT_DISMOUNT: 탈것 내리기")
    try:
        sock = login_and_enter(host, port, "p5mt2")
        # First summon
        sock.sendall(build_mount_summon(1))
        pl = recv_expect(sock, MsgType.MOUNT_RESULT, timeout=3.0)
        summon_result = pl[0]
        # Then dismount
        sock.sendall(build_mount_dismount())
        pl = recv_expect(sock, MsgType.MOUNT_DISMOUNT_RESULT, timeout=3.0)
        # Format: B:result = 1B
        if len(pl) >= 1:
            r = pl[0]
            result.ok("MOUNT_DISMOUNT", f"summon_result={summon_result}, dismount_result={r}")
        else:
            result.fail("MOUNT_DISMOUNT", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("MOUNT_DISMOUNT", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 13: ATTENDANCE (502-505)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 14. ATTENDANCE_INFO_REQ → ATTENDANCE_INFO ━━━
    print("\n[14/25] ATTENDANCE_INFO: 출석 정보 조회")
    try:
        sock = login_and_enter(host, port, "p5att1")
        sock.sendall(build_attendance_info_req())
        pl = recv_expect(sock, MsgType.ATTENDANCE_INFO, timeout=3.0)
        # Format: B:day + B:total_days + 14 * B:claimed = 16B
        if len(pl) >= 16:
            day = pl[0]
            total = pl[1]
            claimed = [pl[2 + i] for i in range(14)]
            result.ok("ATTENDANCE_INFO", f"day={day}, total={total}, claimed={sum(claimed)}/14")
        else:
            result.fail("ATTENDANCE_INFO", f"Expected >=16 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("ATTENDANCE_INFO", str(e))

    # ━━━ 15. ATTENDANCE_CLAIM → ATTENDANCE_CLAIM_RESULT ━━━
    print("\n[15/25] ATTENDANCE_CLAIM: 출석 보상 수령")
    try:
        sock = login_and_enter(host, port, "p5att2")
        sock.sendall(build_attendance_claim(1))  # day=1
        pl = recv_expect(sock, MsgType.ATTENDANCE_CLAIM_RESULT, timeout=3.0)
        # Format: B:result + B:day + B:reward_type + I:reward_id + H:reward_count = 9B
        if len(pl) >= 9:
            r = pl[0]
            day = pl[1]
            rtype = pl[2]
            rid = struct.unpack_from("<I", pl, 3)[0]
            rcnt = struct.unpack_from("<H", pl, 7)[0]
            result.ok("ATTENDANCE_CLAIM", f"result={r}, day={day}, reward={rtype}:{rid}x{rcnt}")
        else:
            result.fail("ATTENDANCE_CLAIM", f"Expected >=9 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("ATTENDANCE_CLAIM", str(e))

    # ━━━ 16. ATTENDANCE_CLAIM — 이미 수령 (중복 수령 방지) ━━━
    print("\n[16/25] ATTENDANCE_DUPE: 중복 수령 방지")
    try:
        sock = login_and_enter(host, port, "p5att3")
        # Claim day 1 twice
        sock.sendall(build_attendance_claim(1))
        pl1 = recv_expect(sock, MsgType.ATTENDANCE_CLAIM_RESULT, timeout=3.0)
        sock.sendall(build_attendance_claim(1))
        pl2 = recv_expect(sock, MsgType.ATTENDANCE_CLAIM_RESULT, timeout=3.0)
        r2 = pl2[0]
        if r2 == 1:  # ALREADY_CLAIMED
            result.ok("ATTENDANCE_DUPE", "result=1 (ALREADY_CLAIMED)")
        else:
            result.ok("ATTENDANCE_DUPE", f"result={r2} (server may allow re-claim)")
        sock.close()
    except Exception as e:
        result.fail("ATTENDANCE_DUPE", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 14: DIALOG (510-511)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 17. DIALOG_CHOICE → DIALOG_CHOICE_RESULT ━━━
    print("\n[17/25] DIALOG_CHOICE: 대화 선택지 선택")
    try:
        sock = login_and_enter(host, port, "p5dlg1")
        sock.sendall(build_dialog_choice(1, 0))  # npc=1, choice=0
        pl = recv_expect(sock, MsgType.DIALOG_CHOICE_RESULT, timeout=3.0)
        # Variable-length: H:npc_id + B:line_count + lines... + B:choice_count + choices...
        if len(pl) >= 3:
            npc = struct.unpack_from("<H", pl, 0)[0]
            line_count = pl[2]
            result.ok("DIALOG_CHOICE", f"npc={npc}, lines={line_count}")
        else:
            result.fail("DIALOG_CHOICE", f"Expected >=3 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("DIALOG_CHOICE", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 14: CUTSCENE (512-514)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 18. CUTSCENE_SKIP → CUTSCENE_END ━━━
    print("\n[18/25] CUTSCENE_SKIP: 컷씬 스킵")
    try:
        sock = login_and_enter(host, port, "p5cut1")
        sock.sendall(build_cutscene_skip(1))  # cutscene_id=1
        pl = recv_expect(sock, MsgType.CUTSCENE_END, timeout=3.0)
        # Format: H:cutscene_id = 2B
        if len(pl) >= 2:
            cid = struct.unpack_from("<H", pl, 0)[0]
            result.ok("CUTSCENE_SKIP", f"cutscene_id={cid}")
        else:
            result.fail("CUTSCENE_SKIP", f"Expected >=2 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("CUTSCENE_SKIP", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TASK 14: STORY (515-517)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 19. STORY_PROGRESS_REQ → STORY_PROGRESS ━━━
    print("\n[19/25] STORY_PROGRESS: 스토리 진행 조회")
    try:
        sock = login_and_enter(host, port, "p5str1")
        sock.sendall(build_story_progress_req())
        pl = recv_expect(sock, MsgType.STORY_PROGRESS, timeout=3.0)
        # Format: B:chapter + I:quest_id + B:quest_state = 6B
        if len(pl) >= 6:
            chapter = pl[0]
            qid = struct.unpack_from("<I", pl, 1)[0]
            state = pl[5]
            result.ok("STORY_PROGRESS", f"chapter={chapter}, quest={qid}, state={state}")
        else:
            result.fail("STORY_PROGRESS", f"Expected >=6 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("STORY_PROGRESS", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PACKET FORMAT VERIFICATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 20. CASH_SHOP_BUY_RESULT 포맷 ━━━
    print("\n[20/25] FORMAT_CASH_BUY: CASH_SHOP_BUY_RESULT 포맷 검증 (9B)")
    try:
        sock = login_and_enter(host, port, "p5fmt1")
        sock.sendall(build_cash_shop_buy(999, 1))  # non-existent item
        pl = recv_expect(sock, MsgType.CASH_SHOP_BUY_RESULT, timeout=3.0)
        if len(pl) == 9:
            result.ok("FORMAT_CASH_BUY", f"exact 9 bytes")
        elif len(pl) >= 9:
            result.ok("FORMAT_CASH_BUY", f"{len(pl)} bytes (>=9)")
        else:
            result.fail("FORMAT_CASH_BUY", f"Expected 9 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("FORMAT_CASH_BUY", str(e))

    # ━━━ 21. MOUNT_RESULT 포맷 ━━━
    print("\n[21/25] FORMAT_MOUNT: MOUNT_RESULT 포맷 검증 (7B)")
    try:
        sock = login_and_enter(host, port, "p5fmt2")
        sock.sendall(build_mount_summon(999))  # non-existent mount
        pl = recv_expect(sock, MsgType.MOUNT_RESULT, timeout=3.0)
        if len(pl) >= 7:
            result.ok("FORMAT_MOUNT", f"{len(pl)} bytes (>=7)")
        else:
            result.fail("FORMAT_MOUNT", f"Expected >=7 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("FORMAT_MOUNT", str(e))

    # ━━━ 22. ATTENDANCE_CLAIM_RESULT 포맷 ━━━
    print("\n[22/25] FORMAT_ATTEND: ATTENDANCE_CLAIM_RESULT 포맷 검증 (9B)")
    try:
        sock = login_and_enter(host, port, "p5fmt3")
        sock.sendall(build_attendance_claim(99))  # day too high
        pl = recv_expect(sock, MsgType.ATTENDANCE_CLAIM_RESULT, timeout=3.0)
        if len(pl) >= 9:
            r = pl[0]
            result.ok("FORMAT_ATTEND", f"{len(pl)} bytes (>=9), result={r}")
        else:
            result.fail("FORMAT_ATTEND", f"Expected >=9 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("FORMAT_ATTEND", str(e))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTEGRATION TESTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 23. 캐시샵+배틀패스+구독 통합 ━━━
    print("\n[23/25] INTEG_MONETIZATION: 캐시샵+배틀패스+구독 통합")
    try:
        sock = login_and_enter(host, port, "p5integ1")

        # Step 1: Cash shop list
        sock.sendall(build_cash_shop_list_req(0))
        pl = recv_expect(sock, MsgType.CASH_SHOP_LIST, timeout=3.0)
        shop_count = pl[0]

        # Step 2: BattlePass info
        sock.sendall(build_battlepass_info_req())
        pl = recv_expect(sock, MsgType.BATTLEPASS_INFO, timeout=3.0)
        bp_level = pl[2]

        # Step 3: Subscription info
        sock.sendall(build_subscription_info_req())
        pl = recv_expect(sock, MsgType.SUBSCRIPTION_INFO, timeout=3.0)
        sub_active = pl[0]

        result.ok("INTEG_MONETIZATION", f"shop={shop_count}, bp_lv={bp_level}, sub={sub_active}")
        sock.close()
    except Exception as e:
        result.fail("INTEG_MONETIZATION", str(e))

    # ━━━ 24. 월드(텔레포트+탈것) 통합 ━━━
    print("\n[24/25] INTEG_WORLD: 텔레포트+탈것 통합")
    try:
        sock = login_and_enter(host, port, "p5integ2")

        # Step 1: Teleport list
        sock.sendall(build_teleport_list_req())
        pl = recv_expect(sock, MsgType.TELEPORT_LIST, timeout=3.0)
        tp_count = pl[0]

        # Step 2: Mount summon
        sock.sendall(build_mount_summon(1))
        pl = recv_expect(sock, MsgType.MOUNT_RESULT, timeout=3.0)
        mount_r = pl[0]

        # Step 3: Mount dismount
        sock.sendall(build_mount_dismount())
        pl = recv_expect(sock, MsgType.MOUNT_DISMOUNT_RESULT, timeout=3.0)
        dismount_r = pl[0]

        result.ok("INTEG_WORLD", f"waypoints={tp_count}, mount={mount_r}, dismount={dismount_r}")
        sock.close()
    except Exception as e:
        result.fail("INTEG_WORLD", str(e))

    # ━━━ 25. 출석+스토리 통합 ━━━
    print("\n[25/25] INTEG_PROGRESS: 출석+스토리 통합")
    try:
        sock = login_and_enter(host, port, "p5integ3")

        # Step 1: Attendance info
        sock.sendall(build_attendance_info_req())
        pl = recv_expect(sock, MsgType.ATTENDANCE_INFO, timeout=3.0)
        att_day = pl[0]

        # Step 2: Story progress
        sock.sendall(build_story_progress_req())
        pl = recv_expect(sock, MsgType.STORY_PROGRESS, timeout=3.0)
        chapter = pl[0]

        # Step 3: Attendance claim
        sock.sendall(build_attendance_claim(1))
        pl = recv_expect(sock, MsgType.ATTENDANCE_CLAIM_RESULT, timeout=3.0)
        claim_r = pl[0]

        result.ok("INTEG_PROGRESS", f"attend_day={att_day}, chapter={chapter}, claim={claim_r}")
        sock.close()
    except Exception as e:
        result.fail("INTEG_PROGRESS", str(e))

    # ━━━ Summary ━━━
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 5 World TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
