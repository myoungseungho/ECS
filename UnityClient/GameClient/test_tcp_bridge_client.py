"""
Client-side TCP Bridge Integration Test
========================================
클라이언트 에이전트가 서버 TCP 브릿지와 실제 연동 테스트를 수행.
PacketDefinitions.cs / PacketBuilder.cs와 동일한 바이너리 프로토콜 사용.
S035 Phase 2 테스트 시나리오 11단계 + 추가 검증.

사용법:
  1. 서버 실행: cd Servers/BridgeServer && python tcp_bridge.py
  2. 테스트 실행: python test_tcp_bridge_client.py [--host HOST] [--port PORT]
"""

import asyncio
import struct
import sys
import time
import argparse

# Windows cp949 환경 UnicodeEncodeError 방지 (S038 권고)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


# ━━━ 패킷 프로토콜 상수 ━━━
HEADER_SIZE = 6  # 4(length LE) + 2(type LE)
MAX_PACKET_SIZE = 8192


# ━━━ MsgType (PacketDefinitions.cs 미러) ━━━
class MsgType:
    ECHO = 1
    PING = 2
    MOVE = 10
    MOVE_BROADCAST = 11
    POS_QUERY = 12
    APPEAR = 13
    DISAPPEAR = 14
    POSITION_CORRECTION = 15
    CHANNEL_JOIN = 20
    CHANNEL_INFO = 22
    ZONE_ENTER = 30
    ZONE_INFO = 31
    LOGIN = 60
    LOGIN_RESULT = 61
    CHAR_LIST_REQ = 62
    CHAR_LIST_RESP = 63
    CHAR_SELECT = 64
    ENTER_GAME = 65
    STAT_QUERY = 90
    STAT_SYNC = 91
    ATTACK_REQ = 100
    ATTACK_RESULT = 101
    COMBAT_DIED = 102
    MONSTER_SPAWN = 110
    MONSTER_MOVE = 111
    MONSTER_RESPAWN = 113
    ZONE_TRANSFER_REQ = 120
    ZONE_TRANSFER_RESULT = 121
    SKILL_LIST_REQ = 150
    SKILL_LIST_RESP = 151
    SKILL_USE = 152
    SKILL_RESULT = 153
    INVENTORY_REQ = 190
    INVENTORY_RESP = 191
    BUFF_LIST_REQ = 200
    BUFF_LIST_RESP = 201
    QUEST_LIST_REQ = 230
    QUEST_LIST_RESP = 231
    QUEST_ACCEPT_RESULT = 233
    CHAT_SEND = 240
    CHAT_MESSAGE = 241
    SYSTEM_MESSAGE = 244
    SERVER_LIST_REQ = 320
    SERVER_LIST = 321
    CHARACTER_LIST_REQ = 322
    CHARACTER_LIST = 323
    CHARACTER_CREATE = 324
    CHARACTER_CREATE_RESULT = 325
    CHARACTER_DELETE = 326
    CHARACTER_DELETE_RESULT = 327
    TUTORIAL_STEP_COMPLETE = 330
    TUTORIAL_REWARD = 331
    NPC_INTERACT = 332
    NPC_DIALOG = 333
    ENHANCE_REQ = 340
    ENHANCE_RESULT = 341
    # Phase 3: Instance/Matching
    INSTANCE_CREATE = 170
    INSTANCE_ENTER = 171
    INSTANCE_LEAVE = 172
    INSTANCE_LEAVE_RESULT = 173
    INSTANCE_INFO = 174
    MATCH_ENQUEUE = 180
    MATCH_DEQUEUE = 181
    MATCH_FOUND = 182
    MATCH_ACCEPT = 183
    MATCH_STATUS = 184
    # Guild/Trade/Mail
    GUILD_CREATE = 290
    GUILD_INFO_REQ = 296
    GUILD_INFO = 297
    GUILD_LIST_REQ = 298
    GUILD_LIST = 299
    TRADE_REQUEST = 300
    TRADE_RESULT = 307
    MAIL_LIST_REQ = 311
    MAIL_LIST = 312


# ━━━ 패킷 빌드/파싱 ━━━
def build_packet(msg_type: int, payload: bytes = b'') -> bytes:
    total_len = HEADER_SIZE + len(payload)
    header = struct.pack('<IH', total_len, msg_type)
    return header + payload


def build_login(username: str, password: str) -> bytes:
    u = username.encode('utf-8')
    p = password.encode('utf-8')
    payload = struct.pack('<B', len(u)) + u + struct.pack('<B', len(p)) + p
    return build_packet(MsgType.LOGIN, payload)


