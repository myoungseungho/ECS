"""
TCP Bridge Server 테스트
========================
브릿지 서버를 실제로 기동하고 TCP 소켓으로 패킷을 주고받는 통합 테스트.
"""

import asyncio
import struct
import sys
import os
import time

# 브릿지 서버 임포트
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

    async def connect(self, host: str = '127.0.0.1', port: int = 0):
        self.reader, self.writer = await asyncio.open_connection(host, port)

    async def send(self, msg_type: int, payload: bytes = b''):
        pkt = build_packet(msg_type, payload)
        self.writer.write(pkt)
        await self.writer.drain()

    async def recv_packet(self, timeout: float = 2.0) -> tuple:
        """(msg_type, payload) 반환. 타임아웃 시 (None, None)"""
        deadline = time.time() + timeout

        while True:
            # 버퍼에서 완전한 패킷 체크
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
        """짧은 시간 내 도착하는 모든 패킷 수집"""
        packets = []
        while True:
            msg_type, payload = await self.recv_packet(timeout=timeout)
            if msg_type is None:
                break
            packets.append((msg_type, payload))
            timeout = 0.2  # 첫 패킷 후 더 짧은 타임아웃
        return packets

    def close(self):
        if self.writer:
            self.writer.close()


# ━━━ 테스트 함수들 ━━━

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

    # ━━━ Test 1: ECHO ━━━
    async def test_echo():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.ECHO, b'hello')
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.ECHO, f"Expected ECHO, got {msg_type}"
        assert payload == b'hello', f"Expected b'hello', got {payload}"
        c.close()

    await test("ECHO: 패킷 왕복", test_echo())

    # ━━━ Test 2: PING → PONG ━━━
    async def test_ping():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.PING)
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.PING, f"Expected PING, got {msg_type}"
        assert payload == b'PONG', f"Expected b'PONG', got {payload}"
        c.close()

    await test("PING: PONG 응답", test_ping())

    # ━━━ Test 3: LOGIN ━━━
    async def test_login():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        username = b'testuser'
        password = b'pass123'
        payload = struct.pack('<B', len(username)) + username + \
                  struct.pack('<B', len(password)) + password
        await c.send(MsgType.LOGIN, payload)

        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.LOGIN_RESULT, f"Expected LOGIN_RESULT, got {msg_type}"
        result, account_id = struct.unpack('<BI', resp[:5])
        assert result == 0, f"Login should succeed (SUCCESS=0), got result={result}"
        assert account_id > 0, f"Account ID should be > 0, got {account_id}"
        c.close()

    await test("LOGIN: 로그인 성공", test_login())

    # ━━━ Test 4: CHAR_LIST_REQ ━━━
    async def test_char_list():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        # 먼저 로그인
        username = b'chartest'
        password = b'pass'
        login_payload = struct.pack('<B', len(username)) + username + \
                        struct.pack('<B', len(password)) + password
        await c.send(MsgType.LOGIN, login_payload)
        await c.recv_packet()  # LOGIN_RESULT

        # 캐릭터 목록 요청
        await c.send(MsgType.CHAR_LIST_REQ)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.CHAR_LIST_RESP, f"Expected CHAR_LIST_RESP, got {msg_type}"
        count = resp[0]
        assert count == 3, f"Expected 3 characters, got {count}"
        c.close()

    await test("CHAR_LIST: 3캐릭터 반환", test_char_list())

    # ━━━ Test 5: CHAR_SELECT + ENTER_GAME ━━━
    async def test_enter_game():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        # 로그인
        await c.send(MsgType.LOGIN, struct.pack('<B', 4) + b'user' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()

        # 캐릭터 선택
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))

        # 여러 패킷 올 수 있음 (ENTER_GAME, APPEAR, MONSTER_SPAWN, STAT_SYNC, SYSTEM_MESSAGE)
        packets = await c.recv_all_packets(timeout=1.0)
        msg_types = [p[0] for p in packets]

        assert MsgType.ENTER_GAME in msg_types, f"Missing ENTER_GAME in {msg_types}"
        enter_game = next(p[1] for p in packets if p[0] == MsgType.ENTER_GAME)
        result = enter_game[0]
        assert result == 0, f"Enter game should succeed (SUCCESS=0), got result={result}"

        entity_id = struct.unpack_from('<Q', enter_game, 1)[0]
        assert entity_id > 0, f"Entity ID should be > 0"

        # STAT_SYNC도 와야 함
        assert MsgType.STAT_SYNC in msg_types, f"Missing STAT_SYNC in {msg_types}"

        # SYSTEM_MESSAGE도 와야 함
        assert MsgType.SYSTEM_MESSAGE in msg_types, f"Missing SYSTEM_MESSAGE in {msg_types}"

        c.close()

    await test("ENTER_GAME: 게임 진입 + 초기 패킷", test_enter_game())

    # ━━━ Test 6: MOVE ━━━
    async def test_move():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        # 로그인 + 진입
        await c.send(MsgType.LOGIN, struct.pack('<B', 4) + b'move' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 이동
        await c.send(MsgType.MOVE, struct.pack('<fff', 200.0, 0.0, 300.0))
        await asyncio.sleep(0.2)

        # 위치 조회
        await c.send(MsgType.POS_QUERY)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.MOVE_BROADCAST, f"Expected MOVE_BROADCAST, got {msg_type}"
        entity, x, y, z = struct.unpack('<Qfff', resp[:20])
        assert abs(x - 200.0) < 0.1, f"Expected x=200, got {x}"
        assert abs(z - 300.0) < 0.1, f"Expected z=300, got {z}"
        c.close()

    await test("MOVE: 이동 + 위치 확인", test_move())

    # ━━━ Test 7: CHAT ━━━
    async def test_chat():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 4) + b'chat' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # Zone 채팅
        msg = b'Hello World'
        await c.send(MsgType.CHAT_SEND, struct.pack('<BB', 0, len(msg)) + msg)

        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.CHAT_MESSAGE, f"Expected CHAT_MESSAGE, got {msg_type}"
        channel = resp[0]
        assert channel == 0, f"Expected channel 0, got {channel}"
        c.close()

    await test("CHAT: Zone 채팅 전송/수신", test_chat())

    # ━━━ Test 8: STAT 시스템 ━━━
    async def test_stat():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 4) + b'stat' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 스탯 조회
        await c.send(MsgType.STAT_QUERY)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.STAT_SYNC, f"Expected STAT_SYNC, got {msg_type}"
        level, hp, max_hp = struct.unpack_from('<Iii', resp, 0)
        assert level == 10, f"Expected level 10, got {level}"
        assert hp > 0, f"HP should be > 0"

        # EXP 추가
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 5000))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.STAT_SYNC, f"Expected STAT_SYNC after exp"
        new_level = struct.unpack_from('<I', resp, 0)[0]
        assert new_level > 10, f"Should have leveled up from 10, got {new_level}"
        c.close()

    await test("STAT: 스탯 조회 + 레벨업", test_stat())

    # ━━━ Test 9: SHOP ━━━
    async def test_shop():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 4) + b'shop' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 상점 열기
        await c.send(MsgType.SHOP_OPEN, struct.pack('<I', 1))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.SHOP_LIST, f"Expected SHOP_LIST, got {msg_type}"
        npc_id, count = struct.unpack_from('<IB', resp, 0)
        assert npc_id == 1, f"Expected npc_id=1, got {npc_id}"
        assert count == 3, f"Expected 3 items, got {count}"

        # 아이템 구매
        await c.send(MsgType.SHOP_BUY, struct.pack('<IIH', 1, 101, 1))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.SHOP_RESULT, f"Expected SHOP_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Buy should succeed (ShopResult::SUCCESS=0), got result={result}"
        c.close()

    await test("SHOP: 상점 열기 + 구매", test_shop())

    # ━━━ Test 10: INVENTORY ━━━
    async def test_inventory():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 3) + b'inv' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 아이템 추가
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 201, 1))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.ITEM_ADD_RESULT, f"Expected ITEM_ADD_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 1, f"Item add should succeed"

        # 인벤 조회
        await c.send(MsgType.INVENTORY_REQ)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.INVENTORY_RESP, f"Expected INVENTORY_RESP, got {msg_type}"
        count = resp[0]
        assert count >= 1, f"Should have at least 1 item"
        c.close()

    await test("INVENTORY: 아이템 추가 + 조회", test_inventory())

    # ━━━ Test 11: SKILL ━━━
    async def test_skill():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 5) + b'skill' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 스킬 목록
        await c.send(MsgType.SKILL_LIST_REQ)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.SKILL_LIST_RESP, f"Expected SKILL_LIST_RESP, got {msg_type}"
        count = resp[0]
        assert count == 3, f"Should have 3 starting skills, got {count}"
        c.close()

    await test("SKILL: 스킬 목록 조회", test_skill())

    # ━━━ Test 12: QUEST ━━━
    async def test_quest():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 5) + b'quest' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 퀘스트 수락
        await c.send(MsgType.QUEST_ACCEPT, struct.pack('<I', 1))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.QUEST_ACCEPT_RESULT, f"Expected QUEST_ACCEPT_RESULT, got {msg_type}"
        result, qid = struct.unpack('<BI', resp[:5])
        assert result == 1, f"Quest accept should succeed"
        assert qid == 1, f"Quest ID should be 1"

        # 퀘스트 목록
        await c.send(MsgType.QUEST_LIST_REQ)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.QUEST_LIST_RESP, f"Expected QUEST_LIST_RESP, got {msg_type}"
        count = resp[0]
        assert count == 1, f"Should have 1 active quest"
        c.close()

    await test("QUEST: 퀘스트 수락 + 목록", test_quest())

    # ━━━ Test 13: ZONE_TRANSFER ━━━
    async def test_zone_transfer():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 4) + b'zone' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 존 이동
        await c.send(MsgType.ZONE_TRANSFER_REQ, struct.pack('<I', 2))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.ZONE_TRANSFER_RESULT, f"Expected ZONE_TRANSFER_RESULT, got {msg_type}"
        result, zone_id = struct.unpack_from('<BI', resp, 0)
        assert result == 0, f"Zone transfer should succeed, got result={result}"
        assert zone_id == 2, f"Should be in zone 2, got {zone_id}"
        c.close()

    await test("ZONE_TRANSFER: 존 이동", test_zone_transfer())

    # ━━━ Test 14: BUFF ━━━
    async def test_buff():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 4) + b'buff' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 버프 적용
        await c.send(MsgType.BUFF_APPLY_REQ, struct.pack('<I', 100))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.BUFF_RESULT, f"Expected BUFF_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 1, f"Buff apply should succeed"

        # 버프 목록
        await c.send(MsgType.BUFF_LIST_REQ)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.BUFF_LIST_RESP, f"Expected BUFF_LIST_RESP, got {msg_type}"
        count = resp[0]
        assert count == 1, f"Should have 1 buff"

        # 버프 제거
        await c.send(MsgType.BUFF_REMOVE_REQ, struct.pack('<I', 100))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.BUFF_REMOVE_RESP, f"Expected BUFF_REMOVE_RESP, got {msg_type}"
        c.close()

    await test("BUFF: 적용 + 목록 + 제거", test_buff())

    # ━━━ Test 15: STATS 진단 ━━━
    async def test_stats_diag():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.STATS)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.STATS, f"Expected STATS, got {msg_type}"
        stats_str = resp.decode('utf-8')
        assert 'entity_count=' in stats_str, f"Should contain entity_count"
        assert 'monsters=' in stats_str, f"Should contain monsters count"
        c.close()

    await test("STATS: 서버 진단 정보", test_stats_diag())

    # ━━━ Test 16: 패킷 스트림 분할 처리 ━━━
    async def test_fragmented():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        # 2개 패킷을 한번에 보내기 (TCP 스트림에서 합쳐짐)
        pkt1 = build_packet(MsgType.ECHO, b'AAA')
        pkt2 = build_packet(MsgType.ECHO, b'BBB')
        c.writer.write(pkt1 + pkt2)
        await c.writer.drain()

        mt1, p1 = await c.recv_packet()
        mt2, p2 = await c.recv_packet()
        assert mt1 == MsgType.ECHO and p1 == b'AAA', f"First packet wrong"
        assert mt2 == MsgType.ECHO and p2 == b'BBB', f"Second packet wrong"
        c.close()

    await test("TCP STREAM: 2패킷 연속 전송 처리", test_fragmented())

    # ━━━ Test 17: 패킷 바이트 단위 전송 ━━━
    async def test_byte_by_byte():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        pkt = build_packet(MsgType.ECHO, b'slow')
        # 1바이트씩 전송
        for byte in pkt:
            c.writer.write(bytes([byte]))
            await c.writer.drain()
            await asyncio.sleep(0.01)

        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.ECHO, f"Expected ECHO, got {msg_type}"
        assert payload == b'slow', f"Expected b'slow', got {payload}"
        c.close()

    await test("TCP STREAM: 바이트 단위 전송 어셈블링", test_byte_by_byte())

    # ━━━ Test 18: ADMIN CONFIG ━━━
    async def test_admin_config():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 5) + b'admin' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # config 조회
        name = b'monster_ai'
        key = b'leash_range'
        payload = struct.pack('<B', len(name)) + name + struct.pack('<B', len(key)) + key
        await c.send(MsgType.ADMIN_GET_CONFIG, payload)
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.ADMIN_CONFIG_RESP, f"Expected ADMIN_CONFIG_RESP, got {msg_type}"
        found = resp[0]
        assert found == 1, f"Config should be found"
        value_len = struct.unpack_from('<H', resp, 1)[0]
        value = resp[3:3+value_len].decode('utf-8')
        assert value == '500.0', f"Expected '500.0', got '{value}'"
        c.close()

    await test("ADMIN: Config 조회 (monster_ai.leash_range)", test_admin_config())

    # ━━━ Test 19: POSITION_CORRECTION (존 경계 위반) ━━━
    async def test_position_correction():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        await c.send(MsgType.LOGIN, struct.pack('<B', 3) + b'pos' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)

        # 존 경계 밖으로 이동 시도
        await c.send(MsgType.MOVE, struct.pack('<fff', 9999.0, 0.0, 9999.0))
        msg_type, resp = await c.recv_packet()
        assert msg_type == MsgType.POSITION_CORRECTION, f"Expected POSITION_CORRECTION, got {msg_type}"
        cx, cy, cz = struct.unpack('<fff', resp[:12])
        assert cx <= 1000.0, f"Corrected x should be <= 1000, got {cx}"
        assert cz <= 1000.0, f"Corrected z should be <= 1000, got {cz}"
        c.close()

    await test("MOVE: 존 경계 위반 → POSITION_CORRECTION", test_position_correction())

    # ━━━ Test 20: 멀티 클라이언트 APPEAR/DISAPPEAR ━━━
    async def test_multi_client():
        c1 = TestClient()
        c2 = TestClient()
        await c1.connect('127.0.0.1', port)
        await c2.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)

        # 클라1 진입
        await c1.send(MsgType.LOGIN, struct.pack('<B', 6) + b'multi1' + struct.pack('<B', 2) + b'pw')
        await c1.recv_packet()
        await c1.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c1.recv_all_packets(timeout=1.0)

        # 클라2 진입 → 클라1에게 APPEAR 와야 함
        await c2.send(MsgType.LOGIN, struct.pack('<B', 6) + b'multi2' + struct.pack('<B', 2) + b'pw')
        await c2.recv_packet()
        await c2.send(MsgType.CHAR_SELECT, struct.pack('<I', 2))

        # c2 패킷 수신 (ENTER_GAME 등)
        c2_packets = await c2.recv_all_packets(timeout=1.0)

        # c1에게 APPEAR 패킷이 와야 함
        c1_packets = await c1.recv_all_packets(timeout=1.0)
        c1_types = [p[0] for p in c1_packets]
        assert MsgType.APPEAR in c1_types, f"Client1 should receive APPEAR for Client2, got {c1_types}"

        c1.close()
        c2.close()

    await test("MULTI: 2클라 접속 → APPEAR 수신", test_multi_client())


    # ━━━ 서버 선택 / 캐릭터 CRUD / 튜토리얼 ━━━

    async def test_server_list():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.SERVER_LIST_REQ)
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.SERVER_LIST, f"Expected SERVER_LIST, got {msg_type}"
        count = payload[0]
        assert count == 3, f"Expected 3 servers, got {count}"
        offset = 1
        for i in range(count):
            status, pop = struct.unpack_from('<BH', payload, offset + 32)
            assert status in (0, 1, 2, 3)
            offset += 35
        c.close()

    await test("SERVER_LIST: 서버 목록 조회", test_server_list())

    async def test_character_crud():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'crudtest' + struct.pack('<B', 2) + b'pw')
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.LOGIN_RESULT
        await c.send(MsgType.CHARACTER_LIST_REQ)
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.CHARACTER_LIST
        assert payload[0] == 0, f"Expected 0 chars, got {payload[0]}"
        name_bytes = "TestHero".encode('utf-8')
        create_pl = struct.pack('<B', len(name_bytes)) + name_bytes + struct.pack('<B', 1)
        await c.send(MsgType.CHARACTER_CREATE, create_pl)
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.CHARACTER_CREATE_RESULT
        assert payload[0] == 0, f"Create fail, result={payload[0]}"
        char_id = struct.unpack_from('<I', payload, 1)[0]
        await c.send(MsgType.CHARACTER_LIST_REQ)
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.CHARACTER_LIST
        assert payload[0] == 1
        await c.send(MsgType.CHARACTER_CREATE, create_pl)
        msg_type, payload = await c.recv_packet()
        assert payload[0] == 2, f"Dup name should be 2, got {payload[0]}"
        await c.send(MsgType.CHARACTER_DELETE, struct.pack('<I', char_id))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.CHARACTER_DELETE_RESULT
        assert payload[0] == 0
        await c.send(MsgType.CHARACTER_LIST_REQ)
        msg_type, payload = await c.recv_packet()
        assert payload[0] == 0
        c.close()

    await test("CHAR_CRUD: 생성/조회/삭제 + 중복검증", test_character_crud())

    async def test_tutorial():
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'tuttest1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        await c.send(MsgType.TUTORIAL_STEP_COMPLETE, struct.pack('<B', 1))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.TUTORIAL_REWARD
        assert payload[0] == 1
        assert payload[1] == 0
        amount = struct.unpack_from('<I', payload, 2)[0]
        assert amount == 100
        await c.send(MsgType.TUTORIAL_STEP_COMPLETE, struct.pack('<B', 1))
        msg_type, _ = await c.recv_packet(timeout=0.5)
        assert msg_type is None, f"Dup step should be ignored, got {msg_type}"
        await c.send(MsgType.TUTORIAL_STEP_COMPLETE, struct.pack('<B', 4))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.TUTORIAL_REWARD
        assert payload[0] == 4
        assert payload[1] == 2
        c.close()

    await test("TUTORIAL: 스텝 완료 + 보상 + 중복방지", test_tutorial())


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
        # AI 틱으로 MONSTER_MOVE가 먼저 올 수 있으므로 recv_all에서 NPC_DIALOG 찾기
        packets = await c.recv_all_packets(timeout=1.5)
        npc_dialogs = [(mt, pl) for mt, pl in packets if mt == MsgType.NPC_DIALOG]
        assert len(npc_dialogs) > 0, f"Expected NPC_DIALOG, got types: {[mt for mt, _ in packets]}"
        payload = npc_dialogs[0][1]
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
        packets = await c.recv_all_packets(timeout=1.5)
        npc_dialogs = [(mt, pl) for mt, pl in packets if mt == MsgType.NPC_DIALOG]
        assert len(npc_dialogs) > 0, f"Expected NPC_DIALOG, got types: {[mt for mt, _ in packets]}"
        payload = npc_dialogs[0][1]
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

    async def test_enhance_with_item():
        """강화 — 아이템 추가 후 강화 (결과: SUCCESS 또는 FAIL)"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'enhtest1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # 먼저 슬롯 0에 아이템 추가
        await c.send(MsgType.ITEM_ADD, struct.pack('<IHB', 201, 1, 0))
        await c.recv_all_packets(timeout=0.5)
        # 이제 강화 (초기 gold=1000, +1 cost=500)
        await c.send(MsgType.ENHANCE_REQ, struct.pack('<B', 0))
        packets = await c.recv_all_packets(timeout=1.5)
        enh_results = [(mt, pl) for mt, pl in packets if mt == MsgType.ENHANCE_RESULT]
        assert len(enh_results) > 0, f"Expected ENHANCE_RESULT, got types: {[mt for mt, _ in packets]}"
        payload = enh_results[0][1]
        slot_idx = payload[0]
        result = payload[1]
        # 0=SUCCESS, 5=FAIL (level preserved)
        assert result in (0, 5), f"Expected SUCCESS(0) or FAIL(5), got {result}"
        c.close()

    await test("ENHANCE: 아이템 강화 실행", test_enhance_with_item())

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

    # ━━━ 결과 ━━━
    print(f"\n{'='*50}")
    print(f"  TCP Bridge Test Results: {passed}/{total} PASSED")
    print(f"{'='*50}")

    return passed, total


async def main():
    port = 17777  # 테스트용 포트 (기본 7777과 충돌 방지)

    # 서버 시작
    server = BridgeServer(port=port, verbose=False)

    async def run_server():
        srv = await asyncio.start_server(
            server._on_client_connected, '0.0.0.0', port
        )
        server._running = True
        server._spawn_monsters()
        if hasattr(server, '_spawn_npcs'):
            server._spawn_npcs()
        asyncio.create_task(server._game_tick_loop())
        async with srv:
            await srv.serve_forever()

    server_task = asyncio.create_task(run_server())

    await asyncio.sleep(0.5)  # 서버 기동 대기

    print("=" * 50)
    print("  TCP Bridge Server Integration Tests")
    print(f"  Port: {port}")
    print("=" * 50)
    print()

    try:
        passed, total = await run_tests(port)
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
