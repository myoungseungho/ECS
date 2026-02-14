"""
_patch_s041.py - TASK 2: Crafting/Gathering/Cooking/Enchant (MsgType 380-389)
"""

import re
import os

BRIDGE_PATH = os.path.join(os.path.dirname(__file__), "tcp_bridge.py")
PATCH_MARKER = "# --- S041 PATCHED ---"


def apply_s041():
    with open(BRIDGE_PATH, "r", encoding="utf-8") as f:
        code = f.read()

    if PATCH_MARKER in code:
        print("[bridge] S041 already patched")
        print("\nS041 all patches applied!")
        return

    # 1. MsgType enum 확장 (380-389)
    msgtype_block = "\n".join([
        "",
        "    # --- S041: Crafting/Gathering/Cooking/Enchant ---",
        "    CRAFT_LIST_REQ = 380",
        "    CRAFT_LIST = 381",
        "    CRAFT_EXECUTE = 382",
        "    CRAFT_RESULT = 383",
        "    GATHER_START = 384",
        "    GATHER_RESULT = 385",
        "    COOK_EXECUTE = 386",
        "    COOK_RESULT = 387",
        "    ENCHANT_REQ = 388",
        "    ENCHANT_RESULT = 389",
    ])

    raid_pat = re.compile(r"(    RAID_ATTACK_RESULT\s*=\s*379)")
    if raid_pat.search(code):
        code = raid_pat.sub(r"\1" + msgtype_block, code)
    else:
        code = code.replace(
            "    ITEM_ADD_RESULT = 193",
            "    ITEM_ADD_RESULT = 193" + msgtype_block,
        )

    # 2. __init__ 에 S041 필드 추가
    init_anchor = "self.next_pvp_match_id = 1"
    s041_fields = "\n".join([
        "",
        "        # S041: Crafting system",
        "        self.craft_proficiency = {}",
        "        self.gather_energy = {}",
        "        self.gather_proficiency = {}",
        "        self.food_buffs = {}",
        "        self.enchantments = {}",
    ])
    if init_anchor in code:
        code = code.replace(init_anchor, init_anchor + s041_fields)
    else:
        code = code.replace(
            "self.instances = {}",
            "self.instances = {}" + s041_fields,
        )

    # 3. _dispatch 에 핸들러 등록
    dispatch_anchor = "MsgType.RAID_ATTACK: self._on_raid_attack,"
    dispatch_lines = "\n".join([
        "",
        "            # S041: Crafting",
        "            MsgType.CRAFT_LIST_REQ: self._on_craft_list_req,",
        "            MsgType.CRAFT_EXECUTE: self._on_craft_execute,",
        "            MsgType.GATHER_START: self._on_gather_start,",
        "            MsgType.COOK_EXECUTE: self._on_cook_execute,",
        "            MsgType.ENCHANT_REQ: self._on_enchant_req,",
    ])
    if dispatch_anchor in code:
        code = code.replace(dispatch_anchor, dispatch_anchor + dispatch_lines)

    # 4. 핸들러 + 데이터 코드 (if __name__ 앞에 삽입)
    handler_code = _build_handler_code()
    if "if __name__" in code:
        code = code.replace("if __name__", handler_code + "\n\nif __name__")
    else:
        code += handler_code

    with open(BRIDGE_PATH, "w", encoding="utf-8") as f:
        f.write(code)

    print("[bridge] S041 patched: Crafting/Gathering/Cooking/Enchant (MsgType 380-389)")
    print("\nS041 all patches applied!")


