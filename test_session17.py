"""
Session 17: Dynamic Load Balancing Tests
- Field server auto-registers with Gate via FIELD_REGISTER
- Gate routes clients based on real-time CCU (not static counter)
- Gate detects dead servers via heartbeat timeout (6s)
- Gate skips full servers (CCU >= max_ccu)
- GATE_SERVER_LIST query for monitoring

Heartbeat interval: 2s (Field sends CCU every 2s)
Heartbeat timeout: 6s (Gate marks server TIMEOUT after 6s without heartbeat)
"""

import sys
import os
import time
import socket
import struct
import subprocess

# ━━━ Test Framework ━━━
passed = 0
failed = 0
total = 0

def run_test(name, func):
    global passed, failed, total
    total += 1
    time.sleep(0.3)
    try:
        func()
        passed += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name}: {e}")

# ━━━ Network Helpers ━━━

def recv_exact(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed")
        data += chunk
    return data

def recv_packet(sock, timeout=3.0):
    """Receive one full packet: [length(4)][type(2)][payload]"""
    sock.settimeout(timeout)
    hdr = recv_exact(sock, 6)
    length, msg_type = struct.unpack('<IH', hdr)
    payload = recv_exact(sock, length - 6) if length > 6 else b''
    return msg_type, payload

def send_packet(sock, msg_type, payload=b''):
    length = 6 + len(payload)
    hdr = struct.pack('<IH', length, msg_type)
    sock.sendall(hdr + payload)

# ━━━ Gate Protocol Helpers ━━━

def gate_route(gate_port=8888):
    """Send GATE_ROUTE_REQ, return (ip, port) or None"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', gate_port))
    try:
        send_packet(sock, 70)  # GATE_ROUTE_REQ
        msg_type, payload = recv_packet(sock)
        assert msg_type == 71, f"Expected GATE_ROUTE_RESP(71), got {msg_type}"
        result = payload[0]
        if result != 0:
            return None
        port = struct.unpack('<H', payload[1:3])[0]
        ip_len = payload[3]
        ip = payload[4:4+ip_len].decode()
        return (ip, port)
    finally:
        sock.close()

def gate_server_list(gate_port=8888):
    """Query GATE_SERVER_LIST, return list of server info dicts"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', gate_port))
    try:
        send_packet(sock, 133)  # GATE_SERVER_LIST
        msg_type, payload = recv_packet(sock)
        assert msg_type == 134, f"Expected GATE_SERVER_LIST_RESP(134), got {msg_type}"
        count = payload[0]
        servers = []
        for i in range(count):
            off = 1 + i * 11
            port = struct.unpack('<H', payload[off:off+2])[0]
            ccu = struct.unpack('<I', payload[off+2:off+6])[0]
            max_ccu = struct.unpack('<I', payload[off+6:off+10])[0]
            status = payload[off+10]
            servers.append({'port': port, 'ccu': ccu, 'max_ccu': max_ccu, 'status': status})
        return servers
    finally:
        sock.close()

def wait_for_servers(gate_port, count, timeout=8.0):
    """Poll until gate reports >= count ALIVE servers"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            servers = gate_server_list(gate_port)
            alive = [s for s in servers if s['status'] == 1]  # ALIVE=1
            if len(alive) >= count:
                return servers
        except:
            pass
        time.sleep(0.5)
    return gate_server_list(gate_port)

def wait_for_ccu(gate_port, field_port, min_ccu, timeout=8.0):
    """Poll until gate reports field_port has >= min_ccu"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            servers = gate_server_list(gate_port)
            for s in servers:
                if s['port'] == field_port and s['ccu'] >= min_ccu:
                    return True
        except:
            pass
        time.sleep(0.5)
    return False

def wait_for_status(gate_port, field_port, expected_status, timeout=10.0):
    """Poll until gate reports field_port has expected status"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            servers = gate_server_list(gate_port)
            for s in servers:
                if s['port'] == field_port and s['status'] == expected_status:
                    return True
        except:
            pass
        time.sleep(0.5)
    return False

# ━━━ Server Process Management ━━━

server_procs = []

def start_servers(field_configs, gate_port=8888):
    """
    Start Gate + Field servers.
    field_configs: list of (port, max_ccu) tuples
    """
    global server_procs
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')
    gate_exe = os.path.join(build_dir, 'GateServer.exe')
    field_exe = os.path.join(build_dir, 'FieldServer.exe')

    if not os.path.exists(gate_exe):
        print(f"ERROR: {gate_exe} not found. Build first!")
        sys.exit(1)
    if not os.path.exists(field_exe):
        print(f"ERROR: {field_exe} not found. Build first!")
        sys.exit(1)

    # Start Gate first
    gate_proc = subprocess.Popen(
        [gate_exe, str(gate_port)],
        cwd=build_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    server_procs = [gate_proc]
    time.sleep(1.0)  # Wait for gate to start

    # Start Field servers (connect to gate)
    for port, max_ccu in field_configs:
        field_proc = subprocess.Popen(
            [field_exe, str(port), str(gate_port), str(max_ccu)],
            cwd=build_dir,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        server_procs.append(field_proc)

    time.sleep(2.0)  # Wait for fields to register with gate

def stop_servers():
    global server_procs
    for p in server_procs:
        try:
            p.terminate()
            p.wait(timeout=3)
        except:
            try:
                p.kill()
            except:
                pass
    server_procs = []

# ━━━ Test 1: Field registers with Gate ━━━

def test_field_registers():
    """Field server auto-registers with Gate, appears in server list"""
    servers = gate_server_list(8888)
    assert len(servers) >= 1, f"Expected >= 1 server, got {len(servers)}"

    # Find our field server
    field = [s for s in servers if s['port'] == 7777]
    assert len(field) == 1, f"Expected field on port 7777, got {[s['port'] for s in servers]}"
    assert field[0]['status'] == 1, f"Expected ALIVE(1), got {field[0]['status']}"
    assert field[0]['max_ccu'] == 200, f"Expected max_ccu=200, got {field[0]['max_ccu']}"

# ━━━ Test 2: Route to registered server ━━━

def test_route_to_registered():
    """Gate routes client to registered field server"""
    result = gate_route(8888)
    assert result is not None, "Route should succeed"
    ip, port = result
    assert port == 7777, f"Expected port 7777, got {port}"
    assert ip == "127.0.0.1", f"Expected 127.0.0.1, got {ip}"

# ━━━ Test 3: Two servers, route to least CCU ━━━

def test_dynamic_ccu_routing():
    """With 2 fields, clients on Field1 increase CCU -> Gate routes to Field2"""
    # Wait for both servers to register
    servers = wait_for_servers(8888, 2)
    alive = [s for s in servers if s['status'] == 1]
    assert len(alive) >= 2, f"Expected 2 ALIVE servers, got {len(alive)}"

    # Connect 3 clients directly to Field1 (port 7777)
    client_socks = []
    for i in range(3):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 7777))
        sock.settimeout(3.0)
        client_socks.append(sock)

    try:
        # Wait for heartbeat to report CCU >= 3 on Field1
        assert wait_for_ccu(8888, 7777, 3), \
            f"Field1 CCU should be >= 3"

        # Route through Gate -> should go to Field2 (lower CCU)
        result = gate_route(8888)
        assert result is not None, "Route should succeed"
        _, port = result
        assert port == 7778, f"Expected route to 7778 (lower CCU), got {port}"
    finally:
        for s in client_socks:
            s.close()

# ━━━ Test 4: CCU decreases on disconnect ━━━

def test_ccu_decreases():
    """Disconnecting clients from Field1 decreases reported CCU"""
    # Connect 3 clients to Field1
    client_socks = []
    for i in range(3):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 7777))
        sock.settimeout(3.0)
        client_socks.append(sock)

    # Wait for CCU to rise
    assert wait_for_ccu(8888, 7777, 3), "CCU should rise to 3"

    # Disconnect all clients
    for s in client_socks:
        s.close()

    # Wait for CCU to drop back (next heartbeat)
    time.sleep(3.0)  # Wait for at least one heartbeat cycle

    servers = gate_server_list(8888)
    field1 = [s for s in servers if s['port'] == 7777]
    assert len(field1) == 1, "Field1 should exist"
    assert field1[0]['ccu'] < 3, f"CCU should have decreased, got {field1[0]['ccu']}"

# ━━━ Test 5: Dead server detection ━━━

def test_dead_server_detection():
    """Kill Field2 -> Gate detects timeout -> stops routing to it"""
    # Verify both servers alive
    servers = wait_for_servers(8888, 2)
    alive = [s for s in servers if s['status'] == 1]
    assert len(alive) >= 2, f"Need 2 ALIVE servers, got {len(alive)}"

    # Kill Field2 (it's the 3rd process: [gate, field1, field2])
    field2_proc = server_procs[2]
    field2_proc.terminate()
    try:
        field2_proc.wait(timeout=3)
    except:
        field2_proc.kill()

    # Wait for timeout (6s) + buffer
    assert wait_for_status(8888, 7778, 2, timeout=10.0), \
        "Field2 should be TIMEOUT(2) after heartbeat timeout"

    # Route should only go to Field1
    result = gate_route(8888)
    assert result is not None, "Route should succeed (Field1 still alive)"
    _, port = result
    assert port == 7777, f"Should route to Field1(7777), got {port}"

# ━━━ Test 6: No servers returns error ━━━

def test_no_servers_error():
    """Gate with no registered servers returns error"""
    # Start a fresh Gate with no Field servers
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')
    gate_exe = os.path.join(build_dir, 'GateServer.exe')

    gate_proc = subprocess.Popen(
        [gate_exe, '8889'],
        cwd=build_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1.0)

    try:
        result = gate_route(8889)
        assert result is None, "Should fail with no servers"

        servers = gate_server_list(8889)
        assert len(servers) == 0, f"Should have 0 servers, got {len(servers)}"
    finally:
        gate_proc.terminate()
        try:
            gate_proc.wait(timeout=3)
        except:
            gate_proc.kill()

# ━━━ Test 7: Full server is skipped ━━━

def test_full_server_skip():
    """Server at max_ccu is skipped during routing"""
    # Start fresh: Gate + Field1(max_ccu=2) + Field2(max_ccu=200)
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')
    gate_exe = os.path.join(build_dir, 'GateServer.exe')
    field_exe = os.path.join(build_dir, 'FieldServer.exe')

    procs = []
    gate_proc = subprocess.Popen(
        [gate_exe, '8890'],
        cwd=build_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    procs.append(gate_proc)
    time.sleep(1.0)

    # Field1 with max_ccu=2
    f1 = subprocess.Popen(
        [field_exe, '7780', '8890', '2'],
        cwd=build_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    procs.append(f1)

    # Field2 with max_ccu=200
    f2 = subprocess.Popen(
        [field_exe, '7781', '8890', '200'],
        cwd=build_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    procs.append(f2)
    time.sleep(2.0)

    try:
        # Wait for both to register
        servers = wait_for_servers(8890, 2)
        alive = [s for s in servers if s['status'] == 1]
        assert len(alive) >= 2, f"Need 2 servers, got {len(alive)}"

        # Fill Field1 to max (connect 2 clients)
        client_socks = []
        for i in range(2):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', 7780))
            sock.settimeout(3.0)
            client_socks.append(sock)

        # Wait for Field1 to report FULL
        assert wait_for_ccu(8890, 7780, 2), "Field1 CCU should reach 2"

        # Wait for status to be FULL(3)
        time.sleep(1.0)  # Extra heartbeat cycle
        assert wait_for_status(8890, 7780, 3, timeout=5.0), \
            "Field1 should be FULL(3)"

        # Route should go to Field2
        result = gate_route(8890)
        assert result is not None, "Route should succeed"
        _, port = result
        assert port == 7781, f"Should route to Field2(7781), got {port}"

        for s in client_socks:
            s.close()
    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=3)
            except:
                try:
                    p.kill()
                except:
                    pass

# ━━━ Run ━━━
if __name__ == '__main__':
    print("=" * 50)
    print("  Session 17: Dynamic Load Balancing Tests")
    print("=" * 50)
    print()

    # Test 6 & 7: Independent (own server instances)
    print("[1] Edge Cases (independent)")
    run_test("No servers returns error", test_no_servers_error)
    run_test("Full server is skipped", test_full_server_skip)

    # Tests 1-5: Shared server setup (Gate + 2 Fields)
    start_servers([(7777, 200), (7778, 200)], gate_port=8888)

    try:
        print()
        print("[2] Registration & Routing")
        run_test("Field registers with Gate", test_field_registers)
        run_test("Route to registered server", test_route_to_registered)

        print()
        print("[3] Dynamic CCU")
        run_test("Route to least-loaded server", test_dynamic_ccu_routing)
        run_test("CCU decreases on disconnect", test_ccu_decreases)

        print()
        print("[4] Fault Tolerance")
        run_test("Dead server detection", test_dead_server_detection)

    finally:
        stop_servers()

    print()
    print("=" * 50)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
