"""Quick echo test: start server -> send ECHO packet -> verify response -> stop"""
import subprocess
import socket
import struct
import time
import sys
from pathlib import Path

EXE = Path(__file__).parent / "build" / "FieldServer.exe"
HEADER_SIZE = 6
MSG_ECHO = 1

def build_packet(msg_type, payload=b""):
    total_len = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total_len, msg_type) + payload

def recv_packet(sock):
    sock.settimeout(5)
    hdr = b""
    while len(hdr) < HEADER_SIZE:
        hdr += sock.recv(HEADER_SIZE - len(hdr))
    length, msg_type = struct.unpack('<IH', hdr)
    payload = b""
    while len(payload) < length - HEADER_SIZE:
        payload += sock.recv(length - HEADER_SIZE - len(payload))
    return msg_type, payload

print("=" * 50)
print("  Quick Echo Test (Packet Protocol)")
print("=" * 50)
print()

print("[1] Starting server...")
proc = subprocess.Popen([str(EXE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
time.sleep(3)
if proc.poll() is not None:
    print(f"Server exited immediately (code: {proc.returncode})")
    sys.exit(1)
print(f"    Server running (PID: {proc.pid})")

print("[2] Connecting...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('127.0.0.1', 7777))
    print("    Connected!")
    time.sleep(0.5)

    test_msg = b"hello ECS world!"
    print(f"[3] Sending ECHO: {test_msg.decode()}")
    sock.sendall(build_packet(MSG_ECHO, test_msg))

    rtype, rpayload = recv_packet(sock)
    print(f"[4] Received: type={rtype}, payload={rpayload.decode()}")

    if rtype == MSG_ECHO and rpayload == test_msg:
        print()
        print("  ===========================")
        print("  |  ECHO TEST PASSED!  |")
        print("  ===========================")
        result = 0
    else:
        print(f"  MISMATCH: expected type={MSG_ECHO} payload={test_msg}, got type={rtype} payload={rpayload}")
        result = 1
    sock.close()
except Exception as e:
    print(f"    Error: {e}")
    result = 1

print()
print("[5] Stopping server...")
proc.terminate()
try:
    proc.wait(timeout=3)
except:
    proc.kill()
print("    Done.")
sys.exit(result)
