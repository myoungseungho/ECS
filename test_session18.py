"""
Session 18: Message Bus (Pub/Sub) Tests
- Servers register with central Message Bus
- Subscribe/unsubscribe to topics
- Published messages routed to all subscribers
- Publisher doesn't receive own messages (no self-echo)
- Priority-based message ordering (CRITICAL > HIGH > NORMAL > LOW)
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

def try_recv_packet(sock, timeout=0.5):
    """Try to receive, return None on timeout"""
    try:
        return recv_packet(sock, timeout)
    except (socket.timeout, ConnectionError, OSError):
        return None

# ━━━ Bus Protocol Constants ━━━

BUS_REGISTER     = 140
BUS_REGISTER_ACK = 141
BUS_SUBSCRIBE    = 142
BUS_SUB_ACK      = 143
BUS_UNSUBSCRIBE  = 144
BUS_PUBLISH      = 145
BUS_MESSAGE      = 146

# ━━━ Bus Protocol Helpers ━━━

def bus_connect_and_register(port, name):
    """Connect to bus and register. Returns (sock, server_id)"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', port))

    name_bytes = name.encode()
    payload = struct.pack('B', len(name_bytes)) + name_bytes
    send_packet(sock, BUS_REGISTER, payload)

    msg_type, resp = recv_packet(sock)
    assert msg_type == BUS_REGISTER_ACK, f"Expected BUS_REGISTER_ACK({BUS_REGISTER_ACK}), got {msg_type}"
    result = resp[0]
    assert result == 0, f"Register failed: result={result}"
    server_id = struct.unpack('<I', resp[1:5])[0]

    return sock, server_id

def bus_subscribe(sock, topic):
    """Subscribe to a topic, wait for ACK"""
    topic_bytes = topic.encode()
    payload = struct.pack('B', len(topic_bytes)) + topic_bytes
    send_packet(sock, BUS_SUBSCRIBE, payload)

    msg_type, resp = recv_packet(sock)
    assert msg_type == BUS_SUB_ACK, f"Expected BUS_SUB_ACK({BUS_SUB_ACK}), got {msg_type}"
    assert resp[0] == 0, "Subscribe failed"

def bus_unsubscribe(sock, topic):
    """Unsubscribe from a topic (no ACK)"""
    topic_bytes = topic.encode()
    payload = struct.pack('B', len(topic_bytes)) + topic_bytes
    send_packet(sock, BUS_UNSUBSCRIBE, payload)

def bus_publish(sock, topic, data, priority=1):
    """Publish message to topic"""
    topic_bytes = topic.encode()
    payload = struct.pack('B', priority)
    payload += struct.pack('B', len(topic_bytes)) + topic_bytes
    payload += struct.pack('<H', len(data)) + data
    send_packet(sock, BUS_PUBLISH, payload)

def parse_bus_message(payload):
    """Parse BUS_MESSAGE payload -> (priority, sender_id, topic, data)"""
    off = 0
    priority = payload[off]; off += 1
    sender_id = struct.unpack('<I', payload[off:off+4])[0]; off += 4
    topic_len = payload[off]; off += 1
    topic = payload[off:off+topic_len].decode(); off += topic_len
    data_len = struct.unpack('<H', payload[off:off+2])[0]; off += 2
    data = payload[off:off+data_len]
    return priority, sender_id, topic, data

# ━━━ Server Process Management ━━━

bus_proc = None

def start_bus(port=9999):
    global bus_proc
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')
    bus_exe = os.path.join(build_dir, 'BusServer.exe')

    if not os.path.exists(bus_exe):
        print(f"ERROR: {bus_exe} not found. Build first!")
        sys.exit(1)

    bus_proc = subprocess.Popen(
        [bus_exe, str(port)],
        cwd=build_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1.0)

def stop_bus():
    global bus_proc
    if bus_proc:
        try:
            bus_proc.terminate()
            bus_proc.wait(timeout=3)
        except:
            try:
                bus_proc.kill()
            except:
                pass
        bus_proc = None

# ━━━ Test 1: Server registers with bus ━━━

def test_register():
    """Two servers register, get unique IDs"""
    sock1, id1 = bus_connect_and_register(9999, "GameServer1")
    sock2, id2 = bus_connect_and_register(9999, "GameServer2")
    try:
        assert id1 > 0, f"Expected positive server_id, got {id1}"
        assert id2 > 0, f"Expected positive server_id, got {id2}"
        assert id1 != id2, f"IDs should be unique: {id1} vs {id2}"
    finally:
        sock1.close()
        sock2.close()

# ━━━ Test 2: Subscribe to topic ━━━

def test_subscribe():
    """Server subscribes to topic and gets ACK"""
    sock, _ = bus_connect_and_register(9999, "SubTest")
    try:
        bus_subscribe(sock, "party")
        # If we reach here, subscribe succeeded
    finally:
        sock.close()

# ━━━ Test 3: Publish delivers to subscriber ━━━

def test_publish_deliver():
    """Published message is delivered to subscriber on same topic"""
    sock_a, id_a = bus_connect_and_register(9999, "Publisher")
    sock_b, id_b = bus_connect_and_register(9999, "Subscriber")

    try:
        # B subscribes to "party"
        bus_subscribe(sock_b, "party")

        # A publishes to "party"
        test_data = b"hello_party"
        bus_publish(sock_a, "party", test_data, priority=1)

        # B should receive the message
        time.sleep(0.2)
        msg_type, payload = recv_packet(sock_b, timeout=2.0)
        assert msg_type == BUS_MESSAGE, f"Expected BUS_MESSAGE({BUS_MESSAGE}), got {msg_type}"

        priority, sender_id, topic, data = parse_bus_message(payload)
        assert topic == "party", f"Expected topic 'party', got '{topic}'"
        assert sender_id == id_a, f"Expected sender {id_a}, got {sender_id}"
        assert data == test_data, f"Expected '{test_data}', got '{data}'"
    finally:
        sock_a.close()
        sock_b.close()

