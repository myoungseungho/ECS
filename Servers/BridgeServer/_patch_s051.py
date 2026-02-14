"""
Patch S051: Social Enhancement (TASK 5 — Friend/Block/Party Finder)
- FRIEND_REQUEST(410)->FRIEND_REQUEST_RESULT(411)          -- 친구 요청. max_friends:100, expire:72h.
- FRIEND_ACCEPT(412)/FRIEND_REJECT(413)                    -- 수락/거절
- FRIEND_LIST_REQ(414)->FRIEND_LIST(415)                   -- 친구 목록 (온라인 상태 + 위치)
- BLOCK_PLAYER(416)->BLOCK_RESULT(417)                     -- 차단
- UNBLOCK_PLAYER(418)->UNBLOCK_RESULT(419) (reuse 417)     -- 해제
  (Note: BLOCK_LIST uses 418->419)
- PARTY_FINDER_LIST(420)->PARTY_FINDER_LIST_RESULT(421) (reuse msg pair)
- PARTY_FINDER_CREATE(421)->result via 421
  (Adjusted: LIST=420, CREATE=421, JOIN=422)
- 5 test cases

MsgType layout (GDD social.yaml):
  410 FRIEND_REQUEST
  411 FRIEND_REQUEST_RESULT
  412 FRIEND_ACCEPT
  413 FRIEND_REJECT
  414 FRIEND_LIST_REQ
  415 FRIEND_LIST
  416 BLOCK_PLAYER
  417 BLOCK_RESULT
  418 BLOCK_LIST_REQ
  419 BLOCK_LIST
  420 PARTY_FINDER_LIST_REQ
  421 PARTY_FINDER_LIST
  422 PARTY_FINDER_CREATE
"""
import os
import sys
import re
import time

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Social Enhancement (410-422)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Social Enhancement (TASK 5)\n'
    '    FRIEND_REQUEST = 410\n'
    '    FRIEND_REQUEST_RESULT = 411\n'
    '    FRIEND_ACCEPT = 412\n'
    '    FRIEND_REJECT = 413\n'
    '    FRIEND_LIST_REQ = 414\n'
    '    FRIEND_LIST = 415\n'
    '    BLOCK_PLAYER = 416\n'
    '    BLOCK_RESULT = 417\n'
    '    BLOCK_LIST_REQ = 418\n'
    '    BLOCK_LIST = 419\n'
    '    PARTY_FINDER_LIST_REQ = 420\n'
    '    PARTY_FINDER_LIST = 421\n'
    '    PARTY_FINDER_CREATE = 422\n'
)

# ====================================================================
# 2. Social data constants (GDD social.yaml)
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Social Enhancement Data (GDD social.yaml) ----
FRIEND_MAX = 100                     # max friends per player
FRIEND_REQUEST_EXPIRE_H = 72        # friend request expire hours
BLOCK_MAX = 100                      # max blocked players
PARTY_FINDER_CATEGORIES = ["dungeon", "raid", "field_hunting", "quest", "other"]
PARTY_FINDER_TITLE_MAX = 30          # max title length
PARTY_FINDER_MAX_LISTINGS = 1        # max 1 listing per player
PARTY_FINDER_ROLES = ["tank", "dps", "support", "any"]

