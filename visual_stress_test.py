"""
Visual Stress Test - 실시간 시각화 부하 테스트
================================================

콘솔에 실시간으로:
  - 게이트 로드밸런싱 분배 바
  - 존 맵 위에 봇 위치 (점으로 표시)
  - 경계선 + Ghost 영역
  - 실시간 통계

봇 프로필:
  @ Explorer       넓게 이동, 가끔 존 이동
  o Homebody       좁은 영역 배회
  * Boundary       경계선 300 근처 (Ghost 유발)
"""
import subprocess
import socket
import struct
import time
import sys
import os
import threading
import random
from pathlib import Path
from collections import defaultdict

# ━━━ 설정 ━━━
NUM_BOTS = 200            # 시각화니까 200명이면 충분
RAMP_UP_PER_SEC = 30
BOT_LIFETIME = 30
MOVE_INTERVAL = 0.4

BUILD_DIR = Path(__file__).parent / "build"
FIELD_EXE = BUILD_DIR / "FieldServer.exe"
GATE_EXE = BUILD_DIR / "GateServer.exe"

HOST = '127.0.0.1'
GATE_PORT = 8888
FIELD_PORTS = [7777, 7778]

# 맵 시각화 크기
MAP_W = 40   # 가로 칸 수
MAP_H = 20   # 세로 칸 수
WORLD_SIZE = 1000.0  # 게임 좌표 범위 0~1000

# 패킷
HEADER_SIZE = 6
MSG_MOVE = 10
MSG_MOVE_BROADCAST = 11
MSG_APPEAR = 13
MSG_DISAPPEAR = 14
MSG_CHANNEL_JOIN = 20
MSG_ZONE_ENTER = 30
MSG_LOGIN = 60
MSG_LOGIN_RESULT = 61
MSG_CHAR_SELECT = 64
MSG_ENTER_GAME = 65
MSG_GATE_ROUTE_REQ = 70
MSG_GATE_ROUTE_RESP = 71


# ━━━ 패킷 헬퍼 ━━━

def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload

def build_login(u, p):
    ub = u.encode(); pb = p.encode()
    return build_packet(MSG_LOGIN, struct.pack('B', len(ub)) + ub + struct.pack('B', len(pb)) + pb)

def try_recv(sock, timeout=1.0):
    try:
        sock.settimeout(timeout)
        hdr = b""
        while len(hdr) < HEADER_SIZE:
            c = sock.recv(HEADER_SIZE - len(hdr))
            if not c: return None, None
            hdr += c
        length, mt = struct.unpack('<IH', hdr)
        pl = b""
        plen = length - HEADER_SIZE
        while len(pl) < plen:
            c = sock.recv(plen - len(pl))
            if not c: return mt, pl
            pl += c
        return mt, pl
    except:
        return None, None

def drain(sock):
    while True:
        mt, _ = try_recv(sock, 0.05)
        if mt is None: break


# ━━━ 공유 상태 (시각화용) ━━━

class SharedState:
    def __init__(self):
        self.lock = threading.Lock()
        # 봇 위치: {bot_id: (server_port, zone_id, x, y, profile)}
        self.bots = {}
        # 통계
        self.gate_ok = 0
        self.gate_fail = 0
        self.login_ok = 0
        self.enter_ok = 0
        self.moves_sent = 0
        self.zone_changes = 0
        self.appear_count = 0
        self.disappear_count = 0
        self.bcast_count = 0
        self.errors = 0
        self.server_dist = defaultdict(int)
        self.phase = "Starting..."
        self.active_bots = 0

S = SharedState()


# ━━━ Bot AI ━━━

class BotAI:
    def __init__(self, profile, zone_id, x, y):
        self.profile = profile
        self.zone_id = zone_id
        self.x = x
        self.y = y
        self.tick = 0

    def next_move(self):
        self.tick += 1
        zone_change = None

        if self.profile == "explorer":
            self.x += random.uniform(-50, 50)
            self.y += random.uniform(-50, 50)
            self.x = max(10, min(900, self.x))
            self.y = max(10, min(900, self.y))
            if self.tick % 15 == 0 and random.random() < 0.3:
                zone_change = 2 if self.zone_id == 1 else 1
                self.zone_id = zone_change
                self.x = 500.0 if zone_change == 2 else 100.0
                self.y = 500.0 if zone_change == 2 else 100.0

        elif self.profile == "homebody":
            self.x += random.uniform(-15, 15)
            self.y += random.uniform(-15, 15)
            self.x = max(50, min(400, self.x))
            self.y = max(50, min(400, self.y))

        elif self.profile == "boundary":
            self.x = 300.0 + random.uniform(-100, 100)
            self.y = 300.0 + random.uniform(-100, 100)
            self.x = max(10, min(600, self.x))
            self.y = max(10, min(600, self.y))

        return self.x, self.y, 0.0, zone_change


# ━━━ 봇 스레드 ━━━

