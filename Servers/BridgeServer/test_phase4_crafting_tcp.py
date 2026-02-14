"""
Phase 4 TCP 연동 테스트: Crafting / Gathering / Cooking / Enchant
================================================================
tcp_bridge.py를 실행한 상태에서 돌리면 됩니다.

사용법:
  cd Servers/BridgeServer
  # (터미널 1) python _patch.py && python _patch_s034.py && python _patch_s035.py && python _patch_s036.py && python _patch_s037.py && python _patch_s040.py && python _patch_s041.py && python tcp_bridge.py
  # (터미널 2) python test_phase4_crafting_tcp.py
"""

import asyncio
import struct
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from tcp_bridge import (
    BridgeServer, MsgType, build_packet, parse_header,
    PACKET_HEADER_SIZE, MAX_PACKET_SIZE
)


class TestClient:
    """테스트용 TCP 클라이언트"""

    def __init__(self):
        self.reader = None
        self.writer = None
        self.recv_buf = bytearray()
        self.entity_id = 0

    async def connect(self, host: str = '127.0.0.1', port: int = 0):
        self.reader, self.writer = await asyncio.open_connection(host, port)

    async def send(self, msg_type: int, payload: bytes = b''):
        pkt = build_packet(msg_type, payload)
        self.writer.write(pkt)
        await self.writer.drain()

    async def recv_packet(self, timeout: float = 2.0) -> tuple:
        deadline = time.time() + timeout
        while True:
            if len(self.recv_buf) >= PACKET_HEADER_SIZE:
                pkt_len = struct.unpack_from('<I', self.recv_buf, 0)[0]
                if len(self.recv_buf) >= pkt_len:
                    packet = bytes(self.recv_buf[:pkt_len])
                    self.recv_buf = self.recv_buf[pkt_len:]
                    _, msg_type = parse_header(packet)
                    payload = packet[PACKET_HEADER_SIZE:]
                    return msg_type, payload
            remaining = deadline - time.time()
            if remaining <= 0:
                return None, None
            try:
                data = await asyncio.wait_for(
                    self.reader.read(4096),
                    timeout=min(remaining, 0.5)
                )
                if not data:
                    return None, None
                self.recv_buf.extend(data)
            except asyncio.TimeoutError:
                if time.time() >= deadline:
                    return None, None

    async def recv_all_packets(self, timeout: float = 0.5) -> list:
        packets = []
        while True:
            msg_type, payload = await self.recv_packet(timeout=timeout)
            if msg_type is None:
                break
            packets.append((msg_type, payload))
            timeout = 0.2
        return packets

    async def recv_expect(self, expected: int, timeout: float = 3.0) -> tuple:
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None, None
            msg_type, payload = await self.recv_packet(timeout=remaining)
            if msg_type is None:
                return None, None
            if msg_type == expected:
                return msg_type, payload

    def close(self):
        if self.writer:
            self.writer.close()


