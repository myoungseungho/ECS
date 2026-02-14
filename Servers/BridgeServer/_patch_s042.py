"""
Patch S042: crafting/gathering/cooking/enchant system (TASK 2)
- CRAFT_LIST_REQ(380)->CRAFT_LIST(381)
- CRAFT_EXECUTE(382)->CRAFT_RESULT(383)
- GATHER_START(384)->GATHER_RESULT(385)
- COOK_EXECUTE(386)->COOK_RESULT(387)
- ENCHANT_REQ(388)->ENCHANT_RESULT(389)
- 10 test cases added
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# DATA CONSTANTS to inject after ENHANCE_COST_BASE line
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Crafting System Data (GDD crafting.yaml) ----
CRAFTING_RECIPES = {
    "iron_sword": {
        "id": "iron_sword", "name": "Iron Sword", "category": "weapon",
        "proficiency_required": 1,
        "materials": [{"item": "iron_ore", "count": 5}, {"item": "wood", "count": 2}],
        "gold_cost": 200, "craft_time": 5, "success_rate": 1.0,
        "result": {"item_id": 301, "count": 1},
        "bonus_option_chance": 0.0,
    },
    "steel_sword": {
        "id": "steel_sword", "name": "Steel Sword", "category": "weapon",
        "proficiency_required": 10,
        "materials": [{"item": "steel_ingot", "count": 3}, {"item": "leather", "count": 2}, {"item": "iron_sword", "count": 1}],
        "gold_cost": 1000, "craft_time": 10, "success_rate": 0.9,
        "result": {"item_id": 302, "count": 1},
        "bonus_option_chance": 0.2,
    },
    "hp_potion_s": {
        "id": "hp_potion_s", "name": "HP Potion (S)", "category": "potion",
        "proficiency_required": 1,
        "materials": [{"item": "herb", "count": 3}],
        "gold_cost": 20, "craft_time": 2, "success_rate": 1.0,
        "result": {"item_id": 201, "count": 3},
        "bonus_option_chance": 0.0,
    },
    "hp_potion_l": {
        "id": "hp_potion_l", "name": "HP Potion (L)", "category": "potion",
        "proficiency_required": 15,
        "materials": [{"item": "rare_herb", "count": 5}, {"item": "crystal_water", "count": 1}],
        "gold_cost": 200, "craft_time": 5, "success_rate": 0.8,
        "result": {"item_id": 202, "count": 3},
        "bonus_option_chance": 0.0,
    },
    "polished_ruby": {
        "id": "polished_ruby", "name": "Polished Ruby", "category": "gem",
        "proficiency_required": 10,
        "materials": [{"item": "rough_ruby", "count": 3}],
        "gold_cost": 100, "craft_time": 5, "success_rate": 1.0,
        "result": {"item_id": 501, "count": 1},
        "bonus_option_chance": 0.0,
    },
    "steel_ingot": {
        "id": "steel_ingot", "name": "Steel Ingot", "category": "material",
        "proficiency_required": 5,
        "materials": [{"item": "iron_ore", "count": 3}, {"item": "coal", "count": 1}],
        "gold_cost": 50, "craft_time": 3, "success_rate": 1.0,
        "result": {"item_id": 601, "count": 1},
        "bonus_option_chance": 0.0,
    },
}

GATHER_TYPES = {
    1: {"name": "herbalism", "gather_time": 3.0, "exp": 5, "loot": [
        {"item_id": 701, "name": "herb", "chance": 0.80},
        {"item_id": 702, "name": "rare_herb", "chance": 0.15},
        {"item_id": 703, "name": "legendary_herb", "chance": 0.05},
    ]},
    2: {"name": "mining", "gather_time": 5.0, "exp": 8, "loot": [
        {"item_id": 711, "name": "iron_ore", "chance": 0.70},
        {"item_id": 712, "name": "gold_ore", "chance": 0.20},
        {"item_id": 713, "name": "crystal", "chance": 0.08},
        {"item_id": 714, "name": "diamond_ore", "chance": 0.02},
    ]},
    3: {"name": "logging", "gather_time": 4.0, "exp": 6, "loot": [
        {"item_id": 721, "name": "wood", "chance": 0.80},
        {"item_id": 722, "name": "hardwood", "chance": 0.15},
        {"item_id": 723, "name": "world_tree_branch", "chance": 0.05},
    ]},
}
GATHER_ENERGY_MAX = 200
GATHER_ENERGY_COST = 5
GATHER_ENERGY_REGEN = 1  # per minute

COOKING_RECIPES = {
    "grilled_meat": {
        "id": "grilled_meat", "name": "Grilled Meat",
        "materials": [{"item": "raw_meat", "count": 3}],
        "effect": {"atk": 10}, "duration": 1800,
        "proficiency_required": 1,
        "result_item_id": 801,
    },
    "fish_stew": {
        "id": "fish_stew", "name": "Fish Stew",
        "materials": [{"item": "fish", "count": 2}, {"item": "herb", "count": 1}],
        "effect": {"max_hp": 200, "hp_regen": 5}, "duration": 1800,
        "proficiency_required": 5,
        "result_item_id": 802,
    },
    "royal_feast": {
        "id": "royal_feast", "name": "Royal Feast",
        "materials": [{"item": "rare_meat", "count": 2}, {"item": "rare_herb", "count": 2}, {"item": "spice", "count": 1}],
        "effect": {"all_stats": 5, "exp_bonus": 0.05}, "duration": 3600,
        "proficiency_required": 20,
        "result_item_id": 803,
    },
}

ENCHANT_ELEMENTS = ["fire", "ice", "lightning", "dark", "holy", "nature"]
ENCHANT_LEVELS = {
    1: {"damage_bonus": 0.05, "material_cost": 5, "gold_cost": 1000},
    2: {"damage_bonus": 0.10, "material_cost": 10, "gold_cost": 3000},
    3: {"damage_bonus": 0.15, "material_cost": 20, "gold_cost": 10000},
}
'''

# ====================================================================
# HANDLER CODE to inject before monster system section
# ====================================================================
HANDLER_CODE = r'''
    # ---- Crafting/Gathering/Cooking/Enchanting System (TASK 2: MsgType 380-389) ----

    def _regen_energy(self, session):
        """Energy regen (1/min)"""
        import time as _t
        now = _t.time()
        if session.energy_last_regen == 0.0:
            session.energy_last_regen = now
            return
        elapsed_min = (now - session.energy_last_regen) / 60.0
        regen = int(elapsed_min * GATHER_ENERGY_REGEN)
        if regen > 0:
            session.energy = min(GATHER_ENERGY_MAX, session.energy + regen)
            session.energy_last_regen = now

    async def _on_craft_list_req(self, session: PlayerSession, payload: bytes):
        """CRAFT_LIST_REQ(380): category(u8). proficiency_level filtered recipe list."""
        if not session.in_game:
            return
        category_filter = payload[0] if len(payload) >= 1 else 0xFF
        cat_map = {0: "weapon", 1: "armor", 2: "potion", 3: "gem", 4: "material"}
        filter_cat = cat_map.get(category_filter, None)
        recipes = []
        for rid, recipe in CRAFTING_RECIPES.items():
            if recipe["proficiency_required"] > session.crafting_level:
                continue
            if filter_cat and recipe["category"] != filter_cat:
                continue
            recipes.append(recipe)
        parts = [struct.pack("<B", len(recipes))]
        for r in recipes:
            rid_bytes = r["id"].encode("utf-8")
            parts.append(struct.pack("<B", len(rid_bytes)))
            parts.append(rid_bytes)
            parts.append(struct.pack("<BHB", r["proficiency_required"],
                                     r["gold_cost"], int(r["success_rate"] * 100)))
            parts.append(struct.pack("<HB", r["result"]["item_id"], r["result"]["count"]))
            parts.append(struct.pack("<B", len(r["materials"])))
        resp = b"".join(parts)
        self._send(session, MsgType.CRAFT_LIST, resp)
        self.log(f"CraftList: {session.char_name} got {len(recipes)} recipes (cat={category_filter})", "GAME")

    async def _on_craft_execute(self, session: PlayerSession, payload: bytes):
        """CRAFT_EXECUTE(382): recipe_id_len(u8) + recipe_id(str). Execute crafting."""
        if not session.in_game or len(payload) < 2:
            return
        rid_len = payload[0]
        if len(payload) < 1 + rid_len:
            return
        recipe_id = payload[1:1 + rid_len].decode("utf-8")
        recipe = CRAFTING_RECIPES.get(recipe_id)
        if not recipe:
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 1))
            return
        if session.crafting_level < recipe["proficiency_required"]:
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 2))
            return
        if session.gold < recipe["gold_cost"]:
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 3))
            return
        session.gold -= recipe["gold_cost"]
        import random as _rng
        if _rng.random() > recipe["success_rate"]:
            self.log(f"Craft: {session.char_name} FAIL {recipe_id}", "GAME")
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 5))
            return
        result_item_id = recipe["result"]["item_id"]
        result_count = recipe["result"]["count"]
        for slot in session.inventory:
            if slot.item_id == 0:
                slot.item_id = result_item_id
                slot.count = result_count
                break
        has_bonus = 0
        if recipe.get("bonus_option_chance", 0) > 0 and _rng.random() < recipe["bonus_option_chance"]:
            has_bonus = 1
        session.crafting_exp += recipe["proficiency_required"] * 10
        while session.crafting_exp >= session.crafting_level * 100 and session.crafting_level < 50:
            session.crafting_exp -= session.crafting_level * 100
            session.crafting_level += 1
            self.log(f"Craft: {session.char_name} proficiency UP -> Lv{session.crafting_level}", "GAME")
        self.log(f"Craft: {session.char_name} SUCCESS {recipe_id} -> item={result_item_id}x{result_count} bonus={has_bonus}", "GAME")
        self._send(session, MsgType.CRAFT_RESULT, struct.pack("<BHBB", 0, result_item_id, result_count, has_bonus))

    async def _on_gather_start(self, session: PlayerSession, payload: bytes):
        """GATHER_START(384): gather_type(u8). Gather with energy cost + loot drop."""
        if not session.in_game or len(payload) < 1:
            return
        gather_type = payload[0]
        gtype = GATHER_TYPES.get(gather_type)
        if not gtype:
            self._send(session, MsgType.GATHER_RESULT, struct.pack("<BB", 1, 0))
            return
        self._regen_energy(session)
        if session.energy < GATHER_ENERGY_COST:
            self._send(session, MsgType.GATHER_RESULT, struct.pack("<BB", 2, 0))
            return
        session.energy -= GATHER_ENERGY_COST
        import random as _rng
        dropped_items = []
        for loot in gtype["loot"]:
            if _rng.random() < loot["chance"]:
                dropped_items.append(loot)
        if not dropped_items and gtype["loot"]:
            dropped_items.append(gtype["loot"][0])
        for item in dropped_items:
            for slot in session.inventory:
                if slot.item_id == 0:
                    slot.item_id = item["item_id"]
                    slot.count = 1
                    break
        session.gathering_exp += gtype["exp"]
        while session.gathering_exp >= session.gathering_level * 50 and session.gathering_level < 30:
            session.gathering_exp -= session.gathering_level * 50
            session.gathering_level += 1
            self.log(f"Gather: {session.char_name} level UP -> Lv{session.gathering_level}", "GAME")
        self.log(f"Gather: {session.char_name} type={gtype['name']} got {len(dropped_items)} items, energy={session.energy}", "GAME")
        parts = [struct.pack("<BBB", 0, session.energy, len(dropped_items))]
        for item in dropped_items:
            parts.append(struct.pack("<H", item["item_id"]))
        self._send(session, MsgType.GATHER_RESULT, b"".join(parts))

    async def _on_cook_execute(self, session: PlayerSession, payload: bytes):
        """COOK_EXECUTE(386): recipe_id_len(u8) + recipe_id(str). Cook + apply buff."""
        if not session.in_game or len(payload) < 2:
            return
        rid_len = payload[0]
        if len(payload) < 1 + rid_len:
            return
        recipe_id = payload[1:1 + rid_len].decode("utf-8")
        recipe = COOKING_RECIPES.get(recipe_id)
        if not recipe:
            self._send(session, MsgType.COOK_RESULT, struct.pack("<B", 1))
            return
        if session.cooking_level < recipe["proficiency_required"]:
            self._send(session, MsgType.COOK_RESULT, struct.pack("<B", 2))
            return
        import time as _t
        if session.food_buff and session.food_buff.get("expires", 0) > _t.time():
            self._send(session, MsgType.COOK_RESULT, struct.pack("<B", 3))
            return
        session.food_buff = {
            "recipe_id": recipe_id,
            "effect": recipe["effect"],
            "expires": _t.time() + recipe["duration"],
            "duration": recipe["duration"],
        }
        self.log(f"Cook: {session.char_name} made {recipe_id}, buff={recipe['effect']} for {recipe['duration']}s", "GAME")
        effects = recipe["effect"]
        self._send(session, MsgType.COOK_RESULT, struct.pack("<BHB", 0, recipe["duration"], len(effects)))

    async def _on_enchant_req(self, session: PlayerSession, payload: bytes):
        """ENCHANT_REQ(388): slot_index(u8) + element_id(u8) + target_level(u8). Weapon enchant."""
        if not session.in_game or len(payload) < 3:
            return
        slot_idx = payload[0]
        element_id = payload[1]
        target_level = payload[2]
        if slot_idx >= len(session.inventory):
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 1, 0))
            return
        item = session.inventory[slot_idx]
        if item.item_id == 0:
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 2, 0))
            return
        if element_id >= len(ENCHANT_ELEMENTS):
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 3, 0))
            return
        level_data = ENCHANT_LEVELS.get(target_level)
        if not level_data:
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 4, 0))
            return
        gold_cost = level_data["gold_cost"]
        existing = session.weapon_enchant.get(slot_idx)
        if existing:
            gold_cost = int(gold_cost * 1.5)
        if session.gold < gold_cost:
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 5, 0))
            return
        session.gold -= gold_cost
        element_name = ENCHANT_ELEMENTS[element_id]
        session.weapon_enchant[slot_idx] = {
            "element": element_name,
            "element_id": element_id,
            "level": target_level,
            "damage_bonus": level_data["damage_bonus"],
        }
        self.log(f"Enchant: {session.char_name} slot={slot_idx} -> {element_name} Lv{target_level} (cost={gold_cost}g)", "GAME")
        self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BBBB", 0, element_id, target_level, int(level_data["damage_bonus"] * 100)))

'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check: handlers + data both present
    if 'CRAFTING_RECIPES' in content and 'def _on_craft_list_req' in content:
        print('[bridge] S042 already patched')
        return True

    changed = False

    # 1. MsgType -- check if already added
    if 'CRAFT_LIST_REQ' not in content:
        old = '    RAID_ATTACK_RESULT = 379'
        idx = content.find(old)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            insert = (
                '\n'
                '    # Crafting / Gathering / Cooking / Enchanting (TASK 2)\n'
                '    CRAFT_LIST_REQ = 380     # craft recipe list request\n'
                '    CRAFT_LIST = 381         # craft recipe list response\n'
                '    CRAFT_EXECUTE = 382      # craft execute\n'
                '    CRAFT_RESULT = 383       # craft result\n'
                '    GATHER_START = 384       # gather start\n'
                '    GATHER_RESULT = 385      # gather result\n'
                '    COOK_EXECUTE = 386       # cook execute\n'
                '    COOK_RESULT = 387        # cook result\n'
                '    ENCHANT_REQ = 388        # enchant request\n'
                '    ENCHANT_RESULT = 389     # enchant result\n'
            )
            content = content[:end] + insert + content[end:]
            changed = True
            print('[bridge] Added MsgType 380-389')

    # 2. Data constants -- insert after ENHANCE_COST_BASE line
    if 'CRAFTING_RECIPES' not in content:
        # Find line containing ENHANCE_COST_BASE = 500
        match = re.search(r'^ENHANCE_COST_BASE\s*=\s*500.*$', content, re.MULTILINE)
        if match:
            end = match.end() + 1  # after newline
            content = content[:end] + DATA_CONSTANTS + content[end:]
            changed = True
            print('[bridge] Added data constants (CRAFTING_RECIPES, GATHER_TYPES, etc.)')
        else:
            print('[bridge] WARNING: Could not find ENHANCE_COST_BASE line')

    # 3. PlayerSession fields -- check if already added
    if 'crafting_level' not in content:
        old = '    tutorial_steps: Set[int] = field(default_factory=set)'
        idx = content.find(old)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            insert = (
                '    crafting_level: int = 1           # crafting proficiency\n'
                '    crafting_exp: int = 0             # crafting exp\n'
                '    gathering_level: int = 1          # gathering proficiency\n'
                '    gathering_exp: int = 0            # gathering exp\n'
                '    cooking_level: int = 1            # cooking proficiency\n'
                '    energy: int = 200                 # gathering energy (max:200)\n'
                '    energy_last_regen: float = 0.0    # last energy regen time\n'
                '    food_buff: dict = field(default_factory=dict)  # current food buff\n'
                '    weapon_enchant: dict = field(default_factory=dict)  # {slot: {element, level}}\n'
            )
            content = content[:end] + insert + content[end:]
            changed = True
            print('[bridge] Added PlayerSession crafting fields')

    # 4. Dispatch table -- check if already added
    if 'self._on_craft_list_req' not in content:
        old = '            MsgType.RAID_ATTACK: self._on_raid_attack,\n        }'
        idx = content.find(old)
        if idx >= 0:
            insert_at = content.index('\n        }', idx)
            insert = (
                '\n'
                '            MsgType.CRAFT_LIST_REQ: self._on_craft_list_req,\n'
                '            MsgType.CRAFT_EXECUTE: self._on_craft_execute,\n'
                '            MsgType.GATHER_START: self._on_gather_start,\n'
                '            MsgType.COOK_EXECUTE: self._on_cook_execute,\n'
                '            MsgType.ENCHANT_REQ: self._on_enchant_req,'
            )
            content = content[:insert_at] + insert + content[insert_at:]
            changed = True
            print('[bridge] Added dispatch table entries')

    # 5. Handler implementations -- insert before monster system section
    if 'def _on_craft_list_req' not in content:
        # Find the monster system section marker
        marker = '    # ---- Monster System'
        idx = content.find(marker)
        if idx < 0:
            # Try alternative markers
            for m in ['    def _spawn_monsters', '    # ━━━ Monster', '    # ━━━ monster']:
                # Use a pattern that's more flexible
                pass
            match = re.search(r'^    def _spawn_monsters', content, re.MULTILINE)
            if match:
                idx = match.start()
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + content[idx:]
            changed = True
            print('[bridge] Added handler implementations')
        else:
            print('[bridge] WARNING: Could not find monster system insertion point')

    if changed:
        with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

    # Verify
    checks = [
        'CRAFT_LIST_REQ = 380', 'CRAFTING_RECIPES', 'GATHER_TYPES',
        'COOKING_RECIPES', 'ENCHANT_ELEMENTS', 'def _on_craft_list_req',
        'def _on_craft_execute', 'def _on_gather_start', 'def _on_cook_execute',
        'def _on_enchant_req', 'self._on_craft_list_req',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S042 patched OK -- 5 handlers + data constants')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_craft_list' in content:
        print('[test] S042 already patched')
        return True

    # Add imports
    old_import = (
        'from tcp_bridge import (\n'
        '    BridgeServer, MsgType, build_packet, parse_header,\n'
        '    PACKET_HEADER_SIZE, MAX_PACKET_SIZE\n'
        ')'
    )
    new_import = (
        'from tcp_bridge import (\n'
        '    BridgeServer, MsgType, build_packet, parse_header,\n'
        '    PACKET_HEADER_SIZE, MAX_PACKET_SIZE,\n'
        '    CRAFTING_RECIPES, GATHER_TYPES, COOKING_RECIPES,\n'
        '    ENCHANT_ELEMENTS, ENCHANT_LEVELS,\n'
        '    GATHER_ENERGY_MAX, GATHER_ENERGY_COST\n'
        ')'
    )
    if old_import in content:
        content = content.replace(old_import, new_import, 1)

    # Test cases
    test_code = '''
    # ---- TASK 2: Crafting/Gathering/Cooking/Enchant Tests (S042) ----

    async def login_and_enter(port_num):
        """Helper: login + enter game (gold 1000, inv 20 slots)"""
        c = TestClient()
        await c.connect('127.0.0.1', port_num)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, b'\\x01\\x00\\x00\\x00' + b'test\\x00' + b'pass\\x00')
        await c.recv_expect(MsgType.LOGIN_RESULT)
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_expect(MsgType.ENTER_GAME)
        await c.recv_all_packets(timeout=0.5)
        return c

    async def test_craft_list():
        c = await login_and_enter(port)
        await c.send(MsgType.CRAFT_LIST_REQ, struct.pack('<B', 0xFF))
        msg_type, resp = await c.recv_expect(MsgType.CRAFT_LIST)
        assert msg_type == MsgType.CRAFT_LIST, f"Expected CRAFT_LIST, got {msg_type}"
        count = resp[0]
        assert count >= 2, f"Expected at least 2 recipes for level 1, got {count}"
        c.close()

    await test("CRAFT_LIST: recipe list query", test_craft_list())

    async def test_craft_list_filter():
        c = await login_and_enter(port)
        await c.send(MsgType.CRAFT_LIST_REQ, struct.pack('<B', 2))
        msg_type, resp = await c.recv_expect(MsgType.CRAFT_LIST)
        assert msg_type == MsgType.CRAFT_LIST
        count = resp[0]
        assert count >= 1, f"Expected at least 1 potion recipe, got {count}"
        c.close()

    await test("CRAFT_LIST_FILTER: potion category filter", test_craft_list_filter())

    async def test_craft_execute_success():
        c = await login_and_enter(port)
        recipe_id = b"hp_potion_s"
        await c.send(MsgType.CRAFT_EXECUTE, struct.pack('<B', len(recipe_id)) + recipe_id)
        msg_type, resp = await c.recv_expect(MsgType.CRAFT_RESULT)
        assert msg_type == MsgType.CRAFT_RESULT, f"Expected CRAFT_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        item_id = struct.unpack_from('<H', resp, 1)[0]
        count = resp[3]
        assert item_id == 201, f"Expected item 201, got {item_id}"
        assert count == 3, f"Expected 3 potions, got {count}"
        c.close()

    await test("CRAFT_EXECUTE: success (hp_potion_s)", test_craft_execute_success())

    async def test_craft_execute_no_gold():
        c = await login_and_enter(port)
        # Spend all 1000g: iron_sword costs 200g, 5x = 1000g
        for _ in range(5):
            rid = b"iron_sword"
            await c.send(MsgType.CRAFT_EXECUTE, struct.pack('<B', len(rid)) + rid)
            await c.recv_expect(MsgType.CRAFT_RESULT)
        # Now gold=0, try iron_sword again (needs 200g)
        rid = b"iron_sword"
        await c.send(MsgType.CRAFT_EXECUTE, struct.pack('<B', len(rid)) + rid)
        msg_type, resp = await c.recv_expect(MsgType.CRAFT_RESULT)
        assert msg_type == MsgType.CRAFT_RESULT
        result = resp[0]
        assert result == 3, f"Expected NO_GOLD(3), got {result}"
        c.close()

    await test("CRAFT_FAIL: no gold", test_craft_execute_no_gold())

    async def test_craft_execute_unknown():
        c = await login_and_enter(port)
        rid = b"nonexistent_recipe"
        await c.send(MsgType.CRAFT_EXECUTE, struct.pack('<B', len(rid)) + rid)
        msg_type, resp = await c.recv_expect(MsgType.CRAFT_RESULT)
        assert msg_type == MsgType.CRAFT_RESULT
        result = resp[0]
        assert result == 1, f"Expected UNKNOWN_RECIPE(1), got {result}"
        c.close()

    await test("CRAFT_FAIL: unknown recipe", test_craft_execute_unknown())

    async def test_gather_success():
        c = await login_and_enter(port)
        await c.send(MsgType.GATHER_START, struct.pack('<B', 1))
        msg_type, resp = await c.recv_expect(MsgType.GATHER_RESULT)
        assert msg_type == MsgType.GATHER_RESULT, f"Expected GATHER_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        energy_left = resp[1]
        assert energy_left == GATHER_ENERGY_MAX - GATHER_ENERGY_COST, f"Expected energy {GATHER_ENERGY_MAX - GATHER_ENERGY_COST}, got {energy_left}"
        drop_count = resp[2]
        assert drop_count >= 1, f"Expected at least 1 drop, got {drop_count}"
        c.close()

    await test("GATHER: success + energy cost", test_gather_success())

    async def test_gather_unknown_type():
        c = await login_and_enter(port)
        await c.send(MsgType.GATHER_START, struct.pack('<B', 99))
        msg_type, resp = await c.recv_expect(MsgType.GATHER_RESULT)
        assert msg_type == MsgType.GATHER_RESULT
        result = resp[0]
        assert result == 1, f"Expected UNKNOWN_TYPE(1), got {result}"
        c.close()

    await test("GATHER_FAIL: unknown gather type", test_gather_unknown_type())

    async def test_cook_success():
        c = await login_and_enter(port)
        rid = b"grilled_meat"
        await c.send(MsgType.COOK_EXECUTE, struct.pack('<B', len(rid)) + rid)
        msg_type, resp = await c.recv_expect(MsgType.COOK_RESULT)
        assert msg_type == MsgType.COOK_RESULT, f"Expected COOK_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        duration = struct.unpack_from('<H', resp, 1)[0]
        assert duration == 1800, f"Expected 1800s duration, got {duration}"
        c.close()

    await test("COOK: success (grilled_meat)", test_cook_success())

    async def test_cook_already_buffed():
        c = await login_and_enter(port)
        rid = b"grilled_meat"
        await c.send(MsgType.COOK_EXECUTE, struct.pack('<B', len(rid)) + rid)
        msg_type, resp = await c.recv_expect(MsgType.COOK_RESULT)
        assert resp[0] == 0, "First cook should succeed"
        await c.send(MsgType.COOK_EXECUTE, struct.pack('<B', len(rid)) + rid)
        msg_type, resp = await c.recv_expect(MsgType.COOK_RESULT)
        assert msg_type == MsgType.COOK_RESULT
        result = resp[0]
        assert result == 3, f"Expected ALREADY_BUFFED(3), got {result}"
        c.close()

    await test("COOK_FAIL: already buffed", test_cook_already_buffed())

    async def test_enchant_success():
        c = await login_and_enter(port)
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 301, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        await c.send(MsgType.ENCHANT_REQ, struct.pack('<BBB', 0, 0, 1))
        msg_type, resp = await c.recv_expect(MsgType.ENCHANT_RESULT)
        assert msg_type == MsgType.ENCHANT_RESULT, f"Expected ENCHANT_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        element_id = resp[1]
        assert element_id == 0, f"Expected fire(0), got {element_id}"
        level = resp[2]
        assert level == 1, f"Expected level 1, got {level}"
        dmg_bonus = resp[3]
        assert dmg_bonus == 5, f"Expected 5%% bonus, got {dmg_bonus}"
        c.close()

    await test("ENCHANT: success (fire Lv1)", test_enchant_success())
'''

    # Find insertion point: after last RAID test, before results section
    marker = '    # ━━━ 결과 ━━━'
    # Try to find the marker with the exact unicode chars
    idx = content.find(marker)
    if idx < 0:
        # Try ASCII fallback
        for m in ['    # ---- Result', '    # Results', '    print(f"\\n{']:
            idx = content.find(m)
            if idx >= 0:
                break
    if idx < 0:
        # Last resort: find the results print line
        match = re.search(r'^\s*print\(f"\\n{\'=\'', content, re.MULTILINE)
        if match:
            idx = match.start()

    if idx >= 0:
        content = content[:idx] + test_code + '\n' + content[idx:]
    else:
        print('[test] WARNING: Could not find insertion point for tests')
        return False

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    checks = ['test_craft_list', 'test_craft_execute_success', 'test_gather_success',
              'test_cook_success', 'test_enchant_success']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S042 patched OK -- 10 crafting/gathering/cooking/enchant tests added')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS042 all patches applied!')
    else:
        print('\nS042 PATCH FAILED!')
        sys.exit(1)