def _build_handler_code():
    NUL = "\\x00"
    lines = []
    lines.append("")
    lines.append("# " + "=" * 60)
    lines.append("# S041: Crafting / Gathering / Cooking / Enchant System")
    lines.append("# " + "=" * 60)
    lines.append(PATCH_MARKER)
    lines.append("")
    lines.append("import random as _rng_crafting")
    lines.append("")

    # CRAFT_RECIPES
    lines.append("CRAFT_RECIPES = {")
    _recipes = [
        (1, "Iron Sword", "weapon", 1, [(1001,5),(1002,2)], 200, 5, 1.0, 2001, 1, 0.0),
        (2, "Steel Sword", "weapon", 10, [(1003,3),(1004,2),(2001,1)], 1000, 10, 0.9, 2002, 1, 0.2),
        (3, "HP Potion (S)", "potion", 1, [(1005,3)], 20, 2, 1.0, 3001, 3, 0.0),
        (4, "HP Potion (L)", "potion", 15, [(1006,5),(1007,1)], 200, 5, 0.8, 3002, 3, 0.0),
        (5, "Polished Ruby", "gem", 10, [(1008,3)], 100, 5, 1.0, 4001, 1, 0.0),
        (6, "Iron Armor", "armor", 1, [(1001,8),(1004,3)], 300, 8, 1.0, 2101, 1, 0.0),
        (7, "MP Potion (S)", "potion", 1, [(1005,2),(1007,1)], 30, 2, 1.0, 3003, 3, 0.0),
        (8, "Mithril Sword", "weapon", 20, [(1009,5),(1004,3),(2002,1)], 5000, 15, 0.7, 2003, 1, 0.3),
    ]
    for rid, name, cat, prof, mats, gold, time, sr, ri, rc, bc in _recipes:
        lines.append(f'    {rid}: {{"name": "{name}", "category": "{cat}", "proficiency": {prof},')
        lines.append(f'        "materials": {mats}, "gold": {gold}, "time": {time},')
        lines.append(f'        "success_rate": {sr}, "result_item": {ri}, "result_count": {rc}, "bonus_chance": {bc}}},')
    lines.append("}")
    lines.append("")

    # GATHER_NODES
    lines.append("GATHER_NODES = {")
    _nodes = [
        (1, "Herb", "herb", 5, 3.0, 5, [(1005,0.80),(1006,0.15),(1010,0.05)]),
        (2, "Ore", "mining", 5, 5.0, 8, [(1001,0.70),(1011,0.20),(1012,0.08),(1013,0.02)]),
        (3, "Wood", "logging", 5, 4.0, 6, [(1002,0.80),(1014,0.15),(1015,0.05)]),
        (4, "Fishing", "fishing", 5, 6.0, 7, [(1016,0.60),(1017,0.25),(1018,0.10),(1019,0.05)]),
    ]
    for nid, name, ntype, energy, time, exp, loot in _nodes:
        lines.append(f'    {nid}: {{"name": "{name}", "type": "{ntype}", "energy": {energy}, "time": {time}, "exp": {exp},')
        lines.append(f'        "loot": {loot}}},')
    lines.append("}")
    lines.append("")

    # COOK_RECIPES
    lines.append("COOK_RECIPES = {")
    _cooks = [
        (1, "Grilled Meat", 1, [(1020,3)], 0, "atk", 10, 1800),
        (2, "Fish Stew", 5, [(1016,2),(1005,1)], 0, "hp", 200, 1800),
        (3, "Royal Feast", 20, [(1021,2),(1006,2),(1022,1)], 50, "all", 5, 3600),
    ]
    for cid, name, prof, mats, gold, bt, bv, bd in _cooks:
        lines.append(f'    {cid}: {{"name": "{name}", "proficiency": {prof},')
        lines.append(f'        "materials": {mats}, "gold": {gold},')
        lines.append(f'        "buff_type": "{bt}", "buff_value": {bv}, "buff_duration": {bd}}},')
    lines.append("}")
    lines.append("")

    # ENCHANT
    lines.append("ENCHANT_ELEMENTS = {1: 'fire', 2: 'ice', 3: 'lightning', 4: 'dark', 5: 'holy', 6: 'nature'}")
    lines.append("ENCHANT_LEVELS = {")
    lines.append('    1: {"damage_bonus": 0.05, "material_count": 5, "gold": 1000},')
    lines.append('    2: {"damage_bonus": 0.10, "material_count": 10, "gold": 3000},')
    lines.append('    3: {"damage_bonus": 0.15, "material_count": 20, "gold": 10000},')
    lines.append("}")
    lines.append("")

    # Handler functions — use session.inventory (List[InventorySlot]) not self.inventories
    lines.append("")
    lines.append("def _s041_has_materials(session, materials):")
    lines.append("    '''Check if session.inventory has all required materials'''")
    lines.append("    for mat_id, mat_count in materials:")
    lines.append("        found = sum(s.count for s in session.inventory if s.item_id == mat_id)")
    lines.append("        if found < mat_count: return False")
    lines.append("    return True")
    lines.append("")
    lines.append("def _s041_remove_materials(session, materials):")
    lines.append("    '''Remove materials from session.inventory'''")
    lines.append("    for mat_id, mat_count in materials:")
    lines.append("        remaining = mat_count")
    lines.append("        for s in session.inventory:")
    lines.append("            if s.item_id == mat_id and remaining > 0:")
    lines.append("                take = min(s.count, remaining)")
    lines.append("                s.count -= take")
    lines.append("                remaining -= take")
    lines.append("                if s.count <= 0: s.item_id = 0; s.count = 0; s.equipped = False; s.enhance_level = 0")
    lines.append("")

    lines.append("async def _s041_craft_list(self, session, payload):")
    lines.append("    import struct")
    lines.append("    acct = session.account_id")
    lines.append("    prof_level = self.craft_proficiency.get(acct, 1)")
    lines.append("    buf = bytearray()")
    lines.append("    recipes = [(rid, r) for rid, r in CRAFT_RECIPES.items() if r['proficiency'] <= prof_level]")
    lines.append("    buf.append(len(recipes))")
    lines.append("    for rid, r in recipes:")
    lines.append("        buf += struct.pack('<H', rid)")
    lines.append('        name_b = r["name"].encode("utf-8")[:32].ljust(32, b"' + NUL + '")')
    lines.append("        buf += name_b")
    lines.append('        cat_map = {"weapon": 1, "armor": 2, "potion": 3, "gem": 4, "material": 5}')
    lines.append('        buf.append(cat_map.get(r["category"], 0))')
    lines.append('        buf.append(r["proficiency"])')
    lines.append('        buf.append(len(r["materials"]))')
    lines.append('        buf.append(int(r["success_rate"] * 100))')
    lines.append("        buf += struct.pack('<I', r['gold'])")
    lines.append("    self._send(session, MsgType.CRAFT_LIST, bytes(buf))")
    lines.append('    print(f"    CraftList: {len(recipes)} recipes for {session.char_name} (prof={prof_level})")')
    lines.append("")

    lines.append("async def _s041_craft_execute(self, session, payload):")
    lines.append("    import struct")
    lines.append("    if len(payload) < 2: return")
    lines.append("    recipe_id = struct.unpack_from('<H', payload, 0)[0]")
    lines.append("    acct = session.account_id")
    lines.append("    recipe = CRAFT_RECIPES.get(recipe_id)")
    lines.append("    if not recipe:")
    lines.append("        self._send(session, MsgType.CRAFT_RESULT, struct.pack('<BHIHB', 1, recipe_id, 0, 0, 0)); return")
    lines.append("    prof = self.craft_proficiency.get(acct, 1)")
    lines.append('    if prof < recipe["proficiency"]:')
    lines.append("        self._send(session, MsgType.CRAFT_RESULT, struct.pack('<BHIHB', 2, recipe_id, 0, 0, 0)); return")
    lines.append('    if not _s041_has_materials(session, recipe["materials"]):')
    lines.append("        self._send(session, MsgType.CRAFT_RESULT, struct.pack('<BHIHB', 3, recipe_id, 0, 0, 0)); return")
    lines.append('    if session.gold < recipe["gold"]:')
    lines.append("        self._send(session, MsgType.CRAFT_RESULT, struct.pack('<BHIHB', 4, recipe_id, 0, 0, 0)); return")
    lines.append('    _s041_remove_materials(session, recipe["materials"])')
    lines.append('    session.gold -= recipe["gold"]')
    lines.append('    if _rng_crafting.random() > recipe["success_rate"]:')
    lines.append("        self._send(session, MsgType.CRAFT_RESULT, struct.pack('<BHIHB', 5, recipe_id, 0, 0, 0))")
    lines.append("        return")
    lines.append('    bonus = 1 if recipe["bonus_chance"] > 0 and _rng_crafting.random() < recipe["bonus_chance"] else 0')
    lines.append('    result_item = recipe["result_item"]')
    lines.append('    result_count = recipe["result_count"]')
    lines.append("    slot_idx = self._find_empty_slot(session)")
    lines.append("    if slot_idx >= 0:")
    lines.append("        session.inventory[slot_idx].item_id = result_item")
    lines.append("        session.inventory[slot_idx].count = result_count")
    lines.append("    self._send(session, MsgType.CRAFT_RESULT, struct.pack('<BHIHB', 0, recipe_id, result_item, result_count, bonus))")
    lines.append('    print(f"    Craft: {recipe[\'name\']} x{result_count} ({session.char_name})")')
    lines.append("")

    lines.append("async def _s041_gather(self, session, payload):")
    lines.append("    import struct")
    lines.append("    if len(payload) < 1: return")
    lines.append("    node_type = payload[0]")
    lines.append("    acct = session.account_id")
    lines.append("    node = GATHER_NODES.get(node_type)")
    lines.append("    if not node:")
    lines.append("        self._send(session, MsgType.GATHER_RESULT, struct.pack('<BBIHH', 1, node_type, 0, 0, 0)); return")
    lines.append("    energy = self.gather_energy.get(acct, 200)")
    lines.append('    if energy < node["energy"]:')
    lines.append("        self._send(session, MsgType.GATHER_RESULT, struct.pack('<BBIHH', 2, node_type, 0, 0, energy)); return")
    lines.append('    energy -= node["energy"]')
    lines.append("    self.gather_energy[acct] = energy")
    lines.append("    roll = _rng_crafting.random()")
    lines.append("    cumulative = 0.0")
    lines.append("    dropped_item = 0")
    lines.append('    for item_id, chance in node["loot"]:')
    lines.append("        cumulative += chance")
    lines.append("        if roll <= cumulative: dropped_item = item_id; break")
    lines.append("    if dropped_item == 0:")
    lines.append("        self._send(session, MsgType.GATHER_RESULT, struct.pack('<BBIHH', 3, node_type, 0, 0, energy)); return")
    lines.append("    slot_idx = self._find_empty_slot(session)")
    lines.append("    if slot_idx >= 0:")
    lines.append("        session.inventory[slot_idx].item_id = dropped_item")
    lines.append("        session.inventory[slot_idx].count = 1")
    lines.append("    self._send(session, MsgType.GATHER_RESULT, struct.pack('<BBIHH', 0, node_type, dropped_item, 1, energy))")
    lines.append('    print(f"    Gather: {node[\'name\']} -> item {dropped_item} (energy={energy}) ({session.char_name})")')
    lines.append("")

    lines.append("async def _s041_cook(self, session, payload):")
    lines.append("    import struct, time as _time")
    lines.append("    if len(payload) < 1: return")
    lines.append("    recipe_id = payload[0]")
    lines.append("    acct = session.account_id")
    lines.append("    recipe = COOK_RECIPES.get(recipe_id)")
    lines.append("    if not recipe:")
    lines.append("        self._send(session, MsgType.COOK_RESULT, struct.pack('<BBBHH', 1, recipe_id, 0, 0, 0)); return")
    lines.append("    existing = self.food_buffs.get(acct)")
    lines.append('    if existing and existing.get("expires", 0) > _time.time():')
    lines.append("        self._send(session, MsgType.COOK_RESULT, struct.pack('<BBBHH', 3, recipe_id, 0, 0, 0)); return")
    lines.append('    if not _s041_has_materials(session, recipe["materials"]):')
    lines.append("        self._send(session, MsgType.COOK_RESULT, struct.pack('<BBBHH', 2, recipe_id, 0, 0, 0)); return")
    lines.append('    _s041_remove_materials(session, recipe["materials"])')
    lines.append('    buff_type_map = {"atk": 1, "hp": 2, "all": 3}')
    lines.append('    bt = buff_type_map.get(recipe["buff_type"], 0)')
    lines.append("    self.food_buffs[acct] = {")
    lines.append('        "type": recipe["buff_type"], "value": recipe["buff_value"],')
    lines.append('        "expires": _time.time() + recipe["buff_duration"]}')
    lines.append('    self._send(session, MsgType.COOK_RESULT, struct.pack("<BBBHH", 0, recipe_id, bt, recipe["buff_value"], recipe["buff_duration"]))')
    lines.append('    print(f"    Cook: {recipe[\'name\']} buff={recipe[\'buff_type\']}+{recipe[\'buff_value\']} ({session.char_name})")')
    lines.append("")

    lines.append("async def _s041_enchant(self, session, payload):")
    lines.append("    import struct")
    lines.append("    if len(payload) < 3: return")
    lines.append("    slot, element, level = payload[0], payload[1], payload[2]")
    lines.append("    acct = session.account_id")
    lines.append("    if element not in ENCHANT_ELEMENTS:")
    lines.append("        self._send(session, MsgType.ENCHANT_RESULT, struct.pack('<BBBBB', 1, slot, element, level, 0)); return")
    lines.append("    if level not in ENCHANT_LEVELS:")
    lines.append("        self._send(session, MsgType.ENCHANT_RESULT, struct.pack('<BBBBB', 2, slot, element, level, 0)); return")
    lines.append("    if slot >= len(session.inventory) or session.inventory[slot].item_id == 0:")
    lines.append("        self._send(session, MsgType.ENCHANT_RESULT, struct.pack('<BBBBB', 5, slot, element, level, 0)); return")
    lines.append("    ench_data = ENCHANT_LEVELS[level]")
    lines.append('    cost = ench_data["gold"]')
    lines.append("    existing = self.enchantments.get((acct, slot))")
    lines.append("    if existing: cost = int(cost * 1.5)")
    lines.append("    if session.gold < cost:")
    lines.append("        self._send(session, MsgType.ENCHANT_RESULT, struct.pack('<BBBBB', 4, slot, element, level, 0)); return")
    lines.append("    session.gold -= cost")
    lines.append('    self.enchantments[(acct, slot)] = {"element": element, "level": level}')
    lines.append('    dmg_pct = int(ench_data["damage_bonus"] * 100)')
    lines.append("    self._send(session, MsgType.ENCHANT_RESULT, struct.pack('<BBBBB', 0, slot, element, level, dmg_pct))")
    lines.append('    print(f"    Enchant: slot={slot} {ENCHANT_ELEMENTS[element]} Lv{level} (+{dmg_pct}%) ({session.char_name})")')
    lines.append("")

    # Bind
    lines.append("BridgeServer._on_craft_list_req = _s041_craft_list")
    lines.append("BridgeServer._on_craft_execute = _s041_craft_execute")
    lines.append("BridgeServer._on_gather_start = _s041_gather")
    lines.append("BridgeServer._on_cook_execute = _s041_cook")
    lines.append("BridgeServer._on_enchant_req = _s041_enchant")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    apply_s041()