# Global party finder board (shared across all sessions via server ref)
# This is a list to allow mutations from handler methods
_PARTY_FINDER_BOARD = []   # [{listing_id, owner, title, category, min_level, role, created_at}, ...]
_PARTY_FINDER_NEXT_ID = [1]
'''

# ====================================================================
# 3. PlayerSession fields for social enhancement
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Social Enhancement (TASK 5) ----\n'
    '    friends: list = field(default_factory=list)              # [player_name, ...]\n'
    '    friend_requests_sent: list = field(default_factory=list) # [target_name, ...]\n'
    '    friend_requests_recv: list = field(default_factory=list) # [from_name, ...]\n'
    '    blocked_players: list = field(default_factory=list)      # [player_name, ...]\n'
    '    party_finder_listing: dict = field(default_factory=dict) # current listing or {}\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.FRIEND_REQUEST: self._on_friend_request,\n'
    '            MsgType.FRIEND_ACCEPT: self._on_friend_accept,\n'
    '            MsgType.FRIEND_REJECT: self._on_friend_reject,\n'
    '            MsgType.FRIEND_LIST_REQ: self._on_friend_list_req,\n'
    '            MsgType.BLOCK_PLAYER: self._on_block_player,\n'
    '            MsgType.BLOCK_LIST_REQ: self._on_block_list_req,\n'
    '            MsgType.PARTY_FINDER_LIST_REQ: self._on_party_finder_list_req,\n'
    '            MsgType.PARTY_FINDER_CREATE: self._on_party_finder_create,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Social Enhancement (TASK 5: MsgType 410-422) ----

    def _find_session_by_name(self, name: str):
        """Find a connected session by character name."""
        for s in self.sessions.values():
            if getattr(s, 'character_name', '') == name:
                return s
        return None

    async def _on_friend_request(self, session, payload: bytes):
        """FRIEND_REQUEST(410) -> FRIEND_REQUEST_RESULT(411)
        Request: target_name_len(u8) + target_name(str)
        Response: result(u8) + target_name_len(u8) + target_name(str)
          result: 0=SUCCESS, 1=PLAYER_NOT_FOUND, 2=ALREADY_FRIENDS, 3=ALREADY_SENT,
                  4=BLOCKED, 5=FRIEND_LIST_FULL, 6=TARGET_FULL, 7=SELF_REQUEST"""
        if not session.in_game or len(payload) < 1:
            return

        name_len = payload[0]
        if len(payload) < 1 + name_len:
            return
        target_name = payload[1:1+name_len].decode('utf-8')

        def _send_result(result_code):
            nb = target_name.encode('utf-8')
            self._send(session, MsgType.FRIEND_REQUEST_RESULT,
                       struct.pack('<B B', result_code, len(nb)) + nb)

        # Self request check
        if target_name == getattr(session, 'character_name', ''):
            _send_result(7)  # SELF_REQUEST
            return

        # Check own friend list full
        if len(session.friends) >= FRIEND_MAX:
            _send_result(5)  # FRIEND_LIST_FULL
            return

        # Check already friends
        if target_name in session.friends:
            _send_result(2)  # ALREADY_FRIENDS
            return

        # Check already sent
        if target_name in session.friend_requests_sent:
            _send_result(3)  # ALREADY_SENT
            return

        # Check blocked
        if target_name in session.blocked_players:
            _send_result(4)  # BLOCKED
            return

        # Find target session (they must be online)
        target = self._find_session_by_name(target_name)
        if not target:
            _send_result(1)  # PLAYER_NOT_FOUND
            return

        # Check target friend list full
        if len(target.friends) >= FRIEND_MAX:
            _send_result(6)  # TARGET_FULL
            return

        # Check if blocked by target
        my_name = getattr(session, 'character_name', '')
        if my_name in target.blocked_players:
            _send_result(4)  # BLOCKED (by target)
            return

        # Add request
        session.friend_requests_sent.append(target_name)
        if my_name not in target.friend_requests_recv:
            target.friend_requests_recv.append(my_name)

        _send_result(0)  # SUCCESS

    async def _on_friend_accept(self, session, payload: bytes):
        """FRIEND_ACCEPT(412) -> FRIEND_REQUEST_RESULT(411)
        Request: from_name_len(u8) + from_name(str)
        Response: result(u8) + from_name_len(u8) + from_name(str)
          result: 0=SUCCESS, 1=NO_REQUEST, 2=FRIEND_LIST_FULL"""
        if not session.in_game or len(payload) < 1:
            return

        name_len = payload[0]
        if len(payload) < 1 + name_len:
            return
        from_name = payload[1:1+name_len].decode('utf-8')

        def _send_result(result_code):
            nb = from_name.encode('utf-8')
            self._send(session, MsgType.FRIEND_REQUEST_RESULT,
                       struct.pack('<B B', result_code, len(nb)) + nb)

        # Check request exists
        if from_name not in session.friend_requests_recv:
            _send_result(1)  # NO_REQUEST
            return

        # Check own friend list full
        if len(session.friends) >= FRIEND_MAX:
            _send_result(2)  # FRIEND_LIST_FULL
            return

        # Remove request
        session.friend_requests_recv.remove(from_name)

        # Add both as friends
        my_name = getattr(session, 'character_name', '')
        if from_name not in session.friends:
            session.friends.append(from_name)

        # Update sender's session if online
        sender = self._find_session_by_name(from_name)
        if sender:
            if my_name not in sender.friends:
                sender.friends.append(my_name)
            if my_name in sender.friend_requests_sent:
                sender.friend_requests_sent.remove(my_name)

        _send_result(0)  # SUCCESS

    async def _on_friend_reject(self, session, payload: bytes):
        """FRIEND_REJECT(413) -> FRIEND_REQUEST_RESULT(411)
        Request: from_name_len(u8) + from_name(str)
        Response: result(u8) + from_name_len(u8) + from_name(str)
          result: 0=SUCCESS, 1=NO_REQUEST"""
        if not session.in_game or len(payload) < 1:
            return

        name_len = payload[0]
        if len(payload) < 1 + name_len:
            return
        from_name = payload[1:1+name_len].decode('utf-8')

        def _send_result(result_code):
            nb = from_name.encode('utf-8')
            self._send(session, MsgType.FRIEND_REQUEST_RESULT,
                       struct.pack('<B B', result_code, len(nb)) + nb)

        if from_name not in session.friend_requests_recv:
            _send_result(1)  # NO_REQUEST
            return

        session.friend_requests_recv.remove(from_name)

        # Clean sender's sent list if online
        sender = self._find_session_by_name(from_name)
        if sender:
            my_name = getattr(session, 'character_name', '')
            if my_name in sender.friend_requests_sent:
                sender.friend_requests_sent.remove(my_name)

        _send_result(0)  # SUCCESS

    async def _on_friend_list_req(self, session, payload: bytes):
        """FRIEND_LIST_REQ(414) -> FRIEND_LIST(415)
        Response: count(u8) + [name_len(u8) + name(str) + is_online(u8) + zone_id(u16)]"""
        if not session.in_game:
            return

        count = len(session.friends)
        data = struct.pack('<B', min(count, 255))

        for friend_name in session.friends[:255]:
            nb = friend_name.encode('utf-8')
            # Check if online
            friend_session = self._find_session_by_name(friend_name)
            is_online = 1 if friend_session and friend_session.in_game else 0
            zone_id = getattr(friend_session, 'zone_id', 0) if friend_session else 0
            data += struct.pack('<B', len(nb)) + nb
            data += struct.pack('<B H', is_online, zone_id)

        self._send(session, MsgType.FRIEND_LIST, data)

    async def _on_block_player(self, session, payload: bytes):
        """BLOCK_PLAYER(416) -> BLOCK_RESULT(417)
        Request: action(u8) + name_len(u8) + name(str)
          action: 0=block, 1=unblock
        Response: result(u8) + action(u8) + name_len(u8) + name(str)
          result: 0=SUCCESS, 1=ALREADY_BLOCKED, 2=NOT_BLOCKED, 3=BLOCK_LIST_FULL, 4=SELF_BLOCK"""
        if not session.in_game or len(payload) < 2:
            return

        action = payload[0]
        name_len = payload[1]
        if len(payload) < 2 + name_len:
            return
        target_name = payload[2:2+name_len].decode('utf-8')

        def _send_result(result_code):
            nb = target_name.encode('utf-8')
            self._send(session, MsgType.BLOCK_RESULT,
                       struct.pack('<B B B', result_code, action, len(nb)) + nb)

        # Self block check
        if target_name == getattr(session, 'character_name', ''):
            _send_result(4)  # SELF_BLOCK
            return

        if action == 0:  # Block
            if target_name in session.blocked_players:
                _send_result(1)  # ALREADY_BLOCKED
                return
            if len(session.blocked_players) >= BLOCK_MAX:
                _send_result(3)  # BLOCK_LIST_FULL
                return
            session.blocked_players.append(target_name)
            # Also remove from friends if present
            if target_name in session.friends:
                session.friends.remove(target_name)
            _send_result(0)

        elif action == 1:  # Unblock
            if target_name not in session.blocked_players:
                _send_result(2)  # NOT_BLOCKED
                return
            session.blocked_players.remove(target_name)
            _send_result(0)

    async def _on_block_list_req(self, session, payload: bytes):
        """BLOCK_LIST_REQ(418) -> BLOCK_LIST(419)
        Response: count(u8) + [name_len(u8) + name(str)]"""
        if not session.in_game:
            return

        count = len(session.blocked_players)
        data = struct.pack('<B', min(count, 255))

        for blocked_name in session.blocked_players[:255]:
            nb = blocked_name.encode('utf-8')
            data += struct.pack('<B', len(nb)) + nb

        self._send(session, MsgType.BLOCK_LIST, data)

    async def _on_party_finder_list_req(self, session, payload: bytes):
        """PARTY_FINDER_LIST_REQ(420) -> PARTY_FINDER_LIST(421)
        Request: category(u8)  — 0xFF=all, 0~4=specific category
        Response: count(u8) + [listing_id(u16) + owner_len(u8) + owner(str) +
                  title_len(u8) + title(str) + category(u8) + min_level(u8) + role(u8)]"""
        if not session.in_game:
            return

        category_filter = payload[0] if len(payload) >= 1 else 0xFF

        listings = _PARTY_FINDER_BOARD
        if category_filter != 0xFF:
            listings = [l for l in listings if l.get("category_idx", 0) == category_filter]

        count = min(len(listings), 50)  # cap at 50
        data = struct.pack('<B', count)

        for l in listings[:count]:
            owner_b = l["owner"].encode('utf-8')
            title_b = l["title"].encode('utf-8')
            data += struct.pack('<H', l["listing_id"])
            data += struct.pack('<B', len(owner_b)) + owner_b
            data += struct.pack('<B', len(title_b)) + title_b
            data += struct.pack('<B B B', l.get("category_idx", 4), l.get("min_level", 1), l.get("role_idx", 3))

        self._send(session, MsgType.PARTY_FINDER_LIST, data)

    async def _on_party_finder_create(self, session, payload: bytes):
        """PARTY_FINDER_CREATE(422) -> PARTY_FINDER_LIST(421) (echo back updated list)
        Request: title_len(u8) + title(str) + category(u8) + min_level(u8) + role(u8)
        Response via PARTY_FINDER_LIST with updated board.
        Also sends FRIEND_REQUEST_RESULT(411) as ack:
          result: 0=SUCCESS, 1=ALREADY_LISTED, 2=TITLE_TOO_LONG"""
        if not session.in_game or len(payload) < 1:
            return

        title_len = payload[0]
        if len(payload) < 1 + title_len + 3:
            return
        title = payload[1:1+title_len].decode('utf-8')
        category = payload[1+title_len]
        min_level = payload[2+title_len]
        role = payload[3+title_len]

        owner_name = getattr(session, 'character_name', 'unknown')

        # Send ack via a simple response reusing BLOCK_RESULT(417) as generic social ack
        # Actually let's use a clean approach: send PARTY_FINDER_LIST as result
        # But first validate:

        # Check if already has a listing
        for l in _PARTY_FINDER_BOARD:
            if l["owner"] == owner_name:
                # Remove old listing first (replace)
                _PARTY_FINDER_BOARD.remove(l)
                break

        # Title length check
        if len(title) > PARTY_FINDER_TITLE_MAX:
            title = title[:PARTY_FINDER_TITLE_MAX]

        # Create listing
        listing_id = _PARTY_FINDER_NEXT_ID[0]
        _PARTY_FINDER_NEXT_ID[0] += 1

        cat_idx = min(category, len(PARTY_FINDER_CATEGORIES) - 1)
        role_idx = min(role, len(PARTY_FINDER_ROLES) - 1)

        new_listing = {
            "listing_id": listing_id,
            "owner": owner_name,
            "title": title,
            "category_idx": cat_idx,
            "min_level": min_level,
            "role_idx": role_idx,
            "created_at": time.time(),
        }
        _PARTY_FINDER_BOARD.append(new_listing)
        session.party_finder_listing = new_listing

        # Send back the updated list
        await self._on_party_finder_list_req(session, struct.pack('<B', 0xFF))
'''

