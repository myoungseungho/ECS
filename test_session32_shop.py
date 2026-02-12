"""Session 32: NPC Shop Tests — 7 tests
NPC 상점: 구매/판매, 골드, 재고

MsgType:
  SHOP_OPEN(250)   C→S: [npc_id(4)]
  SHOP_LIST(251)   S→C: [npc_id(4) count(1) {item_id(4) price(4) stock(2)}...]
  SHOP_BUY(252)    C→S: [npc_id(4) item_id(4) count(2)]
  SHOP_SELL(253)   C→S: [slot(1) count(2)]
  SHOP_RESULT(254) S→C: [result(1) action(1) item_id(4) count(2) gold(4)]
"""
import socket, struct, time, subprocess, sys, os

PORT = 7777
HEADER = 6

# MsgType IDs
SHOP_OPEN = 250
SHOP_LIST = 251
SHOP_BUY = 252
SHOP_SELL = 253
SHOP_RESULT = 254
ITEM_ADD = 192
ITEM_ADD_RESULT = 193
INVENTORY_REQ = 190
INVENTORY_RESP = 191

# ShopResult
SR_SUCCESS = 0
SR_SHOP_NOT_FOUND = 1
SR_ITEM_NOT_FOUND = 2
SR_NOT_ENOUGH_GOLD = 3
SR_INVENTORY_FULL = 4

# ShopAction
SA_BUY = 0
SA_SELL = 1


