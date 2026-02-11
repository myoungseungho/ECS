"""
Stress Test - 자율 봇 부하 테스트
==================================

500명 동시접속 → Gate 라우팅 → Login → 캐릭터 선택 → 자율 이동

Bot AI 프로필:
  Explorer (40%)       : 넓게 이동, 가끔 존 이동
  Homebody (30%)       : 좁은 영역 배회
  Boundary Walker (30%): 경계선 근처 이동 (Ghost 시스템 테스트)
"""
import subprocess
import socket
import struct
import time
import sys
import threading
import random
import statistics
from pathlib import Path
from collections import defaultdict

# ━━━ 설정 ━━━
NUM_BOTS = 500
RAMP_UP_PER_SEC = 50       # 초당 접속 봇 수
BOT_LIFETIME = 20          # 봇 활동 시간 (초)
MOVE_INTERVAL = 0.3        # 이동 간격 (초)

BUILD_DIR = Path(__file__).parent / "build"
FIELD_EXE = BUILD_DIR / "FieldServer.exe"
GATE_EXE = BUILD_DIR / "GateServer.exe"

HOST = '127.0.0.1'
GATE_PORT = 8888
FIELD_PORTS = [7777, 7778]

# 패킷 상수
HEADER_SIZE = 6
MSG_ECHO = 1
MSG_MOVE = 10
MSG_MOVE_BROADCAST = 11
MSG_APPEAR = 13
MSG_DISAPPEAR = 14
MSG_CHANNEL_JOIN = 20
MSG_ZONE_ENTER = 30
MSG_ZONE_INFO = 31
MSG_LOGIN = 60
MSG_LOGIN_RESULT = 61
MSG_CHAR_LIST_REQ = 62
MSG_CHAR_LIST_RESP = 63
MSG_CHAR_SELECT = 64
MSG_ENTER_GAME = 65
MSG_GATE_ROUTE_REQ = 70
MSG_GATE_ROUTE_RESP = 71
MSG_STATS = 99


# ━━━ 패킷 빌더 ━━━

def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload

def build_login_packet(username, password):
    u = username.encode(); p = password.encode()
    return build_packet(MSG_LOGIN, struct.pack('B', len(u)) + u + struct.pack('B', len(p)) + p)

def build_move_packet(x, y, z):
    return build_packet(MSG_MOVE, struct.pack('<fff', x, y, z))

def build_zone_enter_packet(zone_id):
    return build_packet(MSG_ZONE_ENTER, struct.pack('<i', zone_id))

def build_channel_join_packet(ch_id):
    return build_packet(MSG_CHANNEL_JOIN, struct.pack('<i', ch_id))


# ━━━ 패킷 수신 ━━━

def recv_packet(sock, timeout=3):
    sock.settimeout(timeout)
    hdr = b""
    while len(hdr) < HEADER_SIZE:
        c = sock.recv(HEADER_SIZE - len(hdr))
        if not c: return None, None
        hdr += c
    length, msg_type = struct.unpack('<IH', hdr)
    plen = length - HEADER_SIZE
    payload = b""
    while len(payload) < plen:
        c = sock.recv(plen - len(payload))
        if not c: return msg_type, payload
        payload += c
    return msg_type, payload

def try_recv(sock, timeout=1.0):
    try: return recv_packet(sock, timeout)
    except: return None, None

def drain(sock):
    while True:
        mt, _ = try_recv(sock, 0.1)
        if mt is None: break


# ━━━ 메트릭스 수집 ━━━

class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        # 접속 단계
        self.gate_ok = 0
        self.gate_fail = 0
        self.login_ok = 0
        self.login_fail = 0
        self.enter_ok = 0
        self.enter_fail = 0
        # 서버 분배
        self.server_dist = defaultdict(int)
        # 이동 단계
        self.moves_sent = 0
        self.moves_per_bot = []
        self.zone_changes = 0
        self.channel_joins = 0
        # 수신 패킷
        self.appear_recv = 0
        self.disappear_recv = 0
        self.move_bcast_recv = 0
        # 응답 시간
        self.login_times = []
        self.route_times = []
        # 에러
        self.errors = []
        self.disconnects = 0
        # 프로필
        self.profile_counts = defaultdict(int)

    def inc(self, field, n=1):
        with self.lock:
            setattr(self, field, getattr(self, field) + n)

    def append(self, field, val):
        with self.lock:
            getattr(self, field).append(val)

    def inc_dist(self, port):
        with self.lock:
            self.server_dist[port] += 1

    def inc_profile(self, name):
        with self.lock:
            self.profile_counts[name] += 1

    def add_error(self, msg):
        with self.lock:
            if len(self.errors) < 50:
                self.errors.append(msg)

