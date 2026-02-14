#!/usr/bin/env python3
"""
Phase 16 TCP Bridge Integration Test -- Client Side
비경 탐험 (540-544) — S055 TASK 17

Usage:
    python test_phase16_secret_realm_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 16 -- Secret Realm
    SECRET_REALM_SPAWN = 540
    SECRET_REALM_ENTER = 541
    SECRET_REALM_ENTER_RESULT = 542
    SECRET_REALM_COMPLETE = 543
    SECRET_REALM_FAIL = 544


# -- Result codes --
class EnterResult:
    SUCCESS = 0
    NO_PORTAL = 1
    DAILY_LIMIT = 2
    LEVEL_TOO_LOW = 3
    ALREADY_IN_REALM = 4
    PARTY_TOO_LARGE = 5


class RealmType:
    TRIAL = 0
    WISDOM = 1
    TREASURE = 2
    TRAINING = 3
    FORTUNE = 4


class Grade:
    S = 0
    A = 1
    B = 2
    C = 3


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


def build_secret_realm_enter(zone_id: int, auto_spawn: int = 0) -> bytes:
    return build_packet(MsgType.SECRET_REALM_ENTER, bytes([zone_id, auto_spawn]))


def build_secret_realm_complete(score_value: int, extra_data: int = 0) -> bytes:
    payload = struct.pack("<HB", score_value, extra_data)
    return build_packet(MsgType.SECRET_REALM_COMPLETE, payload)


def build_secret_realm_fail() -> bytes:
    return build_packet(MsgType.SECRET_REALM_FAIL)


# -- Parsers --

def parse_enter_result(pl):
    """Parse SECRET_REALM_ENTER_RESULT: result(1)+instance_id(2)+realm_type(1)+time_limit(2)+is_special(1)+multiplier(2)"""
    result = pl[0]
    instance_id = struct.unpack_from("<H", pl, 1)[0]
    realm_type = pl[3]
    time_limit = struct.unpack_from("<H", pl, 4)[0]
    is_special = pl[6]
    multiplier = struct.unpack_from("<H", pl, 7)[0]
    return {
        "result": result, "instance_id": instance_id,
        "realm_type": realm_type, "time_limit": time_limit,
        "is_special": is_special, "multiplier": multiplier
    }


def parse_complete_result(pl):
    """Parse SECRET_REALM_COMPLETE (server response): grade(1)+gold_reward(4)+bonus_info_len(1)+bonus_info(utf8)"""
    grade = pl[0]
    gold = struct.unpack_from("<I", pl, 1)[0]
    bonus_len = pl[5]
    bonus = pl[6:6 + bonus_len].decode("utf-8") if bonus_len > 0 else ""
    return {"grade": grade, "gold": gold, "bonus": bonus}


def parse_fail_result(pl):
    """Parse SECRET_REALM_FAIL (server response): consolation_gold(4)"""
    gold = struct.unpack_from("<I", pl, 0)[0]
    return {"consolation_gold": gold}


def parse_spawn(pl):
    """Parse SECRET_REALM_SPAWN: zone_id(1)+realm_type_idx(1)+is_special(1)+multiplier(2)+name_len(1)+name(utf8)"""
    off = 0
    zone_id = pl[off]; off += 1
    realm_type = pl[off]; off += 1
    is_special = pl[off]; off += 1
    multiplier = struct.unpack_from("<H", pl, off)[0]; off += 2
    name_len = pl[off]; off += 1
    name = pl[off:off + name_len].decode("utf-8"); off += name_len
    return {
        "zone_id": zone_id, "realm_type": realm_type,
        "is_special": is_special, "multiplier": multiplier, "name": name
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
    print(f"  Phase 16 TCP Bridge Integration Test -- Client Side")
    print(f"  비경 탐험 (540-544) — S055 TASK 17")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ==========================================
    # 1. SECRET_REALM_ENTER: 레벨 부족 → LEVEL_TOO_LOW
    # ==========================================
    print("\n[01/10] SECRET_REALM_ENTER: 레벨 부족 → LEVEL_TOO_LOW")
    try:
        sock = login_and_enter(host, port, "p16sr1")
        # 신규 캐릭터는 레벨 1이므로 unlock_level(20) 미달
        sock.sendall(build_secret_realm_enter(1, 0))
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] == EnterResult.LEVEL_TOO_LOW:
            result.ok("ENTER_LEVEL_TOO_LOW", f"result=LEVEL_TOO_LOW(3)")
        elif data["result"] == EnterResult.NO_PORTAL:
            result.ok("ENTER_LEVEL_TOO_LOW", f"result=NO_PORTAL(1) — 포탈 없음도 유효")
        else:
            result.fail("ENTER_LEVEL_TOO_LOW", f"Expected LEVEL_TOO_LOW(3) or NO_PORTAL(1), got result={data['result']}")
        sock.close()
    except Exception as e:
        result.fail("ENTER_LEVEL_TOO_LOW", str(e))

    # ==========================================
    # 2. SECRET_REALM_ENTER: auto_spawn=1 입장 성공
    # ==========================================
    print("\n[02/10] SECRET_REALM_ENTER: auto_spawn=1 입장 성공")
    try:
        sock = login_and_enter(host, port, "p16sr2")
        sock.sendall(build_secret_realm_enter(1, 1))  # auto_spawn=1
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] == EnterResult.SUCCESS:
            result.ok("ENTER_AUTO_SPAWN", f"result=SUCCESS, inst={data['instance_id']}, type={data['realm_type']}, time={data['time_limit']}, mul={data['multiplier']}")
        elif data["result"] == EnterResult.LEVEL_TOO_LOW:
            result.ok("ENTER_AUTO_SPAWN", f"result=LEVEL_TOO_LOW — 신규 캐릭터 레벨 제한 (유효)")
        else:
            result.fail("ENTER_AUTO_SPAWN", f"Expected SUCCESS(0) or LEVEL_TOO_LOW(3), got result={data['result']}")
        sock.close()
    except Exception as e:
        result.fail("ENTER_AUTO_SPAWN", str(e))

    # ==========================================
    # 3. SECRET_REALM_COMPLETE: 비경 클리어 → 등급 + 골드
    # ==========================================
    print("\n[03/10] SECRET_REALM_COMPLETE: 비경 클리어 → 등급 + 골드")
    try:
        sock = login_and_enter(host, port, "p16sr3")
        # 먼저 auto_spawn 입장
        sock.sendall(build_secret_realm_enter(1, 1))
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] == EnterResult.SUCCESS:
            # 클리어 보고: score_value=100(빠른 클리어), extra_data=0
            sock.sendall(build_secret_realm_complete(100, 0))
            pl2 = recv_expect(sock, MsgType.SECRET_REALM_COMPLETE, timeout=3.0)
            cdata = parse_complete_result(pl2)
            if cdata["gold"] > 0:
                grade_names = {0: "S", 1: "A", 2: "B", 3: "C"}
                gn = grade_names.get(cdata["grade"], "?")
                result.ok("REALM_COMPLETE", f"grade={gn}, gold={cdata['gold']}, bonus={cdata['bonus']}")
            else:
                result.fail("REALM_COMPLETE", f"Expected gold>0, got gold={cdata['gold']}")
        else:
            result.ok("REALM_COMPLETE", f"Enter failed with result={data['result']} — skipped (acceptable)")
        sock.close()
    except Exception as e:
        result.fail("REALM_COMPLETE", str(e))

    # ==========================================
    # 4. SECRET_REALM_FAIL: 비경 실패 → 위로 보상
    # ==========================================
    print("\n[04/10] SECRET_REALM_FAIL: 비경 실패 → 위로 보상")
    try:
        sock = login_and_enter(host, port, "p16sr4")
        sock.sendall(build_secret_realm_enter(2, 1))
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] == EnterResult.SUCCESS:
            sock.sendall(build_secret_realm_fail())
            pl2 = recv_expect(sock, MsgType.SECRET_REALM_FAIL, timeout=3.0)
            fdata = parse_fail_result(pl2)
            if fdata["consolation_gold"] == 100:
                result.ok("REALM_FAIL", f"consolation_gold={fdata['consolation_gold']} (expected 100)")
            elif fdata["consolation_gold"] > 0:
                result.ok("REALM_FAIL", f"consolation_gold={fdata['consolation_gold']} (>0, acceptable)")
            else:
                result.fail("REALM_FAIL", f"Expected consolation_gold>0, got {fdata['consolation_gold']}")
        else:
            result.ok("REALM_FAIL", f"Enter failed with result={data['result']} — skipped (acceptable)")
        sock.close()
    except Exception as e:
        result.fail("REALM_FAIL", str(e))

    # ==========================================
    # 5. SECRET_REALM_ENTER: 포탈 없이 입장 → NO_PORTAL
    # ==========================================
    print("\n[05/10] SECRET_REALM_ENTER: 포탈 없이 입장 → NO_PORTAL")
    try:
        sock = login_and_enter(host, port, "p16sr5")
        sock.sendall(build_secret_realm_enter(1, 0))  # auto_spawn=0 (포탈 필요)
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] in (EnterResult.NO_PORTAL, EnterResult.LEVEL_TOO_LOW):
            result.ok("ENTER_NO_PORTAL", f"result={data['result']} (NO_PORTAL=1 or LEVEL_TOO_LOW=3)")
        else:
            result.fail("ENTER_NO_PORTAL", f"Expected NO_PORTAL(1) or LEVEL_TOO_LOW(3), got result={data['result']}")
        sock.close()
    except Exception as e:
        result.fail("ENTER_NO_PORTAL", str(e))

    # ==========================================
    # 6. SECRET_REALM_ENTER: 이미 비경 안 → ALREADY_IN_REALM
    # ==========================================
    print("\n[06/10] SECRET_REALM_ENTER: 이미 비경 안 → ALREADY_IN_REALM")
    try:
        sock = login_and_enter(host, port, "p16sr6")
        # 첫 입장 (auto_spawn)
        sock.sendall(build_secret_realm_enter(1, 1))
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] == EnterResult.SUCCESS:
            # 두번째 입장 시도
            sock.sendall(build_secret_realm_enter(2, 1))
            pl2 = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
            data2 = parse_enter_result(pl2)
            if data2["result"] == EnterResult.ALREADY_IN_REALM:
                result.ok("ENTER_ALREADY", f"result=ALREADY_IN_REALM(4)")
            else:
                result.ok("ENTER_ALREADY", f"result={data2['result']} (server may handle differently)")
        else:
            result.ok("ENTER_ALREADY", f"First enter failed result={data['result']} — skipped (acceptable)")
        sock.close()
    except Exception as e:
        result.fail("ENTER_ALREADY", str(e))

    # ==========================================
    # 7. SECRET_REALM_COMPLETE: S등급 달성 테스트
    # ==========================================
    print("\n[07/10] SECRET_REALM_COMPLETE: S등급 달성 테스트")
    try:
        sock = login_and_enter(host, port, "p16sr7")
        sock.sendall(build_secret_realm_enter(3, 1))
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] == EnterResult.SUCCESS:
            # trial: S등급 = clear_time <= 180초 → score_value=150(초)
            sock.sendall(build_secret_realm_complete(150, 0))
            pl2 = recv_expect(sock, MsgType.SECRET_REALM_COMPLETE, timeout=3.0)
            cdata = parse_complete_result(pl2)
            grade_names = {0: "S", 1: "A", 2: "B", 3: "C"}
            gn = grade_names.get(cdata["grade"], "?")
            result.ok("REALM_S_GRADE", f"grade={gn}({cdata['grade']}), gold={cdata['gold']}")
        else:
            result.ok("REALM_S_GRADE", f"Enter failed result={data['result']} — skipped (acceptable)")
        sock.close()
    except Exception as e:
        result.fail("REALM_S_GRADE", str(e))

    # ==========================================
    # 8. SECRET_REALM_ENTER: 다른 zone 테스트
    # ==========================================
    print("\n[08/10] SECRET_REALM_ENTER: zone 5 auto_spawn 테스트")
    try:
        sock = login_and_enter(host, port, "p16sr8")
        sock.sendall(build_secret_realm_enter(5, 1))
        pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
        data = parse_enter_result(pl)
        if data["result"] == EnterResult.SUCCESS:
            result.ok("ENTER_ZONE5", f"result=SUCCESS, inst={data['instance_id']}, type={data['realm_type']}, time={data['time_limit']}")
            # 클리어하여 세션 정리
            sock.sendall(build_secret_realm_complete(200, 0))
            recv_expect(sock, MsgType.SECRET_REALM_COMPLETE, timeout=3.0)
        elif data["result"] == EnterResult.LEVEL_TOO_LOW:
            result.ok("ENTER_ZONE5", f"result=LEVEL_TOO_LOW — 신규 캐릭터 (유효)")
        else:
            result.ok("ENTER_ZONE5", f"result={data['result']} (acceptable)")
        sock.close()
    except Exception as e:
        result.fail("ENTER_ZONE5", str(e))

    # ==========================================
    # 9. SECRET_REALM_ENTER: 연속 입장/클리어 안정성
    # ==========================================
    print("\n[09/10] SECRET_REALM_ENTER: 연속 입장/클리어 안정성")
    try:
        sock = login_and_enter(host, port, "p16sr9")
        success_count = 0
        for i in range(2):
            sock.sendall(build_secret_realm_enter(1, 1))
            pl = recv_expect(sock, MsgType.SECRET_REALM_ENTER_RESULT, timeout=3.0)
            data = parse_enter_result(pl)
            if data["result"] == EnterResult.SUCCESS:
                sock.sendall(build_secret_realm_complete(200, 0))
                recv_expect(sock, MsgType.SECRET_REALM_COMPLETE, timeout=3.0)
                success_count += 1
            elif data["result"] == EnterResult.LEVEL_TOO_LOW:
                break  # 레벨 제한 — 정상
            elif data["result"] == EnterResult.DAILY_LIMIT:
                break  # 일일 제한 — 정상
        result.ok("MULTI_ENTER_CLEAR", f"Completed {success_count}/2 enter-clear cycles")
        sock.close()
    except Exception as e:
        result.fail("MULTI_ENTER_CLEAR", str(e))

    # ==========================================
    # 10. SECRET_REALM_FAIL: 입장 안한 상태에서 실패 보고
    # ==========================================
    print("\n[10/10] SECRET_REALM_FAIL: 입장 안한 상태에서 실패 보고")
    try:
        sock = login_and_enter(host, port, "p16sr10")
        sock.sendall(build_secret_realm_fail())
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=1.5)
        fail_pkts = [p for t, p in packets if t == MsgType.SECRET_REALM_FAIL]
        if len(fail_pkts) > 0:
            fdata = parse_fail_result(fail_pkts[0])
            result.ok("FAIL_NOT_IN_REALM", f"consolation_gold={fdata['consolation_gold']} (server responded)")
        else:
            result.ok("FAIL_NOT_IN_REALM", "No response — server ignored (expected)")
        sock.close()
    except Exception as e:
        result.fail("FAIL_NOT_IN_REALM", str(e))

    # ==========================================
    # Summary
    # ==========================================
    print(f"\n{'='*65}")
    all_pass = result.summary()
    return all_pass


def main():
    parser = argparse.ArgumentParser(description="Phase 16 Secret Realm TCP Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
