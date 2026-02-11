"""
Web Visual Stress Test
======================
실제 C++ 서버에 봇을 연결하고, 브라우저에서 실시간 시각화

실행: python web_stress_test.py
브라우저: http://localhost:9000 자동 오픈
"""
import subprocess
import socket
import struct
import time
import sys
import os
import json
import threading
import random
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict

# ━━━ 설정 ━━━
NUM_BOTS = 200
RAMP_UP_PER_SEC = 30
BOT_LIFETIME = 40
MOVE_INTERVAL = 0.4
WEB_PORT = 9000

BUILD_DIR = Path(__file__).parent / "build"
HTML_FILE = Path(__file__).parent / "web_visual.html"
FIELD_EXE = BUILD_DIR / "FieldServer.exe"
GATE_EXE = BUILD_DIR / "GateServer.exe"

HOST = '127.0.0.1'
GATE_PORT = 8888
FIELD_PORTS = [7777, 7778]

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

def bpkt(mt, pl=b""):
    tl = HEADER_SIZE + len(pl)
    return struct.pack('<IH', tl, mt) + pl

def blogin(u, p):
    ub, pb = u.encode(), p.encode()
    return bpkt(MSG_LOGIN, struct.pack('B', len(ub)) + ub + struct.pack('B', len(pb)) + pb)

def trecv(sock, to=1.0):
    try:
        sock.settimeout(to)
        hdr = b""
        while len(hdr) < HEADER_SIZE:
            c = sock.recv(HEADER_SIZE - len(hdr))
            if not c: return None, None
            hdr += c
        ln, mt = struct.unpack('<IH', hdr)
        pl = b""
        pn = ln - HEADER_SIZE
        while len(pl) < pn:
            c = sock.recv(pn - len(pl))
            if not c: return mt, pl
            pl += c
        return mt, pl
    except:
        return None, None

def drain(s):
    while True:
        mt, _ = trecv(s, 0.05)
        if mt is None: break


# ━━━ 공유 상태 ━━━

class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.bots = {}
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
        self.active_bots = 0
        self.server_dist = defaultdict(int)
        self.phase = "Starting servers..."

    def to_json(self):
        with self.lock:
            bots_list = [
                {"id": bid, "port": info[0], "zone": info[1],
                 "x": round(info[2], 1), "y": round(info[3], 1), "profile": info[4]}
                for bid, info in self.bots.items()
            ]
            return {
                "bots": bots_list,
                "stats": {
                    "gate_ok": self.gate_ok,
                    "gate_fail": self.gate_fail,
                    "login_ok": self.login_ok,
                    "enter_ok": self.enter_ok,
                    "moves_sent": self.moves_sent,
                    "zone_changes": self.zone_changes,
                    "appear_count": self.appear_count,
                    "disappear_count": self.disappear_count,
                    "bcast_count": self.bcast_count,
                    "errors": self.errors,
                    "active_bots": self.active_bots,
                    "phase": self.phase,
                },
                "server_dist": dict(self.server_dist),
            }

S = State()