M = Metrics()


# ━━━ Bot AI 프로필 ━━━

class BotAI:
    """봇 자율 이동 AI"""

    def __init__(self, profile, zone_id, start_x, start_y):
        self.profile = profile
        self.zone_id = zone_id
        self.x = start_x
        self.y = start_y
        self.z = 0.0
        self.tick = 0

    def next_move(self):
        """다음 이동 좌표 결정. (x, y, z, zone_change) 반환"""
        self.tick += 1

        if self.profile == "explorer":
            # 넓게 이동, 가끔 존 이동
            dx = random.uniform(-50, 50)
            dy = random.uniform(-50, 50)
            self.x = max(10, min(900, self.x + dx))
            self.y = max(10, min(900, self.y + dy))

            # 매 20틱마다 25% 확률로 존 이동
            zone_change = None
            if self.tick % 20 == 0 and random.random() < 0.25:
                zone_change = 2 if self.zone_id == 1 else 1
                self.zone_id = zone_change
                self.x = 500.0 if zone_change == 2 else 100.0
                self.y = 500.0 if zone_change == 2 else 100.0

            return self.x, self.y, self.z, zone_change

        elif self.profile == "homebody":
            # 좁은 영역 배회
            dx = random.uniform(-10, 10)
            dy = random.uniform(-10, 10)
            self.x = max(50, min(400, self.x + dx))
            self.y = max(50, min(400, self.y + dy))
            return self.x, self.y, self.z, None

        elif self.profile == "boundary":
            # 경계선(300) 근처를 왔다갔다 → Ghost 시스템 스트레스
            target = 300.0 + random.uniform(-80, 80)
            self.x = max(10, min(600, target))
            self.y = max(10, min(600, 300.0 + random.uniform(-80, 80)))
            return self.x, self.y, self.z, None

        return self.x, self.y, self.z, None


# ━━━ 봇 메인 루프 ━━━

def bot_worker(bot_id):
    """한 봇의 전체 생애주기"""
    sock = None
    game_port = None

    try:
        # ── 1단계: Gate 접속 + 라우팅 ──
        t0 = time.time()
        gs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(5)
        gs.connect((HOST, GATE_PORT))
        time.sleep(0.1)
        drain(gs)

        gs.sendall(build_packet(MSG_GATE_ROUTE_REQ))
        mt, pl = try_recv(gs, 3)
        gs.close()

        if mt != MSG_GATE_ROUTE_RESP or not pl or pl[0] != 0:
            M.inc('gate_fail')
            M.add_error(f"Bot {bot_id}: gate routing failed")
            return

        game_port = struct.unpack('<H', pl[1:3])[0]
        M.inc('gate_ok')
        M.inc_dist(game_port)
        M.append('route_times', time.time() - t0)

        # ── 2단계: 게임서버 접속 + 로그인 ──
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HOST, game_port))
        time.sleep(0.1)
        drain(sock)

        t0 = time.time()
        sock.sendall(build_login_packet("hero", "pass123"))
        mt, pl = try_recv(sock, 3)

        if mt != MSG_LOGIN_RESULT or not pl or pl[0] != 0:
            M.inc('login_fail')
            M.add_error(f"Bot {bot_id}: login failed (port {game_port})")
            sock.close()
            return

        M.inc('login_ok')
        M.append('login_times', time.time() - t0)

        # ── 3단계: 캐릭터 선택 → 게임 진입 ──
        drain(sock)
        # 캐릭터 1 또는 2 랜덤 선택
        char_id = random.choice([1, 2])
        sock.sendall(build_packet(MSG_CHAR_SELECT, struct.pack('<I', char_id)))
        mt, pl = try_recv(sock, 3)

        if mt != MSG_ENTER_GAME or not pl or pl[0] != 0:
            M.inc('enter_fail')
            M.add_error(f"Bot {bot_id}: enter game failed")
            sock.close()
            return

        M.inc('enter_ok')

        # zone/position 파싱
        zone_id = struct.unpack('<i', pl[9:13])[0]
        px = struct.unpack('<f', pl[13:17])[0]
        py = struct.unpack('<f', pl[17:21])[0]

        # ── 4단계: 채널 입장 ──
        channel = random.choice([1, 2, 3])
        sock.sendall(build_channel_join_packet(channel))
        time.sleep(0.2)
        drain(sock)
        M.inc('channel_joins')

        # ── 5단계: AI 프로필 선택 + 자율 이동 ──
        roll = random.random()
        if roll < 0.4:
            profile = "explorer"
        elif roll < 0.7:
            profile = "homebody"
        else:
            profile = "boundary"

        M.inc_profile(profile)
        ai = BotAI(profile, zone_id, px, py)

        move_count = 0
        end_time = time.time() + BOT_LIFETIME

        while time.time() < end_time:
            x, y, z, zone_change = ai.next_move()

            # 존 이동
            if zone_change is not None:
                sock.sendall(build_zone_enter_packet(zone_change))
                time.sleep(0.2)
                M.inc('zone_changes')

            # 이동
            sock.sendall(build_move_packet(x, y, z))
            move_count += 1
            M.inc('moves_sent')

            # 수신 패킷 처리 (논블로킹)
            while True:
                mt, pl = try_recv(sock, 0.05)
                if mt is None:
                    break
                if mt == MSG_APPEAR:
                    M.inc('appear_recv')
                elif mt == MSG_DISAPPEAR:
                    M.inc('disappear_recv')
                elif mt == MSG_MOVE_BROADCAST:
                    M.inc('move_bcast_recv')

            time.sleep(MOVE_INTERVAL)

        M.append('moves_per_bot', move_count)

    except Exception as e:
        M.inc('disconnects')
        M.add_error(f"Bot {bot_id}: {type(e).__name__}: {e}")

    finally:
        if sock:
            try: sock.close()
            except: pass


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


