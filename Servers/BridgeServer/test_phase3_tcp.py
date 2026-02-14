"""
Phase 3 TCP 연동 테스트: Guild / Trade / Mail
==============================================
tcp_bridge.py를 실행한 상태에서 돌리면 됩니다.

사용법:
  cd Servers/BridgeServer
  # (터미널 1) python _patch.py && python _patch_s034.py && python _patch_s035.py && python _patch_s036.py && python _patch_s037.py && python tcp_bridge.py
  # (터미널 2) python test_phase3_tcp.py
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

    print("\n" + "=" * 60)
    print("  Phase 3 TCP Integration Tests: Guild / Trade / Mail")
    print("=" * 60 + "\n")

    # ━━━ 1. GUILD CREATE ━━━
    async def test_guild_create():
        c = TestClient()
        await login_and_enter(c, 'gmaster', port)

        guild_name = b'TestGuild'
        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', len(guild_name)) + guild_name)

        mt, pl = await c.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        assert mt == MsgType.GUILD_INFO, f"Expected GUILD_INFO, got {mt}"
        result = pl[0]
        assert result == 0, f"Guild create should succeed (result=0), got {result}"
        guild_id = struct.unpack_from('<I', pl, 1)[0]
        assert guild_id > 0, f"Guild ID should be > 0, got {guild_id}"
        c.close()

    await test("GUILD_CREATE: 길드 생성", test_guild_create())

    # ━━━ 2. GUILD LIST ━━━
    async def test_guild_list():
        c = TestClient()
        await login_and_enter(c, 'glist', port)

        await c.send(MsgType.GUILD_LIST_REQ)
        mt, pl = await c.recv_expect(MsgType.GUILD_LIST, timeout=3.0)
        assert mt == MsgType.GUILD_LIST, f"Expected GUILD_LIST, got {mt}"
        count = pl[0]
        assert count >= 1, f"Should have at least 1 guild, got {count}"
        c.close()

    await test("GUILD_LIST: 길드 목록 조회", test_guild_list())

    # ━━━ 3. GUILD INVITE + ACCEPT ━━━
    async def test_guild_invite_accept():
        master = TestClient()
        member = TestClient()
        await login_and_enter(master, 'ginvmas', port)
        await login_and_enter(member, 'ginvmem', port)

        # Master creates guild
        guild_name = b'InvGuild'
        await master.send(MsgType.GUILD_CREATE, struct.pack('<B', len(guild_name)) + guild_name)
        mt, pl = await master.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        assert mt == MsgType.GUILD_INFO, "Master should receive GUILD_INFO"
        guild_id = struct.unpack_from('<I', pl, 1)[0]

        # Master invites member
        await master.send(MsgType.GUILD_INVITE, struct.pack('<Q', member.entity_id))

        # Member receives invite
        mt, pl = await member.recv_expect(MsgType.GUILD_INVITE, timeout=3.0)
        assert mt == MsgType.GUILD_INVITE, f"Member should receive GUILD_INVITE, got {mt}"
        recv_guild_id = struct.unpack_from('<I', pl, 0)[0]
        assert recv_guild_id == guild_id, f"Invite guild_id mismatch: {recv_guild_id} != {guild_id}"

        # Member accepts
        await member.send(MsgType.GUILD_ACCEPT, struct.pack('<I', guild_id))
        mt, pl = await member.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        assert mt == MsgType.GUILD_INFO, "Member should receive GUILD_INFO after accept"
        result = pl[0]
        assert result == 0, f"Accept should succeed, got result={result}"

        master.close()
        member.close()

    await test("GUILD_INVITE+ACCEPT: 길드 초대 + 수락", test_guild_invite_accept())

    # ━━━ 4. GUILD LEAVE ━━━
    async def test_guild_leave():
        master = TestClient()
        member = TestClient()
        await login_and_enter(master, 'glvmas', port)
        await login_and_enter(member, 'glvmem', port)

        # Create + invite + accept
        await master.send(MsgType.GUILD_CREATE, struct.pack('<B', 7) + b'LvGuild')
        await master.recv_expect(MsgType.GUILD_INFO)
        mt, pl = await master.recv_packet(timeout=1.0)  # drain any extra
        guild_id_data = None

        # Re-get guild info to find guild_id
        await master.send(MsgType.GUILD_INFO_REQ)
        mt, pl = await master.recv_expect(MsgType.GUILD_INFO)
        guild_id = struct.unpack_from('<I', pl, 1)[0]

        await master.send(MsgType.GUILD_INVITE, struct.pack('<Q', member.entity_id))
        await member.recv_expect(MsgType.GUILD_INVITE)
        await member.send(MsgType.GUILD_ACCEPT, struct.pack('<I', guild_id))
        await member.recv_expect(MsgType.GUILD_INFO)
        await asyncio.sleep(0.2)
        # Drain master's notification
        await master.recv_all_packets(timeout=0.5)

        # Member leaves
        await member.send(MsgType.GUILD_LEAVE)
        mt, pl = await member.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        assert mt == MsgType.GUILD_INFO, "Should receive GUILD_INFO after leave"
        # After leave, result=0 but guild_id=0 (empty info)
        member_guild_id = struct.unpack_from('<I', pl, 1)[0]
        assert member_guild_id == 0, f"After leave, guild_id should be 0, got {member_guild_id}"

        master.close()
        member.close()

    await test("GUILD_LEAVE: 길드 탈퇴", test_guild_leave())

    # ━━━ 5. GUILD DISBAND ━━━
    async def test_guild_disband():
        c = TestClient()
        await login_and_enter(c, 'gdisband', port)

        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', 8) + b'DiGuild1')
        mt, pl = await c.recv_expect(MsgType.GUILD_INFO)
        assert mt == MsgType.GUILD_INFO

        await c.send(MsgType.GUILD_DISBAND)
        mt, pl = await c.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        assert mt == MsgType.GUILD_INFO, "Should receive GUILD_INFO after disband"
        guild_id = struct.unpack_from('<I', pl, 1)[0]
        assert guild_id == 0, f"After disband, guild_id should be 0, got {guild_id}"
        c.close()

    await test("GUILD_DISBAND: 길드 해산", test_guild_disband())

    # ━━━ 6. GUILD INFO REQ ━━━
    async def test_guild_info():
        c = TestClient()
        await login_and_enter(c, 'ginfo', port)

        # No guild yet
        await c.send(MsgType.GUILD_INFO_REQ)
        mt, pl = await c.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        assert mt == MsgType.GUILD_INFO
        guild_id = struct.unpack_from('<I', pl, 1)[0]
        assert guild_id == 0, f"No guild, should get guild_id=0, got {guild_id}"

        # Create guild and check info
        await c.send(MsgType.GUILD_CREATE, struct.pack('<B', 7) + b'InfoGld')
        await c.recv_expect(MsgType.GUILD_INFO)

        await c.send(MsgType.GUILD_INFO_REQ)
        mt, pl = await c.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        guild_id = struct.unpack_from('<I', pl, 1)[0]
        assert guild_id > 0, f"After create, guild_id should be > 0"
        c.close()

    await test("GUILD_INFO: 길드 정보 조회", test_guild_info())

    # ━━━ 7. TRADE REQUEST + ACCEPT + ADD_ITEM + CONFIRM ━━━
    async def test_trade_full_flow():
        seller = TestClient()
        buyer = TestClient()
        await login_and_enter(seller, 'seller1', port)
        await login_and_enter(buyer, 'buyer01', port)

        # Seller adds item to inventory first
        await seller.send(MsgType.ITEM_ADD, struct.pack('<IH', 501, 3))
        await seller.recv_expect(MsgType.ITEM_ADD_RESULT, timeout=2.0)

        # Seller requests trade with buyer
        await seller.send(MsgType.TRADE_REQUEST, struct.pack('<Q', buyer.entity_id))

        # Seller should get TRADE_RESULT(0) = request sent
        mt, pl = await seller.recv_expect(MsgType.TRADE_RESULT, timeout=3.0)
        assert mt == MsgType.TRADE_RESULT, f"Seller should get TRADE_RESULT, got {mt}"
        assert pl[0] == 0, f"Trade request should succeed, got {pl[0]}"

        # Buyer receives TRADE_REQUEST
        mt, pl = await buyer.recv_expect(MsgType.TRADE_REQUEST, timeout=3.0)
        assert mt == MsgType.TRADE_REQUEST, f"Buyer should get TRADE_REQUEST, got {mt}"
        requester_entity = struct.unpack_from('<Q', pl, 0)[0]
        assert requester_entity == seller.entity_id

        # Buyer accepts
        await buyer.send(MsgType.TRADE_ACCEPT, struct.pack('<Q', seller.entity_id))
        await asyncio.sleep(0.2)

        # Both receive TRADE_RESULT(0)
        buyer_pkts = await buyer.recv_all_packets(timeout=1.0)
        buyer_results = [p for p in buyer_pkts if p[0] == MsgType.TRADE_RESULT]
        assert len(buyer_results) >= 1, "Buyer should get TRADE_RESULT after accept"

        seller_pkts = await seller.recv_all_packets(timeout=1.0)
        seller_results = [p for p in seller_pkts if p[0] == MsgType.TRADE_RESULT]
        assert len(seller_results) >= 1, "Seller should get TRADE_RESULT after accept"

        # Seller adds item to trade (slot 0, count 2)
        await seller.send(MsgType.TRADE_ADD_ITEM, struct.pack('<BH', 0, 2))
        await asyncio.sleep(0.2)

        # Buyer should see TRADE_ADD_ITEM
        mt, pl = await buyer.recv_expect(MsgType.TRADE_ADD_ITEM, timeout=3.0)
        assert mt == MsgType.TRADE_ADD_ITEM, f"Buyer should receive TRADE_ADD_ITEM, got {mt}"

        # Buyer adds gold
        await buyer.send(MsgType.TRADE_ADD_GOLD, struct.pack('<I', 100))
        await asyncio.sleep(0.2)

        # Seller should see TRADE_ADD_GOLD
        mt, pl = await seller.recv_expect(MsgType.TRADE_ADD_GOLD, timeout=3.0)
        assert mt == MsgType.TRADE_ADD_GOLD, f"Seller should receive TRADE_ADD_GOLD, got {mt}"

        # Both confirm
        await seller.send(MsgType.TRADE_CONFIRM)
        await asyncio.sleep(0.1)
        await buyer.send(MsgType.TRADE_CONFIRM)
        await asyncio.sleep(0.3)

        # Both should get TRADE_RESULT(0) = complete
        mt, pl = await seller.recv_expect(MsgType.TRADE_RESULT, timeout=3.0)
        assert mt == MsgType.TRADE_RESULT, f"Seller should get final TRADE_RESULT, got {mt}"
        assert pl[0] == 0, f"Trade should complete (result=0), got {pl[0]}"

        mt, pl = await buyer.recv_expect(MsgType.TRADE_RESULT, timeout=3.0)
        assert mt == MsgType.TRADE_RESULT, f"Buyer should get final TRADE_RESULT, got {mt}"
        assert pl[0] == 0, f"Trade should complete (result=0), got {pl[0]}"

        seller.close()
        buyer.close()

    await test("TRADE: 전체 흐름 (요청→수락→아이템/골드→확정)", test_trade_full_flow())

    # ━━━ 8. TRADE CANCEL ━━━
    async def test_trade_cancel():
        c1 = TestClient()
        c2 = TestClient()
        await login_and_enter(c1, 'tcanc1', port)
        await login_and_enter(c2, 'tcanc2', port)

        # Request trade
        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', c2.entity_id))
        await c1.recv_expect(MsgType.TRADE_RESULT)
        await c2.recv_expect(MsgType.TRADE_REQUEST)

        # Accept
        await c2.send(MsgType.TRADE_ACCEPT, struct.pack('<Q', c1.entity_id))
        await asyncio.sleep(0.3)
        await c1.recv_all_packets(timeout=0.5)
        await c2.recv_all_packets(timeout=0.5)

        # Cancel
        await c1.send(MsgType.TRADE_CANCEL)
        await asyncio.sleep(0.2)

        mt, pl = await c1.recv_expect(MsgType.TRADE_RESULT, timeout=3.0)
        assert mt == MsgType.TRADE_RESULT, f"Canceller should get TRADE_RESULT, got {mt}"
        assert pl[0] == 4, f"Cancel result should be 4, got {pl[0]}"

        mt, pl = await c2.recv_expect(MsgType.TRADE_RESULT, timeout=3.0)
        assert mt == MsgType.TRADE_RESULT, f"Partner should get TRADE_RESULT, got {mt}"
        assert pl[0] == 4, f"Partner cancel result should be 4, got {pl[0]}"

        c1.close()
        c2.close()

    await test("TRADE_CANCEL: 거래 취소", test_trade_cancel())

    # ━━━ 9. TRADE DECLINE ━━━
    async def test_trade_decline():
        c1 = TestClient()
        c2 = TestClient()
        await login_and_enter(c1, 'tdecl1', port)
        await login_and_enter(c2, 'tdecl2', port)

        await c1.send(MsgType.TRADE_REQUEST, struct.pack('<Q', c2.entity_id))
        await c1.recv_expect(MsgType.TRADE_RESULT)
        await c2.recv_expect(MsgType.TRADE_REQUEST)

        # c2 accepts first (to establish trade partner)
        await c2.send(MsgType.TRADE_ACCEPT, struct.pack('<Q', c1.entity_id))
        await asyncio.sleep(0.3)
        await c1.recv_all_packets(timeout=0.5)
        await c2.recv_all_packets(timeout=0.5)

        # Now decline (essentially cancel the established trade)
        await c2.send(MsgType.TRADE_DECLINE)
        await asyncio.sleep(0.2)

        mt, pl = await c2.recv_expect(MsgType.TRADE_RESULT, timeout=3.0)
        assert mt == MsgType.TRADE_RESULT, f"Decliner should get TRADE_RESULT, got {mt}"
        assert pl[0] == 3, f"Decline result should be 3, got {pl[0]}"

        c1.close()
        c2.close()

    await test("TRADE_DECLINE: 거래 거절", test_trade_decline())

    # ━━━ 10. MAIL SEND + LIST + READ ━━━
    # NOTE: 모든 플레이어가 CHAR_SELECT(1) → char_name="Warrior_01"
    # 수신자 이름은 char_name 기준으로 찾으므로 "Warrior_01" 사용
    async def test_mail_send_and_read():
        sender = TestClient()
        receiver = TestClient()
        await login_and_enter(receiver, 'mrecver', port)  # receiver 먼저 (세션 순서)
        await login_and_enter(sender, 'msender', port)

        # Send mail to "Warrior_01" (receiver의 char_name)
        recipient = b'Warrior_01'
        subject = b'Hello'
        body = b'Test mail body'

        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 0, 0, 0)  # gold=0, item_id=0, item_count=0

        await sender.send(MsgType.MAIL_SEND, payload)

        # Sender gets MAIL_DELETE_RESULT (reused as send result)
        mt, pl = await sender.recv_expect(MsgType.MAIL_DELETE_RESULT, timeout=3.0)
        assert mt == MsgType.MAIL_DELETE_RESULT, f"Sender should get result, got {mt}"
        result = pl[0]
        assert result == 0, f"Mail send should succeed (result=0), got {result}"
        mail_id = struct.unpack_from('<I', pl, 1)[0]
        assert mail_id > 0, f"Mail ID should be > 0"

        # 수신자가 목록 확인 — char_name이 같으므로 first-match가 receiver일 수 있음
        # receiver의 account_id로 메일이 저장되므로 receiver에서 조회
        await receiver.send(MsgType.MAIL_LIST_REQ)
        mt, pl = await receiver.recv_expect(MsgType.MAIL_LIST, timeout=3.0)
        assert mt == MsgType.MAIL_LIST, f"Expected MAIL_LIST, got {mt}"
        count = pl[0]
        assert count >= 1, f"Should have at least 1 mail, got {count}"

        # Read the mail
        await receiver.send(MsgType.MAIL_READ, struct.pack('<I', mail_id))
        mt, pl = await receiver.recv_expect(MsgType.MAIL_READ_RESP, timeout=3.0)
        assert mt == MsgType.MAIL_READ_RESP, f"Expected MAIL_READ_RESP, got {mt}"
        result = pl[0]
        assert result == 0, f"Mail read should succeed (result=0), got {result}"

        sender.close()
        receiver.close()

    await test("MAIL: 발송 + 목록 + 읽기", test_mail_send_and_read())

    # ━━━ 11. MAIL WITH ATTACHMENT (GOLD + ITEM) ━━━
    async def test_mail_with_attachment():
        sender = TestClient()
        receiver = TestClient()
        await login_and_enter(receiver, 'mattrcv', port)  # receiver 먼저
        await login_and_enter(sender, 'mattsen', port)

        # Sender adds item
        await sender.send(MsgType.ITEM_ADD, struct.pack('<IH', 701, 5))
        await sender.recv_expect(MsgType.ITEM_ADD_RESULT)

        # Send mail with gold(50) + item(701, count 2)
        recipient = b'Warrior_01'
        subject = b'Gift'
        body = b'Here is your stuff'

        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 50, 701, 2)

        await sender.send(MsgType.MAIL_SEND, payload)
        mt, pl = await sender.recv_expect(MsgType.MAIL_DELETE_RESULT, timeout=3.0)
        assert mt == MsgType.MAIL_DELETE_RESULT
        result = pl[0]
        assert result == 0, f"Mail send with attachment should succeed, got {result}"
        mail_id = struct.unpack_from('<I', pl, 1)[0]

        # Receiver claims attachment
        await receiver.send(MsgType.MAIL_CLAIM, struct.pack('<I', mail_id))
        mt, pl = await receiver.recv_expect(MsgType.MAIL_CLAIM_RESULT, timeout=3.0)
        assert mt == MsgType.MAIL_CLAIM_RESULT, f"Expected MAIL_CLAIM_RESULT, got {mt}"
        result = pl[0]
        assert result == 0, f"Claim should succeed (result=0), got {result}"
        claimed_mail_id = struct.unpack_from('<I', pl, 1)[0]
        assert claimed_mail_id == mail_id

        sender.close()
        receiver.close()

    await test("MAIL_ATTACHMENT: 골드+아이템 첨부 + 수령", test_mail_with_attachment())

    # ━━━ 12. MAIL DELETE ━━━
    async def test_mail_delete():
        sender = TestClient()
        receiver = TestClient()
        await login_and_enter(receiver, 'mdelrcv', port)  # receiver 먼저
        await login_and_enter(sender, 'mdelsen', port)

        # Send simple mail (no attachment)
        recipient = b'Warrior_01'
        subject = b'DelMe'
        body = b'Delete this'

        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 0, 0, 0)

        await sender.send(MsgType.MAIL_SEND, payload)
        mt, pl = await sender.recv_expect(MsgType.MAIL_DELETE_RESULT, timeout=3.0)
        mail_id = struct.unpack_from('<I', pl, 1)[0]

        # Receiver deletes
        await receiver.send(MsgType.MAIL_DELETE, struct.pack('<I', mail_id))
        mt, pl = await receiver.recv_expect(MsgType.MAIL_DELETE_RESULT, timeout=3.0)
        assert mt == MsgType.MAIL_DELETE_RESULT, f"Expected MAIL_DELETE_RESULT, got {mt}"
        result = pl[0]
        assert result == 0, f"Delete should succeed (result=0), got {result}"

        # Verify list is now empty (or doesn't contain deleted mail)
        await receiver.send(MsgType.MAIL_LIST_REQ)
        mt, pl = await receiver.recv_expect(MsgType.MAIL_LIST, timeout=3.0)
        assert mt == MsgType.MAIL_LIST
        count = pl[0]
        # Might have 0 mails now
        # Verify the deleted mail_id is not in list
        offset = 1
        for i in range(count):
            listed_id = struct.unpack_from('<I', pl, offset)[0]
            assert listed_id != mail_id, f"Deleted mail {mail_id} should not appear in list"
            offset += 4 + 32 + 64 + 2 + 4  # id + sender_name + subject + read/attach + time

        sender.close()
        receiver.close()

    await test("MAIL_DELETE: 우편 삭제", test_mail_delete())

    # ━━━ 13. MAIL DELETE BLOCKED (unclaimed attachment) ━━━
    async def test_mail_delete_unclaimed():
        sender = TestClient()
        receiver = TestClient()
        await login_and_enter(receiver, 'mblkrcv', port)  # receiver 먼저
        await login_and_enter(sender, 'mblksen', port)

        # Sender adds item and sends mail with attachment
        await sender.send(MsgType.ITEM_ADD, struct.pack('<IH', 801, 1))
        await sender.recv_expect(MsgType.ITEM_ADD_RESULT)

        recipient = b'Warrior_01'
        subject = b'Blocked'
        body = b'Cannot delete'

        payload = struct.pack('<B', len(recipient)) + recipient
        payload += struct.pack('<B', len(subject)) + subject
        payload += struct.pack('<H', len(body)) + body
        payload += struct.pack('<IIH', 100, 801, 1)

        await sender.send(MsgType.MAIL_SEND, payload)
        mt, pl = await sender.recv_expect(MsgType.MAIL_DELETE_RESULT, timeout=3.0)
        mail_id = struct.unpack_from('<I', pl, 1)[0]

        # Try to delete without claiming
        await receiver.send(MsgType.MAIL_DELETE, struct.pack('<I', mail_id))
        mt, pl = await receiver.recv_expect(MsgType.MAIL_DELETE_RESULT, timeout=3.0)
        assert mt == MsgType.MAIL_DELETE_RESULT
        result = pl[0]
        assert result == 2, f"Delete unclaimed should fail (result=2), got {result}"

        sender.close()
        receiver.close()

    await test("MAIL_DELETE_BLOCKED: 미수령 첨부 삭제 불가", test_mail_delete_unclaimed())

    # ━━━ 14. GUILD KICK ━━━
    async def test_guild_kick():
        master = TestClient()
        member = TestClient()
        await login_and_enter(master, 'gkckmas', port)
        await login_and_enter(member, 'gkckmem', port)

        # Create guild
        await master.send(MsgType.GUILD_CREATE, struct.pack('<B', 8) + b'KickGild')
        await master.recv_expect(MsgType.GUILD_INFO)

        await master.send(MsgType.GUILD_INFO_REQ)
        mt, pl = await master.recv_expect(MsgType.GUILD_INFO)
        guild_id = struct.unpack_from('<I', pl, 1)[0]

        # Invite + accept
        await master.send(MsgType.GUILD_INVITE, struct.pack('<Q', member.entity_id))
        await member.recv_expect(MsgType.GUILD_INVITE)
        await member.send(MsgType.GUILD_ACCEPT, struct.pack('<I', guild_id))
        await member.recv_expect(MsgType.GUILD_INFO)
        await asyncio.sleep(0.2)
        await master.recv_all_packets(timeout=0.5)

        # Master kicks member
        await master.send(MsgType.GUILD_KICK, struct.pack('<Q', member.entity_id))
        await asyncio.sleep(0.3)

        # Member should get empty GUILD_INFO (kicked)
        mt, pl = await member.recv_expect(MsgType.GUILD_INFO, timeout=3.0)
        assert mt == MsgType.GUILD_INFO, f"Kicked member should get GUILD_INFO, got {mt}"
        kicked_guild_id = struct.unpack_from('<I', pl, 1)[0]
        assert kicked_guild_id == 0, f"Kicked member guild_id should be 0, got {kicked_guild_id}"

        master.close()
        member.close()

    await test("GUILD_KICK: 길드 추방", test_guild_kick())

    # ━━━ Summary ━━━
    print("\n" + "=" * 60)
    print(f"  Phase 3 Results: {passed}/{total} PASS")
    print("=" * 60)
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