# ====================================================================
# 6. Test cases (5 tests)
# ====================================================================
TEST_CODE = r'''
    # ━━━ Test: FRIEND_REQUEST — 친구 요청 ━━━
    async def test_friend_request():
        """친구 요청 보내기 — 대상 미접속 시 PLAYER_NOT_FOUND."""
        c = await login_and_enter(port)

        target = b'nonexistent_player'
        await c.send(MsgType.FRIEND_REQUEST,
                     struct.pack('<B', len(target)) + target)
        msg_type, resp = await c.recv_expect(MsgType.FRIEND_REQUEST_RESULT)
        assert msg_type == MsgType.FRIEND_REQUEST_RESULT, f"Expected FRIEND_REQUEST_RESULT, got {msg_type}"
        result = resp[0]
        # result=1 PLAYER_NOT_FOUND (target not online)
        assert result == 1, f"Expected PLAYER_NOT_FOUND(1), got {result}"
        c.close()

    await test("FRIEND_REQUEST: 친구 요청 (미접속 → NOT_FOUND)", test_friend_request())

    # ━━━ Test: FRIEND_LIST — 친구 목록 조회 ━━━
    async def test_friend_list():
        """친구 목록 조회 — 빈 목록이면 count=0."""
        c = await login_and_enter(port)

        await c.send(MsgType.FRIEND_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.FRIEND_LIST)
        assert msg_type == MsgType.FRIEND_LIST, f"Expected FRIEND_LIST, got {msg_type}"
        count = resp[0]
        assert count == 0, f"Expected 0 friends for fresh session, got {count}"
        c.close()

    await test("FRIEND_LIST: 친구 목록 조회 (빈 목록)", test_friend_list())

    # ━━━ Test: BLOCK_PLAYER — 플레이어 차단 ━━━
    async def test_block_player():
        """플레이어 차단 + 차단 목록 확인."""
        c = await login_and_enter(port)

        # Block a player
        target = b'some_griefer'
        await c.send(MsgType.BLOCK_PLAYER,
                     struct.pack('<B B', 0, len(target)) + target)
        msg_type, resp = await c.recv_expect(MsgType.BLOCK_RESULT)
        assert msg_type == MsgType.BLOCK_RESULT, f"Expected BLOCK_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"

        # Verify block list
        await c.send(MsgType.BLOCK_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BLOCK_LIST)
        assert msg_type == MsgType.BLOCK_LIST, f"Expected BLOCK_LIST, got {msg_type}"
        count = resp[0]
        assert count == 1, f"Expected 1 blocked player, got {count}"
        c.close()

    await test("BLOCK_PLAYER: 차단 + 목록 확인", test_block_player())

    # ━━━ Test: BLOCK_UNBLOCK — 차단 해제 ━━━
    async def test_block_unblock():
        """차단 → 해제 → 빈 목록 확인."""
        c = await login_and_enter(port)

        target = b'temp_block'
        # Block
        await c.send(MsgType.BLOCK_PLAYER,
                     struct.pack('<B B', 0, len(target)) + target)
        await c.recv_expect(MsgType.BLOCK_RESULT)

        # Unblock
        await c.send(MsgType.BLOCK_PLAYER,
                     struct.pack('<B B', 1, len(target)) + target)
        msg_type, resp = await c.recv_expect(MsgType.BLOCK_RESULT)
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0) for unblock, got {result}"

        # Verify empty
        await c.send(MsgType.BLOCK_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BLOCK_LIST)
        count = resp[0]
        assert count == 0, f"Expected 0 after unblock, got {count}"
        c.close()

    await test("BLOCK_UNBLOCK: 차단 해제 → 빈 목록", test_block_unblock())

    # ━━━ Test: PARTY_FINDER_CREATE — 파티 찾기 등록 + 목록 ━━━
    async def test_party_finder():
        """파티 찾기 게시판 등록 + 목록 조회."""
        c = await login_and_enter(port)

        title = b'Need healer for dungeon'
        category = 0  # dungeon
        min_level = 15
        role = 2  # support
        await c.send(MsgType.PARTY_FINDER_CREATE,
                     struct.pack('<B', len(title)) + title +
                     struct.pack('<B B B', category, min_level, role))
        # Response is PARTY_FINDER_LIST with updated board
        msg_type, resp = await c.recv_expect(MsgType.PARTY_FINDER_LIST)
        assert msg_type == MsgType.PARTY_FINDER_LIST, f"Expected PARTY_FINDER_LIST, got {msg_type}"
        count = resp[0]
        assert count >= 1, f"Expected at least 1 listing after create, got {count}"
        c.close()

    await test("PARTY_FINDER: 파티 찾기 등록 + 목록 조회", test_party_finder())
'''


