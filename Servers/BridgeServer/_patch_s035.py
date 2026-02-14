"""
Patch S035: 필드 몬스터 확장 + 던전 매칭 시스템
- P2_S01_S01: 필드 존 몬스터 스폰 테이블 확장 (zone별 레벨 차등, monsters.csv 기반)
- P2_S03_S01: 던전 매칭 큐 + 인스턴스 생성 (MATCH_ENQUEUE/DEQUEUE/FOUND/ACCEPT + INSTANCE_CREATE/ENTER/LEAVE/INFO)
"""
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'DUNGEON_LIST_DATA' in content:
        print('[bridge] S035 already patched')
        return True

    replacements = []

    # 1. MONSTER_SPAWNS 확장 — zone 1에 더 많은 몬스터, zone 2/3 다양화
    old_spawns = (
        '    # Field zone 1\n'
        '    {"id": 1, "name": "Goblin", "level": 5, "hp": 100, "atk": 15, "zone": 1, "x": 200, "y": 0, "z": 200},\n'
        '    {"id": 1, "name": "Goblin", "level": 5, "hp": 100, "atk": 15, "zone": 1, "x": 300, "y": 0, "z": 150},\n'
        '    {"id": 2, "name": "Wolf", "level": 8, "hp": 200, "atk": 25, "zone": 1, "x": 500, "y": 0, "z": 400},\n'
        '    {"id": 2, "name": "Wolf", "level": 8, "hp": 200, "atk": 25, "zone": 1, "x": 600, "y": 0, "z": 300},\n'
        '    {"id": 3, "name": "Orc", "level": 12, "hp": 350, "atk": 35, "zone": 2, "x": 100, "y": 0, "z": 100},\n'
        '    {"id": 3, "name": "Orc", "level": 12, "hp": 350, "atk": 35, "zone": 2, "x": 300, "y": 0, "z": 200},\n'
        '    {"id": 4, "name": "Bear", "level": 15, "hp": 500, "atk": 40, "zone": 2, "x": 800, "y": 0, "z": 600},\n'
        '    {"id": 5, "name": "Skeleton", "level": 18, "hp": 300, "atk": 50, "zone": 3, "x": 200, "y": 0, "z": 200},\n'
        '    {"id": 5, "name": "Skeleton", "level": 18, "hp": 300, "atk": 50, "zone": 3, "x": 400, "y": 0, "z": 400},\n'
    )

    new_spawns = (
        '    # ──── Field zone 1: 초원 평야 (Lv.3~8) ────  P2_S01_S01\n'
        '    {"id": 1001, "name": "Slime", "level": 3, "hp": 50, "atk": 5, "zone": 1, "x": 100, "y": 0, "z": 100},\n'
        '    {"id": 1001, "name": "Slime", "level": 3, "hp": 50, "atk": 5, "zone": 1, "x": 150, "y": 0, "z": 180},\n'
        '    {"id": 1001, "name": "Slime", "level": 3, "hp": 50, "atk": 5, "zone": 1, "x": 200, "y": 0, "z": 120},\n'
        '    {"id": 1002, "name": "Goblin", "level": 5, "hp": 120, "atk": 12, "zone": 1, "x": 300, "y": 0, "z": 200},\n'
        '    {"id": 1002, "name": "Goblin", "level": 5, "hp": 120, "atk": 12, "zone": 1, "x": 350, "y": 0, "z": 250},\n'
        '    {"id": 1002, "name": "Goblin", "level": 5, "hp": 120, "atk": 12, "zone": 1, "x": 400, "y": 0, "z": 180},\n'
        '    {"id": 1003, "name": "Wolf", "level": 5, "hp": 180, "atk": 20, "zone": 1, "x": 500, "y": 0, "z": 400},\n'
        '    {"id": 1003, "name": "Wolf", "level": 5, "hp": 180, "atk": 20, "zone": 1, "x": 550, "y": 0, "z": 350},\n'
        '    {"id": 1004, "name": "Bear", "level": 7, "hp": 350, "atk": 30, "zone": 1, "x": 700, "y": 0, "z": 500},\n'
        '    {"id": 1007, "name": "Bandit", "level": 8, "hp": 300, "atk": 25, "zone": 1, "x": 800, "y": 0, "z": 700},\n'
        '    {"id": 1007, "name": "Bandit", "level": 8, "hp": 300, "atk": 25, "zone": 1, "x": 850, "y": 0, "z": 650},\n'
        '    # ──── Field zone 2: 어둠의 숲 (Lv.8~15) ────\n'
        '    {"id": 1005, "name": "Skeleton", "level": 8, "hp": 200, "atk": 25, "zone": 2, "x": 100, "y": 0, "z": 100},\n'
        '    {"id": 1005, "name": "Skeleton", "level": 8, "hp": 200, "atk": 25, "zone": 2, "x": 200, "y": 0, "z": 150},\n'
        '    {"id": 1005, "name": "Skeleton", "level": 10, "hp": 250, "atk": 30, "zone": 2, "x": 400, "y": 0, "z": 300},\n'
        '    {"id": 1006, "name": "Orc", "level": 10, "hp": 400, "atk": 35, "zone": 2, "x": 300, "y": 0, "z": 200},\n'
        '    {"id": 1006, "name": "Orc", "level": 12, "hp": 450, "atk": 40, "zone": 2, "x": 500, "y": 0, "z": 400},\n'
        '    {"id": 1004, "name": "Bear", "level": 12, "hp": 500, "atk": 40, "zone": 2, "x": 800, "y": 0, "z": 600},\n'
        '    {"id": 1007, "name": "Bandit", "level": 12, "hp": 350, "atk": 38, "zone": 2, "x": 600, "y": 0, "z": 500},\n'
        '    {"id": 2001, "name": "EliteGolem", "level": 15, "hp": 3000, "atk": 120, "zone": 2, "x": 1000, "y": 0, "z": 1000},\n'
        '    # ──── Field zone 3: 얼어붙은 봉우리 (Lv.15~20) ────\n'
        '    {"id": 1008, "name": "IceGolem", "level": 15, "hp": 600, "atk": 45, "zone": 3, "x": 200, "y": 0, "z": 200},\n'
        '    {"id": 1008, "name": "IceGolem", "level": 15, "hp": 600, "atk": 45, "zone": 3, "x": 400, "y": 0, "z": 300},\n'
        '    {"id": 1009, "name": "FrostWolf", "level": 15, "hp": 350, "atk": 35, "zone": 3, "x": 500, "y": 0, "z": 500},\n'
        '    {"id": 1009, "name": "FrostWolf", "level": 15, "hp": 350, "atk": 35, "zone": 3, "x": 600, "y": 0, "z": 400},\n'
        '    {"id": 1010, "name": "Yeti", "level": 18, "hp": 800, "atk": 55, "zone": 3, "x": 800, "y": 0, "z": 800},\n'
        '    {"id": 1005, "name": "Skeleton", "level": 18, "hp": 300, "atk": 50, "zone": 3, "x": 1000, "y": 0, "z": 600},\n'
        '    {"id": 2002, "name": "IceQueenElite", "level": 18, "hp": 2500, "atk": 100, "zone": 3, "x": 1500, "y": 0, "z": 1500},\n'
    )

    replacements.append((old_spawns, new_spawns))

    # 2. ZONE_BOUNDS에 던전 존 추가
    replacements.append((
        '    10: {"min_x": 0, "max_x": 300, "min_z": 0, "max_z": 300},     # village\n}',
        '    10: {"min_x": 0, "max_x": 300, "min_z": 0, "max_z": 300},     # village\n'
        '    # 던전 존 (인스턴스)\n'
        '    100: {"min_x": 0, "max_x": 500, "min_z": 0, "max_z": 500},    # goblin_cave\n'
        '    101: {"min_x": 0, "max_x": 800, "min_z": 0, "max_z": 800},    # frozen_temple\n'
        '    102: {"min_x": 0, "max_x": 600, "min_z": 0, "max_z": 600},    # demon_fortress\n'
        '    103: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},  # ancient_dragon_raid\n'
        '}'
    ))

    # 3. 던전 데이터 + 매칭 상수 (ENHANCE_COST_BASE 뒤에)
    replacements.append((
        "ENHANCE_COST_BASE = 500  # 강화 비용 = base * level\n\n# 이동 상수",
        "ENHANCE_COST_BASE = 500  # 강화 비용 = base * level\n\n"
        "# ──── 던전 목록 데이터 (P2_S03_S01) ────\n"
        "DUNGEON_LIST_DATA = [\n"
        '    {"id": 1, "name": "고블린 동굴",    "type": "party", "min_level": 15, "stages": 3, "zone_id": 100, "party_size": 4, "boss_id": 3004, "boss_hp": 30000},\n'
        '    {"id": 2, "name": "얼어붙은 신전",  "type": "party", "min_level": 25, "stages": 4, "zone_id": 101, "party_size": 4, "boss_id": 3005, "boss_hp": 80000},\n'
        '    {"id": 3, "name": "마왕의 요새",    "type": "abyss", "min_level": 40, "stages": 3, "zone_id": 102, "party_size": 4, "boss_id": 3003, "boss_hp": 200000},\n'
        '    {"id": 4, "name": "고대 용의 둥지", "type": "raid",  "min_level": 50, "stages": 1, "zone_id": 103, "party_size": 8, "boss_id": 3002, "boss_hp": 2000000},\n'
        "]\n\n"
        "MATCH_TIMEOUT = 300  # 매칭 최대 대기 5분\n"
        "MATCH_FLEX_AFTER = 120  # 2분 후 조건 완화\n\n"
        "# 던전 난이도 보정\n"
        "DIFFICULTY_MULT = {\n"
        '    "normal": {"hp": 1.0, "atk": 1.0, "reward": 1.0},\n'
        '    "hard":   {"hp": 2.0, "atk": 1.5, "reward": 2.0},\n'
        '    "hell":   {"hp": 4.0, "atk": 2.5, "reward": 4.0},\n'
        "}\n\n"
        "# 이동 상수"
    ))

    # 4. BridgeServer.__init__에 던전/매칭 필드 추가
    replacements.append((
        '        self.npcs: Dict[int, dict] = {}  # entity_id -> npc data\n',
        '        self.npcs: Dict[int, dict] = {}  # entity_id -> npc data\n'
        '        self.instances: Dict[int, dict] = {}  # instance_id -> instance data\n'
        '        self.next_instance_id = 1\n'
        '        self.match_queue: Dict[int, dict] = {}  # dungeon_id -> {players: [], created_at: float}\n'
    ))

    # 5. _dispatch 핸들러 등록 (ENHANCE_REQ 뒤에)
    replacements.append((
        '            MsgType.ENHANCE_REQ: self._on_enhance_req,\n        }',
        '            MsgType.ENHANCE_REQ: self._on_enhance_req,\n'
        '            MsgType.MATCH_ENQUEUE: self._on_match_enqueue,\n'
        '            MsgType.MATCH_DEQUEUE: self._on_match_dequeue,\n'
        '            MsgType.MATCH_ACCEPT: self._on_match_accept,\n'
        '            MsgType.INSTANCE_ENTER: self._on_instance_enter,\n'
        '            MsgType.INSTANCE_LEAVE: self._on_instance_leave,\n'
        '        }'
    ))

    # 6. 핸들러 구현 (_on_enhance_req 끝나는 곳 뒤에 삽입)
    # _on_enhance_req 마지막 줄 뒤에 추가
    replacements.append((
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 5, current_level))  # 5=FAIL (level preserved)\n\n'
        '    # ━━━ 몬스터 시스템 ━━━',
        '            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 5, current_level))  # 5=FAIL (level preserved)\n\n'
        '    # ━━━ 던전 매칭 시스템 (P2_S03_S01) ━━━\n\n'
        '    async def _on_match_enqueue(self, session: PlayerSession, payload: bytes):\n'
        '        """MATCH_ENQUEUE: dungeon_id(u8) + difficulty(u8). 매칭 큐에 등록."""\n'
        '        if not session.in_game or len(payload) < 2:\n'
        '            return\n'
        '        dungeon_id = payload[0]\n'
        '        difficulty = payload[1]  # 0=normal, 1=hard, 2=hell\n'
        '        dungeon = next((d for d in DUNGEON_LIST_DATA if d["id"] == dungeon_id), None)\n'
        '        if not dungeon:\n'
        '            # result: 1=INVALID_DUNGEON\n'
        '            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 1, 0))\n'
        '            return\n'
        '        if session.stats.level < dungeon["min_level"]:\n'
        '            # result: 2=LEVEL_TOO_LOW\n'
        '            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 2, 0))\n'
        '            return\n'
        '        import time as _time\n'
        '        queue_key = dungeon_id\n'
        '        if queue_key not in self.match_queue:\n'
        '            self.match_queue[queue_key] = {"players": [], "created_at": _time.time(), "difficulty": difficulty}\n'
        '        queue = self.match_queue[queue_key]\n'
        '        # 중복 등록 방지\n'
        '        if any(p["session"] is session for p in queue["players"]):\n'
        '            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 3, len(queue["players"])))\n'
        '            return\n'
        '        queue["players"].append({"session": session, "joined_at": _time.time()})\n'
        '        self.log(f"MatchQueue: {session.char_name} joined dungeon={dungeon_id} ({len(queue[\'players\'])}/{dungeon[\'party_size\']})", "GAME")\n'
        '        # result: 0=QUEUED, count=현재 인원\n'
        '        self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 0, len(queue["players"])))\n'
        '        # 파티 모집 완료 확인\n'
        '        if len(queue["players"]) >= dungeon["party_size"]:\n'
        '            await self._match_found(queue_key, dungeon)\n\n'
        '    async def _match_found(self, queue_key: int, dungeon: dict):\n'
        '        """매칭 완료 → 인스턴스 생성 → MATCH_FOUND 전송"""\n'
        '        queue = self.match_queue.pop(queue_key, None)\n'
        '        if not queue:\n'
        '            return\n'
        '        inst_id = self.next_instance_id\n'
        '        self.next_instance_id += 1\n'
        '        diff_name = ["normal", "hard", "hell"][queue.get("difficulty", 0)]\n'
        '        mult = DIFFICULTY_MULT.get(diff_name, DIFFICULTY_MULT["normal"])\n'
        '        instance = {\n'
        '            "id": inst_id,\n'
        '            "dungeon_id": dungeon["id"],\n'
        '            "dungeon_name": dungeon["name"],\n'
        '            "zone_id": dungeon["zone_id"],\n'
        '            "difficulty": queue.get("difficulty", 0),\n'
        '            "boss_hp": int(dungeon["boss_hp"] * mult["hp"]),\n'
        '            "boss_current_hp": int(dungeon["boss_hp"] * mult["hp"]),\n'
        '            "stage": 1,\n'
        '            "max_stages": dungeon["stages"],\n'
        '            "players": [p["session"] for p in queue["players"]],\n'
        '            "active": True,\n'
        '        }\n'
        '        self.instances[inst_id] = instance\n'
        '        self.log(f"Instance #{inst_id} created: {dungeon[\'name\']} ({diff_name}) with {len(instance[\'players\'])} players", "GAME")\n'
        '        # MATCH_FOUND: instance_id(u32) + dungeon_id(u8) + difficulty(u8)\n'
        '        for s in instance["players"]:\n'
        '            self._send(s, MsgType.MATCH_FOUND, struct.pack("<IBB", inst_id, dungeon["id"], instance["difficulty"]))\n\n'
        '    async def _on_match_dequeue(self, session: PlayerSession, payload: bytes):\n'
        '        """MATCH_DEQUEUE: dungeon_id(u8). 매칭 큐에서 이탈."""\n'
        '        if not session.in_game or len(payload) < 1:\n'
        '            return\n'
        '        dungeon_id = payload[0]\n'
        '        queue = self.match_queue.get(dungeon_id)\n'
        '        if queue:\n'
        '            queue["players"] = [p for p in queue["players"] if p["session"] is not session]\n'
        '            if not queue["players"]:\n'
        '                del self.match_queue[dungeon_id]\n'
        '        self.log(f"MatchQueue: {session.char_name} left dungeon={dungeon_id}", "GAME")\n'
        '        self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 4, 0))  # 4=DEQUEUED\n\n'
        '    async def _on_match_accept(self, session: PlayerSession, payload: bytes):\n'
        '        """MATCH_ACCEPT: instance_id(u32). 매칭 수락 (현재는 자동 수락)."""\n'
        '        if not session.in_game or len(payload) < 4:\n'
        '            return\n'
        '        inst_id = struct.unpack("<I", payload[:4])[0]\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not instance or not instance["active"]:\n'
        '            return\n'
        '        # INSTANCE_INFO 전송\n'
        '        await self._send_instance_info(session, instance)\n\n'
        '    async def _send_instance_info(self, session: PlayerSession, instance: dict):\n'
        '        """인스턴스 정보 전송"""\n'
        '        name_bytes = instance["dungeon_name"].encode("utf-8")[:32].ljust(32, b"\\x00")\n'
        '        buf = struct.pack("<IBB", instance["id"], instance["dungeon_id"], instance["difficulty"])\n'
        '        buf += name_bytes\n'
        '        buf += struct.pack("<BBII", instance["stage"], instance["max_stages"],\n'
        '                           instance["boss_hp"], instance["boss_current_hp"])\n'
        '        buf += struct.pack("<B", len(instance["players"]))\n'
        '        self._send(session, MsgType.INSTANCE_INFO, buf)\n\n'
        '    async def _on_instance_enter(self, session: PlayerSession, payload: bytes):\n'
        '        """INSTANCE_ENTER: instance_id(u32). 던전 인스턴스 입장."""\n'
        '        if not session.in_game or len(payload) < 4:\n'
        '            return\n'
        '        inst_id = struct.unpack("<I", payload[:4])[0]\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not instance or not instance["active"]:\n'
        '            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 1))  # 1=NOT_FOUND\n'
        '            return\n'
        '        if session not in instance["players"]:\n'
        '            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 2))  # 2=NOT_MEMBER\n'
        '            return\n'
        '        # 존 전환\n'
        '        old_zone = session.zone_id\n'
        '        session.zone_id = instance["zone_id"]\n'
        '        session.pos.x = 50.0\n'
        '        session.pos.y = 0.0\n'
        '        session.pos.z = 50.0\n'
        '        self.log(f"InstanceEnter: {session.char_name} → Instance#{inst_id} zone={instance[\'zone_id\']}", "GAME")\n'
        '        await self._send_instance_info(session, instance)\n\n'
        '    async def _on_instance_leave(self, session: PlayerSession, payload: bytes):\n'
        '        """INSTANCE_LEAVE: instance_id(u32). 던전 퇴장."""\n'
        '        if not session.in_game or len(payload) < 4:\n'
        '            return\n'
        '        inst_id = struct.unpack("<I", payload[:4])[0]\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not instance:\n'
        '            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 1))\n'
        '            return\n'
        '        if session in instance["players"]:\n'
        '            instance["players"].remove(session)\n'
        '        if not instance["players"]:\n'
        '            instance["active"] = False\n'
        '            self.log(f"Instance #{inst_id} closed (no players left)", "GAME")\n'
        '        # 마을로 복귀\n'
        '        session.zone_id = 10\n'
        '        session.pos.x = 150.0\n'
        '        session.pos.y = 0.0\n'
        '        session.pos.z = 150.0\n'
        '        self.log(f"InstanceLeave: {session.char_name} ← Instance#{inst_id}", "GAME")\n'
        '        self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 0))  # 0=OK\n\n'
        '    # ━━━ 몬스터 시스템 ━━━'
    ))

    for old, new in replacements:
        if old not in content:
            print(f'[bridge] WARNING: Pattern not found:\n  {repr(old[:80])}...')
            continue
        content = content.replace(old, new, 1)

    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    # Verify
    checks = ['DUNGEON_LIST_DATA', '_on_match_enqueue', '_on_match_dequeue',
              '_on_match_accept', '_on_instance_enter', '_on_instance_leave',
              '_match_found', 'MATCH_TIMEOUT', 'DIFFICULTY_MULT',
              'IceGolem', 'FrostWolf', 'Yeti', 'Bandit', 'EliteGolem',
              '"zone_id": 100', '"zone_id": 101']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S035 patched OK')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_field_monsters_expanded' in content:
        print('[test] S035 already patched')
        return True

    new_tests = r'''
    # ━━━ 필드 몬스터 확장 / 던전 매칭 (S035) ━━━

    async def test_field_monsters_expanded():
        """P2_S01_S01: 필드 존별 다양한 몬스터가 스폰되었는지 확인"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'fldmon01' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        packets = await c.recv_all_packets(timeout=1.0)
        spawns = [p for mt, p in packets if mt == MsgType.MONSTER_SPAWN]
        # 최소 11개 zone-1 몬스터 + 8개 zone-2 + 7개 zone-3 = 26+ (+ 4 tutorial)
        assert len(spawns) >= 20, f"Expected >= 20 MONSTER_SPAWN packets, got {len(spawns)}"
        c.close()

    await test("FIELD_MONSTERS: 필드 존 몬스터 다양화 확인", test_field_monsters_expanded())

    async def test_match_enqueue_level_low():
        """P2_S03_S01: 레벨 부족 시 매칭 거부"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'matchlv1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # 레벨 1 상태에서 min_level=15 던전 매칭 시도
        await c.send(MsgType.MATCH_ENQUEUE, struct.pack('<BB', 1, 0))  # dungeon_id=1, normal
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.MATCH_STATUS
        assert payload[1] == 2, f"Expected LEVEL_TOO_LOW(2), got {payload[1]}"
        c.close()

    await test("MATCH_LEVEL: 레벨 부족 매칭 거부", test_match_enqueue_level_low())

    async def test_match_enqueue_invalid_dungeon():
        """P2_S03_S01: 존재하지 않는 던전 매칭 거부"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'matchiv1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        await c.send(MsgType.MATCH_ENQUEUE, struct.pack('<BB', 99, 0))  # 존재하지 않는 던전
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.MATCH_STATUS
        assert payload[1] == 1, f"Expected INVALID_DUNGEON(1), got {payload[1]}"
        c.close()

    await test("MATCH_INVALID: 잘못된 던전 ID 매칭 거부", test_match_enqueue_invalid_dungeon())

    async def test_match_enqueue_and_dequeue():
        """P2_S03_S01: 매칭 등록 및 취소"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'matchdq1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # 레벨 올려서 매칭 가능하게
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_all_packets(timeout=0.5)
        # 매칭 등록
        await c.send(MsgType.MATCH_ENQUEUE, struct.pack('<BB', 1, 0))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.MATCH_STATUS
        assert payload[1] == 0, f"Expected QUEUED(0), got {payload[1]}"
        # 매칭 취소
        await c.send(MsgType.MATCH_DEQUEUE, struct.pack('<B', 1))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.MATCH_STATUS
        assert payload[1] == 4, f"Expected DEQUEUED(4), got {payload[1]}"
        c.close()

    await test("MATCH_QUEUE: 매칭 등록 및 취소", test_match_enqueue_and_dequeue())

    async def test_match_found_full_party():
        """P2_S03_S01: 4인 매칭 완료 → MATCH_FOUND + 인스턴스 생성"""
        clients = []
        for i in range(4):
            c = TestClient()
            await c.connect('127.0.0.1', port)
            await asyncio.sleep(0.05)
            name = f'mf{i:02d}test'.encode('utf-8')
            await c.send(MsgType.LOGIN, struct.pack('<B', len(name)) + name + struct.pack('<B', 2) + b'pw')
            await c.recv_packet()
            await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
            await c.recv_all_packets(timeout=1.0)
            # 레벨업
            await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
            await c.recv_all_packets(timeout=0.5)
            clients.append(c)
        # 4명 순차 등록
        for i, c in enumerate(clients):
            await c.send(MsgType.MATCH_ENQUEUE, struct.pack('<BB', 1, 0))
            msg_type, payload = await c.recv_packet()
            assert msg_type == MsgType.MATCH_STATUS
            if i < 3:
                assert payload[1] == 0, f"Client {i}: Expected QUEUED(0), got {payload[1]}"
            else:
                # 4번째: QUEUED 받은 후 MATCH_FOUND도 받아야 함
                # QUEUED가 먼저 올 수도 있고 MATCH_FOUND가 먼저 올 수도 있음
                pass
        # 모든 클라이언트가 MATCH_FOUND를 받아야 함
        found_count = 0
        instance_ids = set()
        for c in clients:
            packets = await c.recv_all_packets(timeout=1.0)
            for mt, pl in packets:
                if mt == MsgType.MATCH_FOUND:
                    found_count += 1
                    inst_id = struct.unpack_from('<I', pl, 0)[0]
                    instance_ids.add(inst_id)
        # 마지막 클라이언트는 이미 MATCH_FOUND를 STATUS와 함께 받았을 수 있음
        assert found_count >= 3, f"Expected >= 3 MATCH_FOUND, got {found_count}"
        assert len(instance_ids) >= 1, "Expected at least 1 instance"
        # 인스턴스 정보 요청
        inst_id = list(instance_ids)[0]
        await clients[0].send(MsgType.MATCH_ACCEPT, struct.pack('<I', inst_id))
        msg_type, payload = await clients[0].recv_packet()
        assert msg_type == MsgType.INSTANCE_INFO, f"Expected INSTANCE_INFO, got {msg_type}"
        # 인스턴스 퇴장
        await clients[0].send(MsgType.INSTANCE_LEAVE, struct.pack('<I', inst_id))
        msg_type, payload = await clients[0].recv_packet()
        assert msg_type == MsgType.INSTANCE_LEAVE_RESULT
        assert payload[4] == 0, f"Expected OK(0), got {payload[4]}"
        for c in clients:
            c.close()

    await test("MATCH_FOUND: 4인 파티 매칭 완료 + 인스턴스", test_match_found_full_party())

    async def test_instance_enter_leave():
        """P2_S03_S01: 인스턴스 입장/퇴장 + 존 전환"""
        clients = []
        for i in range(4):
            c = TestClient()
            await c.connect('127.0.0.1', port)
            await asyncio.sleep(0.05)
            name = f'ie{i:02d}test'.encode('utf-8')
            await c.send(MsgType.LOGIN, struct.pack('<B', len(name)) + name + struct.pack('<B', 2) + b'pw')
            await c.recv_packet()
            await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
            await c.recv_all_packets(timeout=1.0)
            await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
            await c.recv_all_packets(timeout=0.5)
            clients.append(c)
        # 매칭
        for c in clients:
            await c.send(MsgType.MATCH_ENQUEUE, struct.pack('<BB', 1, 0))
            await c.recv_packet()
        await asyncio.sleep(0.5)
        # MATCH_FOUND에서 instance_id 수집
        inst_id = None
        for c in clients:
            packets = await c.recv_all_packets(timeout=1.0)
            for mt, pl in packets:
                if mt == MsgType.MATCH_FOUND:
                    inst_id = struct.unpack_from('<I', pl, 0)[0]
        assert inst_id is not None, "No MATCH_FOUND received"
        # 입장
        await clients[0].send(MsgType.INSTANCE_ENTER, struct.pack('<I', inst_id))
        msg_type, payload = await clients[0].recv_packet()
        assert msg_type == MsgType.INSTANCE_INFO
        # 퇴장
        await clients[0].send(MsgType.INSTANCE_LEAVE, struct.pack('<I', inst_id))
        msg_type, payload = await clients[0].recv_packet()
        assert msg_type == MsgType.INSTANCE_LEAVE_RESULT
        assert payload[4] == 0
        for c in clients:
            c.close()

    await test("INSTANCE: 던전 입장 + 퇴장 + 존 전환", test_instance_enter_leave())

'''

    marker = '    # \u2501\u2501\u2501 \uacb0\uacfc \u2501\u2501\u2501'
    if marker not in content:
        print('[test] WARNING: Result section marker not found')
        return False

    content = content.replace(marker, new_tests + marker, 1)

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    if 'test_field_monsters_expanded' in content and 'test_match_found_full_party' in content:
        print('[test] S035 patched OK')
        return True
    else:
        print('[test] S035 FAILED')
        return False


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS035 all patches applied!')
    else:
        print('\nSome patches failed!')
        sys.exit(1)
