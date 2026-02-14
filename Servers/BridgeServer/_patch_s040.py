"""
Patch S040: Phase 3 클라이언트 연동 호환성 패치
- INSTANCE_CREATE(170) 핸들러 추가: 클라이언트가 직접 던전 생성 (단독 입장)
- MATCH_ENQUEUE: <BB>(서버 테스트) + <I>(클라이언트 테스트) 듀얼 포맷 지원
- MATCH_DEQUEUE: 빈 페이로드 지원 (클라이언트는 payload 없이 전송)
- INSTANCE_LEAVE: 빈 페이로드 지원 (세션의 현재 인스턴스에서 자동 퇴장)
- MATCH_STATUS 응답: 클라이언트 예상 포맷 <BI>(status + queue_pos u32) 호환
"""
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if '_on_instance_create' in content:
        print('[bridge] S040 already patched')
        return True

    replacements = []

    # 1. 디스패치 테이블에 INSTANCE_CREATE 핸들러 추가
    replacements.append((
        '            MsgType.INSTANCE_ENTER: self._on_instance_enter,\n'
        '            MsgType.INSTANCE_LEAVE: self._on_instance_leave,',
        '            MsgType.INSTANCE_CREATE: self._on_instance_create,\n'
        '            MsgType.INSTANCE_ENTER: self._on_instance_enter,\n'
        '            MsgType.INSTANCE_LEAVE: self._on_instance_leave,'
    ))

    # 2. _on_match_enqueue 수정: 듀얼 포맷 지원 (<BB> 또는 <I>)
    # 기존: payload[0]=dungeon_id(u8), payload[1]=difficulty(u8), 최소 2바이트
    # 클라이언트: struct.pack('<I', dungeon_type), 4바이트
    # MATCH_STATUS 응답도 클라이언트 호환: <BI> (status u8 + queue_pos u32)
    replacements.append((
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
        '            await self._match_found(queue_key, dungeon)\n',
        '    async def _on_match_enqueue(self, session: PlayerSession, payload: bytes):\n'
        '        """MATCH_ENQUEUE: dungeon_id(u8)+difficulty(u8) 또는 dungeon_id(u32). 매칭 큐 등록."""\n'
        '        if not session.in_game or len(payload) < 1:\n'
        '            return\n'
        '        # 듀얼 포맷 감지: 4바이트 && byte[1]==0 && byte[2]==0 && byte[3]==0 → u32\n'
        '        if len(payload) == 4 and payload[2] == 0 and payload[3] == 0:\n'
        '            import struct as _st\n'
        '            dungeon_id = _st.unpack("<I", payload[:4])[0]\n'
        '            difficulty = 0\n'
        '            is_client_format = True\n'
        '        else:\n'
        '            dungeon_id = payload[0]\n'
        '            difficulty = payload[1] if len(payload) >= 2 else 0\n'
        '            is_client_format = False\n'
        '        dungeon = next((d for d in DUNGEON_LIST_DATA if d["id"] == dungeon_id), None)\n'
        '        if not dungeon:\n'
        '            if is_client_format:\n'
        '                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 1, 0))\n'
        '            else:\n'
        '                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 1, 0))\n'
        '            return\n'
        '        if session.stats.level < dungeon["min_level"]:\n'
        '            if is_client_format:\n'
        '                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 2, 0))\n'
        '            else:\n'
        '                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 2, 0))\n'
        '            return\n'
        '        import time as _time\n'
        '        queue_key = dungeon_id\n'
        '        if queue_key not in self.match_queue:\n'
        '            self.match_queue[queue_key] = {"players": [], "created_at": _time.time(), "difficulty": difficulty}\n'
        '        queue = self.match_queue[queue_key]\n'
        '        if any(p["session"] is session for p in queue["players"]):\n'
        '            if is_client_format:\n'
        '                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 3, len(queue["players"])))\n'
        '            else:\n'
        '                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 3, len(queue["players"])))\n'
        '            return\n'
        '        queue["players"].append({"session": session, "joined_at": _time.time()})\n'
        '        session._match_queue_key = queue_key\n'
        '        session._match_client_format = is_client_format\n'
        '        self.log(f"MatchQueue: {session.char_name} joined dungeon={dungeon_id} ({len(queue[\'players\'])}/{dungeon[\'party_size\']})", "GAME")\n'
        '        if is_client_format:\n'
        '            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 0, len(queue["players"])))\n'
        '        else:\n'
        '            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 0, len(queue["players"])))\n'
        '        if len(queue["players"]) >= dungeon["party_size"]:\n'
        '            await self._match_found(queue_key, dungeon)\n'
    ))

    # 3. _on_match_dequeue 수정: 빈 페이로드 지원
    replacements.append((
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
        '        self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 4, 0))  # 4=DEQUEUED\n',
        '    async def _on_match_dequeue(self, session: PlayerSession, payload: bytes):\n'
        '        """MATCH_DEQUEUE: dungeon_id(u8) 또는 빈 페이로드. 매칭 큐 이탈."""\n'
        '        if not session.in_game:\n'
        '            return\n'
        '        if len(payload) >= 1:\n'
        '            dungeon_id = payload[0]\n'
        '            queue = self.match_queue.get(dungeon_id)\n'
        '            if queue:\n'
        '                queue["players"] = [p for p in queue["players"] if p["session"] is not session]\n'
        '                if not queue["players"]:\n'
        '                    del self.match_queue[dungeon_id]\n'
        '            self.log(f"MatchQueue: {session.char_name} left dungeon={dungeon_id}", "GAME")\n'
        '            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 4, 0))  # 4=DEQUEUED\n'
        '        else:\n'
        '            # 빈 페이로드: 세션이 참여 중인 모든 큐에서 제거\n'
        '            removed_key = getattr(session, "_match_queue_key", None)\n'
        '            for qk in list(self.match_queue.keys()):\n'
        '                queue = self.match_queue[qk]\n'
        '                queue["players"] = [p for p in queue["players"] if p["session"] is not session]\n'
        '                if not queue["players"]:\n'
        '                    del self.match_queue[qk]\n'
        '            self.log(f"MatchQueue: {session.char_name} dequeued (all)", "GAME")\n'
    ))

    # 4. _on_instance_leave 수정: 빈 페이로드 지원 + 응답 포맷 호환
    replacements.append((
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
        '        self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 0))  # 0=OK\n',
        '    async def _on_instance_leave(self, session: PlayerSession, payload: bytes):\n'
        '        """INSTANCE_LEAVE: instance_id(u32) 또는 빈 페이로드. 던전 퇴장."""\n'
        '        if not session.in_game:\n'
        '            return\n'
        '        if len(payload) >= 4:\n'
        '            inst_id = struct.unpack("<I", payload[:4])[0]\n'
        '            is_client_format = False\n'
        '        else:\n'
        '            # 빈 페이로드: 세션의 현재 인스턴스 찾기\n'
        '            inst_id = getattr(session, "_current_instance_id", None)\n'
        '            if inst_id is None:\n'
        '                # 인스턴스에 있는지 스캔\n'
        '                for iid, inst in self.instances.items():\n'
        '                    if inst.get("active") and session in inst.get("players", []):\n'
        '                        inst_id = iid\n'
        '                        break\n'
        '            if inst_id is None:\n'
        '                self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<B", 1))  # 1=NOT_FOUND\n'
        '                return\n'
        '            is_client_format = True\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not instance:\n'
        '            if is_client_format:\n'
        '                self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<B", 1))\n'
        '            else:\n'
        '                self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 1))\n'
        '            return\n'
        '        if session in instance["players"]:\n'
        '            instance["players"].remove(session)\n'
        '        if not instance["players"]:\n'
        '            instance["active"] = False\n'
        '            self.log(f"Instance #{inst_id} closed (no players left)", "GAME")\n'
        '        session.zone_id = 10\n'
        '        session.pos.x = 150.0\n'
        '        session.pos.y = 0.0\n'
        '        session.pos.z = 150.0\n'
        '        session._current_instance_id = None\n'
        '        self.log(f"InstanceLeave: {session.char_name} <- Instance#{inst_id}", "GAME")\n'
        '        if is_client_format:\n'
        '            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<B", 0))  # 0=OK\n'
        '        else:\n'
        '            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 0))  # 0=OK\n'
    ))

    # 5. INSTANCE_CREATE 핸들러 추가 (던전 매칭 시스템 섹션 앞)
    # _on_instance_enter 앞에 새 핸들러 삽입
    replacements.append((
        '    async def _on_instance_enter(self, session: PlayerSession, payload: bytes):\n'
        '        """INSTANCE_ENTER: instance_id(u32). 던전 인스턴스 입장."""',
        '    async def _on_instance_create(self, session: PlayerSession, payload: bytes):\n'
        '        """INSTANCE_CREATE: dungeon_type(u32). 즉시 인스턴스 생성 + 입장."""\n'
        '        if not session.in_game or len(payload) < 4:\n'
        '            return\n'
        '        dungeon_type = struct.unpack("<I", payload[:4])[0]\n'
        '        # 던전 데이터에서 찾기\n'
        '        dungeon = next((d for d in DUNGEON_LIST_DATA if d["id"] == dungeon_type), None)\n'
        '        if not dungeon:\n'
        '            # 기본 던전 데이터 생성 (클라이언트 테스트용)\n'
        '            dungeon = {"id": dungeon_type, "name": f"Dungeon_{dungeon_type}", "type": "party",\n'
        '                       "min_level": 1, "stages": 1, "zone_id": 100, "party_size": 4,\n'
        '                       "boss_id": 0, "boss_hp": 10000}\n'
        '        inst_id = self.next_instance_id\n'
        '        self.next_instance_id += 1\n'
        '        instance = {\n'
        '            "id": inst_id,\n'
        '            "dungeon_id": dungeon["id"],\n'
        '            "dungeon_name": dungeon["name"],\n'
        '            "zone_id": dungeon.get("zone_id", 100),\n'
        '            "difficulty": 0,\n'
        '            "boss_hp": dungeon.get("boss_hp", 10000),\n'
        '            "boss_current_hp": dungeon.get("boss_hp", 10000),\n'
        '            "stage": 1,\n'
        '            "max_stages": dungeon.get("stages", 1),\n'
        '            "players": [session],\n'
        '            "active": True,\n'
        '        }\n'
        '        self.instances[inst_id] = instance\n'
        '        session._current_instance_id = inst_id\n'
        '        session.zone_id = dungeon.get("zone_id", 100)\n'
        '        session.pos.x = 50.0\n'
        '        session.pos.y = 0.0\n'
        '        session.pos.z = 50.0\n'
        '        self.log(f"InstanceCreate: {session.char_name} -> Instance#{inst_id} dungeon={dungeon_type}", "GAME")\n'
        '        # INSTANCE_ENTER 응답: result(u8) + instance_id(u32) + dungeon_type(u32)\n'
        '        self._send(session, MsgType.INSTANCE_ENTER, struct.pack("<BII", 0, inst_id, dungeon_type))\n\n'
        '    async def _on_instance_enter(self, session: PlayerSession, payload: bytes):\n'
        '        """INSTANCE_ENTER: instance_id(u32). 던전 인스턴스 입장."""'
    ))

    # Apply all replacements
    for old, new in replacements:
        if old not in content:
            print(f'[bridge] WARNING: Pattern not found:\n  {repr(old[:100])}...')
            continue
        content = content.replace(old, new, 1)

    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    # Verify
    checks = [
        '_on_instance_create', 'INSTANCE_CREATE: dungeon_type',
        'is_client_format', '_match_queue_key', '_current_instance_id',
        'MsgType.INSTANCE_CREATE: self._on_instance_create',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S040 patched OK')
    return True


if __name__ == '__main__':
    ok = patch_bridge()
    if ok:
        print('\nS040 all patches applied!')
    else:
        print('\nS040 PATCH FAILED!')
        sys.exit(1)
