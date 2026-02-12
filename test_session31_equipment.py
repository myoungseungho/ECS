"""Session 31: Equipment Stat Reflection Tests — 6 tests
장비 시스템: 무기/방어구 장착 시 ATK/DEF 스탯 반영

기존 ITEM_EQUIP(196)/ITEM_UNEQUIP(197)/ITEM_EQUIP_RESULT(198) 패킷 사용.
새로 추가된 기능: 장착/해제 시 STAT_SYNC(91) 자동 전송.

아이템 목록 (InventoryComponents.h):
  10: Iron Sword   (WEAPON, ATK+15)
  11: Steel Sword  (WEAPON, ATK+30)
  20: Leather Armor (ARMOR, DEF+10)
  21: Iron Armor   (ARMOR, DEF+25)
"""
import socket, struct, time, subprocess, sys, os

PORT = 7777
HEADER = 6

# MsgType IDs
ITEM_ADD = 192
ITEM_ADD_RESULT = 193
ITEM_EQUIP = 196
ITEM_UNEQUIP = 197
ITEM_EQUIP_RESULT = 198
STAT_QUERY = 90
STAT_SYNC = 91


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
    """로그인 + 캐릭터 선택 + 게임 진입"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", PORT))
    uname = username.encode()
    pw = b"pass"
    send(s, 60, bytes([len(uname)]) + uname + bytes([len(pw)]) + pw)
    recv_pkt(s)  # LOGIN_RESULT
    send(s, 62)  # CHAR_LIST_REQ
    _, cl = recv_pkt(s)
    char_id = struct.unpack_from("<I", cl, 1)[0] if cl[0] > 0 else 2000
    send(s, 64, struct.pack("<I", char_id))  # CHAR_SELECT
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
    """특정 타입의 패킷이 올 때까지 수신"""
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


def get_stats(s):
    """STAT_QUERY → STAT_SYNC 응답에서 스탯 파싱
    STAT_SYNC: level(4) hp(4) max_hp(4) mp(4) max_mp(4) atk(4) def(4) exp(4) exp_next(4)"""
    send(s, STAT_QUERY)
    t, p = recv_specific(s, STAT_SYNC)
    assert t == STAT_SYNC, "Should receive STAT_SYNC"
    level, hp, max_hp, mp, max_mp, atk, def_, exp, exp_next = struct.unpack_from("<iiiiiiiii", p, 0)
    return {"level": level, "hp": hp, "max_hp": max_hp, "mp": mp, "max_mp": max_mp,
            "atk": atk, "def": def_, "exp": exp, "exp_next": exp_next}


def add_item(s, item_id, count=1):
    """ITEM_ADD로 아이템 추가 → ITEM_ADD_RESULT 반환"""
    send(s, ITEM_ADD, struct.pack("<Ih", item_id, count))
    t, p = recv_specific(s, ITEM_ADD_RESULT)
    assert t == ITEM_ADD_RESULT, f"Expected ITEM_ADD_RESULT, got {t}"
    result = p[0]
    slot = p[1]
    return result, slot


def equip_item(s, slot):
    """ITEM_EQUIP → ITEM_EQUIP_RESULT + STAT_SYNC 수신"""
    send(s, ITEM_EQUIP, bytes([slot]))
    # ITEM_EQUIP_RESULT 수신
    t, p = recv_specific(s, ITEM_EQUIP_RESULT)
    assert t == ITEM_EQUIP_RESULT, f"Expected ITEM_EQUIP_RESULT, got {t}"
    result = p[0]
    eq_slot = p[1]
    item_id = struct.unpack_from("<I", p, 2)[0]
    equipped = p[6]
    # STAT_SYNC도 수신해야 함
    t2, p2 = recv_specific(s, STAT_SYNC, timeout=1.0)
    stats = None
    if t2 == STAT_SYNC:
        level, hp, max_hp, mp, max_mp, atk, def_, exp, exp_next = struct.unpack_from("<iiiiiiiii", p2, 0)
        stats = {"atk": atk, "def": def_, "level": level}
    return result, item_id, equipped, stats


def unequip_item(s, slot):
    """ITEM_UNEQUIP → ITEM_EQUIP_RESULT + STAT_SYNC 수신"""
    send(s, ITEM_UNEQUIP, bytes([slot]))
    t, p = recv_specific(s, ITEM_EQUIP_RESULT)
    assert t == ITEM_EQUIP_RESULT, f"Expected ITEM_EQUIP_RESULT, got {t}"
    result = p[0]
    equipped = p[6]
    # STAT_SYNC
    t2, p2 = recv_specific(s, STAT_SYNC, timeout=1.0)
    stats = None
    if t2 == STAT_SYNC:
        level, hp, max_hp, mp, max_mp, atk, def_, exp, exp_next = struct.unpack_from("<iiiiiiiii", p2, 0)
        stats = {"atk": atk, "def": def_, "level": level}
    return result, equipped, stats


# ━━━ Test Cases ━━━

def test_equip_weapon_atk_increase():
    """Test 1: 무기 장착 → ATK 증가"""
    s, e = connect_and_login("eq1")
    base = get_stats(s)
    base_atk = base["atk"]

    # Iron Sword (id=10, ATK+15) 추가
    result, slot = add_item(s, 10)
    assert result == 0, f"Item add failed: {result}"

    # 장착
    result, item_id, equipped, stats = equip_item(s, slot)
    assert result == 0, f"Equip failed: {result}"
    assert equipped == 1, "Should be equipped"
    assert stats is not None, "Should receive STAT_SYNC after equip"
    assert stats["atk"] == base_atk + 15, f"ATK should be {base_atk}+15={base_atk+15}, got {stats['atk']}"

    s.close()
    print(f"  PASS: Iron Sword equipped, ATK {base_atk} → {stats['atk']} (+15)")


def test_equip_armor_def_increase():
    """Test 2: 방어구 장착 → DEF 증가"""
    s, e = connect_and_login("eq2")
    base = get_stats(s)
    base_def = base["def"]

    # Leather Armor (id=20, DEF+10) 추가
    result, slot = add_item(s, 20)
    assert result == 0

    result, item_id, equipped, stats = equip_item(s, slot)
    assert result == 0
    assert stats is not None
    assert stats["def"] == base_def + 10, f"DEF should be {base_def}+10={base_def+10}, got {stats['def']}"

    s.close()
    print(f"  PASS: Leather Armor equipped, DEF {base_def} → {stats['def']} (+10)")


def test_unequip_reverts_stats():
    """Test 3: 장비 해제 → 스탯 원래대로"""
    s, e = connect_and_login("eq3")
    base = get_stats(s)
    base_atk = base["atk"]

    # Steel Sword (id=11, ATK+30) 추가 + 장착
    result, slot = add_item(s, 11)
    assert result == 0
    result, _, _, stats_equipped = equip_item(s, slot)
    assert stats_equipped["atk"] == base_atk + 30

    # 해제
    result, equipped, stats_unequipped = unequip_item(s, slot)
    assert result == 0
    assert equipped == 0, "Should be unequipped"
    assert stats_unequipped is not None
    assert stats_unequipped["atk"] == base_atk, f"ATK should revert to {base_atk}, got {stats_unequipped['atk']}"

    s.close()
    print(f"  PASS: Steel Sword unequipped, ATK {base_atk+30} → {stats_unequipped['atk']} (reverted)")


def test_equip_multiple_items():
    """Test 4: 무기 + 방어구 동시 장착 → ATK+DEF 둘 다 증가"""
    s, e = connect_and_login("eq4")
    base = get_stats(s)
    base_atk = base["atk"]
    base_def = base["def"]

    # Iron Sword (ATK+15) + Iron Armor (DEF+25)
    _, sword_slot = add_item(s, 10)
    _, armor_slot = add_item(s, 21)

    # 무기 장착
    equip_item(s, sword_slot)
    # 방어구 장착
    _, _, _, stats = equip_item(s, armor_slot)

    assert stats is not None
    assert stats["atk"] == base_atk + 15, f"ATK should be {base_atk+15}, got {stats['atk']}"
    assert stats["def"] == base_def + 25, f"DEF should be {base_def+25}, got {stats['def']}"

    s.close()
    print(f"  PASS: Sword+Armor equipped, ATK +15, DEF +25")


def test_equip_non_equipment():
    """Test 5: 소모품 장착 시도 → 실패"""
    s, e = connect_and_login("eq5")

    # HP Potion (id=1, CONSUMABLE)
    result, slot = add_item(s, 1)
    assert result == 0

    # 장착 시도
    send(s, ITEM_EQUIP, bytes([slot]))
    t, p = recv_specific(s, ITEM_EQUIP_RESULT)
    assert t == ITEM_EQUIP_RESULT
    result = p[0]
    assert result == 4, f"Expected NOT_EQUIPMENT(4), got {result}"

    s.close()
    print(f"  PASS: cannot equip consumable (result=NOT_EQUIPMENT)")


def test_stat_sync_after_equip():
    """Test 6: 장착 후 STAT_QUERY로 확인해도 보너스 반영됨"""
    s, e = connect_and_login("eq6")
    base = get_stats(s)
    base_atk = base["atk"]

    # Steel Sword (ATK+30)
    _, slot = add_item(s, 11)
    equip_item(s, slot)

    # STAT_QUERY로 다시 확인
    verify = get_stats(s)
    assert verify["atk"] == base_atk + 30, f"STAT_QUERY should show ATK={base_atk+30}, got {verify['atk']}"

    s.close()
    print(f"  PASS: STAT_QUERY confirms ATK bonus after equip")


# ━━━ Runner ━━━

def main():
    server = None
    if "--no-server" not in sys.argv:
        server = start_server()
        print(f"Server started (PID={server.pid})")

    tests = [
        test_equip_weapon_atk_increase,
        test_equip_armor_def_increase,
        test_unequip_reverts_stats,
        test_equip_multiple_items,
        test_equip_non_equipment,
        test_stat_sync_after_equip,
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
    print(f"Session 31 Equipment: {passed}/{len(tests)} passed, {failed} failed")

    if server:
        server.terminate()
        server.wait(timeout=5)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