def build_char_select(char_id: int) -> bytes:
    return build_packet(MsgType.CHAR_SELECT, struct.pack('<I', char_id))


def build_move(x: float, y: float, z: float, ts: int = 0) -> bytes:
    return build_packet(MsgType.MOVE, struct.pack('<fffI', x, y, z, ts))


def build_chat_send(channel: int, message: str) -> bytes:
    msg = message.encode('utf-8')
    return build_packet(MsgType.CHAT_SEND, struct.pack('<BB', channel, len(msg)) + msg)


# ━━━ 테스트 클라이언트 ━━━
class TestClient:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.recv_buf = bytearray()

    async def connect(self, host: str, port: int):
        self.reader, self.writer = await asyncio.open_connection(host, port)

    async def send_raw(self, data: bytes):
        self.writer.write(data)
        await self.writer.drain()

    async def send(self, msg_type: int, payload: bytes = b''):
        pkt = build_packet(msg_type, payload)
        self.writer.write(pkt)
        await self.writer.drain()

    async def recv_packet(self, timeout: float = 3.0):
        """단일 패킷 수신. (msg_type, payload) 또는 (None, None)"""
        deadline = time.time() + timeout
        while True:
            if len(self.recv_buf) >= HEADER_SIZE:
                pkt_len = struct.unpack_from('<I', self.recv_buf, 0)[0]
                if pkt_len < HEADER_SIZE or pkt_len > MAX_PACKET_SIZE:
                    self.recv_buf.clear()
                    return None, None
                if len(self.recv_buf) >= pkt_len:
                    msg_type = struct.unpack_from('<H', self.recv_buf, 4)[0]
                    payload = bytes(self.recv_buf[HEADER_SIZE:pkt_len])
                    self.recv_buf = self.recv_buf[pkt_len:]
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

    async def recv_all(self, timeout: float = 1.0):
        """짧은 시간 내 모든 패킷 수집"""
        packets = []
        while True:
            mt, pl = await self.recv_packet(timeout=timeout)
            if mt is None:
                break
            packets.append((mt, pl))
            timeout = 0.3
        return packets

    async def recv_expect(self, expected: int, timeout: float = 3.0):
        """특정 타입 패킷이 올 때까지 대기. 다른 패킷은 무시."""
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None, None
            mt, pl = await self.recv_packet(timeout=remaining)
            if mt is None:
                return None, None
            if mt == expected:
                return mt, pl

    async def login_and_enter(self, host: str, port: int, username: str = 'testuser'):
        """연결 → 로그인 → 캐릭터 선택 → 게임 입장. 초기 패킷 반환."""
        await self.connect(host, port)
        await asyncio.sleep(0.1)
        await self.send_raw(build_login(username, 'pass123'))
        await self.recv_packet()  # LOGIN_RESULT
        await self.send_raw(build_char_select(1))
        return await self.recv_all(timeout=1.5)

    def close(self):
        if self.writer:
            self.writer.close()