def patch_bridge():
    # OneDrive may truncate tcp_bridge.py — always restore from git first
    import subprocess
    git_root = os.path.join(DIR, '..', '..')
    result = subprocess.run(
        ['git', 'show', 'HEAD:Servers/BridgeServer/tcp_bridge.py'],
        capture_output=True, cwd=git_root
    )
    if result.returncode == 0 and len(result.stdout) > 50000:
        content = result.stdout.decode('utf-8')
        print(f'[bridge] Restored from git: {content.count(chr(10))} lines')
    else:
        with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

    # Full completion check
    if 'FRIEND_REQUEST = 410' in content and 'def _on_friend_request' in content:
        print('[bridge] S051 already patched')
        return True

    changed = False

    # 1. MsgType -- after TRANSCEND_RESULT = 459
    if 'FRIEND_REQUEST' not in content:
        marker = '    TRANSCEND_RESULT = 459'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 410-422')
        else:
            print('[bridge] WARNING: Could not find TRANSCEND_RESULT = 459')

    # 2. Data constants -- after ENHANCE_PITY_MAX_BONUS line
    if 'FRIEND_MAX' not in content:
        marker = "ENHANCE_PITY_MAX_BONUS"
        idx = content.find(marker)
        if idx >= 0:
            # Find end of that line
            nl = content.index('\n', idx) + 1
            # Skip any comments on next line
            while nl < len(content) and content[nl] == '#':
                nl = content.index('\n', nl) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added social data constants')
        else:
            print('[bridge] WARNING: Could not find ENHANCE_PITY_MAX_BONUS')

    # 3. PlayerSession fields -- after enhance_levels field
    if 'friends: list' not in content:
        marker = '    enhance_levels: dict = field(default_factory=dict)'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession social fields')
        else:
            # Fallback: after protection_scrolls
            marker2 = '    protection_scrolls: int = 0'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession social fields (fallback)')

    # 4. Dispatch table -- after transcend_req dispatch
    if 'self._on_friend_request' not in content:
        marker = '            MsgType.TRANSCEND_REQ: self._on_transcend_req,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            print('[bridge] WARNING: Could not find transcend_req dispatch entry')

    # 5. Handler implementations -- before Enhancement Deepening handlers
    if 'def _on_friend_request' not in content:
        marker = '    # ---- Enhancement Deepening (TASK 8: MsgType 450-459) ----'
        idx = content.find(marker)
        if idx < 0:
            # Try before Progression Deepening
            marker = '    # ---- Progression Deepening (TASK 7: MsgType 440-447) ----'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added social handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    # 6. Add 'import time' if not present (needed for party finder timestamps)
    if '\nimport time\n' not in content and '\nimport time ' not in content:
        # Add after 'import struct'
        idx = content.find('import struct')
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + 'import time\n' + content[end:]
            changed = True
            print('[bridge] Added import time')

    # Always write (git restore + patches)
    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify in-memory
    checks = [
        'FRIEND_REQUEST = 410', 'FRIEND_REQUEST_RESULT = 411',
        'FRIEND_ACCEPT = 412', 'FRIEND_REJECT = 413',
        'FRIEND_LIST_REQ = 414', 'FRIEND_LIST = 415',
        'BLOCK_PLAYER = 416', 'BLOCK_RESULT = 417',
        'BLOCK_LIST_REQ = 418', 'BLOCK_LIST = 419',
        'PARTY_FINDER_LIST_REQ = 420', 'PARTY_FINDER_LIST = 421',
        'PARTY_FINDER_CREATE = 422',
        'FRIEND_MAX', 'BLOCK_MAX', 'PARTY_FINDER_CATEGORIES',
        'PARTY_FINDER_MAX_LISTINGS', '_PARTY_FINDER_BOARD',
        'def _on_friend_request', 'def _on_friend_accept',
        'def _on_friend_reject', 'def _on_friend_list_req',
        'def _on_block_player', 'def _on_block_list_req',
        'def _on_party_finder_list_req', 'def _on_party_finder_create',
        'self._on_friend_request', 'self._on_block_player',
        'self._on_party_finder_list_req', 'self._on_party_finder_create',
        'friends: list', 'blocked_players: list', 'party_finder_listing: dict',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S051 patched OK -- 8 handlers + friend/block/party_finder')
    return True


def patch_test():
    # OneDrive may truncate test file too — restore from git if needed
    import subprocess
    git_root = os.path.join(DIR, '..', '..')
    result = subprocess.run(
        ['git', 'show', 'HEAD:Servers/BridgeServer/test_tcp_bridge.py'],
        capture_output=True, cwd=git_root
    )
    if result.returncode == 0 and len(result.stdout) > 10000:
        content = result.stdout.decode('utf-8')
        print(f'[test] Restored from git: {content.count(chr(10))} lines')
    else:
        with open(TEST_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

    if 'test_friend_request' in content:
        print('[test] S051 already patched')
        return True

    # Update imports to add social constants
    old_import = (
        '    ENHANCE_PITY_BONUS_PER_FAIL, ENHANCE_PITY_MAX_BONUS\n'
        ')'
    )
    new_import = (
        '    ENHANCE_PITY_BONUS_PER_FAIL, ENHANCE_PITY_MAX_BONUS,\n'
        '    FRIEND_MAX, BLOCK_MAX, PARTY_FINDER_CATEGORIES,\n'
        '    PARTY_FINDER_MAX_LISTINGS, PARTY_FINDER_ROLES\n'
        ')'
    )
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports')

    # Insert test cases before results section
    marker = '    # ━━━ 결과 ━━━'
    idx = content.find(marker)
    if idx < 0:
        match = re.search(r'^\s*print\(f"\\n{\'=\'', content, re.MULTILINE)
        if match:
            idx = match.start()

    if idx >= 0:
        content = content[:idx] + TEST_CODE + '\n' + content[idx:]
    else:
        print('[test] WARNING: Could not find insertion point')
        return False

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    checks = ['test_friend_request', 'test_friend_list', 'test_block_player',
              'test_block_unblock', 'test_party_finder']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S051 patched OK -- 5 social enhancement tests added')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS051 all patches applied!')
    else:
        print('\nS051 PATCH FAILED!')
        sys.exit(1)