def bot_worker(bot_id):
    sock = None
    try:
        # Gate
        gs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(5)
        gs.connect((HOST, GATE_PORT))
        drain(gs)
        gs.sendall(build_packet(MSG_GATE_ROUTE_REQ))
        mt, pl = try_recv(gs, 3)
        gs.close()

        if mt != MSG_GATE_ROUTE_RESP or not pl or pl[0] != 0:
            with S.lock: S.gate_fail += 1; S.errors += 1
            return

        port = struct.unpack('<H', pl[1:3])[0]
        with S.lock:
            S.gate_ok += 1
            S.server_dist[port] += 1

        # Game server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HOST, port))
        drain(sock)

        # Login
        sock.sendall(build_login("hero", "pass123"))
        mt, pl = try_recv(sock, 3)
        if mt != MSG_LOGIN_RESULT or not pl or pl[0] != 0:
            with S.lock: S.errors += 1
            sock.close(); return
        with S.lock: S.login_ok += 1

        # Char select
        drain(sock)
        cid = random.choice([1, 2])
        sock.sendall(build_packet(MSG_CHAR_SELECT, struct.pack('<I', cid)))
        mt, pl = try_recv(sock, 3)
        if mt != MSG_ENTER_GAME or not pl or pl[0] != 0:
            with S.lock: S.errors += 1
            sock.close(); return

        zone = struct.unpack('<i', pl[9:13])[0]
        px = struct.unpack('<f', pl[13:17])[0]
        py = struct.unpack('<f', pl[17:21])[0]
        with S.lock:
            S.enter_ok += 1
            S.active_bots += 1

        # Channel
        ch = random.choice([1, 2, 3])
        sock.sendall(build_packet(MSG_CHANNEL_JOIN, struct.pack('<i', ch)))
        time.sleep(0.1)
        drain(sock)

        # AI profile
        roll = random.random()
        profile = "explorer" if roll < 0.4 else ("homebody" if roll < 0.7 else "boundary")
        ai = BotAI(profile, zone, px, py)

        # 위치 등록
        with S.lock:
            S.bots[bot_id] = (port, zone, px, py, profile)

        # 이동 루프
        end_time = time.time() + BOT_LIFETIME
        while time.time() < end_time:
            x, y, z, zc = ai.next_move()

            if zc is not None:
                sock.sendall(build_packet(MSG_ZONE_ENTER, struct.pack('<i', zc)))
                time.sleep(0.15)
                with S.lock: S.zone_changes += 1

            sock.sendall(build_packet(MSG_MOVE, struct.pack('<fff', x, y, z)))
            with S.lock:
                S.moves_sent += 1
                S.bots[bot_id] = (port, ai.zone_id, x, y, profile)

            # 수신 패킷 카운트
            while True:
                mt2, _ = try_recv(sock, 0.02)
                if mt2 is None: break
                with S.lock:
                    if mt2 == MSG_APPEAR: S.appear_count += 1
                    elif mt2 == MSG_DISAPPEAR: S.disappear_count += 1
                    elif mt2 == MSG_MOVE_BROADCAST: S.bcast_count += 1

            time.sleep(MOVE_INTERVAL)

    except Exception:
        with S.lock: S.errors += 1
    finally:
        with S.lock:
            S.active_bots = max(0, S.active_bots - 1)
            if bot_id in S.bots:
                del S.bots[bot_id]
        if sock:
            try: sock.close()
            except: pass


# ━━━ 시각화 렌더러 ━━━

def render_frame():
    """콘솔에 한 프레임을 그린다"""
    with S.lock:
        bots = dict(S.bots)
        gate_ok = S.gate_ok
        gate_fail = S.gate_fail
        login_ok = S.login_ok
        enter_ok = S.enter_ok
        moves = S.moves_sent
        zone_ch = S.zone_changes
        appear = S.appear_count
        disappear = S.disappear_count
        bcast = S.bcast_count
        errs = S.errors
        dist = dict(S.server_dist)
        active = S.active_bots
        phase = S.phase

    lines = []

    # 헤더
    lines.append("=" * 65)
    lines.append(f"  VISUAL STRESS TEST | {phase}")
    lines.append("=" * 65)
    lines.append("")

    # 로드밸런싱 바
    total = sum(dist.values()) or 1
    lines.append("  GATE LOAD BALANCING:")
    for p in sorted(dist.keys()):
        cnt = dist[p]
        pct = cnt / total * 100
        bar_len = int(pct / 100 * 30)
        bar = "#" * bar_len + "." * (30 - bar_len)
        lines.append(f"    Port {p}: [{bar}] {cnt:3d} ({pct:.0f}%)")
    lines.append("")

    # 서버별 존 맵
    # 서버 1 = Zone 1+2, 서버 2 = Zone 1+2 (같은 존 구조)
    for server_port in sorted(set(FIELD_PORTS)):
        server_bots = {bid: info for bid, info in bots.items() if info[0] == server_port}

        for zone_id in [1, 2]:
            zone_bots = [(info[2], info[3], info[4]) for info in server_bots.values() if info[1] == zone_id]

            # 맵 초기화
            grid = [['.' for _ in range(MAP_W)] for _ in range(MAP_H)]

            # 경계선 그리기 (x=300 → 맵의 12/40 위치)
            bx = int(300.0 / WORLD_SIZE * MAP_W)
            by = int(300.0 / WORLD_SIZE * MAP_H)
            for row in range(MAP_H):
                if 0 <= bx < MAP_W:
                    grid[row][bx] = '|'
            for col in range(MAP_W):
                if 0 <= by < MAP_H:
                    grid[by][col] = '-'

            # 봇 그리기
            for bx_, by_, prof in zone_bots:
                mx = int(bx_ / WORLD_SIZE * (MAP_W - 1))
                my = int(by_ / WORLD_SIZE * (MAP_H - 1))
                mx = max(0, min(MAP_W - 1, mx))
                my = max(0, min(MAP_H - 1, my))
                if prof == "explorer":
                    grid[my][mx] = '@'
                elif prof == "homebody":
                    grid[my][mx] = 'o'
                else:  # boundary
                    grid[my][mx] = '*'

            lines.append(f"  Server:{server_port} Zone:{zone_id} ({len(zone_bots)} bots)")
            lines.append("  +" + "-" * MAP_W + "+")
            for row in grid:
                lines.append("  |" + "".join(row) + "|")
            lines.append("  +" + "-" * MAP_W + "+")
            lines.append("")

    # 범례
    lines.append("  Legend: @ Explorer  o Homebody  * Boundary  | - = boundary(300)")
    lines.append("")

    # 실시간 통계
    lines.append("  LIVE STATS:")
    lines.append(f"    Connected: {gate_ok}/{NUM_BOTS}  |  In-Game: {enter_ok}  |  Active: {active}")
    lines.append(f"    Moves: {moves:,}  |  Zone Changes: {zone_ch}  |  Errors: {errs}")
    lines.append(f"    APPEAR: {appear:,}  |  DISAPPEAR: {disappear:,}  |  BROADCAST: {bcast:,}")
    lines.append("=" * 65)

    # 화면 클리어 + 출력
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\n".join(lines))