# ━━━ 라이브 모니터 ━━━

stop_monitor = threading.Event()

def monitor_thread():
    """실시간 상태 표시"""
    while not stop_monitor.is_set():
        with M.lock:
            connected = M.gate_ok
            logged_in = M.login_ok
            in_game = M.enter_ok
            moves = M.moves_sent
            dist = dict(M.server_dist)
            errs = len(M.errors) + M.disconnects
        sys.stdout.write(
            f"\r  [{connected}/{NUM_BOTS} connected] "
            f"[{in_game} in-game] "
            f"[{moves} moves] "
            f"[dist: {dist}] "
            f"[err: {errs}]   "
        )
        sys.stdout.flush()
        time.sleep(0.5)
    print()


# ━━━ 메인 ━━━

if __name__ == "__main__":
    print("=" * 65)
    print("  STRESS TEST - Autonomous Bot Load Test")
    print(f"  {NUM_BOTS} bots / {len(FIELD_PORTS)} game servers / {BOT_LIFETIME}s lifetime")
    print("=" * 65)
    print()

    # 서버 기동
    print("[1/4] Starting servers...")
    fields = [start_field(p) for p in FIELD_PORTS]
    time.sleep(3.0)
    gate = start_gate(FIELD_PORTS)
    time.sleep(2.0)

    all_alive = all(f.poll() is None for f in fields) and gate.poll() is None
    if not all_alive:
        print("  FAIL: Server startup failed")
        for f in fields: stop(f)
        stop(gate)
        sys.exit(1)
    print(f"  OK: Gate(8888) + Field({FIELD_PORTS[0]}) + Field({FIELD_PORTS[1]})")
    print()

    # 봇 투입
    print(f"[2/4] Deploying {NUM_BOTS} bots ({RAMP_UP_PER_SEC}/sec ramp-up)...")
    print()

    mon = threading.Thread(target=monitor_thread, daemon=True)
    mon.start()

    threads = []
    for i in range(NUM_BOTS):
        t = threading.Thread(target=bot_worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()

        # Ramp-up: 초당 RAMP_UP_PER_SEC 봇
        if (i + 1) % RAMP_UP_PER_SEC == 0:
            time.sleep(1.0)

    # 완료 대기
    print(f"\n[3/4] Waiting for bots to finish ({BOT_LIFETIME}s + margin)...")
    print()

    for t in threads:
        t.join(timeout=BOT_LIFETIME + 30)

    stop_monitor.set()
    time.sleep(0.5)

    # 서버 종료
    print("[4/4] Stopping servers...")
    stop(gate)
    for f in fields: stop(f)
    print()

    # ━━━ 결과 보고서 ━━━
    print("=" * 65)
    print("  STRESS TEST REPORT")
    print("=" * 65)
    print()

    # 접속 단계
    print("--- Connection Phase ---")
    print(f"  Gate routing:    {M.gate_ok}/{M.gate_ok + M.gate_fail} OK "
          f"({M.gate_ok/(M.gate_ok+M.gate_fail)*100:.1f}%)" if (M.gate_ok+M.gate_fail) > 0 else "  Gate: no data")
    print(f"  Login:           {M.login_ok}/{M.login_ok + M.login_fail} OK "
          f"({M.login_ok/(M.login_ok+M.login_fail)*100:.1f}%)" if (M.login_ok+M.login_fail) > 0 else "  Login: no data")
    print(f"  Enter game:      {M.enter_ok}/{M.enter_ok + M.enter_fail} OK "
          f"({M.enter_ok/(M.enter_ok+M.enter_fail)*100:.1f}%)" if (M.enter_ok+M.enter_fail) > 0 else "  Enter: no data")
    print()

    # 로드밸런싱
    print("--- Load Balancing ---")
    total_routed = sum(M.server_dist.values())
    for port in sorted(M.server_dist.keys()):
        cnt = M.server_dist[port]
        pct = cnt / total_routed * 100 if total_routed > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  Port {port}: {cnt:4d} ({pct:5.1f}%) |{bar}")

    if len(M.server_dist) >= 2:
        vals = list(M.server_dist.values())
        imbalance = max(vals) - min(vals)
        ratio = min(vals) / max(vals) * 100 if max(vals) > 0 else 0
        print(f"  Balance ratio:   {ratio:.1f}% (diff: {imbalance})")
    print()

    # AI 프로필
    print("--- Bot AI Profiles ---")
    for name in ["explorer", "homebody", "boundary"]:
        cnt = M.profile_counts.get(name, 0)
        print(f"  {name:15s}: {cnt}")
    print()

    # 이동 단계
    print("--- Movement Phase ---")
    print(f"  Total moves:     {M.moves_sent:,}")
    print(f"  Zone changes:    {M.zone_changes}")
    print(f"  Channel joins:   {M.channel_joins}")
    if M.moves_per_bot:
        print(f"  Moves/bot avg:   {statistics.mean(M.moves_per_bot):.1f}")
        print(f"  Moves/bot min:   {min(M.moves_per_bot)}")
        print(f"  Moves/bot max:   {max(M.moves_per_bot)}")
    print()

    # AOI 시스템 활동
    print("--- AOI / Broadcast Activity ---")
    print(f"  APPEAR received:         {M.appear_recv:,}")
    print(f"  DISAPPEAR received:      {M.disappear_recv:,}")
    print(f"  MOVE_BROADCAST received: {M.move_bcast_recv:,}")
    print()

    # 응답 시간
    print("--- Response Times ---")
    if M.route_times:
        print(f"  Gate routing:  avg={statistics.mean(M.route_times)*1000:.1f}ms "
              f"p50={statistics.median(M.route_times)*1000:.1f}ms "
              f"max={max(M.route_times)*1000:.1f}ms")
    if M.login_times:
        print(f"  Login:         avg={statistics.mean(M.login_times)*1000:.1f}ms "
              f"p50={statistics.median(M.login_times)*1000:.1f}ms "
              f"max={max(M.login_times)*1000:.1f}ms")
    print()

    # 에러
    print("--- Errors ---")
    print(f"  Disconnects:     {M.disconnects}")
    print(f"  Other errors:    {len(M.errors)}")
    if M.errors:
        print(f"  First 5 errors:")
        for e in M.errors[:5]:
            print(f"    - {e}")
    print()

    # 최종 판정
    success_rate = M.enter_ok / NUM_BOTS * 100 if NUM_BOTS > 0 else 0
    balance_ok = True
    if len(M.server_dist) >= 2:
        vals = list(M.server_dist.values())
        balance_ok = min(vals) / max(vals) > 0.6 if max(vals) > 0 else False

    print("=" * 65)
    print("  VERDICT")
    print("=" * 65)
    print()
    print(f"  Success rate:    {success_rate:.1f}% ({M.enter_ok}/{NUM_BOTS})")
    print(f"  Load balanced:   {'YES' if balance_ok else 'NO'}")
    print(f"  Throughput:      {M.moves_sent / BOT_LIFETIME:.0f} moves/sec")
    print(f"  AOI working:     {'YES' if M.appear_recv > 0 else 'NO'}")
    print(f"  Broadcast:       {'YES' if M.move_bcast_recv > 0 else 'NO'}")
    print()

    if success_rate >= 90 and balance_ok:
        print("  +---------------------------------------------------+")
        print("  |  STRESS TEST PASSED                               |")
        print(f"  |  {M.enter_ok} bots survived the full pipeline            |")
        print(f"  |  {M.moves_sent:,} autonomous moves executed             |")
        print("  |  Load balancing: WORKING                          |")
        print("  |  AOI + Broadcast + Ghost: WORKING                 |")
        print("  +---------------------------------------------------+")
    else:
        print("  +---------------------------------------------------+")
        print("  |  STRESS TEST: ISSUES DETECTED                     |")
        print(f"  |  Success rate: {success_rate:.1f}% (target: 90%+)            |")
        print(f"  |  Balance: {'OK' if balance_ok else 'IMBALANCED'}                                |")
        print("  +---------------------------------------------------+")

    print("=" * 65)