async def login_and_enter(client, name: str, port: int):
    """로그인 + CHAR_SELECT + ENTER_GAME. entity_id 저장."""
    await client.connect('127.0.0.1', port)
    await asyncio.sleep(0.05)

    name_bytes = name.encode('utf-8')
    pw = b'pw'
    await client.send(MsgType.LOGIN,
                      struct.pack('<B', len(name_bytes)) + name_bytes +
                      struct.pack('<B', len(pw)) + pw)
    await client.recv_packet()  # LOGIN_RESULT

    await client.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
    packets = await client.recv_all_packets(timeout=1.0)

    for mt, pl in packets:
        if mt == MsgType.ENTER_GAME and len(pl) >= 9:
            client.entity_id = struct.unpack_from('<Q', pl, 1)[0]
            break


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 테스트 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_tests(port: int):
    results = []
    total = 0
    passed = 0

    async def test(name: str, coro):
        nonlocal total, passed
        total += 1
        try:
            await coro
            passed += 1
            results.append(f"  PASS [{total:02d}] {name}")
            print(f"  PASS [{total:02d}] {name}")
        except AssertionError as e:
            results.append(f"  FAIL [{total:02d}] {name}: {e}")
            print(f"  FAIL [{total:02d}] {name}: {e}")
        except Exception as e:
            results.append(f"  ERR  [{total:02d}] {name}: {type(e).__name__}: {e}")
            print(f"  ERR  [{total:02d}] {name}: {type(e).__name__}: {e}")

    print("\n" + "=" * 65)
    print("  Phase 4 TCP Integration Tests: Crafting / Gathering / Cooking / Enchant")
    print("  Target: 127.0.0.1:" + str(port))
    print("=" * 65 + "\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CRAFTING (380-383)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 1. CRAFT_LIST_REQ ━━━
    async def test_craft_list():
        c = TestClient()
        await login_and_enter(c, 'crftls1', port)

        await c.send(MsgType.CRAFT_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.CRAFT_LIST, timeout=3.0)
        assert mt == MsgType.CRAFT_LIST, f"Expected CRAFT_LIST, got {mt}"
        count = pl[0]
        # 기본 숙련도 1이면 proficiency=1인 레시피만: Iron Sword, HP Potion(S), Iron Armor, MP Potion(S) = 4개
        assert count >= 4, f"Should have at least 4 recipes at prof 1, got {count}"
        # 첫 레시피 파싱 확인
        recipe_id = struct.unpack_from('<H', pl, 1)[0]
        assert recipe_id > 0, f"Recipe ID should be > 0, got {recipe_id}"
        c.close()

    await test("CRAFT_LIST: 제작 레시피 목록 조회", test_craft_list())

    # ━━━ 2. CRAFT_EXECUTE (재료 부족) ━━━
    async def test_craft_no_materials():
        c = TestClient()
        await login_and_enter(c, 'crftnm1', port)

        # Iron Sword (recipe_id=1) 재료 없이 제작 시도
        await c.send(MsgType.CRAFT_EXECUTE, struct.pack('<H', 1))
        mt, pl = await c.recv_expect(MsgType.CRAFT_RESULT, timeout=3.0)
        assert mt == MsgType.CRAFT_RESULT, f"Expected CRAFT_RESULT, got {mt}"
        result = pl[0]
        assert result == 3, f"Expected MATERIAL_MISSING(3), got {result}"
        c.close()

    await test("CRAFT_FAIL: 재료 부족 제작 실패", test_craft_no_materials())

    # ━━━ 3. CRAFT_EXECUTE (성공) ━━━
    async def test_craft_success():
        c = TestClient()
        await login_and_enter(c, 'crftok1', port)

        # 재료 추가: Iron Ore x5 (1001) + Wood x2 (1002)
        for _ in range(5):
            await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 1001, 1))
            await c.recv_expect(MsgType.ITEM_ADD_RESULT, timeout=1.0)
        for _ in range(2):
            await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 1002, 1))
            await c.recv_expect(MsgType.ITEM_ADD_RESULT, timeout=1.0)

        # Iron Sword (recipe_id=1, success_rate=1.0) 제작
        await c.send(MsgType.CRAFT_EXECUTE, struct.pack('<H', 1))
        mt, pl = await c.recv_expect(MsgType.CRAFT_RESULT, timeout=3.0)
        assert mt == MsgType.CRAFT_RESULT, f"Expected CRAFT_RESULT, got {mt}"
        result = pl[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        recipe_id = struct.unpack_from('<H', pl, 1)[0]
        assert recipe_id == 1, f"Recipe ID mismatch: {recipe_id}"
        item_id = struct.unpack_from('<I', pl, 3)[0]
        assert item_id == 2001, f"Result item should be 2001 (Iron Sword), got {item_id}"
        count = struct.unpack_from('<H', pl, 7)[0]
        assert count == 1, f"Result count should be 1, got {count}"
        c.close()

    await test("CRAFT_SUCCESS: 재료 넣고 Iron Sword 제작 성공", test_craft_success())

    # ━━━ 4. CRAFT_EXECUTE (존재하지 않는 레시피) ━━━
    async def test_craft_invalid_recipe():
        c = TestClient()
        await login_and_enter(c, 'crftiv1', port)

        await c.send(MsgType.CRAFT_EXECUTE, struct.pack('<H', 999))
        mt, pl = await c.recv_expect(MsgType.CRAFT_RESULT, timeout=3.0)
        assert mt == MsgType.CRAFT_RESULT
        result = pl[0]
        assert result == 1, f"Expected RECIPE_NOT_FOUND(1), got {result}"
        c.close()

    await test("CRAFT_INVALID: 존재하지 않는 레시피", test_craft_invalid_recipe())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # GATHERING (384-385)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 5. GATHER (약초) ━━━
    async def test_gather_herb():
        c = TestClient()
        await login_and_enter(c, 'gathr01', port)

        await c.send(MsgType.GATHER_START, struct.pack('<B', 1))  # Herb
        mt, pl = await c.recv_expect(MsgType.GATHER_RESULT, timeout=3.0)
        assert mt == MsgType.GATHER_RESULT, f"Expected GATHER_RESULT, got {mt}"
        result = pl[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        node_type = pl[1]
        assert node_type == 1, f"Node type should be 1, got {node_type}"
        item_id = struct.unpack_from('<I', pl, 2)[0]
        assert item_id > 0, f"Should drop an item, got {item_id}"
        energy = struct.unpack_from('<H', pl, 8)[0]
        assert energy == 195, f"Energy should be 195 (200-5), got {energy}"
        c.close()

    await test("GATHER_HERB: 약초 채집 성공", test_gather_herb())

    # ━━━ 6. GATHER (잘못된 노드) ━━━
    async def test_gather_invalid():
        c = TestClient()
        await login_and_enter(c, 'gathriv', port)

        await c.send(MsgType.GATHER_START, struct.pack('<B', 99))
        mt, pl = await c.recv_expect(MsgType.GATHER_RESULT, timeout=3.0)
        assert mt == MsgType.GATHER_RESULT
        result = pl[0]
        assert result == 1, f"Expected NODE_NOT_FOUND(1), got {result}"
        c.close()

    await test("GATHER_INVALID: 잘못된 노드 타입", test_gather_invalid())

    # ━━━ 7. GATHER (에너지 소모) ━━━
    async def test_gather_energy_drain():
        c = TestClient()
        await login_and_enter(c, 'gathre1', port)

        # 40번 채집 = 200 에너지 소진
        for i in range(40):
            await c.send(MsgType.GATHER_START, struct.pack('<B', 2))  # Ore
            mt, pl = await c.recv_expect(MsgType.GATHER_RESULT, timeout=2.0)
            assert mt == MsgType.GATHER_RESULT

        # 41번째 채집 → 에너지 부족
        await c.send(MsgType.GATHER_START, struct.pack('<B', 2))
        mt, pl = await c.recv_expect(MsgType.GATHER_RESULT, timeout=3.0)
        assert mt == MsgType.GATHER_RESULT
        result = pl[0]
        assert result == 2, f"Expected ENERGY_EMPTY(2), got {result}"
        energy = struct.unpack_from('<H', pl, 8)[0]
        assert energy == 0, f"Energy should be 0, got {energy}"
        c.close()

    await test("GATHER_ENERGY: 에너지 소진 후 채집 불가", test_gather_energy_drain())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COOKING (386-387)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 8. COOK (재료 부족) ━━━
    async def test_cook_no_materials():
        c = TestClient()
        await login_and_enter(c, 'cooknm1', port)

        await c.send(MsgType.COOK_EXECUTE, struct.pack('<B', 1))  # Grilled Meat
        mt, pl = await c.recv_expect(MsgType.COOK_RESULT, timeout=3.0)
        assert mt == MsgType.COOK_RESULT
        result = pl[0]
        assert result == 2, f"Expected MATERIAL_MISSING(2), got {result}"
        c.close()

    await test("COOK_FAIL: 재료 부족 요리 실패", test_cook_no_materials())

    # ━━━ 9. COOK (성공) ━━━
    async def test_cook_success():
        c = TestClient()
        await login_and_enter(c, 'cookok1', port)

        # 재료 추가: Raw Meat x3 (1020)
        for _ in range(3):
            await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 1020, 1))
            await c.recv_expect(MsgType.ITEM_ADD_RESULT, timeout=1.0)

        await c.send(MsgType.COOK_EXECUTE, struct.pack('<B', 1))  # Grilled Meat
        mt, pl = await c.recv_expect(MsgType.COOK_RESULT, timeout=3.0)
        assert mt == MsgType.COOK_RESULT
        result = pl[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        recipe_id = pl[1]
        assert recipe_id == 1
        buff_type = pl[2]
        assert buff_type == 1, f"Buff type should be 1(atk), got {buff_type}"
        buff_value = struct.unpack_from('<H', pl, 3)[0]
        assert buff_value == 10, f"Buff value should be 10, got {buff_value}"
        duration = struct.unpack_from('<H', pl, 5)[0]
        assert duration == 1800, f"Duration should be 1800, got {duration}"
        c.close()

    await test("COOK_SUCCESS: Grilled Meat 요리 + ATK 버프", test_cook_success())

    # ━━━ 10. COOK (중복 버프 거부) ━━━
    async def test_cook_duplicate_buff():
        c = TestClient()
        await login_and_enter(c, 'cookdb1', port)

        # 재료 추가: Raw Meat x6 (1020) — 2번 요리 시도
        for _ in range(6):
            await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 1020, 1))
            await c.recv_expect(MsgType.ITEM_ADD_RESULT, timeout=1.0)

        # 첫 번째 요리 → 성공
        await c.send(MsgType.COOK_EXECUTE, struct.pack('<B', 1))
        mt, pl = await c.recv_expect(MsgType.COOK_RESULT, timeout=3.0)
        assert pl[0] == 0, "First cook should succeed"

        # 두 번째 요리 → 이미 버프 중
        await c.send(MsgType.COOK_EXECUTE, struct.pack('<B', 1))
        mt, pl = await c.recv_expect(MsgType.COOK_RESULT, timeout=3.0)
        assert mt == MsgType.COOK_RESULT
        result = pl[0]
        assert result == 3, f"Expected ALREADY_BUFFED(3), got {result}"
        c.close()

    await test("COOK_DUP: 중복 음식 버프 거부", test_cook_duplicate_buff())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ENCHANT (388-389)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 11. ENCHANT (빈 슬롯) ━━━
    async def test_enchant_empty_slot():
        c = TestClient()
        await login_and_enter(c, 'enchnt1', port)

        await c.send(MsgType.ENCHANT_REQ, struct.pack('<BBB', 99, 1, 1))  # slot=99 없음
        mt, pl = await c.recv_expect(MsgType.ENCHANT_RESULT, timeout=3.0)
        assert mt == MsgType.ENCHANT_RESULT
        result = pl[0]
        assert result == 5, f"Expected NO_ITEM_IN_SLOT(5), got {result}"
        c.close()

    await test("ENCHANT_EMPTY: 빈 슬롯 인챈트 실패", test_enchant_empty_slot())

    # ━━━ 12. ENCHANT (잘못된 원소) ━━━
    async def test_enchant_invalid_element():
        c = TestClient()
        await login_and_enter(c, 'enchiv1', port)

        await c.send(MsgType.ENCHANT_REQ, struct.pack('<BBB', 0, 99, 1))  # element=99 없음
        mt, pl = await c.recv_expect(MsgType.ENCHANT_RESULT, timeout=3.0)
        assert mt == MsgType.ENCHANT_RESULT
        result = pl[0]
        assert result == 1, f"Expected INVALID_ELEMENT(1), got {result}"
        c.close()

    await test("ENCHANT_ELEMENT: 잘못된 원소 거부", test_enchant_invalid_element())

    # ━━━ 13. ENCHANT (성공) ━━━
    async def test_enchant_success():
        c = TestClient()
        await login_and_enter(c, 'enchok1', port)

        # 아이템 추가해서 슬롯 확보
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 2001, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT, timeout=1.0)

        # Fire enchant Lv1 on slot 0
        await c.send(MsgType.ENCHANT_REQ, struct.pack('<BBB', 0, 1, 1))
        mt, pl = await c.recv_expect(MsgType.ENCHANT_RESULT, timeout=3.0)
        assert mt == MsgType.ENCHANT_RESULT
        result = pl[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        slot = pl[1]
        assert slot == 0
        element = pl[2]
        assert element == 1, f"Element should be 1(fire), got {element}"
        level = pl[3]
        assert level == 1
        dmg_pct = pl[4]
        assert dmg_pct == 5, f"Damage bonus should be 5%, got {dmg_pct}"
        c.close()

    await test("ENCHANT_SUCCESS: Fire Lv1 인챈트 성공", test_enchant_success())

    # ━━━ 14. ENCHANT (잘못된 레벨) ━━━
    async def test_enchant_invalid_level():
        c = TestClient()
        await login_and_enter(c, 'enchil1', port)

        await c.send(MsgType.ENCHANT_REQ, struct.pack('<BBB', 0, 1, 99))  # level=99
        mt, pl = await c.recv_expect(MsgType.ENCHANT_RESULT, timeout=3.0)
        assert mt == MsgType.ENCHANT_RESULT
        result = pl[0]
        assert result == 2, f"Expected INVALID_LEVEL(2), got {result}"
        c.close()

    await test("ENCHANT_LEVEL: 잘못된 레벨 거부", test_enchant_invalid_level())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DATA VALIDATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━ 15. CRAFT_RECIPES 데이터 검증 ━━━
    async def test_craft_data():
        from tcp_bridge import CRAFT_RECIPES
        assert len(CRAFT_RECIPES) == 8, f"Should have 8 recipes, got {len(CRAFT_RECIPES)}"
        for rid, r in CRAFT_RECIPES.items():
            assert "name" in r, f"Recipe {rid} missing 'name'"
            assert "materials" in r, f"Recipe {rid} missing 'materials'"
            assert "success_rate" in r, f"Recipe {rid} missing 'success_rate'"
            assert 0.0 < r["success_rate"] <= 1.0, f"Recipe {rid} invalid success_rate: {r['success_rate']}"
            assert r["result_item"] > 0, f"Recipe {rid} invalid result_item"

    await test("CRAFT_DATA: 제작 레시피 8종 데이터 검증", test_craft_data())

    # ━━━ 16. GATHER_NODES 데이터 검증 ━━━
    async def test_gather_data():
        from tcp_bridge import GATHER_NODES
        assert len(GATHER_NODES) == 4, f"Should have 4 gather nodes, got {len(GATHER_NODES)}"
        for nid, n in GATHER_NODES.items():
            assert n["energy"] == 5, f"Node {nid} energy should be 5"
            total_chance = sum(chance for _, chance in n["loot"])
            assert abs(total_chance - 1.0) < 0.01, f"Node {nid} loot chances don't sum to 1.0: {total_chance}"

    await test("GATHER_DATA: 채집 노드 4종 데이터 검증", test_gather_data())

    # ━━━ 17. COOK_RECIPES 데이터 검증 ━━━
    async def test_cook_data():
        from tcp_bridge import COOK_RECIPES
        assert len(COOK_RECIPES) == 3, f"Should have 3 cook recipes, got {len(COOK_RECIPES)}"
        for cid, r in COOK_RECIPES.items():
            assert r["buff_duration"] >= 1800, f"Cook {cid} duration too short: {r['buff_duration']}"
            assert r["buff_value"] > 0, f"Cook {cid} buff_value should be > 0"

    await test("COOK_DATA: 요리 레시피 3종 데이터 검증", test_cook_data())

    # ━━━ 18. ENCHANT 데이터 검증 ━━━
    async def test_enchant_data():
        from tcp_bridge import ENCHANT_ELEMENTS, ENCHANT_LEVELS
        assert len(ENCHANT_ELEMENTS) == 6, f"Should have 6 elements, got {len(ENCHANT_ELEMENTS)}"
        assert len(ENCHANT_LEVELS) == 3, f"Should have 3 enchant levels, got {len(ENCHANT_LEVELS)}"
        for lv, data in ENCHANT_LEVELS.items():
            assert data["damage_bonus"] > 0
            assert data["gold"] > 0

    await test("ENCHANT_DATA: 인챈트 원소 6종 + 레벨 3종 검증", test_enchant_data())

    # ━━━ Summary ━━━
    print("\n" + "=" * 65)
    print(f"  Phase 4 Crafting TCP Results: {passed}/{total} PASS")
    print("=" * 65)
    for r in results:
        print(r)

    if passed == total:
        print(f"\n  ALL {total} TESTS PASSED!")
    else:
        print(f"\n  {total - passed} FAILED!")

    return passed, total


async def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7777

    # Try connecting to existing server
    try:
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        writer.close()
        await writer.wait_closed()
        print(f"  Connected to existing server on port {port}")
        passed, total = await run_tests(port)
    except ConnectionRefusedError:
        # Start embedded server
        print(f"  No server running, starting embedded server on port {port}...")
        server = BridgeServer(port=port)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(1.0)
        passed, total = await run_tests(port)
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    asyncio.run(main())
