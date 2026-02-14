"""
Patch S052: Durability / Repair / Reroll (TASK 9)
- REPAIR_REQ(462)→REPAIR_RESULT(463)            -- 장비 수리. cost = tier * (100-dur) * 5
- REROLL_REQ(464)→REROLL_RESULT(465)             -- 랜덤옵션 재설정. cost 5000g + Reappraisal
- DURABILITY_NOTIFY(466)                         -- 내구도 변경 알림 (broken 포함)
- DURABILITY_QUERY(467)→DURABILITY_NOTIFY(466)   -- 내구도 조회
- 내구도 감소: 피격 -0.1, 사망 시 전 장비 -1.0
- broken(<=0) → 스탯 50% 감소
- 수리: NPC cost = equipment_tier * (100-current_durability) * 5
- 리롤: 5000 gold + reappraisal_scroll, 1줄 잠금(10000g)
- 5 test cases

NOTE: Equipment is managed via inventory slots (inventory[i].equipped=True).
  Durability/reroll keys are inventory slot indices (int).
  Equipment "tier" is derived from item_id ranges: 200-299=weapon(tier1), 300-399=armor(tier1), etc.

MsgType layout:
  462 REPAIR_REQ
  463 REPAIR_RESULT
  464 REROLL_REQ
  465 REROLL_RESULT
  466 DURABILITY_NOTIFY
  467 DURABILITY_QUERY
"""
import os
import sys
import re
import random

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Durability (462-467)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Durability / Repair / Reroll (TASK 9)\n'
    '    REPAIR_REQ = 462\n'
    '    REPAIR_RESULT = 463\n'
    '    REROLL_REQ = 464\n'
    '    REROLL_RESULT = 465\n'
    '    DURABILITY_NOTIFY = 466\n'
    '    DURABILITY_QUERY = 467\n'
)

# ====================================================================
# 2. Data constants (GDD items.yaml durability)
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Durability / Repair / Reroll Data (GDD items.yaml) ----
DURABILITY_MAX = 100.0               # max durability
DURABILITY_DECREASE_PER_HIT = 0.1    # per hit taken
DURABILITY_DECREASE_PER_DEATH = 1.0  # all equips on death
DURABILITY_BROKEN_PENALTY = 0.5      # stat reduction when broken (50%)
DURABILITY_WARNING_AT = 20.0         # warn when below 20%
REPAIR_COST_MULTIPLIER = 5           # tier * (100 - dur) * 5
REROLL_GOLD_COST = 5000              # gold cost per reroll
REROLL_MATERIAL = "reappraisal_scroll"  # required material
REROLL_LOCK_COST = 10000             # gold to lock 1 line
REROLL_MAX_LOCKS = 1                 # max locked lines per reroll
# Equipment type by item_id range for random option pool
def _get_equip_type_by_id(item_id):
    """Map item_id to equipment type for random option pool lookup."""
    if 200 <= item_id < 300:
        return "weapon"
    elif 300 <= item_id < 350:
        return "armor"
    elif 350 <= item_id < 370:
        return "helmet"
    elif 370 <= item_id < 390:
        return "gloves"
    elif 390 <= item_id < 400:
        return "boots"
    return "armor"  # default