# ━━━ HTTP 서버 ━━━

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(str(HTML_FILE), 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/api/state':
            data = json.dumps(S.to_json()).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 조용히


# ━━━ Bot AI ━━━

class BotAI:
    def __init__(self, profile, zone, x, y):
        self.profile = profile
        self.zone = zone
        self.x, self.y = x, y
        self.tick = 0

    def step(self):
        self.tick += 1
        zc = None

        if self.profile == "explorer":
            self.x += random.uniform(-50, 50)
            self.y += random.uniform(-50, 50)
            self.x = max(10, min(900, self.x))
            self.y = max(10, min(900, self.y))
            if self.tick % 15 == 0 and random.random() < 0.3:
                zc = 2 if self.zone == 1 else 1
                self.zone = zc
                self.x = 500 if zc == 2 else 100
                self.y = 500 if zc == 2 else 100

        elif self.profile == "homebody":
            self.x += random.uniform(-15, 15)
            self.y += random.uniform(-15, 15)
            self.x = max(50, min(400, self.x))
            self.y = max(50, min(400, self.y))

        elif self.profile == "boundary":
            self.x = 300 + random.uniform(-100, 100)
            self.y = 300 + random.uniform(-100, 100)
            self.x = max(10, min(600, self.x))
            self.y = max(10, min(600, self.y))

        return self.x, self.y, 0.0, zc


# ━━━ 봇 워커 ━━━

def bot_worker(bid):
    sock = None
    try:
        # Gate
        gs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(5)
        gs.connect((HOST, GATE_PORT))
        drain(gs)
        gs.sendall(bpkt(MSG_GATE_ROUTE_REQ))
        mt, pl = trecv(gs, 3)
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
        sock.sendall(blogin("hero", "pass123"))
        mt, pl = trecv(sock, 3)
        if mt != MSG_LOGIN_RESULT or not pl or pl[0] != 0:
            with S.lock: S.errors += 1
            sock.close(); return
        with S.lock: S.login_ok += 1

        # Char select
        drain(sock)
        cid = random.choice([1, 2])
        sock.sendall(bpkt(MSG_CHAR_SELECT, struct.pack('<I', cid)))
        mt, pl = trecv(sock, 3)
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
        sock.sendall(bpkt(MSG_CHANNEL_JOIN, struct.pack('<i', ch)))
        time.sleep(0.1)
        drain(sock)

        # AI
        r = random.random()
        prof = "explorer" if r < 0.4 else ("homebody" if r < 0.7 else "boundary")
        ai = BotAI(prof, zone, px, py)

        with S.lock:
            S.bots[bid] = (port, zone, px, py, prof)

        # Move loop
        end = time.time() + BOT_LIFETIME
        while time.time() < end:
            x, y, z, zc = ai.step()

            if zc is not None:
                sock.sendall(bpkt(MSG_ZONE_ENTER, struct.pack('<i', zc)))
                time.sleep(0.15)
                with S.lock: S.zone_changes += 1

            sock.sendall(bpkt(MSG_MOVE, struct.pack('<fff', x, y, z)))
            with S.lock:
                S.moves_sent += 1
                S.bots[bid] = (port, ai.zone, x, y, prof)

            # Drain received
            while True:
                m2, _ = trecv(sock, 0.02)
                if m2 is None: break
                with S.lock:
                    if m2 == MSG_APPEAR: S.appear_count += 1
                    elif m2 == MSG_DISAPPEAR: S.disappear_count += 1
                    elif m2 == MSG_MOVE_BROADCAST: S.bcast_count += 1

            time.sleep(MOVE_INTERVAL)

    except Exception:
        with S.lock: S.errors += 1
    finally:
        with S.lock:
            S.active_bots = max(0, S.active_bots - 1)
            if bid in S.bots:
                del S.bots[bid]
        if sock:
            try: sock.close()
            except: pass


# ━━━ 서버 관리 ━━━

def start_field(p):
    return subprocess.Popen(
        [str(FIELD_EXE), str(p)],
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
    print("=" * 55)
    print("  Web Visual Stress Test")
    print(f"  {NUM_BOTS} bots / {len(FIELD_PORTS)} servers / {BOT_LIFETIME}s")
    print("=" * 55)
    print()

    # 1. 서버 시작
    print("[1] Starting C++ servers...")
    fields = [start_field(p) for p in FIELD_PORTS]
    time.sleep(3)
    gate = start_gate(FIELD_PORTS)
    time.sleep(2)

    if not all(f.poll() is None for f in fields) or gate.poll() is not None:
        print("  Server startup FAILED!")
        for f in fields: stop(f)
        stop(gate)
        sys.exit(1)
    print("  OK: Gate(8888) + Field(7777) + Field(7778)")

    # 2. 웹 서버 시작
    print(f"[2] Starting web server on http://localhost:{WEB_PORT}")
    httpd = HTTPServer(('0.0.0.0', WEB_PORT), Handler)
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()

    # 3. 브라우저 오픈
    webbrowser.open(f'http://localhost:{WEB_PORT}')
    print(f"  Browser opened: http://localhost:{WEB_PORT}")
    print()

    # 4. 봇 투입
    print(f"[3] Deploying {NUM_BOTS} bots...")
    S.phase = f"Deploying {NUM_BOTS} bots..."

    threads = []
    for i in range(NUM_BOTS):
        t = threading.Thread(target=bot_worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
        if (i + 1) % RAMP_UP_PER_SEC == 0:
            time.sleep(1.0)
            S.phase = f"Deploying... {i+1}/{NUM_BOTS}"
            print(f"  {i+1}/{NUM_BOTS} deployed")

    S.phase = f"Running - {NUM_BOTS} bots active ({BOT_LIFETIME}s)"
    print(f"\n[4] All bots deployed. Running for {BOT_LIFETIME}s...")
    print("    Watch the browser!")
    print()

    # 5. 대기
    for t in threads:
        t.join(timeout=BOT_LIFETIME + 30)

    S.phase = "COMPLETE"
    time.sleep(3)  # 마지막 프레임 볼 시간

    # 6. 정리
    print("[5] Stopping servers...")
    httpd.shutdown()
    stop(gate)
    for f in fields: stop(f)

    # 7. 최종 리포트
    print()
    print("=" * 55)
    print("  FINAL REPORT")
    print("=" * 55)
    print(f"  Gate routing:     {S.gate_ok} OK / {S.gate_fail} FAIL")
    print(f"  Entered game:     {S.enter_ok}")
    print(f"  Total moves:      {S.moves_sent:,}")
    print(f"  Zone changes:     {S.zone_changes}")
    print(f"  APPEAR:           {S.appear_count:,}")
    print(f"  DISAPPEAR:        {S.disappear_count:,}")
    print(f"  BROADCAST:        {S.bcast_count:,}")
    print(f"  Errors:           {S.errors}")
    print()
    total = sum(S.server_dist.values()) or 1
    for p in sorted(S.server_dist.keys()):
        c = S.server_dist[p]
        print(f"  Port {p}: {c} ({c/total*100:.1f}%)")
    print()
    sr = S.enter_ok / NUM_BOTS * 100 if NUM_BOTS > 0 else 0
    print(f"  Success: {sr:.1f}% | Throughput: {S.moves_sent/BOT_LIFETIME:.0f} moves/sec")
    print("=" * 55)