def start_server():
    p = subprocess.Popen(
        [os.path.join("build", "FieldServer.exe"), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return p


def send(s, msg_type, payload=b""):
    length = HEADER + len(payload)
    s.sendall(struct.pack("<IH", length, msg_type) + payload)


def recv_pkt(s, timeout=2.0):
    s.settimeout(timeout)
    hdr = b""
    while len(hdr) < HEADER:
        hdr += s.recv(HEADER - len(hdr))
    length, msg_type = struct.unpack("<IH", hdr)
    payload = b""
    remaining = length - HEADER
    while len(payload) < remaining:
        payload += s.recv(remaining - len(payload))
    return msg_type, payload


def connect_and_login(username="tester"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", PORT))
    uname = username.encode()
    pw = b"pass"
    send(s, 60, bytes([len(uname)]) + uname + bytes([len(pw)]) + pw)
    recv_pkt(s)
    send(s, 62)
    _, cl = recv_pkt(s)
    char_id = struct.unpack_from("<I", cl, 1)[0] if cl[0] > 0 else 2000
    send(s, 64, struct.pack("<I", char_id))
    _, eg = recv_pkt(s)
    entity = struct.unpack_from("<Q", eg, 1)[0]
    drain(s)
    return s, entity


def drain(s, timeout=0.3):
    pkts = []
    try:
        s.settimeout(timeout)
        while True:
            pkts.append(recv_pkt(s, timeout))
    except:
        pass
    return pkts


def recv_specific(s, target_type, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            remaining = max(0.1, deadline - time.time())
            t, p = recv_pkt(s, remaining)
            if t == target_type:
                return t, p
        except:
            break
    return None, None


def parse_shop_result(payload):
    """SHOP_RESULT: result(1) action(1) item_id(4) count(2) gold(4)"""
    result = payload[0]
    action = payload[1]
    item_id = struct.unpack_from("<i", payload, 2)[0]
    count = struct.unpack_from("<h", payload, 6)[0]
    gold = struct.unpack_from("<i", payload, 8)[0]
    return result, action, item_id, count, gold


def parse_shop_list(payload):
    """SHOP_LIST: npc_id(4) count(1) {item_id(4) price(4) stock(2)}..."""
    npc_id = struct.unpack_from("<i", payload, 0)[0]
    count = payload[4]
    items = []
    for i in range(count):
        off = 5 + i * 10
        item_id = struct.unpack_from("<i", payload, off)[0]
        price = struct.unpack_from("<i", payload, off + 4)[0]
        stock = struct.unpack_from("<h", payload, off + 8)[0]
        items.append({"item_id": item_id, "price": price, "stock": stock})
    return npc_id, items


# ━━━ Tests ━━━

def test_open_shop():
    """Test 1: NPC 상점 열기 → 아이템 목록 수신"""
    s, e = connect_and_login("shop1")
    send(s, SHOP_OPEN, struct.pack("<i", 1))  # General Store
    t, p = recv_specific(s, SHOP_LIST)
    assert t == SHOP_LIST, "Should receive SHOP_LIST"
    npc_id, items = parse_shop_list(p)
    assert npc_id == 1
    assert len(items) == 4, f"General Store should have 4 items, got {len(items)}"
    assert items[0]["item_id"] == 1, f"First item should be HP Potion(1), got {items[0]['item_id']}"
    assert items[0]["price"] == 50, f"HP Potion price should be 50, got {items[0]['price']}"
    s.close()
    print(f"  PASS: General Store opened, {len(items)} items listed")


def test_open_invalid_shop():
    """Test 2: 존재하지 않는 NPC → SHOP_NOT_FOUND"""
    s, e = connect_and_login("shop2")
    send(s, SHOP_OPEN, struct.pack("<i", 999))
    t, p = recv_specific(s, SHOP_RESULT)
    assert t == SHOP_RESULT, "Should receive SHOP_RESULT"
    result, _, _, _, _ = parse_shop_result(p)
    assert result == SR_SHOP_NOT_FOUND, f"Expected SHOP_NOT_FOUND(1), got {result}"
    s.close()
    print(f"  PASS: invalid NPC returns SHOP_NOT_FOUND")


def test_buy_item():
    """Test 3: 아이템 구매 → 골드 감소 + 인벤토리 추가"""
    s, e = connect_and_login("shop3")
    # 초기 골드: 1000
    # HP Potion(1) 구매, 50골드 x 2개 = 100골드
    send(s, SHOP_BUY, struct.pack("<iih", 1, 1, 2))
    t, p = recv_specific(s, SHOP_RESULT)
    assert t == SHOP_RESULT
    result, action, item_id, count, gold = parse_shop_result(p)
    assert result == SR_SUCCESS, f"Expected SUCCESS, got {result}"
    assert action == SA_BUY, f"Expected BUY(0), got {action}"
    assert item_id == 1
    assert count == 2
    assert gold == 900, f"Expected 900 gold (1000-100), got {gold}"

    # 인벤토리 확인
    send(s, INVENTORY_REQ)
    t, p = recv_specific(s, INVENTORY_RESP)
    assert t == INVENTORY_RESP
    inv_count = p[0]
    assert inv_count >= 1, f"Should have at least 1 item in inventory"

    s.close()
    print(f"  PASS: bought 2x HP Potion, gold 1000→900")


def test_buy_not_enough_gold():
    """Test 4: 골드 부족 → NOT_ENOUGH_GOLD"""
    s, e = connect_and_login("shop4")
    # 초기 골드 1000. Steel Sword(11) = 1500골드
    send(s, SHOP_BUY, struct.pack("<iih", 2, 11, 1))  # Weapon Shop, Steel Sword
    t, p = recv_specific(s, SHOP_RESULT)
    assert t == SHOP_RESULT
    result, _, _, _, gold = parse_shop_result(p)
    assert result == SR_NOT_ENOUGH_GOLD, f"Expected NOT_ENOUGH_GOLD(3), got {result}"
    assert gold == 1000, f"Gold should remain 1000, got {gold}"
    s.close()
    print(f"  PASS: not enough gold for Steel Sword (need 1500, have 1000)")


def test_sell_item():
    """Test 5: 아이템 판매 → 골드 증가"""
    s, e = connect_and_login("shop5")
    # 먼저 HP Potion 추가 (ITEM_ADD로 테스트용)
    send(s, ITEM_ADD, struct.pack("<Ih", 1, 3))  # HP Potion x3
    t, p = recv_specific(s, ITEM_ADD_RESULT)
    slot = p[1]

    # 판매: HP Potion의 상점 가격 50, 판매가 = 50*0.4 = 20골드
    send(s, SHOP_SELL, bytes([slot]) + struct.pack("<h", 2))  # 2개 판매
    t, p = recv_specific(s, SHOP_RESULT)
    assert t == SHOP_RESULT
    result, action, item_id, count, gold = parse_shop_result(p)
    assert result == SR_SUCCESS, f"Expected SUCCESS, got {result}"
    assert action == SA_SELL, f"Expected SELL(1), got {action}"
    assert item_id == 1  # HP Potion
    assert count == 2
    # 판매가: 20 * 2 = 40골드, 초기 1000 + 40 = 1040
    assert gold == 1040, f"Expected 1040 gold, got {gold}"

    s.close()
    print(f"  PASS: sold 2x HP Potion, gold 1000→1040 (+40)")


def test_sell_empty_slot():
    """Test 6: 빈 슬롯 판매 → EMPTY_SLOT"""
    s, e = connect_and_login("shop6")
    # 빈 인벤토리에서 슬롯 0 판매 시도
    send(s, SHOP_SELL, bytes([0]) + struct.pack("<h", 1))
    t, p = recv_specific(s, SHOP_RESULT)
    assert t == SHOP_RESULT
    result, _, _, _, _ = parse_shop_result(p)
    assert result == 6, f"Expected EMPTY_SLOT(6), got {result}"  # EMPTY_SLOT = 6
    s.close()
    print(f"  PASS: selling from empty slot returns EMPTY_SLOT")


def test_buy_and_verify_inventory():
    """Test 7: 구매 후 인벤토리에 실제로 아이템 존재 확인"""
    s, e = connect_and_login("shop7")
    # Iron Sword(10) 구매, 500골드
    send(s, SHOP_BUY, struct.pack("<iih", 2, 10, 1))
    t, p = recv_specific(s, SHOP_RESULT)
    result, _, _, _, gold = parse_shop_result(p)
    assert result == SR_SUCCESS
    assert gold == 500, f"Expected 500 gold after buying Iron Sword, got {gold}"

    # 인벤토리에서 Iron Sword 확인
    send(s, INVENTORY_REQ)
    t, p = recv_specific(s, INVENTORY_RESP)
    assert t == INVENTORY_RESP
    inv_count = p[0]
    found = False
    for i in range(inv_count):
        off = 1 + i * 8  # slot(1)+item_id(4)+count(2)+equipped(1)
        iid = struct.unpack_from("<I", p, off + 1)[0]
        if iid == 10:
            found = True
            break
    assert found, "Iron Sword should be in inventory after purchase"

    s.close()
    print(f"  PASS: Iron Sword in inventory after purchase, gold=500")


# ━━━ Runner ━━━

def main():
    server = None
    if "--no-server" not in sys.argv:
        server = start_server()
        print(f"Server started (PID={server.pid})")

    tests = [
        test_open_shop,
        test_open_invalid_shop,
        test_buy_item,
        test_buy_not_enough_gold,
        test_sell_item,
        test_sell_empty_slot,
        test_buy_and_verify_inventory,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            print(f"\n{test.__doc__}")
            test()
            passed += 1
        except Exception as ex:
            failed += 1
            print(f"  FAIL: {ex}")

    print(f"\n{'='*50}")
    print(f"Session 32 Shop: {passed}/{len(tests)} passed, {failed} failed")

    if server:
        server.terminate()
        server.wait(timeout=5)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
