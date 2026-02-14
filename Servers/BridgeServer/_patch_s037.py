"""Patch test_tcp_bridge.py to fix INVENTORY test #10 regression.

Problem: After S035 expanded field monsters to 30, the initial spawn packets
sometimes arrive after recv_all_packets() completes, causing recv_packet()
in the ITEM_ADD test to get a MONSTER_MOVE(111) instead of ITEM_ADD_RESULT(193).

Fix: Add recv_expect() method to TestClient that waits for a specific MsgType,
skipping any unrelated packets. Apply it to inventory test assertions.
"""
import os

DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'recv_expect' in content:
        print('[test] S037 already patched')
        return True

    replacements = []

    # 1. Add recv_expect method after recv_all_packets
    replacements.append((
        '    async def recv_all_packets(self, timeout: float = 0.5) -> list:\n'
        '        """짧은 시간 내 도착하는 모든 패킷 수집"""\n'
        '        packets = []\n'
        '        while True:\n'
        '            msg_type, payload = await self.recv_packet(timeout=timeout)\n'
        '            if msg_type is None:\n'
        '                break\n'
        '            packets.append((msg_type, payload))\n'
        '            timeout = 0.2  # 첫 패킷 후 더 짧은 타임아웃\n'
        '        return packets',

        '    async def recv_all_packets(self, timeout: float = 0.5) -> list:\n'
        '        """짧은 시간 내 도착하는 모든 패킷 수집"""\n'
        '        packets = []\n'
        '        while True:\n'
        '            msg_type, payload = await self.recv_packet(timeout=timeout)\n'
        '            if msg_type is None:\n'
        '                break\n'
        '            packets.append((msg_type, payload))\n'
        '            timeout = 0.2  # 첫 패킷 후 더 짧은 타임아웃\n'
        '        return packets\n'
        '\n'
        '    async def recv_expect(self, expected: int, timeout: float = 3.0) -> tuple:\n'
        '        """특정 MsgType 패킷이 올 때까지 대기. 다른 패킷은 무시."""\n'
        '        deadline = time.time() + timeout\n'
        '        while True:\n'
        '            remaining = deadline - time.time()\n'
        '            if remaining <= 0:\n'
        '                return None, None\n'
        '            msg_type, payload = await self.recv_packet(timeout=remaining)\n'
        '            if msg_type is None:\n'
        '                return None, None\n'
        '            if msg_type == expected:\n'
        '                return msg_type, payload\n'
        '            # skip non-matching packets (monster spawns, moves, etc.)'
    ))

    # 2. Fix inventory test to use recv_expect
    replacements.append((
        '        # 아이템 추가\n'
        '        await c.send(MsgType.ITEM_ADD, struct.pack(\'<IH\', 201, 1))\n'
        '        msg_type, resp = await c.recv_packet()\n'
        '        assert msg_type == MsgType.ITEM_ADD_RESULT, f"Expected ITEM_ADD_RESULT, got {msg_type}"\n'
        '        result = resp[0]\n'
        '        assert result == 1, f"Item add should succeed"\n'
        '\n'
        '        # 인벤 조회\n'
        '        await c.send(MsgType.INVENTORY_REQ)\n'
        '        msg_type, resp = await c.recv_packet()\n'
        '        assert msg_type == MsgType.INVENTORY_RESP, f"Expected INVENTORY_RESP, got {msg_type}"',

        '        # 아이템 추가\n'
        '        await c.send(MsgType.ITEM_ADD, struct.pack(\'<IH\', 201, 1))\n'
        '        msg_type, resp = await c.recv_expect(MsgType.ITEM_ADD_RESULT)\n'
        '        assert msg_type == MsgType.ITEM_ADD_RESULT, f"Expected ITEM_ADD_RESULT, got {msg_type}"\n'
        '        result = resp[0]\n'
        '        assert result == 1, f"Item add should succeed"\n'
        '\n'
        '        # 인벤 조회\n'
        '        await c.send(MsgType.INVENTORY_REQ)\n'
        '        msg_type, resp = await c.recv_expect(MsgType.INVENTORY_RESP)\n'
        '        assert msg_type == MsgType.INVENTORY_RESP, f"Expected INVENTORY_RESP, got {msg_type}"'
    ))

    for old, new in replacements:
        if old not in content:
            print(f'[test] WARNING: patch target not found:\n  {old[:80]}...')
            return False
        content = content.replace(old, new, 1)

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print('[test] S037 patched: added recv_expect + fixed inventory test')
    return True


if __name__ == '__main__':
    ok = patch_test()
    if ok:
        print('\nS037 all patches applied!')
    else:
        print('\nS037 PATCH FAILED!')
        exit(1)