# ━━━ Test 4: Multiple subscribers receive ━━━

def test_multiple_subscribers():
    """Multiple subscribers all receive the published message"""
    sock_a, id_a = bus_connect_and_register(9999, "WorldPub")
    sock_b, id_b = bus_connect_and_register(9999, "WorldSub1")
    sock_c, id_c = bus_connect_and_register(9999, "WorldSub2")

    try:
        # B and C subscribe to "world"
        bus_subscribe(sock_b, "world")
        bus_subscribe(sock_c, "world")

        # A publishes to "world"
        test_data = b"world_event_123"
        bus_publish(sock_a, "world", test_data)

        time.sleep(0.2)

        # Both B and C should receive
        msg_b_type, msg_b_payload = recv_packet(sock_b, timeout=2.0)
        assert msg_b_type == BUS_MESSAGE
        _, _, topic_b, data_b = parse_bus_message(msg_b_payload)
        assert topic_b == "world" and data_b == test_data, \
            f"B got topic='{topic_b}', data='{data_b}'"

        msg_c_type, msg_c_payload = recv_packet(sock_c, timeout=2.0)
        assert msg_c_type == BUS_MESSAGE
        _, _, topic_c, data_c = parse_bus_message(msg_c_payload)
        assert topic_c == "world" and data_c == test_data, \
            f"C got topic='{topic_c}', data='{data_c}'"
    finally:
        sock_a.close()
        sock_b.close()
        sock_c.close()

# ━━━ Test 5: Unsubscribe stops delivery ━━━

def test_unsubscribe():
    """Unsubscribed server no longer receives messages"""
    sock_a, _ = bus_connect_and_register(9999, "UnsubPub")
    sock_b, _ = bus_connect_and_register(9999, "UnsubTarget")

    try:
        # B subscribes then unsubscribes
        bus_subscribe(sock_b, "alerts")
        time.sleep(0.1)
        bus_unsubscribe(sock_b, "alerts")
        time.sleep(0.1)

        # A publishes - B should NOT receive
        bus_publish(sock_a, "alerts", b"should_not_arrive")
        time.sleep(0.3)

        result = try_recv_packet(sock_b, timeout=0.5)
        assert result is None, "Should not receive after unsubscribe"
    finally:
        sock_a.close()
        sock_b.close()

# ━━━ Test 6: No self-echo ━━━

def test_no_self_echo():
    """Publisher doesn't receive own message even if subscribed to same topic"""
    sock_a, _ = bus_connect_and_register(9999, "SelfEchoTest")

    try:
        # A subscribes to topic and publishes to it
        bus_subscribe(sock_a, "echo_test")
        time.sleep(0.1)

        bus_publish(sock_a, "echo_test", b"self_msg")
        time.sleep(0.3)

        result = try_recv_packet(sock_a, timeout=0.5)
        assert result is None, "Should not receive own message"
    finally:
        sock_a.close()

# ━━━ Test 7: Priority ordering ━━━

def test_priority_ordering():
    """Higher priority messages delivered before lower priority"""
    sock_pub, _ = bus_connect_and_register(9999, "PriPub")
    sock_sub, _ = bus_connect_and_register(9999, "PriSub")

    try:
        bus_subscribe(sock_sub, "pri_test")
        time.sleep(0.1)

        # Send LOW(0) then CRITICAL(3) rapidly
        # Both should be enqueued in same tick, priority queue sorts them
        bus_publish(sock_pub, "pri_test", b"low_msg", priority=0)
        bus_publish(sock_pub, "pri_test", b"critical_msg", priority=3)

        time.sleep(0.3)

        # Should receive CRITICAL first
        msg1_type, msg1_payload = recv_packet(sock_sub, timeout=2.0)
        assert msg1_type == BUS_MESSAGE
        pri1, _, _, data1 = parse_bus_message(msg1_payload)

        msg2_type, msg2_payload = recv_packet(sock_sub, timeout=2.0)
        assert msg2_type == BUS_MESSAGE
        pri2, _, _, data2 = parse_bus_message(msg2_payload)

        assert pri1 >= pri2, f"Expected higher priority first: got pri={pri1} then pri={pri2}"
        assert data1 == b"critical_msg", f"Expected critical_msg first, got {data1}"
        assert data2 == b"low_msg", f"Expected low_msg second, got {data2}"
    finally:
        sock_pub.close()
        sock_sub.close()

# ━━━ Run ━━━
if __name__ == '__main__':
    print("=" * 50)
    print("  Session 18: Message Bus (Pub/Sub) Tests")
    print("=" * 50)
    print()

    start_bus(9999)

    try:
        print("[1] Registration")
        run_test("Server registers with bus", test_register)
        run_test("Subscribe to topic", test_subscribe)

        print()
        print("[2] Message Routing")
        run_test("Publish delivers to subscriber", test_publish_deliver)
        run_test("Multiple subscribers receive", test_multiple_subscribers)

        print()
        print("[3] Subscription Management")
        run_test("Unsubscribe stops delivery", test_unsubscribe)
        run_test("No self-echo", test_no_self_echo)

        print()
        print("[4] Priority")
        run_test("Priority ordering", test_priority_ordering)
    finally:
        stop_bus()

    print()
    print("=" * 50)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
