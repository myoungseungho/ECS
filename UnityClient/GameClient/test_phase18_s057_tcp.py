#!/usr/bin/env python3
"""
Phase 18 TCP Bridge Integration Test -- Client Side
S057 TASK 11~14 (MsgType 474-517) — CashShop/BattlePass/Event/Subscription/World/Attendance/Story

Usage:
    python test_phase18_s057_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # TASK 11: CashShop/BattlePass/Event/Subscription (474-489)
    CASH_SHOP_LIST_REQ = 474
    CASH_SHOP_LIST = 475
    CASH_SHOP_BUY = 476
    CASH_SHOP_BUY_RESULT = 477
    BATTLEPASS_INFO_REQ = 478
    BATTLEPASS_INFO = 479
    BATTLEPASS_CLAIM = 480
    BATTLEPASS_CLAIM_RESULT = 481
    EVENT_LIST_REQ = 482
    EVENT_LIST = 483
    EVENT_CLAIM = 484
    EVENT_CLAIM_RESULT = 485
    SUBSCRIPTION_INFO = 486
    SUBSCRIPTION_STATUS = 487
    SUBSCRIPTION_BUY = 488
    SUBSCRIPTION_RESULT = 489
    # TASK 12: World System (490-501)
    WEATHER_INFO_REQ = 490
    WEATHER_INFO = 491
    TELEPORT_REQ = 492
    TELEPORT_RESULT = 493
    WAYPOINT_DISCOVER = 494
    WAYPOINT_LIST = 495
    DESTROY_OBJECT = 496
    DESTROY_OBJECT_RESULT = 497
    INTERACT_OBJECT = 498
    INTERACT_OBJECT_RESULT = 499
    MOUNT_SUMMON = 500
    MOUNT_RESULT = 501
    # TASK 13: Attendance/Reset (502-509)
    LOGIN_REWARD_REQ = 502
    LOGIN_REWARD_INFO = 503
    LOGIN_REWARD_CLAIM = 504
    LOGIN_REWARD_CLAIM_RESULT = 505
    DAILY_RESET_NOTIFY = 506
    CONTENT_UNLOCK_NOTIFY = 507
    CONTENT_UNLOCK_ACK = 508
    LOGIN_REWARD_NOTIFY = 509
    # TASK 14: Story/Dialog (510-517)
    DIALOG_CHOICE = 510
    DIALOG_CHOICE_RESULT = 511
    CUTSCENE_TRIGGER = 512
    CUTSCENE_DATA = 513
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


# -- Packet Builders --

def build_login(username: str, password: str) -> bytes:
    u = username.encode("utf-8")
    p = password.encode("utf-8")
    payload = bytes([len(u)]) + u + bytes([len(p)]) + p
    return build_packet(MsgType.LOGIN, payload)


def build_char_select(char_id: int) -> bytes:
    return build_packet(MsgType.CHAR_SELECT, struct.pack("<I", char_id))


# -- Test Infrastructure --

class TestRunner:
    def __init__(self, host: str, port: int, verbose: bool):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        if self.verbose:
            print(f"  Connected to {self.host}:{self.port}")

    def login(self, username: str = "s057_test"):
        self.sock.send(build_login(username, "test"))
        recv_expect(self.sock, MsgType.LOGIN_RESULT)
        self.sock.send(build_char_select(1))
        recv_expect(self.sock, MsgType.ENTER_GAME)
        recv_all_pending(self.sock, 0.5)  # drain stat_sync etc

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def test(self, name: str, fn):
        try:
            fn()
            self.passed += 1
            print(f"  [PASS] {name}")
        except Exception as e:
            self.failed += 1
            print(f"  [FAIL] {name}: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()

    def send(self, msg_type: int, payload: bytes = b""):
        self.sock.send(build_packet(msg_type, payload))

    def expect(self, msg_type: int, timeout: float = 5.0) -> bytes:
        return recv_expect(self.sock, msg_type, timeout)


# ════════════════════════════════════════════════════════════
# TASK 11 Tests: CashShop/BattlePass/Event/Subscription
# ════════════════════════════════════════════════════════════

def test_cash_shop_list(r: TestRunner):
    """캐시상점 목록 조회 — 10종 아이템 확인"""
    def fn():
        r.send(MsgType.CASH_SHOP_LIST_REQ, bytes([0]))  # category=0 all
        payload = r.expect(MsgType.CASH_SHOP_LIST)
        count = payload[0]
        assert count >= 1, f"Expected at least 1 item, got {count}"
        if r.verbose:
            print(f"    CashShop items: {count}")
    r.test("TASK11: 캐시상점 목록 조회", fn)


def test_cash_shop_buy_fail(r: TestRunner):
    """캐시상점 구매 실패 — 크리스탈 부족"""
    def fn():
        r.send(MsgType.CASH_SHOP_BUY, struct.pack("<IB", 1, 1))  # item_id=1, count=1
        payload = r.expect(MsgType.CASH_SHOP_BUY_RESULT)
        result = payload[0]
        # 새 캐릭터는 크리스탈 0이므로 실패해야 함 (result != 0)
        assert result != 0, f"Expected buy failure, got result={result}"
    r.test("TASK11: 캐시상점 구매 실패 (크리스탈 부족)", fn)


def test_battlepass_info(r: TestRunner):
    """배틀패스 정보 조회 — 레벨/EXP/프리미엄 여부"""
    def fn():
        r.send(MsgType.BATTLEPASS_INFO_REQ)
        payload = r.expect(MsgType.BATTLEPASS_INFO)
        assert len(payload) >= 6, f"Expected >= 6 bytes, got {len(payload)}"
        level = payload[0]
        exp = struct.unpack("<H", payload[1:3])[0]
        if r.verbose:
            print(f"    BP: level={level}, exp={exp}")
    r.test("TASK11: 배틀패스 정보 조회", fn)


def test_battlepass_claim_level_not_reached(r: TestRunner):
    """배틀패스 보상 수령 실패 — 레벨 미달"""
    def fn():
        r.send(MsgType.BATTLEPASS_CLAIM, bytes([50, 0]))  # level=50 (max), track=free
        payload = r.expect(MsgType.BATTLEPASS_CLAIM_RESULT)
        result = payload[0]
        # level 50 보상은 레벨 미달로 실패해야 함
        assert result != 0, f"Expected claim failure, got result={result}"
    r.test("TASK11: 배틀패스 보상 레벨 미달", fn)


def test_event_list(r: TestRunner):
    """이벤트 목록 조회 — 3종 이벤트"""
    def fn():
        r.send(MsgType.EVENT_LIST_REQ)
        payload = r.expect(MsgType.EVENT_LIST)
        count = payload[0]
        assert count >= 1, f"Expected at least 1 event, got {count}"
        if r.verbose:
            print(f"    Events: {count}")
    r.test("TASK11: 이벤트 목록 조회", fn)


def test_event_claim(r: TestRunner):
    """이벤트 보상 수령 — Day 1 출석"""
    def fn():
        r.send(MsgType.EVENT_CLAIM, struct.pack("<BB", 1, 1))  # event_id=1, day=1
        payload = r.expect(MsgType.EVENT_CLAIM_RESULT)
        result = payload[0]
        if r.verbose:
            print(f"    Claim result={result}")
    r.test("TASK11: 이벤트 보상 수령", fn)


def test_event_claim_duplicate(r: TestRunner):
    """이벤트 보상 중복 수령 방지"""
    def fn():
        r.send(MsgType.EVENT_CLAIM, struct.pack("<BB", 1, 1))  # same event/day again
        payload = r.expect(MsgType.EVENT_CLAIM_RESULT)
        result = payload[0]
        assert result != 0, f"Expected duplicate claim failure, got result={result}"
    r.test("TASK11: 이벤트 중복 수령 방지", fn)


def test_subscription_info(r: TestRunner):
    """구독 정보 조회"""
    def fn():
        r.send(MsgType.SUBSCRIPTION_INFO)
        payload = r.expect(MsgType.SUBSCRIPTION_STATUS)
        assert len(payload) >= 5, f"Expected >= 5 bytes, got {len(payload)}"
        is_active = payload[0]
        days = struct.unpack("<H", payload[1:3])[0]
        if r.verbose:
            print(f"    Sub: active={is_active}, days={days}")
    r.test("TASK11: 구독 정보 조회", fn)


def test_subscription_buy_fail(r: TestRunner):
    """구독 구매 실패 — 크리스탈 부족"""
    def fn():
        r.send(MsgType.SUBSCRIPTION_BUY)
        payload = r.expect(MsgType.SUBSCRIPTION_RESULT)
        result = payload[0]
        assert result != 0, f"Expected buy failure, got result={result}"
    r.test("TASK11: 구독 구매 실패 (크리스탈 부족)", fn)


# ════════════════════════════════════════════════════════════
# TASK 12 Tests: World System
# ════════════════════════════════════════════════════════════

def test_weather_info(r: TestRunner):
    """날씨 정보 조회"""
    def fn():
        r.send(MsgType.WEATHER_INFO_REQ)
        payload = r.expect(MsgType.WEATHER_INFO)
        assert len(payload) >= 4, f"Expected >= 4 bytes, got {len(payload)}"
        if r.verbose:
            weather = payload[0] if len(payload) > 0 else "?"
            print(f"    Weather type={weather}")
    r.test("TASK12: 날씨 정보 조회", fn)


def test_teleport_not_discovered(r: TestRunner):
    """텔레포트 실패 — 미발견 웨이포인트"""
    def fn():
        r.send(MsgType.TELEPORT_REQ, struct.pack("<H", 999))  # waypoint_id=999
        payload = r.expect(MsgType.TELEPORT_RESULT)
        result = payload[0]
        assert result != 0, f"Expected teleport failure, got result={result}"
    r.test("TASK12: 텔레포트 미발견 웨이포인트", fn)


def test_waypoint_discover_and_teleport(r: TestRunner):
    """웨이포인트 발견 + 텔레포트"""
    def fn():
        r.send(MsgType.WAYPOINT_DISCOVER, struct.pack("<H", 1))  # discover wp 1
        payload = r.expect(MsgType.WAYPOINT_LIST)
        count = payload[0] if len(payload) > 0 else 0
        if r.verbose:
            print(f"    Waypoints after discover: {count}")
        # Now teleport to discovered waypoint
        r.send(MsgType.TELEPORT_REQ, struct.pack("<H", 1))
        payload2 = r.expect(MsgType.TELEPORT_RESULT)
        if r.verbose:
            print(f"    Teleport result={payload2[0]}")
    r.test("TASK12: 웨이포인트 발견+텔레포트", fn)


def test_destroy_object(r: TestRunner):
    """파괴 오브젝트 — 배럴 파괴"""
    def fn():
        # object_id(4) + damage(2)
        r.send(MsgType.DESTROY_OBJECT, struct.pack("<IH", 1, 100))  # barrel_id=1, damage=100
        payload = r.expect(MsgType.DESTROY_OBJECT_RESULT)
        assert len(payload) >= 1, f"Expected result, got {len(payload)} bytes"
    r.test("TASK12: 배럴 파괴", fn)


def test_interact_object(r: TestRunner):
    """보물상자 열기"""
    def fn():
        r.send(MsgType.INTERACT_OBJECT, struct.pack("<I", 1))  # chest_id=1
        payload = r.expect(MsgType.INTERACT_OBJECT_RESULT)
        assert len(payload) >= 1, f"Expected result, got {len(payload)} bytes"
    r.test("TASK12: 보물상자 열기", fn)


def test_mount_summon(r: TestRunner):
    """탈것 소환"""
    def fn():
        r.send(MsgType.MOUNT_SUMMON, bytes([1]))  # mount_id=1
        payload = r.expect(MsgType.MOUNT_RESULT)
        assert len(payload) >= 1, f"Expected result, got {len(payload)} bytes"
    r.test("TASK12: 탈것 소환", fn)


# ════════════════════════════════════════════════════════════
# TASK 13 Tests: Attendance/Reset
# ════════════════════════════════════════════════════════════

def test_login_reward_info(r: TestRunner):
    """출석보상 정보 조회"""
    def fn():
        r.send(MsgType.LOGIN_REWARD_REQ)
        payload = r.expect(MsgType.LOGIN_REWARD_INFO)
        assert len(payload) >= 2, f"Expected >= 2 bytes, got {len(payload)}"
        if r.verbose:
            day = payload[0]
            print(f"    Login reward day={day}")
    r.test("TASK13: 출석보상 정보 조회", fn)


def test_login_reward_claim(r: TestRunner):
    """출석보상 수령 + 중복방지"""
    def fn():
        r.send(MsgType.LOGIN_REWARD_CLAIM, bytes([1]))  # day=1
        payload = r.expect(MsgType.LOGIN_REWARD_CLAIM_RESULT)
        result = payload[0]
        if r.verbose:
            print(f"    Claim day1 result={result}")
        # Duplicate claim
        r.send(MsgType.LOGIN_REWARD_CLAIM, bytes([1]))
        payload2 = r.expect(MsgType.LOGIN_REWARD_CLAIM_RESULT)
        result2 = payload2[0]
        assert result2 != 0, f"Expected duplicate claim failure, got result={result2}"
    r.test("TASK13: 출석보상 수령+중복방지", fn)


def test_content_unlock_query(r: TestRunner):
    """컨텐츠 해금 조회"""
    def fn():
        r.send(MsgType.CONTENT_UNLOCK_ACK)
        # 서버는 CONTENT_UNLOCK_NOTIFY로 응답
        payload = r.expect(MsgType.CONTENT_UNLOCK_NOTIFY)
        assert len(payload) >= 1, f"Expected content unlock data, got {len(payload)} bytes"
    r.test("TASK13: 컨텐츠 해금 조회", fn)


# ════════════════════════════════════════════════════════════
# TASK 14 Tests: Story/Dialog
# ════════════════════════════════════════════════════════════

def test_dialog_choice(r: TestRunner):
    """NPC 대화 + 선택지"""
    def fn():
        # npc_id(2) + choice_index(1)
        r.send(MsgType.DIALOG_CHOICE, struct.pack("<HB", 1, 0))  # npc_id=1(장로), choice=0
        payload = r.expect(MsgType.DIALOG_CHOICE_RESULT)
        assert len(payload) >= 1, f"Expected dialog result, got {len(payload)} bytes"
        if r.verbose:
            print(f"    Dialog result: {len(payload)} bytes")
    r.test("TASK14: NPC 대화+선택지", fn)


def test_dialog_invalid_npc(r: TestRunner):
    """NPC 대화 — 잘못된 NPC"""
    def fn():
        r.send(MsgType.DIALOG_CHOICE, struct.pack("<HB", 999, 0))  # invalid npc
        payload = r.expect(MsgType.DIALOG_CHOICE_RESULT)
        # Should handle gracefully
        assert len(payload) >= 1, f"Expected response, got {len(payload)} bytes"
    r.test("TASK14: 잘못된 NPC 대화", fn)


def test_cutscene_trigger(r: TestRunner):
    """오프닝 컷씬 트리거"""
    def fn():
        r.send(MsgType.CUTSCENE_TRIGGER, struct.pack("<H", 1))  # cutscene_id=1 (opening)
        payload = r.expect(MsgType.CUTSCENE_DATA)
        assert len(payload) >= 2, f"Expected cutscene data, got {len(payload)} bytes"
        if r.verbose:
            print(f"    Cutscene data: {len(payload)} bytes")
    r.test("TASK14: 오프닝 컷씬 트리거", fn)


def test_chapter_progress(r: TestRunner):
    """챕터 진행 조회"""
    def fn():
        r.send(MsgType.STORY_PROGRESS_REQ)
        payload = r.expect(MsgType.STORY_PROGRESS)
        assert len(payload) >= 2, f"Expected progress data, got {len(payload)} bytes"
        if r.verbose:
            chapter = payload[0]
            print(f"    Chapter={chapter}")
    r.test("TASK14: 챕터 진행 조회", fn)


def test_main_quest_data(r: TestRunner):
    """메인퀘 목록 조회"""
    def fn():
        r.send(MsgType.MAIN_QUEST_DATA)
        payload = r.expect(MsgType.MAIN_QUEST_DATA)
        assert len(payload) >= 1, f"Expected quest data, got {len(payload)} bytes"
        if r.verbose:
            print(f"    MainQuest data: {len(payload)} bytes")
    r.test("TASK14: 메인퀘 목록 조회", fn)


# ════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Phase 18 S057 TCP Bridge Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 18 — S057 TASK 11~14 TCP Bridge Integration Test")
    print("=" * 60)

    r = TestRunner(args.host, args.port, args.verbose)

    try:
        r.connect()
        r.login()
    except Exception as e:
        print(f"[ERROR] Connection/Login failed: {e}")
        print("[INFO] Server must be running with _patch_s057.py loaded")
        sys.exit(1)

    print("\n── TASK 11: CashShop/BattlePass/Event/Subscription ──")
    test_cash_shop_list(r)
    test_cash_shop_buy_fail(r)
    test_battlepass_info(r)
    test_battlepass_claim_level_not_reached(r)
    test_event_list(r)
    test_event_claim(r)
    test_event_claim_duplicate(r)
    test_subscription_info(r)
    test_subscription_buy_fail(r)

    print("\n── TASK 12: World System ──")
    test_weather_info(r)
    test_teleport_not_discovered(r)
    test_waypoint_discover_and_teleport(r)
    test_destroy_object(r)
    test_interact_object(r)
    test_mount_summon(r)

    print("\n── TASK 13: Attendance/Reset ──")
    test_login_reward_info(r)
    test_login_reward_claim(r)
    test_content_unlock_query(r)

    print("\n── TASK 14: Story/Dialog ──")
    test_dialog_choice(r)
    test_dialog_invalid_npc(r)
    test_cutscene_trigger(r)
    test_chapter_progress(r)
    test_main_quest_data(r)

    r.close()

    print("\n" + "=" * 60)
    total = r.passed + r.failed
    print(f"Results: {r.passed}/{total} PASS, {r.failed} FAIL")
    print("=" * 60)

    sys.exit(0 if r.failed == 0 else 1)


if __name__ == "__main__":
    main()
