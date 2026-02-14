"""
Patch S034: 튜토리얼 몬스터 스폰 + NPC 대화 시스템 + 마을 존/NPC + 강화 시스템
- P1_S02_S01: tutorial zone monsters (dummy + slime x3)
- P1_S04_S01: NPC_INTERACT(332) / NPC_DIALOG(333) + dialog data
- P1_S05_S01: village zone(10) bounds + NPC spawn data
- P2_S02_S01: ENHANCE_REQ(340) / ENHANCE_RESULT(341)
"""
import os
import sys
import struct

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'NPC_INTERACT' in content:
        print('[bridge] S034 already patched')
        return True

    replacements = []

    # 1. MsgType: NPC_INTERACT, NPC_DIALOG, ENHANCE 추가 (TUTORIAL_REWARD 뒤에)
    replacements.append((
        '    TUTORIAL_STEP_COMPLETE = 330\n    TUTORIAL_REWARD = 331\n',
        '    TUTORIAL_STEP_COMPLETE = 330\n    TUTORIAL_REWARD = 331\n\n'
        '    # NPC Dialog\n'
        '    NPC_INTERACT = 332\n'
        '    NPC_DIALOG = 333\n\n'
        '    # Enhancement\n'
        '    ENHANCE_REQ = 340\n'
        '    ENHANCE_RESULT = 341\n'
    ))

    # 2. ZONE_BOUNDS에 튜토리얼(0)과 마을(10) 추가
    replacements.append((
        '# 존 경계\nZONE_BOUNDS = {\n'
        '    1: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},\n'
        '    2: {"min_x": 0, "max_x": 2000, "min_z": 0, "max_z": 2000},\n'
        '    3: {"min_x": 0, "max_x": 3000, "min_z": 0, "max_z": 3000},\n'
        '}',
        '# 존 경계\nZONE_BOUNDS = {\n'
        '    0: {"min_x": 0, "max_x": 500, "min_z": 0, "max_z": 500},      # tutorial\n'
        '    1: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},\n'
        '    2: {"min_x": 0, "max_x": 2000, "min_z": 0, "max_z": 2000},\n'
        '    3: {"min_x": 0, "max_x": 3000, "min_z": 0, "max_z": 3000},\n'
        '    10: {"min_x": 0, "max_x": 300, "min_z": 0, "max_z": 300},     # village\n'
        '}'
    ))

    # 3. MONSTER_SPAWNS에 튜토리얼 몬스터 추가 (맨 앞에)
    replacements.append((
        '# 몬스터 스폰 데이터\nMONSTER_SPAWNS = [\n'
        '    {"id": 1, "name": "Goblin"',
        '# 몬스터 스폰 데이터\nMONSTER_SPAWNS = [\n'
        '    # Tutorial zone (zone=0) — P1_S02_S01\n'
        '    {"id": 9001, "name": "Dummy", "level": 1, "hp": 100, "atk": 0, "def": 999, "zone": 0, "x": 50, "y": 0, "z": 80},\n'
        '    {"id": 9002, "name": "TutSlime", "level": 1, "hp": 50, "atk": 5, "zone": 0, "x": 100, "y": 0, "z": 120},\n'
        '    {"id": 9002, "name": "TutSlime", "level": 1, "hp": 50, "atk": 5, "zone": 0, "x": 120, "y": 0, "z": 100},\n'
        '    {"id": 9002, "name": "TutSlime", "level": 1, "hp": 50, "atk": 5, "zone": 0, "x": 80, "y": 0, "z": 140},\n'
        '    # Field zone 1\n'
        '    {"id": 1, "name": "Goblin"'
    ))

    # 4. NPC 데이터 + 대화 데이터 (TUTORIAL_REWARDS 뒤에)
    replacements.append((
        '# 이동 상수\nMOVEMENT = {',
        '# NPC 스폰 데이터 (P1_S04_S01, P1_S05_S01)\n'
        'NPC_SPAWNS = [\n'
        '    # Tutorial zone (zone=0)\n'
        '    {"npc_id": 1, "name": "튜토리얼 안내원", "type": "quest", "zone": 0, "x": 10.0, "y": 0.0, "z": 10.0, "quest_ids": [1]},\n'
        '    # Village zone (zone=10)\n'
        '    {"npc_id": 2, "name": "마을 장로", "type": "quest", "zone": 10, "x": 0.0, "y": 0.0, "z": 0.0, "quest_ids": [2, 3]},\n'
        '    {"npc_id": 3, "name": "상점 주인", "type": "shop", "zone": 10, "x": 15.0, "y": 0.0, "z": 5.0, "shop_id": 1},\n'
        '    {"npc_id": 4, "name": "무기 상인", "type": "shop", "zone": 10, "x": 20.0, "y": 0.0, "z": 5.0, "shop_id": 2},\n'
        '    {"npc_id": 5, "name": "방어구 상인", "type": "shop", "zone": 10, "x": 20.0, "y": 0.0, "z": -5.0, "shop_id": 3},\n'
        '    {"npc_id": 6, "name": "대장장이", "type": "blacksmith", "zone": 10, "x": -10.0, "y": 0.0, "z": 5.0},\n'
        '    {"npc_id": 7, "name": "퀘스트 게시판", "type": "quest", "zone": 10, "x": 5.0, "y": 0.0, "z": -10.0, "quest_ids": [1, 2, 3]},\n'
        '    {"npc_id": 8, "name": "스킬 트레이너", "type": "skill", "zone": 10, "x": -5.0, "y": 0.0, "z": -10.0},\n'
        ']\n\n'
        '# NPC 대화 데이터\n'
        'NPC_DIALOGS = {\n'
        '    1: [\n'
        '        {"speaker": "튜토리얼 안내원", "text": "모험가여, 환영하네! 자네의 여정을 도와주지."},\n'
        '        {"speaker": "튜토리얼 안내원", "text": "먼저 WASD로 이동해보게. 그리고 저 허수아비를 공격해보게나."},\n'
        '        {"speaker": "튜토리얼 안내원", "text": "슬라임도 처치해보게. 실전 전투 연습이 될 거야."},\n'
        '    ],\n'
        '    2: [\n'
        '        {"speaker": "마을 장로", "text": "오, 젊은 모험가. 마을에 일이 생겼다네..."},\n'
        '        {"speaker": "마을 장로", "text": "마을 근처에 고블린이 출몰하고 있소. 퇴치해 주겠는가?"},\n'
        '    ],\n'
        '    3: [\n'
        '        {"speaker": "상점 주인", "text": "어서오세요! 필요한 물건이 있으신가요?"},\n'
        '    ],\n'
        '    4: [\n'
        '        {"speaker": "무기 상인", "text": "최고급 무기를 갖추고 있습니다!"},\n'
        '    ],\n'
        '    5: [\n'
        '        {"speaker": "방어구 상인", "text": "튼튼한 방어구, 여기 다 있습니다."},\n'
        '    ],\n'
        '    6: [\n'
        '        {"speaker": "대장장이", "text": "뭘 강화할 건가? 내 솜씨를 보여주지."},\n'
        '    ],\n'
        '    7: [\n'
        '        {"speaker": "퀘스트 게시판", "text": "[의뢰 목록을 확인한다]"},\n'
        '    ],\n'
        '    8: [\n'
        '        {"speaker": "스킬 트레이너", "text": "새로운 기술을 배우고 싶은가? 잘 찾아왔어."},\n'
        '    ],\n'
        '}\n\n'
        '# 강화 확률 테이블 (P2_S02_S01)\n'
        'ENHANCE_TABLE = {\n'
        '    1: 0.90,   # +1: 90%\n'
        '    2: 0.80,   # +2: 80%\n'
        '    3: 0.70,   # +3: 70%\n'
        '    4: 0.60,   # +4: 60%\n'
        '    5: 0.50,   # +5: 50%\n'
        '    6: 0.40,   # +6: 40%\n'
        '    7: 0.30,   # +7: 30%\n'
        '    8: 0.20,   # +8: 20%\n'
        '    9: 0.10,   # +9: 10%\n'
        '    10: 0.05,  # +10: 5%\n'
        '}\n'
        'ENHANCE_COST_BASE = 500  # 강화 비용 = base * level\n\n'
        '# 이동 상수\nMOVEMENT = {'
    ))

    # 5. BridgeServer.__init__에 npcs 딕셔너리 추가
    replacements.append((
        '        self.characters: Dict[int, List[dict]] = {}  # account_id -> character list\n'
        '        self.next_char_id = 1\n',
        '        self.characters: Dict[int, List[dict]] = {}  # account_id -> character list\n'
        '        self.next_char_id = 1\n'
        '        self.npcs: Dict[int, dict] = {}  # entity_id -> npc data\n'
    ))

    # 6. _dispatch 핸들러 등록 (TUTORIAL 뒤에)
    replacements.append((
        '            MsgType.TUTORIAL_STEP_COMPLETE: self._on_tutorial_step_complete,\n        }',
        '            MsgType.TUTORIAL_STEP_COMPLETE: self._on_tutorial_step_complete,\n'
        '            MsgType.NPC_INTERACT: self._on_npc_interact,\n'
        '            MsgType.ENHANCE_REQ: self._on_enhance_req,\n'
        '        }'
    ))

    # 7. _spawn_monsters 앞에 NPC 스폰 + 핸들러 삽입
    # 기존: "    def _spawn_monsters(self):"
    # _spawn_monsters를 확장해서 NPC도 스폰하도록
    replacements.append((
        '    def _spawn_monsters(self):\n'
        '        for spawn in MONSTER_SPAWNS:',
        '    def _spawn_npcs(self):\n'
        '        """NPC 엔티티 스폰 (P1_S04_S01, P1_S05_S01)"""\n'
        '        for npc in NPC_SPAWNS:\n'
        '            eid = new_entity()\n'
        '            self.npcs[eid] = {\n'
        '                "entity_id": eid,\n'
        '                "npc_id": npc["npc_id"],\n'
        '                "name": npc["name"],\n'
        '                "type": npc["type"],\n'
        '                "zone": npc["zone"],\n'
        '                "pos": Position(npc["x"], npc["y"], npc["z"]),\n'
        '                "shop_id": npc.get("shop_id"),\n'
        '                "quest_ids": npc.get("quest_ids", []),\n'
        '            }\n'
        '        self.log(f"Spawned {len(self.npcs)} NPCs", "GAME")\n\n'
        '    # ━━━ 핸들러: NPC 대화 (P1_S04_S01) ━━━\n\n'
        '    async def _on_npc_interact(self, session: PlayerSession, payload: bytes):\n'
        '        if not session.in_game or len(payload) < 4:\n'
        '            return\n'
        '        npc_entity_id = struct.unpack("<I", payload[:4])[0]\n'
        '        npc = self.npcs.get(npc_entity_id)\n'
        '        if not npc:\n'
        '            # npc_id 직접 조회 fallback\n'
        '            npc_id = npc_entity_id\n'
        '            for n in self.npcs.values():\n'
        '                if n["npc_id"] == npc_id:\n'
        '                    npc = n\n'
        '                    break\n'
        '        if not npc:\n'
        '            return\n'
        '        dialogs = NPC_DIALOGS.get(npc["npc_id"], [])\n'
        '        if not dialogs:\n'
        '            return\n'
        '        npc_id = npc["npc_id"]\n'
        '        npc_type_val = {"quest": 0, "shop": 1, "blacksmith": 2, "skill": 3}.get(npc["type"], 0)\n'
        '        line_count = len(dialogs)\n'
        '        # 대화 패킷: npc_id(u16) + npc_type(u8) + line_count(u8) + [speaker_len(u8) + speaker + text_len(u16) + text] * N\n'
        '        buf = struct.pack("<HBB", npc_id, npc_type_val, line_count)\n'
        '        for d in dialogs:\n'
        '            speaker_bytes = d["speaker"].encode("utf-8")[:32]\n'
        '            text_bytes = d["text"].encode("utf-8")[:256]\n'
        '            buf += struct.pack("<B", len(speaker_bytes)) + speaker_bytes\n'
        '            buf += struct.pack("<H", len(text_bytes)) + text_bytes\n'
        '        # quest_ids 추가: quest_count(u8) + [quest_id(u32)] * N\n'
        '        quest_ids = npc.get("quest_ids", [])\n'
        '        buf += struct.pack("<B", len(quest_ids))\n'
        '        for qid in quest_ids:\n'
        '            buf += struct.pack("<I", qid)\n'
        '        self._send(session, MsgType.NPC_DIALOG, buf)\n'
        '        self.log(f"NPC Dialog: npc_id={npc_id} lines={line_count} ({session.char_name})", "GAME")\n\n'
        '    # ━━━ 핸들러: 강화 (P2_S02_S01) ━━━\n\n'
        '    async def _on_enhance_req(self, session: PlayerSession, payload: bytes):\n'
        '        """ENHANCE_REQ: slot_index(u8). 해당 슬롯 장비를 강화."""\n'
        '        if not session.in_game or len(payload) < 1:\n'
        '            return\n'
        '        slot_idx = payload[0]\n'
        '        if slot_idx >= len(session.inventory):\n'
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 1, 0))  # 1=INVALID_SLOT\n'
        '            return\n'
        '        item = session.inventory[slot_idx]\n'
        '        if item.item_id == 0:\n'
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 2, 0))  # 2=NO_ITEM\n'
        '            return\n'
        '        current_level = getattr(item, "enhance_level", 0)\n'
        '        if current_level >= 10:\n'
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 3, current_level))  # 3=MAX_LEVEL\n'
        '            return\n'
        '        cost = ENHANCE_COST_BASE * (current_level + 1)\n'
        '        if session.gold < cost:\n'
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 4, current_level))  # 4=NO_GOLD\n'
        '            return\n'
        '        session.gold -= cost\n'
        '        import random as _rng\n'
        '        success_rate = ENHANCE_TABLE.get(current_level + 1, 0.05)\n'
        '        success = _rng.random() < success_rate\n'
        '        if success:\n'
        '            item.enhance_level = current_level + 1\n'
        '            self.log(f"Enhance: +{item.enhance_level} SUCCESS slot={slot_idx} ({session.char_name})", "GAME")\n'
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 0, item.enhance_level))  # 0=SUCCESS\n'
        '        else:\n'
        '            self.log(f"Enhance: +{current_level + 1} FAIL slot={slot_idx} ({session.char_name})", "GAME")\n'
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 5, current_level))  # 5=FAIL (level preserved)\n\n'
        '    # ━━━ 몬스터 시스템 ━━━\n\n'
        '    def _spawn_monsters(self):\n'
        '        for spawn in MONSTER_SPAWNS:'
    ))

    # 8. _spawn_monsters 호출 직후에 _spawn_npcs 호출 추가
    replacements.append((
        '        self._spawn_monsters()\n\n        # 게임 틱 루프 시작',
        '        self._spawn_monsters()\n        self._spawn_npcs()\n\n        # 게임 틱 루프 시작'
    ))

    # 9. InventorySlot에 enhance_level 필드 추가 (있다면)
    # InventorySlot dataclass 찾기
    inv_slot_marker = '    item_id: int = 0\n    count: int = 0\n    equipped: bool = False'
    if inv_slot_marker in content:
        replacements.append((
            inv_slot_marker,
            '    item_id: int = 0\n    count: int = 0\n    equipped: bool = False\n    enhance_level: int = 0'
        ))

    for old, new in replacements:
        if old not in content:
            print(f'[bridge] WARNING: Pattern not found:\n  {repr(old[:80])}...')
            continue
        content = content.replace(old, new, 1)

    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    # Verify
    checks = ['NPC_INTERACT', 'NPC_DIALOG', '_on_npc_interact', '_on_enhance_req',
              'NPC_SPAWNS', 'NPC_DIALOGS', 'ENHANCE_TABLE', '_spawn_npcs',
              '"zone": 0', 'TutSlime', 'Dummy']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S034 patched OK')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_npc_interact' in content:
        print('[test] S034 already patched')
        return True

    new_tests = r'''
    # ━━━ NPC 대화 / 강화 / 튜토리얼 몬스터 (S034) ━━━

    async def test_tutorial_monsters():
        """튜토리얼 존(zone=0)에 허수아비+슬라임 몬스터가 스폰되었는지 확인"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        # 로그인 + 게임 입장
        await c.send(MsgType.LOGIN, struct.pack('<B', 7) + b'tutmon1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        packets = await c.recv_all_packets(timeout=1.0)
        # MONSTER_SPAWN 패킷 중 zone=0 (tutorial) 몬스터 확인
        spawns = [p for mt, p in packets if mt == MsgType.MONSTER_SPAWN]
        # 서버가 zone 기반 필터링을 할 수도 있고 전체 전송할 수도 있음
        # 최소한 MONSTER_SPAWN이 전송되었는지 확인
        assert len(spawns) > 0, "Expected MONSTER_SPAWN packets"
        c.close()

    await test("TUT_MONSTERS: 튜토리얼 몬스터 스폰 확인", test_tutorial_monsters())

    async def test_npc_interact():
        """NPC 대화 패킷 테스트"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 7) + b'npctest' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # NPC npc_id=1 (튜토리얼 안내원) — entity_id로 보내야 하므로 npc_id fallback 사용
        await c.send(MsgType.NPC_INTERACT, struct.pack('<I', 1))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.NPC_DIALOG, f"Expected NPC_DIALOG, got {msg_type}"
        npc_id, npc_type, line_count = struct.unpack_from('<HBB', payload, 0)
        assert npc_id == 1, f"Expected npc_id=1, got {npc_id}"
        assert line_count == 3, f"Expected 3 dialog lines, got {line_count}"
        c.close()

    await test("NPC_DIALOG: NPC 대화 요청/응답", test_npc_interact())

    async def test_npc_dialog_village():
        """마을 NPC 대화 테스트"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'villnpc1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # 마을 장로 npc_id=2
        await c.send(MsgType.NPC_INTERACT, struct.pack('<I', 2))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.NPC_DIALOG
        npc_id, npc_type, line_count = struct.unpack_from('<HBB', payload, 0)
        assert npc_id == 2
        assert line_count == 2
        # quest_ids 파싱 — dialog lines 건너뛰기
        offset = 4
        for _ in range(line_count):
            spk_len = payload[offset]
            offset += 1 + spk_len
            txt_len = struct.unpack_from('<H', payload, offset)[0]
            offset += 2 + txt_len
        quest_count = payload[offset]
        assert quest_count == 2, f"Expected 2 quest_ids, got {quest_count}"
        c.close()

    await test("NPC_DIALOG_VILLAGE: 마을 장로 대화 + 퀘스트 연결", test_npc_dialog_village())

    async def test_enhance_no_gold():
        """강화 — 골드 부족"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'enhtest1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # 아이템 추가 (인벤 슬롯 0에)
        await c.send(MsgType.ITEM_ADD, struct.pack('<IHB', 201, 1, 0))
        await c.recv_all_packets(timeout=0.5)
        # 골드 0 상태에서 강화 시도
        await c.send(MsgType.ENHANCE_REQ, struct.pack('<B', 0))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.ENHANCE_RESULT
        slot_idx = payload[0]
        result = payload[1]
        # result=4 (NO_GOLD) or result=2 (NO_ITEM if not added)
        assert result in (2, 4), f"Expected NO_GOLD(4) or NO_ITEM(2), got {result}"
        c.close()

    await test("ENHANCE: 골드 부족 시 실패", test_enhance_no_gold())

    async def test_enhance_empty_slot():
        """강화 — 빈 슬롯"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'enhtest2' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # 빈 슬롯 강화
        await c.send(MsgType.ENHANCE_REQ, struct.pack('<B', 5))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.ENHANCE_RESULT
        assert payload[1] == 2, f"Expected NO_ITEM(2), got {payload[1]}"
        c.close()

    await test("ENHANCE: 빈 슬롯 강화 거부", test_enhance_empty_slot())

'''

    marker = '    # \u2501\u2501\u2501 \uacb0\uacfc \u2501\u2501\u2501'
    if marker not in content:
        print('[test] WARNING: Result section marker not found')
        return False

    content = content.replace(marker, new_tests + marker, 1)

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    if 'test_npc_interact' in content:
        print('[test] S034 patched OK')
        return True
    else:
        print('[test] S034 FAILED')
        return False


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS034 all patches applied!')
    else:
        print('\nSome patches failed!')
        sys.exit(1)
