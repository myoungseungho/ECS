"""
Session 38-40 테스트: 길드 + 거래 + 우편 시스템
==================================================
tcp_bridge.py에 추가된 3개 시스템 통합 테스트.
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
    def __init__(self):
        self.reader = None
        self.writer = None
        self.recv_buf = bytearray()

    async def connect(self, host='127.0.0.1', port=0):
        self.reader, self.writer = await asyncio.open_connection(host, port)

    async def send(self, msg_type: int, payload: bytes = b''):
        pkt = build_packet(msg_type, payload)
        self.writer.write(pkt)
        await self.writer.drain()

    async def recv_packet(self, timeout=2.0):
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
                data = await asyncio.wait_for(self.reader.read(4096), timeout=min(remaining, 0.5))
                if not data:
                    return None, None
                self.recv_buf.extend(data)
            except asyncio.TimeoutError:
                if time.time() >= deadline:
                    return None, None

    async def recv_all_packets(self, timeout=0.5):
        packets = []
        while True:
            msg_type, payload = await self.recv_packet(timeout=timeout)
            if msg_type is None:
                break
            packets.append((msg_type, payload))
            timeout = 0.2
        return packets

    async def recv_specific(self, target_msg_type, timeout=2.0):
        """Receive packets until target_msg_type is found"""
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            msg_type, payload = await self.recv_packet(timeout=remaining)
            if msg_type is None:
                return None
            if msg_type == target_msg_type:
                return payload

    def close(self):
        if self.writer:
            self.writer.close()


async def login_and_enter(client, port, username='testuser', char_id=1):
    """Helper: connect, login, enter game"""
    await client.connect('127.0.0.1', port)
    await asyncio.sleep(0.1)

    uname = username.encode('utf-8')
    pw = b'pass123'
    await client.send(MsgType.LOGIN, struct.pack('<B', len(uname)) + uname + struct.pack('<B', len(pw)) + pw)
    await client.recv_packet()  # LOGIN_RESULT

    await client.send(MsgType.CHAR_SELECT, struct.pack('<I', char_id))
    packets = await client.recv_all_packets(timeout=1.0)

    # Find ENTER_GAME packet
    enter_game = None
    for mt, pl in packets:
        if mt == MsgType.ENTER_GAME:
            enter_game = pl
            break

    assert enter_game is not None, "ENTER_GAME not received"
    result = enter_game[0]
    assert result == 0, f"Enter game failed: result={result}"
    entity_id = struct.unpack_from('<Q', enter_game, 1)[0]
    return entity_id


async def run_tests(port: int):
    results = []
    total = 0
    passed = 0

    async def test(name, coro):
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

    print("\n" + "=" * 60)
    print("  Session 38-40: Guild / Trade / Mail Tests")
    print("=" * 60 + "\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  GUILD TESTS (Session 38)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Test 1: Guild Create
    async def test_guild_create():
        c = TestClient()
        eid = await login_and_enter(c, port, 'guild_master')

        name = b'TestGuild'
        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)

        resp = await c.recv_specific(MsgType.GUILD_INFO)
        assert resp is not None, "No GUILD_INFO response"
        result = resp[0]
        assert result == 0, f"Guild create should succeed, got result={result}"
        guild_id = struct.unpack_from('<I', resp, 1)[0]
        assert guild_id > 0, f"Guild ID should be > 0, got {guild_id}"
        c.close()

    await test("GUILD: 길드 생성 성공", test_guild_create())

    # Test 2: Guild create fails if already in guild
    async def test_guild_create_already():
        c = TestClient()
        eid = await login_and_enter(c, port, 'guild_dup')

        name = b'Guild1'
        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)
        await c.recv_specific(MsgType.GUILD_INFO)

        # Try creating another
        name2 = b'Guild2'
        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name2)) + name2)
        resp = await c.recv_specific(MsgType.GUILD_INFO)
        assert resp is not None, "No response"
        result = resp[0]
        assert result == 1, f"Should fail with already-in-guild, got result={result}"
        c.close()

    await test("GUILD: 이미 길드 소속 시 생성 실패", test_guild_create_already())

    # Test 3: Guild invite + accept
    async def test_guild_invite_accept():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'master2')

        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'member1')

        # c1 creates guild
        name = b'InviteGuild'
        await c1.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)
        resp = await c1.recv_specific(MsgType.GUILD_INFO)
        guild_id = struct.unpack_from('<I', resp, 1)[0]

        # c1 invites c2
        await c1.send(MsgType.GUILD_INVITE, struct.pack('<Q', eid2))

        # c2 should receive invite
        invite = await c2.recv_specific(MsgType.GUILD_INVITE, timeout=2.0)
        assert invite is not None, "c2 should receive GUILD_INVITE"
        invite_guild_id = struct.unpack_from('<I', invite, 0)[0]
        assert invite_guild_id == guild_id, f"Invite guild_id mismatch: {invite_guild_id} != {guild_id}"

        # c2 accepts
        await c2.send(MsgType.GUILD_ACCEPT, struct.pack('<I', guild_id))

        # c2 should get guild info
        resp2 = await c2.recv_specific(MsgType.GUILD_INFO)
        assert resp2 is not None, "c2 should receive GUILD_INFO"
        result2 = resp2[0]
        assert result2 == 0, f"Accept should succeed, got result={result2}"

        c1.close()
        c2.close()

    await test("GUILD: 초대 + 수락", test_guild_invite_accept())

    # Test 4: Guild leave
    async def test_guild_leave():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'master3')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'member2')

        name = b'LeaveGuild'
        await c1.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)
        resp = await c1.recv_specific(MsgType.GUILD_INFO)
        guild_id = struct.unpack_from('<I', resp, 1)[0]

        # invite + accept
        await c1.send(MsgType.GUILD_INVITE, struct.pack('<Q', eid2))
        await c2.recv_specific(MsgType.GUILD_INVITE)
        await c2.send(MsgType.GUILD_ACCEPT, struct.pack('<I', guild_id))
        await c2.recv_specific(MsgType.GUILD_INFO)

        # c2 leaves
        await c2.send(MsgType.GUILD_LEAVE)
        resp = await c2.recv_specific(MsgType.GUILD_INFO)
        assert resp is not None, "Should receive GUILD_INFO"
        result = resp[0]
        assert result == 0, f"Leave should succeed, got result={result}"
        left_guild_id = struct.unpack_from('<I', resp, 1)[0]
        assert left_guild_id == 0, f"Guild ID should be 0 after leaving, got {left_guild_id}"

        c1.close()
        c2.close()

    await test("GUILD: 탈퇴", test_guild_leave())

    # Test 5: Guild kick
    async def test_guild_kick():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'master4')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'kickme')

        name = b'KickGuild'
        await c1.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)
        resp = await c1.recv_specific(MsgType.GUILD_INFO)
        guild_id = struct.unpack_from('<I', resp, 1)[0]

        await c1.send(MsgType.GUILD_INVITE, struct.pack('<Q', eid2))
        await c2.recv_specific(MsgType.GUILD_INVITE)
        await c2.send(MsgType.GUILD_ACCEPT, struct.pack('<I', guild_id))
        await c2.recv_all_packets(timeout=0.5)  # drain
        await c1.recv_all_packets(timeout=0.5)  # drain

        # c1 kicks c2
        await c1.send(MsgType.GUILD_KICK, struct.pack('<Q', eid2))

        # c2 should get guild_id=0
        resp = await c2.recv_specific(MsgType.GUILD_INFO, timeout=2.0)
        assert resp is not None, "c2 should receive kick notification"
        kicked_guild_id = struct.unpack_from('<I', resp, 1)[0]
        assert kicked_guild_id == 0, f"Kicked player guild_id should be 0, got {kicked_guild_id}"

        c1.close()
        c2.close()

    await test("GUILD: 추방", test_guild_kick())

    # Test 6: Guild disband
    async def test_guild_disband():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'master5')

        name = b'DisbandGuild'
        await c1.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)
        await c1.recv_specific(MsgType.GUILD_INFO)

        await c1.send(MsgType.GUILD_DISBAND)
        resp = await c1.recv_specific(MsgType.GUILD_INFO)
        assert resp is not None, "Should receive disband notification"
        guild_id = struct.unpack_from('<I', resp, 1)[0]
        assert guild_id == 0, f"Guild ID should be 0 after disband, got {guild_id}"

        c1.close()

    await test("GUILD: 해산", test_guild_disband())

    # Test 7: Guild list
    async def test_guild_list():
        c = TestClient()
        eid = await login_and_enter(c, port, 'guild_lister')

        # Create a guild first
        name = b'ListTestGuild'
        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)
        await c.recv_specific(MsgType.GUILD_INFO)

        await c.send(MsgType.GUILD_LIST_REQ)
        resp = await c.recv_specific(MsgType.GUILD_LIST)
        assert resp is not None, "Should receive guild list"
        count = resp[0]
        assert count >= 1, f"Should have at least 1 guild, got {count}"
        c.close()

    await test("GUILD: 길드 목록 조회", test_guild_list())

    # Test 8: Guild info request
    async def test_guild_info_req():
        c = TestClient()
        eid = await login_and_enter(c, port, 'guild_info_guy')

        name = b'InfoGuild'
        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', len(name)) + name)
        await c.recv_specific(MsgType.GUILD_INFO)

        await c.send(MsgType.GUILD_INFO_REQ)
        resp = await c.recv_specific(MsgType.GUILD_INFO)
        assert resp is not None, "Should receive guild info"
        result = resp[0]
        assert result == 0, f"Info should succeed, got result={result}"
        c.close()

    await test("GUILD: 길드 정보 조회", test_guild_info_req())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  TRADE TESTS (Session 39)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Test 9: Trade request
    async def test_trade_request():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'trader1')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'trader2')

        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', eid2))

        # c1 should get result=0
        resp1 = await c1.recv_specific(MsgType.TRADE_RESULT)
        assert resp1 is not None, "c1 should receive TRADE_RESULT"
        assert resp1[0] == 0, f"Trade request should succeed, got {resp1[0]}"

        # c2 should get trade request
        resp2 = await c2.recv_specific(MsgType.TRADE_REQUEST)
        assert resp2 is not None, "c2 should receive TRADE_REQUEST"
        req_entity = struct.unpack_from('<Q', resp2, 0)[0]
        assert req_entity == eid1, f"Request entity should be {eid1}, got {req_entity}"

        c1.close()
        c2.close()

    await test("TRADE: 거래 요청", test_trade_request())

    # Test 10: Trade accept
    async def test_trade_accept():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'trade_a1')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'trade_a2')

        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', eid2))
        await c1.recv_specific(MsgType.TRADE_RESULT)
        await c2.recv_specific(MsgType.TRADE_REQUEST)

        await c2.send(MsgType.TRADE_ACCEPT, struct.pack('<Q', eid1))

        resp2 = await c2.recv_specific(MsgType.TRADE_RESULT)
        assert resp2 is not None, "c2 should receive accept result"
        assert resp2[0] == 0, f"Accept should succeed, got {resp2[0]}"

        c1.close()
        c2.close()

    await test("TRADE: 거래 수락", test_trade_accept())

    # Test 11: Trade decline
    async def test_trade_decline():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'trade_d1')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'trade_d2')

        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', eid2))
        await c1.recv_specific(MsgType.TRADE_RESULT)
        await c2.recv_specific(MsgType.TRADE_REQUEST)

        await c2.send(MsgType.TRADE_DECLINE)

        # c1 should receive decline (result=3)
        resp1 = await c1.recv_specific(MsgType.TRADE_RESULT, timeout=2.0)
        assert resp1 is not None, "c1 should receive decline notification"
        assert resp1[0] == 3, f"Decline result should be 3, got {resp1[0]}"

        c1.close()
        c2.close()

    await test("TRADE: 거래 거절", test_trade_decline())

    # Test 12: Trade gold exchange + confirm
    async def test_trade_gold():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'trade_g1')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'trade_g2')

        # Setup trade
        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', eid2))
        await c1.recv_specific(MsgType.TRADE_RESULT)
        await c2.recv_specific(MsgType.TRADE_REQUEST)
        await c2.send(MsgType.TRADE_ACCEPT, struct.pack('<Q', eid1))
        await c2.recv_specific(MsgType.TRADE_RESULT)
        await c1.recv_all_packets(timeout=0.3)  # drain

        # c1 adds 500 gold
        await c1.send(MsgType.TRADE_ADD_GOLD, struct.pack('<I', 500))

        # c2 should see gold
        gold_resp = await c2.recv_specific(MsgType.TRADE_ADD_GOLD)
        assert gold_resp is not None, "c2 should receive gold notification"
        amount = struct.unpack_from('<I', gold_resp, 0)[0]
        assert amount == 500, f"Gold amount should be 500, got {amount}"

        # Both confirm
        await c1.send(MsgType.TRADE_CONFIRM)
        await asyncio.sleep(0.1)
        await c2.send(MsgType.TRADE_CONFIRM)

        # Both should get success
        resp2 = await c2.recv_specific(MsgType.TRADE_RESULT)
        assert resp2 is not None, "c2 should receive trade complete"
        assert resp2[0] == 0, f"Trade should succeed, got {resp2[0]}"

        c1.close()
        c2.close()

    await test("TRADE: 골드 거래 + 확인", test_trade_gold())

    # Test 13: Trade item exchange
    async def test_trade_item():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'trade_i1')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'trade_i2')

        # Give c1 an item
        await c1.send(MsgType.ITEM_ADD, struct.pack('<IH', 201, 1))
        await c1.recv_specific(MsgType.ITEM_ADD_RESULT)

        # Setup trade
        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', eid2))
        await c1.recv_specific(MsgType.TRADE_RESULT)
        await c2.recv_specific(MsgType.TRADE_REQUEST)
        await c2.send(MsgType.TRADE_ACCEPT, struct.pack('<Q', eid1))
        await c2.recv_all_packets(timeout=0.3)
        await c1.recv_all_packets(timeout=0.3)

        # c1 adds item (slot 0, count 1)
        await c1.send(MsgType.TRADE_ADD_ITEM, struct.pack('<BH', 0, 1))

        # c2 should see item
        item_resp = await c2.recv_specific(MsgType.TRADE_ADD_ITEM)
        assert item_resp is not None, "c2 should receive item notification"
        slot, item_id, count = struct.unpack_from('<BIH', item_resp, 0)
        assert item_id == 201, f"Item ID should be 201, got {item_id}"
        assert count == 1, f"Count should be 1, got {count}"

        # Both confirm
        await c1.send(MsgType.TRADE_CONFIRM)
        await asyncio.sleep(0.1)
        await c2.send(MsgType.TRADE_CONFIRM)

        resp = await c2.recv_specific(MsgType.TRADE_RESULT)
        assert resp is not None and resp[0] == 0, "Trade should succeed"

        c1.close()
        c2.close()

    await test("TRADE: 아이템 거래 + 확인", test_trade_item())

    # Test 14: Trade cancel
    async def test_trade_cancel():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'trade_c1')
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'trade_c2')

        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', eid2))
        await c1.recv_specific(MsgType.TRADE_RESULT)
        await c2.recv_specific(MsgType.TRADE_REQUEST)
        await c2.send(MsgType.TRADE_ACCEPT, struct.pack('<Q', eid1))
        await c2.recv_all_packets(timeout=0.3)
        await c1.recv_all_packets(timeout=0.3)

        await c1.send(MsgType.TRADE_CANCEL)

        resp2 = await c2.recv_specific(MsgType.TRADE_RESULT, timeout=2.0)
        assert resp2 is not None, "c2 should receive cancel"
        assert resp2[0] == 4, f"Cancel result should be 4, got {resp2[0]}"

        c1.close()
        c2.close()

    await test("TRADE: 거래 취소", test_trade_cancel())

    # Test 15: Trade with non-existent target
    async def test_trade_invalid_target():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'trade_bad')

        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', 99999))
        resp = await c1.recv_specific(MsgType.TRADE_RESULT)
        assert resp is not None, "Should receive error"
        assert resp[0] == 1, f"Should fail with target not found (1), got {resp[0]}"
        c1.close()

    await test("TRADE: 존재하지 않는 대상", test_trade_invalid_target())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  MAIL TESTS (Session 40)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Test 16: Send mail
    async def test_mail_send():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'mailsender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'mailrecv', char_id=2)

        # c1 sends mail to c2's character name (Mage_01 for char_id=2)
        recipient = b'Mage_01'
        subject = b'Hello!'
        body = b'This is a test mail.'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 100, 0, 0)  # 100 gold, no item

        await c1.send(MsgType.MAIL_SEND, payload)

        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        assert resp is not None, "Should receive send result"
        result = resp[0]
        assert result == 0, f"Mail send should succeed, got result={result}"
        mail_id = struct.unpack_from('<I', resp, 1)[0]
        assert mail_id > 0, f"Mail ID should be > 0, got {mail_id}"

        c1.close()
        c2.close()

    await test("MAIL: 우편 보내기 (골드)", test_mail_send())

    # Test 17: Mail list
    async def test_mail_list():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'mlsender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'mlrecv', char_id=2)

        # Send mail
        recipient = b'Mage_01'
        subject = b'ListTest'
        body = b'body'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 50, 0, 0)
        await c1.send(MsgType.MAIL_SEND, payload)
        await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)

        # c2 checks mail list
        await c2.send(MsgType.MAIL_LIST_REQ)
        resp = await c2.recv_specific(MsgType.MAIL_LIST)
        assert resp is not None, "Should receive mail list"
        count = resp[0]
        assert count >= 1, f"Should have at least 1 mail, got {count}"

        c1.close()
        c2.close()

    await test("MAIL: 우편함 목록", test_mail_list())

    # Test 18: Mail read
    async def test_mail_read():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'mrsender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'mrrecv', char_id=2)

        # Send
        recipient = b'Mage_01'
        subject = b'ReadMe'
        body = b'Please read this mail'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 0, 0, 0)
        await c1.send(MsgType.MAIL_SEND, payload)
        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        mail_id = struct.unpack_from('<I', resp, 1)[0]

        # c2 reads
        await c2.send(MsgType.MAIL_READ, struct.pack('<I', mail_id))
        resp = await c2.recv_specific(MsgType.MAIL_READ_RESP)
        assert resp is not None, "Should receive mail content"
        result = resp[0]
        assert result == 0, f"Read should succeed, got result={result}"

        c1.close()
        c2.close()

    await test("MAIL: 우편 읽기", test_mail_read())

    # Test 19: Mail claim (gold)
    async def test_mail_claim_gold():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'mcsender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'mcrecv', char_id=2)

        # Send mail with gold
        recipient = b'Mage_01'
        subject = b'GoldMail'
        body = b'Take this gold'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 200, 0, 0)
        await c1.send(MsgType.MAIL_SEND, payload)
        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        mail_id = struct.unpack_from('<I', resp, 1)[0]

        # c2 claims
        await c2.send(MsgType.MAIL_CLAIM, struct.pack('<I', mail_id))
        resp = await c2.recv_specific(MsgType.MAIL_CLAIM_RESULT)
        assert resp is not None, "Should receive claim result"
        result = resp[0]
        assert result == 0, f"Claim should succeed, got result={result}"
        claimed_gold = struct.unpack_from('<I', resp, 5)[0]
        assert claimed_gold == 200, f"Claimed gold should be 200, got {claimed_gold}"

        c1.close()
        c2.close()

    await test("MAIL: 첨부 수령 (골드)", test_mail_claim_gold())

    # Test 20: Mail claim (item)
    async def test_mail_claim_item():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'misender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'mirecv', char_id=2)

        # Give c1 an item first
        await c1.send(MsgType.ITEM_ADD, struct.pack('<IH', 101, 5))
        await c1.recv_specific(MsgType.ITEM_ADD_RESULT)

        # Send mail with item
        recipient = b'Mage_01'
        subject = b'ItemMail'
        body = b'Take this item'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 0, 101, 3)  # 0 gold, item 101 x3
        await c1.send(MsgType.MAIL_SEND, payload)
        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        mail_id = struct.unpack_from('<I', resp, 1)[0]

        # c2 claims
        await c2.send(MsgType.MAIL_CLAIM, struct.pack('<I', mail_id))
        resp = await c2.recv_specific(MsgType.MAIL_CLAIM_RESULT)
        assert resp is not None, "Should receive claim result"
        result = resp[0]
        assert result == 0, f"Claim should succeed, got result={result}"
        claimed_item = struct.unpack_from('<I', resp, 9)[0]
        claimed_count = struct.unpack_from('<H', resp, 13)[0]
        assert claimed_item == 101, f"Claimed item should be 101, got {claimed_item}"
        assert claimed_count == 3, f"Claimed count should be 3, got {claimed_count}"

        c1.close()
        c2.close()

    await test("MAIL: 첨부 수령 (아이템)", test_mail_claim_item())

    # Test 21: Mail delete
    async def test_mail_delete():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'mdsender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'mdrecv', char_id=2)

        # Send mail without attachment
        recipient = b'Mage_01'
        subject = b'DeleteMe'
        body = b'No attachment'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 0, 0, 0)
        await c1.send(MsgType.MAIL_SEND, payload)
        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        mail_id = struct.unpack_from('<I', resp, 1)[0]

        # c2 deletes
        await c2.send(MsgType.MAIL_DELETE, struct.pack('<I', mail_id))
        resp = await c2.recv_specific(MsgType.MAIL_DELETE_RESULT)
        assert resp is not None, "Should receive delete result"
        result = resp[0]
        assert result == 0, f"Delete should succeed, got result={result}"

        c1.close()
        c2.close()

    await test("MAIL: 우편 삭제", test_mail_delete())

    # Test 22: Can't delete mail with unclaimed attachment
    async def test_mail_delete_unclaimed():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'mucsender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'mucrecv', char_id=2)

        # Send mail with gold
        recipient = b'Mage_01'
        subject = b'DontDelete'
        body = b'Has gold'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 100, 0, 0)
        await c1.send(MsgType.MAIL_SEND, payload)
        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        mail_id = struct.unpack_from('<I', resp, 1)[0]

        # c2 tries to delete WITHOUT claiming
        await c2.send(MsgType.MAIL_DELETE, struct.pack('<I', mail_id))
        resp = await c2.recv_specific(MsgType.MAIL_DELETE_RESULT)
        assert resp is not None, "Should receive delete error"
        result = resp[0]
        assert result == 2, f"Should fail with unclaimed attachment (2), got {result}"

        c1.close()
        c2.close()

    await test("MAIL: 미수령 첨부 있을 때 삭제 거부", test_mail_delete_unclaimed())

    # Test 23: Mail to non-existent recipient
    async def test_mail_bad_recipient():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'mailbad')

        recipient = b'Nobody'
        subject = b'Test'
        body = b'body'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 0, 0, 0)
        await c1.send(MsgType.MAIL_SEND, payload)

        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        assert resp is not None, "Should receive error"
        assert resp[0] == 1, f"Should fail with recipient not found (1), got {resp[0]}"
        c1.close()

    await test("MAIL: 존재하지 않는 수신자", test_mail_bad_recipient())

    # Test 24: Double claim
    async def test_mail_double_claim():
        c1 = TestClient()
        eid1 = await login_and_enter(c1, port, 'dcsender', char_id=1)
        c2 = TestClient()
        eid2 = await login_and_enter(c2, port, 'dcrecv', char_id=2)

        # Send mail with gold
        recipient = b'Mage_01'
        subject = b'DoubleClaim'
        body = b'Try claiming twice'
        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 50, 0, 0)
        await c1.send(MsgType.MAIL_SEND, payload)
        resp = await c1.recv_specific(MsgType.MAIL_DELETE_RESULT)
        mail_id = struct.unpack_from('<I', resp, 1)[0]

        # c2 claims first time
        await c2.send(MsgType.MAIL_CLAIM, struct.pack('<I', mail_id))
        resp1 = await c2.recv_specific(MsgType.MAIL_CLAIM_RESULT)
        assert resp1[0] == 0, "First claim should succeed"

        # c2 claims second time
        await c2.send(MsgType.MAIL_CLAIM, struct.pack('<I', mail_id))
        resp2 = await c2.recv_specific(MsgType.MAIL_CLAIM_RESULT)
        assert resp2[0] == 2, f"Double claim should fail (2=already claimed), got {resp2[0]}"

        c1.close()
        c2.close()

    await test("MAIL: 중복 수령 방지", test_mail_double_claim())

    # ━━━ 결과 요약 ━━━
    print("\n" + "=" * 60)
    print(f"  Results: {passed} PASS / {total - passed} FAIL / {total} TOTAL")
    print("=" * 60)

    for r in results:
        if "FAIL" in r or "ERR" in r:
            print(r)

    return passed, total


async def main():
    server = BridgeServer(port=0, verbose=False)

    # Find free port
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    server.port = port

    # Start server
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)

    try:
        passed, total = await run_tests(port)
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