# ━━━ 테스트 러너 ━━━
async def run_tests(host: str, port: int):
    results = []
    total = 0
    passed = 0
    failed_names = []

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
            failed_names.append(name)
        except Exception as e:
            results.append(f"  ERR  [{total:02d}] {name}: {type(e).__name__}: {e}")
            print(f"  ERR  [{total:02d}] {name}: {type(e).__name__}: {e}")
            failed_names.append(name)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Phase 2 핵심 테스트 (S035 시나리오 11단계)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # 1. ECHO — TCP 연결 + 기본 응답 확인
    async def test_echo():
        c = TestClient()
        await c.connect(host, port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.ECHO, b'client_hello')
        mt, pl = await c.recv_packet()
        assert mt == MsgType.ECHO, f"Expected ECHO({MsgType.ECHO}), got {mt}"
        assert pl == b'client_hello', f"Expected b'client_hello', got {pl}"
        c.close()

    await test("S035-01 ECHO: TCP 연결 + 패킷 왕복", test_echo())

    # 2. LOGIN_REQ → LOGIN_RESULT
    async def test_login():
        c = TestClient()
        await c.connect(host, port)
        await asyncio.sleep(0.1)
        await c.send_raw(build_login('phase2user', 'pw123'))
        mt, pl = await c.recv_packet()
        assert mt == MsgType.LOGIN_RESULT, f"Expected LOGIN_RESULT({MsgType.LOGIN_RESULT}), got {mt}"
        result = pl[0]
        assert result == 0, f"Login should succeed (SUCCESS=0), got result={result}"
        account_id = struct.unpack_from('<I', pl, 1)[0]
        assert account_id > 0, f"Account ID should be > 0, got {account_id}"
        c.close()

    await test("S035-02 LOGIN: 로그인 성공 (result=0)", test_login())

    # 3. SERVER_LIST_REQ → SERVER_LIST
    async def test_server_list():
        c = TestClient()
        await c.connect(host, port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.SERVER_LIST_REQ)
        mt, pl = await c.recv_packet()
        assert mt == MsgType.SERVER_LIST, f"Expected SERVER_LIST({MsgType.SERVER_LIST}), got {mt}"
        count = pl[0]
        assert count == 3, f"Expected 3 servers, got {count}"
        # 각 서버 35B/entry 파싱 검증
        off = 1
        for i in range(count):
            name_end = off
            while name_end < off + 32 and pl[name_end] != 0:
                name_end += 1
            name = pl[off:name_end].decode('utf-8')
            off += 32
            status = pl[off]; off += 1
            pop = struct.unpack_from('<H', pl, off)[0]; off += 2
            assert status in (0, 1, 2, 3), f"Invalid status={status} for server '{name}'"
        c.close()

    await test("S035-03 SERVER_LIST: 서버 3개 반환", test_server_list())

    # 4. CHARACTER_LIST_REQ → CHARACTER_LIST (빈 리스트)
    async def test_char_list_empty():
        c = TestClient()
        await c.connect(host, port)
        await asyncio.sleep(0.1)
        await c.send_raw(build_login('charlist_empty', 'pw'))
        await c.recv_packet()  # LOGIN_RESULT
        await c.send(MsgType.CHARACTER_LIST_REQ)
        mt, pl = await c.recv_packet()
        assert mt == MsgType.CHARACTER_LIST, f"Expected CHARACTER_LIST({MsgType.CHARACTER_LIST}), got {mt}"
        count = pl[0]
        assert count == 0, f"Expected 0 characters for new user, got {count}"
        c.close()

    await test("S035-04 CHARACTER_LIST: 빈 목록", test_char_list_empty())

    # 5. CHARACTER_CREATE -> CHARACTER_CREATE_RESULT
    async def test_char_create():
        uid = str(int(time.time() * 1000) % 99999999)
        c = TestClient()
        await c.connect(host, port)
        await asyncio.sleep(0.1)
        await c.send_raw(build_login(f'cc{uid}', 'pw'))
        await c.recv_packet()
        # Unique character name with timestamp
        char_name = f'H{uid[:6]}'
        name_bytes = char_name.encode('utf-8')
        payload = struct.pack('<B', len(name_bytes)) + name_bytes + struct.pack('<B', 1)
        await c.send(MsgType.CHARACTER_CREATE, payload)
        mt, pl = await c.recv_packet()
        assert mt == MsgType.CHARACTER_CREATE_RESULT, f"Expected CHARACTER_CREATE_RESULT, got {mt}"
        result = pl[0]
        assert result == 0, f"Create should succeed (SUCCESS=0), got result={result}"
        char_id = struct.unpack_from('<I', pl, 1)[0]
        assert char_id > 0, f"Char ID should be > 0"
        # Verify list
        await c.send(MsgType.CHARACTER_LIST_REQ)
        mt, pl = await c.recv_packet()
        assert mt == MsgType.CHARACTER_LIST
        assert pl[0] == 1, f"Expected 1 character after create, got {pl[0]}"
        c.close()

    await test("S035-05 CHARACTER_CREATE: char create", test_char_create())

    # 6. ENTER_GAME + 초기 패킷 수신
    async def test_enter_game():
        c = TestClient()
        packets = await c.login_and_enter(host, port, 'enter_game_test')
        msg_types = [mt for mt, _ in packets]
        # ENTER_GAME 확인
        assert MsgType.ENTER_GAME in msg_types, f"Missing ENTER_GAME in {msg_types}"
        enter_pkt = next(pl for mt, pl in packets if mt == MsgType.ENTER_GAME)
        result = enter_pkt[0]
        assert result == 0, f"Enter game should succeed, got result={result}"
        entity_id = struct.unpack_from('<Q', enter_pkt, 1)[0]
        assert entity_id > 0, "Entity ID should be > 0"
        zone_id = struct.unpack_from('<i', enter_pkt, 9)[0]
        assert zone_id > 0, f"Zone ID should be > 0, got {zone_id}"
        # STAT_SYNC 확인
        assert MsgType.STAT_SYNC in msg_types, f"Missing STAT_SYNC in {msg_types}"
        stat_pkt = next(pl for mt, pl in packets if mt == MsgType.STAT_SYNC)
        level = struct.unpack_from('<i', stat_pkt, 0)[0]
        hp = struct.unpack_from('<i', stat_pkt, 4)[0]
        max_hp = struct.unpack_from('<i', stat_pkt, 8)[0]
        assert level > 0, f"Level should be > 0, got {level}"
        assert hp > 0, f"HP should be > 0, got {hp}"
        assert max_hp >= hp, f"MaxHP({max_hp}) should be >= HP({hp})"
        c.close()

    await test("S035-06 ENTER_GAME: 게임 진입 + STAT_SYNC", test_enter_game())

    # 7. MOVE — 이동 + 위치 확인
    async def test_move():
        c = TestClient()
        await c.login_and_enter(host, port, 'move_test_user')
        # 이동
        await c.send_raw(build_move(200.0, 0.0, 300.0))
        await asyncio.sleep(0.3)
        # 위치 조회
        await c.send(MsgType.POS_QUERY)
        mt, pl = await c.recv_expect(MsgType.MOVE_BROADCAST)
        assert mt == MsgType.MOVE_BROADCAST, f"Expected MOVE_BROADCAST, got {mt}"
        entity, x, y, z = struct.unpack_from('<Qfff', pl, 0)
        assert abs(x - 200.0) < 1.0, f"Expected x~200, got {x}"
        assert abs(z - 300.0) < 1.0, f"Expected z~300, got {z}"
        c.close()

    await test("S035-07 MOVE: 이동 + 위치 브로드캐스트", test_move())

    # 8. CHAT_SEND → CHAT_MESSAGE
    async def test_chat():
        c = TestClient()
        await c.login_and_enter(host, port, 'chat_test_user')
        # Zone 채팅 전송
        await c.send_raw(build_chat_send(0, 'Hello Phase2!'))
        mt, pl = await c.recv_expect(MsgType.CHAT_MESSAGE)
        assert mt == MsgType.CHAT_MESSAGE, f"Expected CHAT_MESSAGE, got {mt}"
        channel = pl[0]
        assert channel == 0, f"Expected channel=0 (GENERAL), got {channel}"
        # sender_name(32B) + msg_len(1) + msg 파싱
        msg_len = pl[41]
        msg = pl[42:42 + msg_len].decode('utf-8')
        assert msg == 'Hello Phase2!', f"Expected 'Hello Phase2!', got '{msg}'"
        c.close()

    await test("S035-08 CHAT: Zone 채팅 전송/수신", test_chat())

    # 9. NPC_INTERACT → NPC_DIALOG
    async def test_npc_dialog():
        c = TestClient()
        await c.login_and_enter(host, port, 'npc_dialog_test')
        await c.send(MsgType.NPC_INTERACT, struct.pack('<I', 1))
        # AI 틱으로 MONSTER_MOVE가 섞일 수 있으므로 recv_expect 사용
        mt, pl = await c.recv_expect(MsgType.NPC_DIALOG, timeout=3.0)
        assert mt == MsgType.NPC_DIALOG, f"Expected NPC_DIALOG, got {mt}"
        npc_id = struct.unpack_from('<H', pl, 0)[0]
        npc_type = pl[2]
        line_count = pl[3]
        assert npc_id == 1, f"Expected npc_id=1, got {npc_id}"
        assert line_count > 0, f"Expected > 0 dialog lines, got {line_count}"
        # 대화 라인 파싱 검증
        off = 4
        for i in range(line_count):
            spk_len = pl[off]; off += 1
            speaker = pl[off:off + spk_len].decode('utf-8'); off += spk_len
            txt_len = struct.unpack_from('<H', pl, off)[0]; off += 2
            text = pl[off:off + txt_len].decode('utf-8'); off += txt_len
            assert len(speaker) > 0, f"Speaker should not be empty"
            assert len(text) > 0, f"Text should not be empty"
        c.close()

    await test("S035-09 NPC_DIALOG: NPC 대화 요청/응답 + UTF8 파싱", test_npc_dialog())

    # 10. ENHANCE_REQ → ENHANCE_RESULT
    async def test_enhance():
        c = TestClient()
        await c.login_and_enter(host, port, 'enhance_test_01')
        # 빈 슬롯 강화 → NO_ITEM(2) 예상
        await c.send(MsgType.ENHANCE_REQ, struct.pack('<B', 5))
        mt, pl = await c.recv_expect(MsgType.ENHANCE_RESULT)
        assert mt == MsgType.ENHANCE_RESULT, f"Expected ENHANCE_RESULT, got {mt}"
        slot_idx = pl[0]
        result = pl[1]
        assert result == 2, f"Expected NO_ITEM(2) for empty slot, got result={result}"
        c.close()

    await test("S035-10 ENHANCE: 강화 요청/응답", test_enhance())

    # 11. TUTORIAL_STEP_COMPLETE → TUTORIAL_REWARD
    async def test_tutorial():
        c = TestClient()
        await c.login_and_enter(host, port, 'tutorial_test_p2')
        await c.send(MsgType.TUTORIAL_STEP_COMPLETE, struct.pack('<B', 1))
        mt, pl = await c.recv_expect(MsgType.TUTORIAL_REWARD)
        assert mt == MsgType.TUTORIAL_REWARD, f"Expected TUTORIAL_REWARD, got {mt}"
        step_id = pl[0]
        reward_type = pl[1]
        amount = struct.unpack_from('<I', pl, 2)[0]
        assert step_id == 1, f"Expected step_id=1, got {step_id}"
        assert amount > 0, f"Reward amount should be > 0, got {amount}"
        # 중복 전송 → 무시 확인
        await c.send(MsgType.TUTORIAL_STEP_COMPLETE, struct.pack('<B', 1))
        mt, _ = await c.recv_packet(timeout=0.5)
        assert mt is None or mt != MsgType.TUTORIAL_REWARD, \
            f"Duplicate step should be ignored, got {mt}"
        c.close()

    await test("S035-11 TUTORIAL: 튜토리얼 보상 + 중복방지", test_tutorial())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 추가 검증 (클라이언트 파서 호환성)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # 12. TCP 스트림 어셈블링 — 2패킷 연속 전송
    async def test_stream_assembly():
        c = TestClient()
        await c.connect(host, port)
        await asyncio.sleep(0.1)
        pkt1 = build_packet(MsgType.ECHO, b'AAA')
        pkt2 = build_packet(MsgType.ECHO, b'BBB')
        c.writer.write(pkt1 + pkt2)
        await c.writer.drain()
        mt1, p1 = await c.recv_packet()
        mt2, p2 = await c.recv_packet()
        assert mt1 == MsgType.ECHO and p1 == b'AAA', f"First packet wrong: {mt1}, {p1}"
        assert mt2 == MsgType.ECHO and p2 == b'BBB', f"Second packet wrong: {mt2}, {p2}"
        c.close()

    await test("S035-12 TCP_STREAM: 연속 패킷 어셈블링", test_stream_assembly())

    # 13. MONSTER_SPAWN — 게임 입장 시 몬스터 스폰 수신
    async def test_monster_spawn():
        c = TestClient()
        packets = await c.login_and_enter(host, port, 'monster_spawn_t')
        spawns = [(mt, pl) for mt, pl in packets if mt == MsgType.MONSTER_SPAWN]
        assert len(spawns) > 0, f"Expected MONSTER_SPAWN packets after ENTER_GAME"
        # 첫 번째 몬스터 스폰 데이터 검증 (36B)
        pl = spawns[0][1]
        entity_id = struct.unpack_from('<Q', pl, 0)[0]
        monster_id = struct.unpack_from('<I', pl, 8)[0]
        level = struct.unpack_from('<I', pl, 12)[0]
        hp = struct.unpack_from('<i', pl, 16)[0]
        max_hp = struct.unpack_from('<i', pl, 20)[0]
        assert entity_id > 0, f"Monster entity_id should be > 0"
        assert monster_id > 0, f"Monster ID should be > 0"
        assert hp > 0, f"Monster HP should be > 0"
        assert max_hp >= hp, f"Monster MaxHP({max_hp}) >= HP({hp})"
        c.close()

    await test("S035-13 MONSTER_SPAWN: 몬스터 스폰 수신 + 파싱", test_monster_spawn())

    # 14. SKILL_LIST — 스킬 목록 조회
    async def test_skill_list():
        c = TestClient()
        await c.login_and_enter(host, port, 'skill_list_test')
        await c.send(MsgType.SKILL_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.SKILL_LIST_RESP)
        assert mt == MsgType.SKILL_LIST_RESP, f"Expected SKILL_LIST_RESP, got {mt}"
        count = pl[0]
        assert count >= 1, f"Expected >= 1 skills, got {count}"
        # 첫 스킬 엔트리 파싱 (43B/entry)
        off = 1
        skill_id = struct.unpack_from('<I', pl, off)[0]; off += 4
        name_end = off
        while name_end < off + 16 and pl[name_end] != 0:
            name_end += 1
        name = pl[off:name_end].decode('utf-8'); off += 16
        cd_ms = struct.unpack_from('<I', pl, off)[0]; off += 4
        dmg = struct.unpack_from('<I', pl, off)[0]; off += 4
        assert skill_id > 0, f"Skill ID should be > 0"
        assert len(name) > 0, f"Skill name should not be empty"
        c.close()

    await test("S035-14 SKILL_LIST: 스킬 목록 파싱", test_skill_list())

    # 15. INVENTORY — 인벤토리 조회
    async def test_inventory():
        c = TestClient()
        await c.login_and_enter(host, port, 'inv_list_test')
        await c.send(MsgType.INVENTORY_REQ)
        mt, pl = await c.recv_expect(MsgType.INVENTORY_RESP)
        assert mt == MsgType.INVENTORY_RESP, f"Expected INVENTORY_RESP, got {mt}"
        count = pl[0]
        # 초기 아이템이 있을 수 있고 없을 수도 있음 — 파싱 검증만
        if count > 0:
            off = 1
            slot = pl[off]; off += 1
            item_id = struct.unpack_from('<I', pl, off)[0]; off += 4
            item_count = struct.unpack_from('<H', pl, off)[0]; off += 2
            equipped = pl[off]; off += 1
            assert item_id > 0, f"Item ID should be > 0"
        c.close()

    await test("S035-15 INVENTORY: 인벤토리 파싱", test_inventory())

    # 16. BUFF_LIST — 버프 목록 조회
    async def test_buff_list():
        c = TestClient()
        await c.login_and_enter(host, port, 'buff_list_test')
        await c.send(MsgType.BUFF_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.BUFF_LIST_RESP)
        assert mt == MsgType.BUFF_LIST_RESP, f"Expected BUFF_LIST_RESP, got {mt}"
        count = pl[0]
        # 초기 버프 없을 수 있음 — 파싱만 확인
        assert count >= 0, f"Buff count should be >= 0"
        c.close()

    await test("S035-16 BUFF_LIST: 버프 목록 파싱", test_buff_list())

    # 17. QUEST_LIST — 퀘스트 목록 조회
    async def test_quest_list():
        c = TestClient()
        await c.login_and_enter(host, port, 'quest_list_test')
        await c.send(MsgType.QUEST_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.QUEST_LIST_RESP)
        assert mt == MsgType.QUEST_LIST_RESP, f"Expected QUEST_LIST_RESP, got {mt}"
        count = pl[0]
        assert count >= 0, f"Quest count should be >= 0"
        c.close()

    await test("S035-17 QUEST_LIST: 퀘스트 목록 파싱", test_quest_list())

    # 18. STAT_SYNC 상세 파싱 — 9 x int32 = 36B
    async def test_stat_sync_detail():
        c = TestClient()
        await c.login_and_enter(host, port, 'stat_detail_tst')
        await c.send(MsgType.STAT_QUERY)
        mt, pl = await c.recv_expect(MsgType.STAT_SYNC)
        assert mt == MsgType.STAT_SYNC, f"Expected STAT_SYNC, got {mt}"
        assert len(pl) == 36, f"STAT_SYNC should be 36B, got {len(pl)}B"
        level = struct.unpack_from('<i', pl, 0)[0]
        hp = struct.unpack_from('<i', pl, 4)[0]
        max_hp = struct.unpack_from('<i', pl, 8)[0]
        mp = struct.unpack_from('<i', pl, 12)[0]
        max_mp = struct.unpack_from('<i', pl, 16)[0]
        atk = struct.unpack_from('<i', pl, 20)[0]
        _def = struct.unpack_from('<i', pl, 24)[0]
        exp = struct.unpack_from('<i', pl, 28)[0]
        exp_next = struct.unpack_from('<i', pl, 32)[0]
        assert level > 0, f"Level should be > 0"
        assert max_hp > 0, f"MaxHP should be > 0"
        assert max_mp >= 0, f"MaxMP should be >= 0"
        assert atk > 0, f"ATK should be > 0"
        assert _def >= 0, f"DEF should be >= 0"
        assert exp_next > 0, f"EXP_NEXT should be > 0"
        c.close()

    await test("S035-18 STAT_SYNC: 9필드 상세 파싱 (36B)", test_stat_sync_detail())

    # 19. 멀티 클라이언트 APPEAR 테스트
    async def test_multi_appear():
        c1 = TestClient()
        c2 = TestClient()
        # 클라1 입장
        await c1.login_and_enter(host, port, 'multi_app_usr1')
        # 클라2 입장 → 클라1에게 APPEAR 와야 함
        await c2.login_and_enter(host, port, 'multi_app_usr2')
        await asyncio.sleep(0.5)
        c1_packets = await c1.recv_all(timeout=1.0)
        c1_types = [mt for mt, _ in c1_packets]
        assert MsgType.APPEAR in c1_types, \
            f"Client1 should receive APPEAR for Client2, got {c1_types}"
        c1.close()
        c2.close()

    await test("S035-19 MULTI_APPEAR: 2클라 접속 시 APPEAR 수신", test_multi_appear())

    # 20. Full lobby flow: LOGIN -> SERVER_LIST -> CHARACTER_CRUD -> ENTER_GAME
    async def test_full_lobby_flow():
        uid = str(int(time.time() * 1000) % 99999999)
        c = TestClient()
        await c.connect(host, port)
        await asyncio.sleep(0.1)
        # 1) Login with unique username
        await c.send_raw(build_login(f'lf{uid}', 'pw'))
        mt, pl = await c.recv_expect(MsgType.LOGIN_RESULT)
        assert mt == MsgType.LOGIN_RESULT, f"Expected LOGIN_RESULT, got {mt}"
        assert pl[0] == 0, f"Login fail: result={pl[0]}"
        # 2) Server list
        await c.send(MsgType.SERVER_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.SERVER_LIST)
        assert mt == MsgType.SERVER_LIST, f"Expected SERVER_LIST, got {mt}"
        assert pl[0] == 3, f"Expected 3 servers, got {pl[0]}"
        # 3) Character list (should be empty for new user)
        await c.send(MsgType.CHARACTER_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.CHARACTER_LIST)
        assert mt == MsgType.CHARACTER_LIST, f"Expected CHARACTER_LIST, got {mt}"
        assert pl[0] == 0, f"Expected 0 chars for new user, got {pl[0]}"
        # 4) Character create with unique name
        char_name = f'L{uid[:6]}'
        name_bytes = char_name.encode('utf-8')
        create_pl = struct.pack('<B', len(name_bytes)) + name_bytes + struct.pack('<B', 1)
        await c.send(MsgType.CHARACTER_CREATE, create_pl)
        mt, pl = await c.recv_expect(MsgType.CHARACTER_CREATE_RESULT)
        assert mt == MsgType.CHARACTER_CREATE_RESULT, f"Expected CREATE_RESULT, got {mt}"
        assert pl[0] == 0, f"Create fail: result={pl[0]}"
        # 5) Enter game
        await c.send_raw(build_char_select(1))
        packets = await c.recv_all(timeout=2.0)
        msg_types = [mt for mt, _ in packets]
        assert MsgType.ENTER_GAME in msg_types, f"Missing ENTER_GAME in {msg_types}"
        assert MsgType.STAT_SYNC in msg_types, f"Missing STAT_SYNC in {msg_types}"
        c.close()

    await test("S035-20 LOBBY_FLOW: Full lobby flow", test_full_lobby_flow())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Phase 3 테스트 (던전/매칭/길드/우편)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # 21. INSTANCE_CREATE -> INSTANCE_ENTER
    async def test_instance_create():
        c = TestClient()
        await c.login_and_enter(host, port, 'dungeon_test_01')
        # dungeonType=2 (Party Dungeon)
        await c.send(MsgType.INSTANCE_CREATE, struct.pack('<I', 2))
        mt, pl = await c.recv_expect(MsgType.INSTANCE_ENTER, timeout=3.0)
        assert mt == MsgType.INSTANCE_ENTER, f"Expected INSTANCE_ENTER, got {mt}"
        result = pl[0]
        instance_id = struct.unpack_from('<I', pl, 1)[0]
        dungeon_type = struct.unpack_from('<I', pl, 5)[0]
        assert result == 0, f"Instance create should succeed, got result={result}"
        assert instance_id > 0, f"Instance ID should be > 0, got {instance_id}"
        assert dungeon_type == 2, f"Expected dungeon_type=2, got {dungeon_type}"
        c.close()

    await test("P3-21 INSTANCE_CREATE: dungeon entry", test_instance_create())

    # 22. INSTANCE_LEAVE -> INSTANCE_LEAVE_RESULT
    async def test_instance_leave():
        c = TestClient()
        await c.login_and_enter(host, port, 'dungeon_leave_t')
        # enter dungeon first
        await c.send(MsgType.INSTANCE_CREATE, struct.pack('<I', 1))
        mt, pl = await c.recv_expect(MsgType.INSTANCE_ENTER, timeout=3.0)
        assert mt == MsgType.INSTANCE_ENTER, f"Expected INSTANCE_ENTER, got {mt}"
        assert pl[0] == 0, f"Instance create failed: result={pl[0]}"
        # now leave
        await c.send(MsgType.INSTANCE_LEAVE)
        mt, pl = await c.recv_expect(MsgType.INSTANCE_LEAVE_RESULT, timeout=3.0)
        assert mt == MsgType.INSTANCE_LEAVE_RESULT, f"Expected INSTANCE_LEAVE_RESULT, got {mt}"
        result = pl[0]
        assert result == 0, f"Instance leave should succeed, got result={result}"
        c.close()

    await test("P3-22 INSTANCE_LEAVE: dungeon exit", test_instance_leave())

    # 23. MATCH_ENQUEUE -> MATCH_STATUS
    async def test_match_enqueue():
        c = TestClient()
        await c.login_and_enter(host, port, 'match_q_test01')
        # enqueue for Party Dungeon (dungeon_type=1, min_level=15)
        # 테스트 유저 레벨이 1이므로 status=2(레벨 부족)도 유효한 프로토콜 응답
        await c.send(MsgType.MATCH_ENQUEUE, struct.pack('<I', 1))
        mt, pl = await c.recv_expect(MsgType.MATCH_STATUS, timeout=3.0)
        assert mt == MsgType.MATCH_STATUS, f"Expected MATCH_STATUS, got {mt}"
        status = pl[0]
        queue_pos = struct.unpack_from('<I', pl, 1)[0]
        assert status in (0, 1, 2, 3), f"Expected valid status (0-3), got {status}"
        # dequeue (빈 페이로드 = 현재 큐에서 제거)
        await c.send(MsgType.MATCH_DEQUEUE)
        c.close()

    await test("P3-23 MATCH_ENQUEUE: matchmaking queue", test_match_enqueue())

    # 24. GUILD_LIST_REQ -> GUILD_LIST
    async def test_guild_list():
        c = TestClient()
        await c.login_and_enter(host, port, 'guild_list_tst')
        await c.send(MsgType.GUILD_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.GUILD_LIST, timeout=3.0)
        assert mt == MsgType.GUILD_LIST, f"Expected GUILD_LIST, got {mt}"
        count = pl[0]
        assert count >= 0, f"Guild count should be >= 0, got {count}"
        c.close()

    await test("P3-24 GUILD_LIST: guild listing", test_guild_list())

    # 25. MAIL_LIST_REQ -> MAIL_LIST
    async def test_mail_list():
        c = TestClient()
        await c.login_and_enter(host, port, 'mail_list_test')
        await c.send(MsgType.MAIL_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.MAIL_LIST, timeout=3.0)
        assert mt == MsgType.MAIL_LIST, f"Expected MAIL_LIST, got {mt}"
        count = pl[0]
        assert count >= 0, f"Mail count should be >= 0, got {count}"
        c.close()

    await test("P3-25 MAIL_LIST: mail listing", test_mail_list())

    # ━━━ 결과 요약 ━━━
    fail_count = total - passed
    print()
    print("=" * 55)
    print(f"  Phase 2+3 TCP Bridge Client Test: {passed}/{total} PASSED, {fail_count} FAILED")
    print("=" * 55)
    if failed_names:
        print(f"\n  Failed tests:")
        for name in failed_names:
            print(f"    - {name}")
    print()

    return passed, total


async def main():
    parser = argparse.ArgumentParser(description='Phase 2+3 TCP Bridge Client Test')
    parser.add_argument('--host', default='127.0.0.1', help='Bridge server host')
    parser.add_argument('--port', type=int, default=7777, help='Bridge server port')
    args = parser.parse_args()

    print("=" * 55)
    print("  Phase 2+3 TCP Bridge - Client Integration Tests")
    print(f"  Target: {args.host}:{args.port}")
    print("=" * 55)
    print()

    try:
        passed, total = await run_tests(args.host, args.port)
    except ConnectionRefusedError:
        print(f"\n  ERROR: Cannot connect to {args.host}:{args.port}")
        print(f"  서버를 먼저 실행하세요:")
        print(f"    cd Servers/BridgeServer")
        print(f"    python tcp_bridge.py")
        print()
        return 1
    except Exception as e:
        print(f"\n  FATAL ERROR: {type(e).__name__}: {e}")
        return 1

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