# ━━━ 서버 관리 ━━━

def start_field(port):
    return subprocess.Popen(
        [str(FIELD_EXE), str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

def start_gate(ports):
    return subprocess.Popen(
        [str(GATE_EXE)] + [str(p) for p in ports],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

def stop(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=3)
        except: proc.kill()


# ━━━ 메인 ━━━

if __name__ == "__main__":
    print("Starting servers...")
    fields = [start_field(p) for p in FIELD_PORTS]
    time.sleep(3.0)
    gate = start_gate(FIELD_PORTS)
    time.sleep(2.0)

    if not all(f.poll() is None for f in fields) or gate.poll() is not None:
        print("Server startup failed!")
        for f in fields: stop(f)
        stop(gate)
        sys.exit(1)

    S.phase = f"Deploying {NUM_BOTS} bots..."

    # 봇 투입
    threads = []
    for i in range(NUM_BOTS):
        t = threading.Thread(target=bot_worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
        if (i + 1) % RAMP_UP_PER_SEC == 0:
            time.sleep(1.0)
            S.phase = f"Deploying... {i+1}/{NUM_BOTS}"
            render_frame()

    S.phase = f"Running ({BOT_LIFETIME}s)..."

    # 시각화 루프
    end_time = time.time() + BOT_LIFETIME + 15
    while time.time() < end_time:
        render_frame()
        time.sleep(0.5)

        # 모든 봇 종료 확인
        with S.lock:
            if S.active_bots == 0 and S.enter_ok > 0:
                break

    S.phase = "COMPLETE"
    render_frame()

    # 봇 스레드 대기
    for t in threads:
        t.join(timeout=5)

    # 서버 종료
    stop(gate)
    for f in fields: stop(f)

    # 최종 리포트
    time.sleep(1)
    os.system('cls' if os.name == 'nt' else 'clear')

    print("=" * 65)
    print("  FINAL REPORT")
    print("=" * 65)
    print()
    print(f"  Bots deployed:    {NUM_BOTS}")
    print(f"  Gate routing:     {S.gate_ok} OK / {S.gate_fail} FAIL")
    print(f"  Entered game:     {S.enter_ok}")
    print(f"  Total moves:      {S.moves_sent:,}")
    print(f"  Zone changes:     {S.zone_changes}")
    print(f"  APPEAR events:    {S.appear_count:,}")
    print(f"  DISAPPEAR events: {S.disappear_count:,}")
    print(f"  BROADCAST events: {S.bcast_count:,}")
    print(f"  Errors:           {S.errors}")
    print()
    print("  Load Balancing:")
    total = sum(S.server_dist.values()) or 1
    for p in sorted(S.server_dist.keys()):
        cnt = S.server_dist[p]
        pct = cnt / total * 100
        print(f"    Port {p}: {cnt} ({pct:.1f}%)")
    print()

    sr = S.enter_ok / NUM_BOTS * 100 if NUM_BOTS > 0 else 0
    print(f"  Success rate:     {sr:.1f}%")
    print(f"  Throughput:       {S.moves_sent / BOT_LIFETIME:.0f} moves/sec")

    if sr >= 80:
        print()
        print("  VERDICT: PASSED")
    else:
        print()
        print("  VERDICT: NEEDS INVESTIGATION")

    print("=" * 65)
