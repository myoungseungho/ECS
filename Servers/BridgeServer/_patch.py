"""Patch tcp_bridge.py and test_tcp_bridge.py to add SERVER_LIST, CHARACTER CRUD, TUTORIAL packets."""
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'SERVER_LIST_REQ' in content:
        print('[bridge] Already patched')
        return True

    replacements = []

    # 1. MsgType enum additions
    replacements.append((
        '    MAIL_DELETE = 317\n    MAIL_DELETE_RESULT = 318\n\n\n# \u2501\u2501\u2501 \ud328\ud0b7 \ube4c\ub4dc/\ud30c\uc2f1 \uc720\ud2f8 \u2501\u2501\u2501',
        '    MAIL_DELETE = 317\n    MAIL_DELETE_RESULT = 318\n\n'
        '    # Server Selection\n'
        '    SERVER_LIST_REQ = 320\n'
        '    SERVER_LIST = 321\n\n'
        '    # Character CRUD\n'
        '    CHARACTER_LIST_REQ = 322\n'
        '    CHARACTER_LIST = 323\n'
        '    CHARACTER_CREATE = 324\n'
        '    CHARACTER_CREATE_RESULT = 325\n'
        '    CHARACTER_DELETE = 326\n'
        '    CHARACTER_DELETE_RESULT = 327\n\n'
        '    # Tutorial\n'
        '    TUTORIAL_STEP_COMPLETE = 330\n'
        '    TUTORIAL_REWARD = 331\n\n\n'
        '# \u2501\u2501\u2501 \ud328\ud0b7 \ube4c\ub4dc/\ud30c\uc2f1 \uc720\ud2f8 \u2501\u2501\u2501'
    ))

    # 2. PlayerSession.tutorial_steps
    replacements.append((
        '    trade_confirmed: bool = False\n\n\n# \u2501\u2501\u2501 \uac8c\uc784 \ub370\uc774\ud130 \uc815\uc758 \u2501\u2501\u2501',
        '    trade_confirmed: bool = False\n'
        '    tutorial_steps: Set[int] = field(default_factory=set)  # completed step IDs\n\n\n'
        '# \u2501\u2501\u2501 \uac8c\uc784 \ub370\uc774\ud130 \uc815\uc758 \u2501\u2501\u2501'
    ))

    # 3. Game data: SERVER_LIST_DATA + TUTORIAL_REWARDS
    replacements.append((
        '# \uc774\ub3d9 \uc0c1\uc218\nMOVEMENT = {',
        '# \uc11c\ubc84 \ub9ac\uc2a4\ud2b8 (\uc11c\ubc84 \uc120\ud0dd \ud654\uba74\uc6a9)\n'
        'SERVER_LIST_DATA = [\n'
        '    {"name": "\ud06c\ub85c\ub178\uc2a4", "status": 1, "population": 120},   # status: 0=OFF, 1=NORMAL, 2=BUSY, 3=FULL\n'
        '    {"name": "\uc544\ub974\uce74\ub098", "status": 1, "population": 85},\n'
        '    {"name": "\uc5d8\ub9ac\uc2dc\uc6c0", "status": 2, "population": 350},\n'
        ']\n\n'
        '# \ud29c\ud1a0\ub9ac\uc5bc \uc2a4\ud15d \ubcf4\uc0c1\n'
        'TUTORIAL_REWARDS = {\n'
        '    1: {"reward_type": 0, "amount": 100},     # step 1: \uace8\ub4dc 100\n'
        '    2: {"reward_type": 1, "amount": 101},     # step 2: item_id 101 x1\n'
        '    3: {"reward_type": 0, "amount": 200},     # step 3: \uace8\ub4dc 200\n'
        '    4: {"reward_type": 2, "amount": 50},      # step 4: \uacbd\ud5d8\uce58 50\n'
        '    5: {"reward_type": 0, "amount": 500},     # step 5: \uace8\ub4dc 500\n'
        '}\n\n'
        '# \uc774\ub3d9 \uc0c1\uc218\nMOVEMENT = {'
    ))

    # 4. BridgeServer.__init__ additions
    replacements.append((
        '        self.mails: Dict[int, List[dict]] = {}  # account_id -> mail list\n'
        '        self.next_mail_id = 1\n\n'
        '    def log(self, msg: str, level: str = "INFO"):',
        '        self.mails: Dict[int, List[dict]] = {}  # account_id -> mail list\n'
        '        self.next_mail_id = 1\n'
        '        self.characters: Dict[int, List[dict]] = {}  # account_id -> character list\n'
        '        self.next_char_id = 1\n\n'
        '    def log(self, msg: str, level: str = "INFO"):'
    ))

    # 5. _dispatch handler registrations
    replacements.append((
        '            MsgType.MAIL_DELETE: self._on_mail_delete,\n        }',
        '            MsgType.MAIL_DELETE: self._on_mail_delete,\n'
        '            MsgType.SERVER_LIST_REQ: self._on_server_list_req,\n'
        '            MsgType.CHARACTER_LIST_REQ: self._on_character_list_req,\n'
        '            MsgType.CHARACTER_CREATE: self._on_character_create,\n'
        '            MsgType.CHARACTER_DELETE: self._on_character_delete,\n'
        '            MsgType.TUTORIAL_STEP_COMPLETE: self._on_tutorial_step_complete,\n'
        '        }'
    ))

    # 6. Handler implementations
    handler_code = r'''    # ━━━ 핸들러: 서버 선택 ━━━

    async def _on_server_list_req(self, session: PlayerSession, payload: bytes):
        count = len(SERVER_LIST_DATA)
        buf = struct.pack('<B', count)
        for srv in SERVER_LIST_DATA:
            name_bytes = srv["name"].encode('utf-8')[:32].ljust(32, b'\x00')
            buf += name_bytes
            buf += struct.pack('<BH', srv["status"], srv["population"])
        self._send(session, MsgType.SERVER_LIST, buf)
        self.log(f"ServerList: sent {count} servers", "GAME")

    # ━━━ 핸들러: 캐릭터 CRUD ━━━

    async def _on_character_list_req(self, session: PlayerSession, payload: bytes):
        if not session.logged_in:
            self._send(session, MsgType.CHARACTER_LIST, struct.pack('<B', 0))
            return
        chars = self.characters.get(session.account_id, [])
        buf = struct.pack('<B', len(chars))
        for ch in chars:
            name_bytes = ch["name"].encode('utf-8')[:16].ljust(16, b'\x00')
            buf += name_bytes
            buf += struct.pack('<BHI', ch["class"], ch["level"], ch["zone_id"])
        self._send(session, MsgType.CHARACTER_LIST, buf)
        self.log(f"CharacterList: {len(chars)} chars for account {session.account_id}", "GAME")

    async def _on_character_create(self, session: PlayerSession, payload: bytes):
        if not session.logged_in:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 1, 0))
            return
        if len(payload) < 2:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 3, 0))
            return
        name_len = payload[0]
        if len(payload) < 1 + name_len + 1:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 3, 0))
            return
        char_name = payload[1:1+name_len].decode('utf-8', errors='replace')
        char_class = payload[1+name_len]
        if len(char_name) < 2 or len(char_name) > 8:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 3, 0))
            return
        if char_class not in (1, 2, 3):
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 1, 0))
            return
        for acct_chars in self.characters.values():
            for ch in acct_chars:
                if ch["name"] == char_name:
                    self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 2, 0))
                    return
        char_id = self.next_char_id
        self.next_char_id += 1
        new_char = {"id": char_id, "name": char_name, "class": char_class, "level": 1, "zone_id": 1}
        if session.account_id not in self.characters:
            self.characters[session.account_id] = []
        self.characters[session.account_id].append(new_char)
        self.log(f"CharCreate: {char_name} class={char_class} (account={session.account_id})", "GAME")
        self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 0, char_id))

    async def _on_character_delete(self, session: PlayerSession, payload: bytes):
        if not session.logged_in:
            self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 2, 0))
            return
        if len(payload) < 4:
            self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 1, 0))
            return
        char_id = struct.unpack('<I', payload[:4])[0]
        chars = self.characters.get(session.account_id, [])
        target = next((ch for ch in chars if ch["id"] == char_id), None)
        if not target:
            self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 1, char_id))
            return
        chars.remove(target)
        self.log(f"CharDelete: {target['name']} id={char_id} (account={session.account_id})", "GAME")
        self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 0, char_id))

    # ━━━ 핸들러: 튜토리얼 ━━━

    async def _on_tutorial_step_complete(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 1:
            return
        step_id = payload[0]
        if step_id in session.tutorial_steps:
            return
        reward = TUTORIAL_REWARDS.get(step_id)
        if not reward:
            return
        session.tutorial_steps.add(step_id)
        reward_type = reward["reward_type"]
        amount = reward["amount"]
        if reward_type == 0:
            session.gold += amount
        elif reward_type == 1:
            for slot in session.inventory:
                if slot.item_id == 0:
                    slot.item_id = amount
                    slot.count = 1
                    break
        elif reward_type == 2:
            session.stats.add_exp(amount)
        self.log(f"Tutorial: step {step_id} complete, reward_type={reward_type} amount={amount} ({session.char_name})", "GAME")
        self._send(session, MsgType.TUTORIAL_REWARD, struct.pack('<BBI', step_id, reward_type, amount))

    # ━━━ 몬스터 시스템 ━━━

    def _spawn_monsters(self):'''

    # Use direct Korean text matching instead of unicode escapes
    monster_marker = '    # \u2501\u2501\u2501 ' + '\ubaac\uc2a4\ud130 \uc2dc\uc2a4\ud15c' + ' \u2501\u2501\u2501\n\n    def _spawn_monsters(self):'
    replacements.append((
        monster_marker,
        handler_code
    ))

    for old, new in replacements:
        if old not in content:
            print(f'[bridge] WARNING: Pattern not found: {old[:60]}...')
            continue
        content = content.replace(old, new, 1)

    # Remove test marker if present
    content = content.rstrip()
    if content.endswith('# test marker'):
        content = content[:-len('# test marker')].rstrip()
    content += '\n'

    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    # Quick verify
    for m in ['SERVER_LIST_REQ', '_on_server_list_req', '_on_character_create', '_on_tutorial_step_complete']:
        if m not in content:
            print(f'[bridge] MISSING: {m}')
            return False
    print('[bridge] Patched OK')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_server_list' in content:
        print('[test] Already patched')
        return True

    # Insert new tests before "# ━━━ 결과 ━━━"
    new_tests = r'''
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

'''

    marker = '    # \u2501\u2501\u2501 \uacb0\uacfc \u2501\u2501\u2501'
    if marker not in content:
        print('[test] WARNING: Result section marker not found')
        return False

    content = content.replace(marker, new_tests + marker, 1)

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    if 'test_server_list' in content:
        print('[test] Patched OK')
        return True
    else:
        print('[test] FAILED')
        return False


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nAll patches applied!')
    else:
        print('\nSome patches failed!')
        sys.exit(1)