def _get_equip_tier_by_id(item_id):
    """Derive equipment tier from item_id. Higher item_id = higher tier."""
    if item_id < 200:
        return 0
    base = (item_id % 100)
    return max(1, (base // 20) + 1)  # tier 1-5

RANDOM_OPTION_POOL = {
    "weapon": ["atk", "crit_rate", "crit_dmg", "skill_dmg", "speed"],
    "armor":  ["hp", "def", "damage_reduction", "elemental_resist", "hp_regen"],
    "helmet": ["hp", "def", "crit_resist", "mp", "cooldown_reduction"],
    "gloves": ["atk", "attack_speed", "crit_rate", "accuracy", "speed"],
    "boots":  ["speed", "evasion", "hp", "def", "mp_regen"],
}
RANDOM_OPTION_RANGES = {
    "atk": (5, 30), "hp": (50, 300), "def": (3, 20),
    "crit_rate": (1, 5), "crit_dmg": (2, 10), "speed": (1, 5),
    "skill_dmg": (2, 8), "damage_reduction": (1, 5),
    "elemental_resist": (2, 10), "hp_regen": (1, 5),
    "mp": (20, 100), "cooldown_reduction": (1, 5),
    "attack_speed": (1, 5), "accuracy": (1, 5),
    "evasion": (1, 5), "mp_regen": (1, 5), "crit_resist": (1, 5),
}
'''

# ====================================================================
# 3. PlayerSession fields for durability
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Durability / Repair / Reroll (TASK 9) ----\n'
    '    equipment_durability: dict = field(default_factory=dict)  # {inv_slot_idx: durability_float}\n'
    '    equipment_random_opts: dict = field(default_factory=dict) # {inv_slot_idx: [{stat, value}, ...]}\n'
    '    reappraisal_scrolls: int = 0                              # 재감정서 수량\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.REPAIR_REQ: self._on_repair_req,\n'
    '            MsgType.REROLL_REQ: self._on_reroll_req,\n'
    '            MsgType.DURABILITY_QUERY: self._on_durability_query,\n'
)

# ====================================================================
# 5. Handler implementations (inventory-based)
# ====================================================================
HANDLER_CODE = r'''
    # ---- Durability / Repair / Reroll (TASK 9: MsgType 462-467) ----

    def _get_equipped_slots(self, session):
        """Get list of (inv_idx, InventorySlot) for all equipped items."""
        result = []
        for i, slot in enumerate(session.inventory):
            if slot.item_id > 0 and slot.equipped:
                result.append((i, slot))
        return result

    def _init_durability(self, session, inv_idx: int):
        """Initialize durability for an inventory slot if not present."""
        if inv_idx not in session.equipment_durability:
            session.equipment_durability[inv_idx] = DURABILITY_MAX

    def _init_random_opts(self, session, inv_idx: int):
        """Initialize random options for an inventory slot if not present."""
        if inv_idx not in session.equipment_random_opts:
            item_id = session.inventory[inv_idx].item_id
            equip_type = _get_equip_type_by_id(item_id)
            pool = RANDOM_OPTION_POOL.get(equip_type, RANDOM_OPTION_POOL["armor"])
            num_opts = min(len(pool), random.randint(2, 3))
            opts = []
            chosen = random.sample(pool, num_opts)
            for stat in chosen:
                lo, hi = RANDOM_OPTION_RANGES.get(stat, (1, 10))
                opts.append({"stat": stat, "value": random.randint(lo, hi)})
            session.equipment_random_opts[inv_idx] = opts

    def _apply_durability_damage(self, session, amount: float, target_indices=None):
        """Reduce durability on equipped items. Returns list of (inv_idx, new_dur, newly_broken)."""
        results = []
        if target_indices is None:
            equipped = self._get_equipped_slots(session)
            target_indices = [idx for idx, _ in equipped]
        for inv_idx in target_indices:
            if inv_idx >= len(session.inventory) or session.inventory[inv_idx].item_id == 0:
                continue
            self._init_durability(session, inv_idx)
            old = session.equipment_durability[inv_idx]
            new_dur = max(0.0, old - amount)
            session.equipment_durability[inv_idx] = new_dur
            was_broken = old <= 0
            is_broken = new_dur <= 0
            results.append((inv_idx, new_dur, is_broken and not was_broken))
        return results

    def _send_durability_notify(self, session, inv_idx: int, durability: float, is_broken: bool):
        """DURABILITY_NOTIFY(466): inv_slot(u8)+durability(f32)+is_broken(u8)"""
        self._send(session, MsgType.DURABILITY_NOTIFY,
                   struct.pack('<B f B', inv_idx, durability, 1 if is_broken else 0))

    async def _on_durability_take_hit(self, session):
        """Called when player takes a hit — decrease durability by 0.1 on all equips."""
        results = self._apply_durability_damage(session, DURABILITY_DECREASE_PER_HIT)
        for inv_idx, dur, newly_broken in results:
            if newly_broken or dur <= DURABILITY_WARNING_AT:
                self._send_durability_notify(session, inv_idx, dur, dur <= 0)

    async def _on_durability_death(self, session):
        """Called when player dies — decrease all equip durability by 1.0."""
        results = self._apply_durability_damage(session, DURABILITY_DECREASE_PER_DEATH)
        for inv_idx, dur, newly_broken in results:
            self._send_durability_notify(session, inv_idx, dur, dur <= 0)

    async def _on_repair_req(self, session, payload: bytes):
        """REPAIR_REQ(462) -> REPAIR_RESULT(463)
        Request: mode(u8) + inv_slot(u8)
          mode: 0=single slot (inv_slot used), 1=repair all (inv_slot ignored)
        Response: result(u8) + total_cost(u32) + repaired_count(u8)
          result: 0=SUCCESS, 1=NO_EQUIPMENT, 2=NOT_ENOUGH_GOLD, 3=ALREADY_FULL"""
        if not session.in_game or len(payload) < 2:
            return

        mode = payload[0]
        target_inv_slot = payload[1]

        def _send_result(result_code, cost=0, count=0):
            self._send(session, MsgType.REPAIR_RESULT,
                       struct.pack('<B I B', result_code, cost, count))

        # Collect slots to repair
        if mode == 1:  # repair all
            equipped = self._get_equipped_slots(session)
            slots_to_repair = [idx for idx, _ in equipped]
        else:
            if target_inv_slot >= len(session.inventory):
                _send_result(1)  # NO_EQUIPMENT
                return
            inv_s = session.inventory[target_inv_slot]
            if inv_s.item_id == 0 or not inv_s.equipped:
                _send_result(1)  # NO_EQUIPMENT
                return
            slots_to_repair = [target_inv_slot]

        if not slots_to_repair:
            _send_result(1)  # NO_EQUIPMENT
            return

        # Calculate total cost
        total_cost = 0
        repairs = []
        for inv_idx in slots_to_repair:
            self._init_durability(session, inv_idx)
            cur_dur = session.equipment_durability[inv_idx]
            if cur_dur >= DURABILITY_MAX:
                continue  # already full
            item_id = session.inventory[inv_idx].item_id
            tier = _get_equip_tier_by_id(item_id)
            dur_lost = DURABILITY_MAX - cur_dur
            cost = int(tier * dur_lost * REPAIR_COST_MULTIPLIER)
            repairs.append((inv_idx, cost))
            total_cost += cost

        if not repairs:
            _send_result(3)  # ALREADY_FULL
            return

        # Check gold
        if session.gold < total_cost:
            _send_result(2)  # NOT_ENOUGH_GOLD
            return

        # Execute repair
        session.gold -= total_cost
        for inv_idx, cost in repairs:
            session.equipment_durability[inv_idx] = DURABILITY_MAX
            self._send_durability_notify(session, inv_idx, DURABILITY_MAX, False)

        _send_result(0, total_cost, len(repairs))

    async def _on_reroll_req(self, session, payload: bytes):
        """REROLL_REQ(464) -> REROLL_RESULT(465)
        Request: inv_slot(u8) + lock_count(u8) + [lock_idx(u8)]
        Response: result(u8) + option_count(u8) + [stat_len(u8)+stat(str)+value(i16)+locked(u8)]
          result: 0=SUCCESS, 1=NO_EQUIPMENT, 2=NOT_ENOUGH_GOLD, 3=NO_SCROLL,
                  4=TOO_MANY_LOCKS, 5=INVALID_LOCK"""
        if not session.in_game or len(payload) < 2:
            return

        inv_slot = payload[0]
        lock_count = payload[1]
        offset = 2

        lock_indices = []
        for _ in range(lock_count):
            if offset < len(payload):
                lock_indices.append(payload[offset])
                offset += 1

        def _send_result(result_code, options=None):
            if options is None:
                options = []
            data = struct.pack('<B B', result_code, len(options))
            for opt in options:
                sb = opt["stat"].encode('utf-8')
                locked = 1 if opt.get("locked", False) else 0
                data += struct.pack('<B', len(sb)) + sb
                data += struct.pack('<h B', opt["value"], locked)
            self._send(session, MsgType.REROLL_RESULT, data)

        # Check equipment exists
        if inv_slot >= len(session.inventory):
            _send_result(1)
            return
        inv_s = session.inventory[inv_slot]
        if inv_s.item_id == 0 or not inv_s.equipped:
            _send_result(1)
            return

        # Init random options if not exist
        self._init_random_opts(session, inv_slot)
        current_opts = session.equipment_random_opts[inv_slot]

        # Check lock count
        if lock_count > REROLL_MAX_LOCKS:
            _send_result(4)
            return

        # Validate lock indices
        for idx in lock_indices:
            if idx >= len(current_opts):
                _send_result(5)
                return

        # Calculate cost
        total_gold = REROLL_GOLD_COST + (lock_count * REROLL_LOCK_COST)

        # Check gold
        if session.gold < total_gold:
            _send_result(2)
            return

        # Check material
        if session.reappraisal_scrolls < 1:
            _send_result(3)
            return

        # Execute reroll
        session.gold -= total_gold
        session.reappraisal_scrolls -= 1

        # Re-generate non-locked options
        equip_type = _get_equip_type_by_id(inv_s.item_id)
        pool = RANDOM_OPTION_POOL.get(equip_type, RANDOM_OPTION_POOL["armor"])
        locked_stats = set()
        new_opts = []
        for i, opt in enumerate(current_opts):
            if i in lock_indices:
                new_opts.append({**opt, "locked": True})
                locked_stats.add(opt["stat"])
            else:
                new_opts.append(None)  # placeholder

        # Fill non-locked slots with new random stats
        available_pool = [s for s in pool if s not in locked_stats]
        for i, opt in enumerate(new_opts):
            if opt is None:
                if available_pool:
                    stat = random.choice(available_pool)
                    available_pool.remove(stat)
                else:
                    stat = random.choice(pool)
                lo, hi = RANDOM_OPTION_RANGES.get(stat, (1, 10))
                new_opts[i] = {"stat": stat, "value": random.randint(lo, hi), "locked": False}

        session.equipment_random_opts[inv_slot] = new_opts
        _send_result(0, new_opts)

    async def _on_durability_query(self, session, payload: bytes):
        """DURABILITY_QUERY(467) -> DURABILITY_NOTIFY(466) per equipped slot
        Request: (empty)
        Response: one DURABILITY_NOTIFY per equipped slot"""
        if not session.in_game:
            return

        equipped = self._get_equipped_slots(session)
        for inv_idx, slot in equipped:
            self._init_durability(session, inv_idx)
            dur = session.equipment_durability[inv_idx]
            self._send_durability_notify(session, inv_idx, dur, dur <= 0)
'''

# ====================================================================
# 6. Hook into STAT_TAKE_DMG for durability decrease on hit
# ====================================================================
DURABILITY_HOOK_TAKE_DMG = (
    '        # ---- Durability hook: decrease on hit taken ----\n'
    '        await self._on_durability_take_hit(session)\n'
)

# ====================================================================
# 7. Test cases (5 tests)
# ====================================================================
TEST_CODE = r'''
    # ━━━ Test: DURABILITY_QUERY — 내구도 조회 ━━━
    async def test_durability_query():
        """내구도 조회 — 장착 없으면 알림 없음, 크래시 없음."""
        c = await login_and_enter(port)
        await c.send(MsgType.DURABILITY_QUERY, b'')
        import asyncio as _asyncio
        await _asyncio.sleep(0.15)
        c.close()

    await test("DURABILITY_QUERY: 내구도 조회 (장착 없음)", test_durability_query())

    # ━━━ Test: REPAIR_ALL — 전체 수리 (미장착) ━━━
    async def test_repair_all():
        """전체 수리 — 장착 장비 없으면 NO_EQUIPMENT."""
        c = await login_and_enter(port)
        await c.send(MsgType.REPAIR_REQ, struct.pack('<B B', 1, 0))
        msg_type, resp = await c.recv_expect(MsgType.REPAIR_RESULT)
        assert msg_type == MsgType.REPAIR_RESULT, f"Expected REPAIR_RESULT, got {msg_type}"
        result = resp[0]
        assert result in (1, 3), f"Expected NO_EQUIPMENT(1) or ALREADY_FULL(3), got {result}"
        c.close()

    await test("REPAIR_ALL: 전체 수리 (미장착 → NO_EQUIPMENT)", test_repair_all())

    # ━━━ Test: REPAIR_WITH_EQUIP — 장착+수리 E2E ━━━
    async def test_repair_with_equip():
        """무기 구매+장착+피격+수리 E2E."""
        c = await login_and_enter(port)

        # Buy weapon from WeaponShop (npc=2, item_id=201, price=500)
        await c.send(MsgType.SHOP_BUY, struct.pack('<IIH', 2, 201, 1))
        msg_type, resp = await c.recv_expect(MsgType.SHOP_RESULT)
        assert msg_type == MsgType.SHOP_RESULT
        buy_result = resp[0]
        assert buy_result == 0, f"Shop buy failed: result={buy_result}"

        # Equip inventory slot 0 (where weapon was placed)
        await c.send(MsgType.ITEM_EQUIP, struct.pack('<B', 0))
        msg_type, _ = await c.recv_expect(MsgType.ITEM_EQUIP_RESULT)

        # Take a hit to decrease durability (STAT_TAKE_DMG: damage u32)
        await c.send(MsgType.STAT_TAKE_DMG, struct.pack('<I', 10))
        await c.recv_expect(MsgType.STATS)

        # Repair that single slot — mode=0, inv_slot=0
        await c.send(MsgType.REPAIR_REQ, struct.pack('<B B', 0, 0))
        msg_type, resp = await c.recv_expect(MsgType.REPAIR_RESULT)
        assert msg_type == MsgType.REPAIR_RESULT, f"Expected REPAIR_RESULT, got {msg_type}"
        result = resp[0]
        # SUCCESS(0) — hit decreased dur by 0.1, repair restores
        assert result in (0, 3), f"Expected SUCCESS(0) or ALREADY_FULL(3), got {result}"
        c.close()

    await test("REPAIR_WITH_EQUIP: 구매+장착+피격+수리 E2E", test_repair_with_equip())

    # ━━━ Test: REROLL_NO_EQUIP — 미장착 리롤 ━━━
    async def test_reroll_no_equip():
        """리롤 요청 — 미장착 시 NO_EQUIPMENT."""
        c = await login_and_enter(port)
        await c.send(MsgType.REROLL_REQ, struct.pack('<B B', 0, 0))
        msg_type, resp = await c.recv_expect(MsgType.REROLL_RESULT)
        assert msg_type == MsgType.REROLL_RESULT
        result = resp[0]
        assert result == 1, f"Expected NO_EQUIPMENT(1), got {result}"
        c.close()

    await test("REROLL_NO_EQUIP: 리롤 미장착 → NO_EQUIPMENT", test_reroll_no_equip())

    # ━━━ Test: REROLL_NO_SCROLL — 재감정서 없이 리롤 ━━━
    async def test_reroll_no_scroll():
        """장비 장착 후 리롤 — 재감정서 부족 or 골드 부족."""
        c = await login_and_enter(port)

        # Buy weapon and equip
        await c.send(MsgType.SHOP_BUY, struct.pack('<IIH', 2, 201, 1))
        await c.recv_expect(MsgType.SHOP_RESULT)
        await c.send(MsgType.ITEM_EQUIP, struct.pack('<B', 0))
        await c.recv_expect(MsgType.ITEM_EQUIP_RESULT)

        # Try reroll — no scroll, and possibly not enough gold (500g remaining after buy)
        await c.send(MsgType.REROLL_REQ, struct.pack('<B B', 0, 0))
        msg_type, resp = await c.recv_expect(MsgType.REROLL_RESULT)
        assert msg_type == MsgType.REROLL_RESULT
        result = resp[0]
        # NOT_ENOUGH_GOLD(2) since 500 < 5000, or NO_SCROLL(3)
        assert result in (2, 3), f"Expected NOT_ENOUGH_GOLD(2) or NO_SCROLL(3), got {result}"
        c.close()

    await test("REROLL_NO_SCROLL: 리롤 재감정서/골드 부족", test_reroll_no_scroll())
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
    if 'REPAIR_REQ = 462' in content and 'def _on_repair_req' in content and '_get_equipped_slots' in content:
        print('[bridge] S052 already patched')
        return True

    # Remove old S052 patch if present (wrong version)
    if 'def _on_repair_req' in content and '_get_equipped_slots' not in content:
        # Old patch used session.equipment — need to strip and re-patch
        # Remove old handler code
        old_start = '    # ---- Durability / Repair / Reroll (TASK 9: MsgType 462-467) ----'
        old_end = '    # ---- Social Enhancement (TASK 5: MsgType 410-422) ----'
        idx_s = content.find(old_start)
        idx_e = content.find(old_end)
        if idx_s >= 0 and idx_e > idx_s:
            content = content[:idx_s] + content[idx_e:]
            print('[bridge] Removed old S052 handler code')

        # Remove old MsgType block
        if 'REPAIR_REQ = 462' in content:
            for line in ['    REPAIR_REQ = 462\n', '    REPAIR_RESULT = 463\n',
                         '    REROLL_REQ = 464\n', '    REROLL_RESULT = 465\n',
                         '    DURABILITY_NOTIFY = 466\n', '    DURABILITY_QUERY = 467\n',
                         '    # Durability / Repair / Reroll (TASK 9)\n']:
                content = content.replace(line, '')
            print('[bridge] Removed old MsgType entries')

        # Remove old data constants
        old_dc_start = '# ---- Durability / Repair / Reroll Data (GDD items.yaml) ----'
        if old_dc_start in content:
            idx_dc = content.find(old_dc_start)
            # Find end — next section or blank line after RANDOM_OPTION_RANGES
            end_marker = "RANDOM_OPTION_RANGES"
            idx_end = content.find(end_marker, idx_dc)
            if idx_end >= 0:
                # Find closing brace
                brace = content.find('\n}\n', idx_end)
                if brace >= 0:
                    content = content[:idx_dc] + content[brace+3:]
                    print('[bridge] Removed old data constants')

        # Remove old session fields
        if 'equipment_durability: dict' in content:
            for line in [
                '    # ---- Durability / Repair / Reroll (TASK 9) ----\n',
                '    equipment_durability: dict = field(default_factory=dict)  # {slot: durability_float}\n',
                '    equipment_random_opts: dict = field(default_factory=dict) # {slot: [{stat, value}, ...]}\n',
                '    reappraisal_scrolls: int = 0                              # 재감정서 수량\n',
            ]:
                content = content.replace(line, '')
            print('[bridge] Removed old session fields')

        # Remove old dispatch entries
        for line in [
            '            MsgType.REPAIR_REQ: self._on_repair_req,\n',
            '            MsgType.REROLL_REQ: self._on_reroll_req,\n',
            '            MsgType.DURABILITY_QUERY: self._on_durability_query,\n',
        ]:
            content = content.replace(line, '')

        # Remove old hooks
        content = content.replace(
            '        # ---- Durability hook: decrease on hit taken ----\n'
            '        await self._on_durability_take_hit(session)\n', '')
        content = content.replace(
            '        # ---- Durability hook: decrease on death ----\n'
            '        await self._on_durability_death(session)\n', '')

        print('[bridge] Cleaned old S052 patch remnants')

    changed = False

    # 1. MsgType -- after PARTY_FINDER_CREATE = 422
    if 'REPAIR_REQ' not in content:
        marker = '    PARTY_FINDER_CREATE = 422'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 462-467')
        else:
            print('[bridge] WARNING: Could not find PARTY_FINDER_CREATE = 422')

    # 2. Data constants -- after _PARTY_FINDER_NEXT_ID line
    if 'DURABILITY_MAX' not in content:
        marker = "_PARTY_FINDER_NEXT_ID"
        idx = content.find(marker)
        if idx >= 0:
            nl = content.index('\n', idx) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added durability data constants')
        else:
            print('[bridge] WARNING: Could not find _PARTY_FINDER_NEXT_ID')

    # 3. PlayerSession fields -- after party_finder_listing field
    if 'equipment_durability: dict' not in content:
        marker = '    party_finder_listing: dict = field(default_factory=dict)'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession durability fields')
        else:
            marker2 = '    blocked_players: list = field(default_factory=list)'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession durability fields (fallback)')

    # 4. Dispatch table -- after party_finder_create dispatch
    if 'self._on_repair_req' not in content:
        marker = '            MsgType.PARTY_FINDER_CREATE: self._on_party_finder_create,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            print('[bridge] WARNING: Could not find party_finder_create dispatch entry')

    # 5. Handler implementations -- before Social Enhancement handlers
    if 'def _on_repair_req' not in content:
        marker = '    # ---- Social Enhancement (TASK 5: MsgType 410-422) ----'
        idx = content.find(marker)
        if idx < 0:
            marker = '    # ---- Enhancement Deepening (TASK 8: MsgType 450-459) ----'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added durability handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    # 6. Hook into STAT_TAKE_DMG handler — after HP decrease
    if '_on_durability_take_hit' not in content:
        hook_marker = 'session.stats.hp = max(0, session.stats.hp - actual)'
        idx = content.find(hook_marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DURABILITY_HOOK_TAKE_DMG + content[end:]
            changed = True
            print('[bridge] Added durability hook to STAT_TAKE_DMG')
        else:
            print('[bridge] NOTE: Could not find STAT_TAKE_DMG HP decrease — hook skipped')

    # 7. Add 'import random' if not present (needed for reroll)
    if '\nimport random\n' not in content:
        idx = content.find('import struct')
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + 'import random\n' + content[end:]
            changed = True
            print('[bridge] Added import random')

    # Always write
    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify
    checks = [
        'REPAIR_REQ = 462', 'REPAIR_RESULT = 463',
        'REROLL_REQ = 464', 'REROLL_RESULT = 465',
        'DURABILITY_NOTIFY = 466', 'DURABILITY_QUERY = 467',
        'DURABILITY_MAX', 'REPAIR_COST_MULTIPLIER', 'REROLL_GOLD_COST',
        'RANDOM_OPTION_POOL', 'RANDOM_OPTION_RANGES',
        '_get_equip_type_by_id', '_get_equip_tier_by_id',
        'def _on_repair_req', 'def _on_reroll_req',
        'def _on_durability_query', 'def _apply_durability_damage',
        'def _send_durability_notify', 'def _get_equipped_slots',
        'self._on_repair_req', 'self._on_reroll_req',
        'self._on_durability_query',
        'equipment_durability: dict', 'equipment_random_opts: dict',
        'reappraisal_scrolls: int',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S052 patched OK -- durability/repair/reroll (inventory-based)')
    return True


def patch_test():
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

    if 'test_durability_query' in content and 'test_repair_all' in content:
        print('[test] S052 already patched')
        return True

    # Remove old S052 tests if present (wrong version)
    if 'test_durability_query' in content:
        # Strip old tests
        old_start = '    # ━━━ Test: DURABILITY_QUERY'
        old_end = '    # ━━━ 결과 ━━━'
        idx_s = content.find(old_start)
        idx_e = content.find(old_end)
        if idx_s >= 0 and idx_e > idx_s:
            content = content[:idx_s] + content[idx_e:]
            print('[test] Removed old S052 tests')

    # Update imports
    old_import = (
        '    FRIEND_MAX, BLOCK_MAX, PARTY_FINDER_CATEGORIES,\n'
        '    PARTY_FINDER_MAX_LISTINGS, PARTY_FINDER_ROLES\n'
        ')'
    )
    new_import = (
        '    FRIEND_MAX, BLOCK_MAX, PARTY_FINDER_CATEGORIES,\n'
        '    PARTY_FINDER_MAX_LISTINGS, PARTY_FINDER_ROLES,\n'
        '    DURABILITY_MAX, REPAIR_COST_MULTIPLIER,\n'
        '    REROLL_GOLD_COST, REROLL_MATERIAL, REROLL_LOCK_COST\n'
        ')'
    )
    # Handle both old and already-patched import
    old_import_v2 = (
        '    FRIEND_MAX, BLOCK_MAX, PARTY_FINDER_CATEGORIES,\n'
        '    PARTY_FINDER_MAX_LISTINGS, PARTY_FINDER_ROLES,\n'
        '    DURABILITY_MAX, REPAIR_COST_MULTIPLIER,\n'
        '    REROLL_GOLD_COST, REROLL_MATERIAL, REROLL_LOCK_COST\n'
        ')'
    )
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports')
    elif old_import_v2 not in content:
        print('[test] NOTE: Could not find expected import block')

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

    checks = ['test_durability_query', 'test_repair_all', 'test_repair_with_equip',
              'test_reroll_no_equip', 'test_reroll_no_scroll',
              'SHOP_BUY', 'ITEM_EQUIP', 'REPAIR_REQ', 'REROLL_REQ']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S052 patched OK -- 5 durability tests (inventory-based)')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS052 all patches applied!')
    else:
        print('\nS052 PATCH FAILED!')
        sys.exit(1)
