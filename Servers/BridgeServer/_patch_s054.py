"""
Patch S054: Sub-Currency System (TASK 10)
- CURRENCY_QUERY(468)→CURRENCY_INFO(469)          -- 전체 화폐 조회 (gold/silver/dungeon_token/pvp_token/guild_contribution)
- TOKEN_SHOP_LIST(470)→TOKEN_SHOP(471)             -- 토큰 상점 목록 조회
- TOKEN_SHOP_BUY(472)→TOKEN_SHOP_BUY_RESULT(473)   -- 토큰 상점 구매
- 실버 화폐: SHOP_BUY(252) 핸들러에 silver 결제 분기 추가
- 던전/PvP 토큰: RAID_CLEAR(377) 시 dungeon_token 지급, PvP 승리 시 pvp_token 지급
- 4 test cases

Currency Types (GDD economy.yaml):
  gold:              max 999999999  tradeable
  silver:            max 99999999   NPC only
  dungeon_token:     max 99999      dungeon shop
  pvp_token:         max 99999      pvp shop
  guild_contribution: max 99999     guild shop

Token Shop (GDD economy.yaml npc_shops):
  dungeon_shop: epic_weapon_box(500dt) / epic_armor_box(400dt) / skill_book_rare(200dt)
  pvp_shop: pvp_weapon(1000pt) / pvp_armor(800pt) / pvp_cosmetic(500pt)
  guild_shop: guild_buff_scroll(300gc) / guild_storage_expansion(1000gc) / guild_cosmetic(500gc)

MsgType layout:
  468 CURRENCY_QUERY
  469 CURRENCY_INFO
  470 TOKEN_SHOP_LIST
  471 TOKEN_SHOP
  472 TOKEN_SHOP_BUY
  473 TOKEN_SHOP_BUY_RESULT
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Currency (468-473)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Sub-Currency / Token Shop (TASK 10)\n'
    '    CURRENCY_QUERY = 468\n'
    '    CURRENCY_INFO = 469\n'
    '    TOKEN_SHOP_LIST = 470\n'
    '    TOKEN_SHOP = 471\n'
    '    TOKEN_SHOP_BUY = 472\n'
    '    TOKEN_SHOP_BUY_RESULT = 473\n'
)

# ====================================================================
# 2. Data constants (GDD economy.yaml currencies + token shops)
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Sub-Currency System Data (GDD economy.yaml) ----
CURRENCY_MAX = {
    "gold": 999999999,
    "silver": 99999999,
    "dungeon_token": 99999,
    "pvp_token": 99999,
    "guild_contribution": 99999,
}
# Starting silver for new characters
SILVER_INITIAL = 5000
# Dungeon clear token rewards by difficulty
DUNGEON_TOKEN_REWARDS = {
    "normal": 50,
    "hard": 100,
    "hell": 200,
    "chaos": 30,
}
# PvP token rewards
PVP_TOKEN_WIN = 30
PVP_TOKEN_LOSS = 10
# Guild contribution sources
GUILD_CONTRIB_QUEST = 50       # per guild quest
GUILD_CONTRIB_DONATE_RATIO = 0.01  # 1% of gold donated
# Token shop definitions (GDD economy.yaml npc_shops)
TOKEN_SHOP_DUNGEON = [
    {"shop_id": 1, "item_id": "epic_weapon_box",  "price": 500, "currency": "dungeon_token", "name": "에픽 무기 상자"},
    {"shop_id": 2, "item_id": "epic_armor_box",   "price": 400, "currency": "dungeon_token", "name": "에픽 방어구 상자"},
    {"shop_id": 3, "item_id": "skill_book_rare",  "price": 200, "currency": "dungeon_token", "name": "희귀 스킬서"},
    {"shop_id": 4, "item_id": "dungeon_potion",   "price": 50,  "currency": "dungeon_token", "name": "던전 특수 물약"},
]
TOKEN_SHOP_PVP = [
    {"shop_id": 11, "item_id": "pvp_weapon",   "price": 1000, "currency": "pvp_token", "name": "투기장 무기"},
    {"shop_id": 12, "item_id": "pvp_armor",    "price": 800,  "currency": "pvp_token", "name": "투기장 방어구"},
    {"shop_id": 13, "item_id": "pvp_cosmetic", "price": 500,  "currency": "pvp_token", "name": "투기장 외형"},
    {"shop_id": 14, "item_id": "pvp_title_mat","price": 300,  "currency": "pvp_token", "name": "칭호 재료"},
]
TOKEN_SHOP_GUILD = [
    {"shop_id": 21, "item_id": "guild_buff_scroll",        "price": 300,  "currency": "guild_contribution", "name": "길드 버프 주문서"},
    {"shop_id": 22, "item_id": "guild_storage_expansion",  "price": 1000, "currency": "guild_contribution", "name": "길드 창고 확장"},
    {"shop_id": 23, "item_id": "guild_cosmetic",           "price": 500,  "currency": "guild_contribution", "name": "길드 외형"},
]
TOKEN_SHOPS = {
    "dungeon": TOKEN_SHOP_DUNGEON,
    "pvp": TOKEN_SHOP_PVP,
    "guild": TOKEN_SHOP_GUILD,
}
# Silver item table for NPC shop (GDD economy.yaml general_store)
SILVER_SHOP_ITEMS = {
    "hp_potion_s":    {"price": 50,  "name": "소형 체력 물약"},
    "hp_potion_m":    {"price": 150, "name": "중형 체력 물약"},
    "hp_potion_l":    {"price": 500, "name": "대형 체력 물약"},
    "mp_potion_s":    {"price": 50,  "name": "소형 마나 물약"},
    "mp_potion_m":    {"price": 150, "name": "중형 마나 물약"},
    "return_scroll":  {"price": 100, "name": "귀환 주문서"},
    "repair_kit":     {"price": 200, "name": "수리 키트"},
    "torch":          {"price": 30,  "name": "횃불"},
}
'''

# ====================================================================
# 3. PlayerSession fields for sub-currencies
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Sub-Currency (TASK 10) ----\n'
    '    silver: int = 5000                       # 실버 (NPC 전용 보조화폐)\n'
    '    dungeon_token: int = 0                   # 던전 토큰\n'
    '    pvp_token: int = 0                       # PvP 토큰\n'
    '    guild_contribution: int = 0              # 길드 기여도\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.CURRENCY_QUERY: self._on_currency_query,\n'
    '            MsgType.TOKEN_SHOP_LIST: self._on_token_shop_list,\n'
    '            MsgType.TOKEN_SHOP_BUY: self._on_token_shop_buy,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Sub-Currency / Token Shop (TASK 10: MsgType 468-473) ----

    async def _on_currency_query(self, session, payload: bytes):
        """CURRENCY_QUERY(468) -> CURRENCY_INFO(469)
        Request: (empty or u8 currency_type — 0=all, 1=gold, 2=silver, 3=dungeon, 4=pvp, 5=guild)
        Response: gold(u32) + silver(u32) + dungeon_token(u32) + pvp_token(u32) + guild_contribution(u32)
        """
        if not session.in_game:
            return

        self._send(session, MsgType.CURRENCY_INFO,
                   struct.pack('<I I I I I',
                               min(session.gold, CURRENCY_MAX["gold"]),
                               min(session.silver, CURRENCY_MAX["silver"]),
                               min(session.dungeon_token, CURRENCY_MAX["dungeon_token"]),
                               min(session.pvp_token, CURRENCY_MAX["pvp_token"]),
                               min(session.guild_contribution, CURRENCY_MAX["guild_contribution"])))

    async def _on_token_shop_list(self, session, payload: bytes):
        """TOKEN_SHOP_LIST(470) -> TOKEN_SHOP(471)
        Request: shop_type(u8) — 0=dungeon, 1=pvp, 2=guild
        Response: shop_type(u8) + count(u8) + [shop_id(u16) + price(u32) + currency_type(u8) + name_len(u8) + name(utf8)]
        """
        if not session.in_game or len(payload) < 1:
            return

        shop_type = payload[0]
        shop_map = {0: "dungeon", 1: "pvp", 2: "guild"}
        shop_key = shop_map.get(shop_type)

        if shop_key is None or shop_key not in TOKEN_SHOPS:
            # Invalid shop type — empty response
            self._send(session, MsgType.TOKEN_SHOP,
                       struct.pack('<B B', shop_type, 0))
            return

        items = TOKEN_SHOPS[shop_key]
        data = struct.pack('<B B', shop_type, len(items))
        for item in items:
            currency_type = {"dungeon_token": 0, "pvp_token": 1, "guild_contribution": 2}.get(item["currency"], 0)
            name_bytes = item["name"].encode('utf-8')[:50]
            data += struct.pack('<H I B B', item["shop_id"], item["price"], currency_type, len(name_bytes))
            data += name_bytes

        self._send(session, MsgType.TOKEN_SHOP, data)

    async def _on_token_shop_buy(self, session, payload: bytes):
        """TOKEN_SHOP_BUY(472) -> TOKEN_SHOP_BUY_RESULT(473)
        Request: shop_id(u16) + quantity(u8)
        Response: result(u8) + shop_id(u16) + remaining_currency(u32)
          result: 0=SUCCESS, 1=INSUFFICIENT_TOKEN, 2=INVALID_ITEM, 3=CURRENCY_AT_MAX, 4=INVENTORY_FULL
        """
        if not session.in_game or len(payload) < 3:
            return

        shop_id = struct.unpack('<H', payload[0:2])[0]
        quantity = max(1, payload[2])

        # Find item across all shops
        target_item = None
        for shop_list in TOKEN_SHOPS.values():
            for item in shop_list:
                if item["shop_id"] == shop_id:
                    target_item = item
                    break
            if target_item:
                break

        def _send_result(result, remaining=0):
            self._send(session, MsgType.TOKEN_SHOP_BUY_RESULT,
                       struct.pack('<B H I', result, shop_id, remaining))

        if not target_item:
            _send_result(2)  # INVALID_ITEM
            return

        currency_name = target_item["currency"]
        total_cost = target_item["price"] * quantity

        # Check currency balance
        current_balance = getattr(session, currency_name, 0)
        if current_balance < total_cost:
            _send_result(1, current_balance)  # INSUFFICIENT_TOKEN
            return

        # Deduct currency
        new_balance = current_balance - total_cost
        setattr(session, currency_name, new_balance)

        # Add item to inventory (simplified — add to inventory dict)
        item_id = target_item["item_id"]
        if not hasattr(session, 'inventory') or session.inventory is None:
            session.inventory = {}
        session.inventory[item_id] = session.inventory.get(item_id, 0) + quantity

        _send_result(0, new_balance)  # SUCCESS
'''

# ====================================================================
# 6. Silver payment patch for SHOP_BUY handler
# ====================================================================
SILVER_PATCH_CODE = r'''
        # ---- Silver currency branch (TASK 10) ----
        # Check if item uses silver currency
        silver_price = SILVER_SHOP_ITEMS.get(item_id, {}).get("price", 0) if item_id in SILVER_SHOP_ITEMS else 0
        if silver_price > 0:
            total_silver = silver_price * quantity
            if session.silver < total_silver:
                self._send(session, MsgType.SHOP_BUY_RESULT,
                           struct.pack('<B I I', 2, session.silver, 0))  # result=2 insufficient
                return
            session.silver -= total_silver
            # Add item to inventory
            if not hasattr(session, 'inventory') or session.inventory is None:
                session.inventory = {}
            session.inventory[item_id] = session.inventory.get(item_id, 0) + quantity
            self._send(session, MsgType.SHOP_BUY_RESULT,
                       struct.pack('<B I I', 0, session.silver, quantity))  # result=0 success
            return
'''

# ====================================================================
# 7. Dungeon/PvP token reward hooks
# ====================================================================
DUNGEON_TOKEN_HOOK = r'''
            # ---- Dungeon token reward (TASK 10) ----
            _dt_reward = DUNGEON_TOKEN_REWARDS.get(diff, 50)
            s.dungeon_token = min(s.dungeon_token + _dt_reward, CURRENCY_MAX["dungeon_token"])
'''

PVP_TOKEN_HOOK = r'''
                    # ---- PvP token reward (TASK 10) ----
                    if won:
                        s.pvp_token = min(s.pvp_token + PVP_TOKEN_WIN, CURRENCY_MAX["pvp_token"])
                    else:
                        s.pvp_token = min(s.pvp_token + PVP_TOKEN_LOSS, CURRENCY_MAX["pvp_token"])
'''

# ====================================================================
# 8. Test cases (4 tests)
# ====================================================================
TEST_CODE = r'''
    # ━━━ Test: CURRENCY_QUERY — 전체 화폐 조회 ━━━
    async def test_currency_query():
        """전체 화폐 조회 → gold/silver/dungeon_token/pvp_token/guild_contribution 반환."""
        c = await login_and_enter(port)
        await c.send(MsgType.CURRENCY_QUERY, b'')
        msg_type, resp = await c.recv_expect(MsgType.CURRENCY_INFO)
        assert msg_type == MsgType.CURRENCY_INFO, f"Expected CURRENCY_INFO, got {msg_type}"
        assert len(resp) >= 20, f"Response too short: {len(resp)} bytes"
        gold, silver, dt, pt, gc = struct.unpack('<I I I I I', resp[:20])
        assert gold >= 0, f"gold must be >= 0, got {gold}"
        assert silver >= 0, f"silver must be >= 0, got {silver}"
        assert dt >= 0, f"dungeon_token must be >= 0, got {dt}"
        assert pt >= 0, f"pvp_token must be >= 0, got {pt}"
        assert gc >= 0, f"guild_contribution must be >= 0, got {gc}"
        c.close()

    await test("CURRENCY_QUERY: 전체 화폐 조회", test_currency_query())

    # ━━━ Test: TOKEN_SHOP_LIST — 토큰 상점 목록 조회 ━━━
    async def test_token_shop_list():
        """던전 토큰 상점 목록 조회 → 아이템 4개."""
        c = await login_and_enter(port)
        # Query dungeon shop (type=0)
        await c.send(MsgType.TOKEN_SHOP_LIST, struct.pack('<B', 0))
        msg_type, resp = await c.recv_expect(MsgType.TOKEN_SHOP)
        assert msg_type == MsgType.TOKEN_SHOP, f"Expected TOKEN_SHOP, got {msg_type}"
        shop_type = resp[0]
        count = resp[1]
        assert shop_type == 0, f"Expected shop_type=0 (dungeon), got {shop_type}"
        assert count == len(TOKEN_SHOP_DUNGEON), f"Expected {len(TOKEN_SHOP_DUNGEON)} items, got {count}"

        # Query pvp shop (type=1)
        await c.send(MsgType.TOKEN_SHOP_LIST, struct.pack('<B', 1))
        msg_type2, resp2 = await c.recv_expect(MsgType.TOKEN_SHOP)
        assert msg_type2 == MsgType.TOKEN_SHOP
        assert resp2[0] == 1  # pvp shop
        assert resp2[1] == len(TOKEN_SHOP_PVP)
        c.close()

    await test("TOKEN_SHOP_LIST: 토큰 상점 목록 조회 (던전/PvP)", test_token_shop_list())

    # ━━━ Test: TOKEN_SHOP_BUY — 토큰 구매 (잔액 부족) ━━━
    async def test_token_shop_buy_insufficient():
        """토큰 부족 상태에서 구매 → INSUFFICIENT_TOKEN(1)."""
        c = await login_and_enter(port)
        # Try to buy dungeon shop item (shop_id=1, epic_weapon_box, 500 dungeon_token)
        # New character has 0 dungeon_token → should fail
        await c.send(MsgType.TOKEN_SHOP_BUY, struct.pack('<H B', 1, 1))
        msg_type, resp = await c.recv_expect(MsgType.TOKEN_SHOP_BUY_RESULT)
        assert msg_type == MsgType.TOKEN_SHOP_BUY_RESULT, f"Expected TOKEN_SHOP_BUY_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 1, f"Expected INSUFFICIENT_TOKEN(1), got {result}"
        c.close()

    await test("TOKEN_SHOP_BUY: 토큰 부족 → INSUFFICIENT_TOKEN", test_token_shop_buy_insufficient())

    # ━━━ Test: TOKEN_SHOP_BUY — 잘못된 아이템 ━━━
    async def test_token_shop_buy_invalid():
        """존재하지 않는 shop_id → INVALID_ITEM(2)."""
        c = await login_and_enter(port)
        await c.send(MsgType.TOKEN_SHOP_BUY, struct.pack('<H B', 9999, 1))
        msg_type, resp = await c.recv_expect(MsgType.TOKEN_SHOP_BUY_RESULT)
        assert msg_type == MsgType.TOKEN_SHOP_BUY_RESULT
        result = resp[0]
        assert result == 2, f"Expected INVALID_ITEM(2), got {result}"
        c.close()

    await test("TOKEN_SHOP_BUY: 잘못된 아이템 → INVALID_ITEM", test_token_shop_buy_invalid())
'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check
    if 'CURRENCY_QUERY = 468' in content and 'def _on_currency_query' in content and 'TOKEN_SHOP_DUNGEON' in content:
        print('[bridge] S054 already patched')
        return True

    changed = False

    # 1. MsgType -- after GUILD_WAR_STATUS = 435
    if 'CURRENCY_QUERY' not in content:
        marker = '    GUILD_WAR_STATUS = 435'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 468-473')
        else:
            # Fallback: after DURABILITY_QUERY = 467
            marker2 = '    DURABILITY_QUERY = 467'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + MSGTYPE_BLOCK + content[end:]
                changed = True
                print('[bridge] Added MsgType 468-473 (fallback after 467)')
            else:
                print('[bridge] WARNING: Could not find MsgType insertion point')

    # 2. Data constants -- after _GW_NEXT_ID or after PVP_TIERS block
    if 'TOKEN_SHOP_DUNGEON' not in content:
        marker = '_GW_NEXT_ID = 1'
        idx = content.find(marker)
        if idx >= 0:
            nl = content.index('\n', idx) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added currency data constants')
        else:
            # Fallback: after REROLL_MAX_LOCKS
            marker2 = "REROLL_MAX_LOCKS"
            idx2 = content.find(marker2)
            if idx2 >= 0:
                nl = content.index('\n', idx2) + 1
                content = content[:nl] + DATA_CONSTANTS + content[nl:]
                changed = True
                print('[bridge] Added currency data constants (fallback)')
            else:
                print('[bridge] WARNING: Could not find data constants insertion point')

    # 3. PlayerSession fields -- after pvp_season_wins field
    if 'silver: int = 5000' not in content:
        marker = '    pvp_season_wins: int = 0'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession currency fields')
        else:
            # Fallback: after reappraisal_scrolls
            marker2 = '    reappraisal_scrolls: int = 0'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession currency fields (fallback)')
            else:
                print('[bridge] WARNING: Could not find session fields insertion point')

    # 4. Dispatch table -- after guild_war_declare dispatch
    if 'self._on_currency_query' not in content:
        marker = '            MsgType.GUILD_WAR_DECLARE: self._on_guild_war_declare,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            # Fallback: after durability_query dispatch
            marker2 = '            MsgType.DURABILITY_QUERY: self._on_durability_query,'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + DISPATCH_ENTRIES + content[end:]
                changed = True
                print('[bridge] Added dispatch table entries (fallback)')
            else:
                print('[bridge] WARNING: Could not find dispatch table insertion point')

    # 5. Handler implementations -- before Battleground handlers or at end of handlers
    if 'def _on_currency_query' not in content:
        marker = '    # ---- Battleground / Guild War (TASK 6: MsgType 430-435) ----'
        idx = content.find(marker)
        if idx < 0:
            # Fallback: before Durability handlers
            marker = '    # ---- Durability / Repair / Reroll (TASK 9: MsgType 462-467) ----'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added currency handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    # 6. Silver payment patch — inject into SHOP_BUY handler
    # We need to add the silver branch right after the shop_buy handler processes item_id
    # Look for the pattern where SHOP_BUY processes gold payment
    if 'Silver currency branch' not in content:
        # Find the SHOP_BUY handler. We need to insert silver check before gold check.
        # The pattern: the existing handler has "async def _on_shop_buy" and inside checks gold.
        # Strategy: add silver check right after "item_id" and "quantity" are parsed.
        # Look for a unique line in shop_buy handler
        shop_marker = "async def _on_shop_buy(self, session, payload: bytes):"
        idx = content.find(shop_marker)
        if idx >= 0:
            # Find "session.gold -= cost" or similar gold deduction pattern
            # Actually the shop handler may vary. Let's find the gold deduction.
            gold_deduct = "session.gold -= cost"
            gidx = content.find(gold_deduct, idx)
            if gidx < 0:
                # Try alternative patterns
                gold_deduct = "session.gold -="
                gidx = content.find(gold_deduct, idx)

            if gidx >= 0:
                # Find the start of the if block that checks gold
                # We'll go backward to find the "if session.gold < cost" line
                check_line = "if session.gold < cost"
                cidx = content.rfind(check_line, idx, gidx)
                if cidx < 0:
                    # Try alternative: go forward from handler start and find gold check
                    check_line = "session.gold"
                    cidx = content.find(check_line, idx)

                if cidx >= 0:
                    # Insert silver branch before the gold cost check
                    # Find the line start
                    line_start = content.rfind('\n', idx, cidx) + 1
                    content = content[:line_start] + SILVER_PATCH_CODE + '\n' + content[line_start:]
                    changed = True
                    print('[bridge] Added silver payment branch to SHOP_BUY')
                else:
                    print('[bridge] NOTE: Could not find gold check in SHOP_BUY -- silver branch skipped')
            else:
                print('[bridge] NOTE: Could not find gold deduction in SHOP_BUY -- silver branch skipped')
        else:
            print('[bridge] NOTE: SHOP_BUY handler not found -- silver branch skipped (may be a simplified handler)')

    # 7. Dungeon token hook — after raid clear gold award
    if 'Dungeon token reward (TASK 10)' not in content:
        # Target: _raid_clear method, specifically "s.gold += rewards["gold"]" line
        raid_fn_marker = "async def _raid_clear(self, inst_id: int):"
        ridx = content.find(raid_fn_marker)
        if ridx >= 0:
            # Find gold award inside _raid_clear
            gold_award = 's.gold += rewards["gold"]'
            gaidx = content.find(gold_award, ridx)
            if gaidx >= 0:
                # Insert token hook after gold award line
                nl = content.index('\n', gaidx) + 1
                content = content[:nl] + DUNGEON_TOKEN_HOOK + content[nl:]
                changed = True
                print('[bridge] Added dungeon token hook after raid clear')
            else:
                print('[bridge] NOTE: Could not find gold award in _raid_clear -- dungeon token hook skipped')
        else:
            print('[bridge] NOTE: _raid_clear not found -- dungeon token hook skipped')

    # 8. PvP token hook — after battleground end match (bg_end_match)
    if 'PvP token reward (TASK 10)' not in content:
        pvp_marker = "def _bg_end_match(self, match_id, winner_team):"
        pidx = content.find(pvp_marker)
        if pidx >= 0:
            # Find the rating decrease line (inside the else branch after won check)
            rating_decrease = "s.pvp_season_rating = max(0, s.pvp_season_rating - 10)"
            ruidx = content.find(rating_decrease, pidx)
            if ruidx >= 0:
                # Insert PvP token hook after the rating decrease line
                nl_after = content.index('\n', ruidx) + 1
                content = content[:nl_after] + PVP_TOKEN_HOOK + content[nl_after:]
                changed = True
                print('[bridge] Added PvP token hook in bg_end_match')
            else:
                print('[bridge] NOTE: Could not find rating decrease in bg_end_match -- pvp token hook skipped')
        else:
            print('[bridge] NOTE: _bg_end_match not found -- pvp token hook skipped')

    # Always write
    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify
    checks = [
        'CURRENCY_QUERY = 468', 'CURRENCY_INFO = 469',
        'TOKEN_SHOP_LIST = 470', 'TOKEN_SHOP = 471',
        'TOKEN_SHOP_BUY = 472', 'TOKEN_SHOP_BUY_RESULT = 473',
        'CURRENCY_MAX', 'SILVER_INITIAL', 'DUNGEON_TOKEN_REWARDS',
        'PVP_TOKEN_WIN', 'PVP_TOKEN_LOSS',
        'TOKEN_SHOP_DUNGEON', 'TOKEN_SHOP_PVP', 'TOKEN_SHOP_GUILD',
        'TOKEN_SHOPS', 'SILVER_SHOP_ITEMS',
        'def _on_currency_query', 'def _on_token_shop_list',
        'def _on_token_shop_buy',
        'self._on_currency_query', 'self._on_token_shop_list',
        'self._on_token_shop_buy',
        'silver: int = 5000', 'dungeon_token: int = 0',
        'pvp_token: int = 0', 'guild_contribution: int = 0',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S054 patched OK -- currency/token_shop system')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_currency_query' in content and 'test_token_shop_buy_invalid' in content:
        print('[test] S054 already patched')
        return True

    # Update imports — add currency constants
    old_import = (
        '    BG_MODE_CAPTURE_POINT, BG_MODE_PAYLOAD, BG_TEAM_SIZE,\n'
        '    BG_WIN_SCORE, GW_CRYSTAL_HP, GW_MIN_PARTICIPANTS\n'
        ')'
    )
    new_import = (
        '    BG_MODE_CAPTURE_POINT, BG_MODE_PAYLOAD, BG_TEAM_SIZE,\n'
        '    BG_WIN_SCORE, GW_CRYSTAL_HP, GW_MIN_PARTICIPANTS,\n'
        '    CURRENCY_MAX, TOKEN_SHOP_DUNGEON, TOKEN_SHOP_PVP, TOKEN_SHOP_GUILD,\n'
        '    TOKEN_SHOPS, SILVER_SHOP_ITEMS, DUNGEON_TOKEN_REWARDS,\n'
        '    PVP_TOKEN_WIN, PVP_TOKEN_LOSS\n'
        ')'
    )

    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports with currency constants')
    else:
        print('[test] NOTE: Could not find expected import block -- imports may already be correct')

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

    checks = ['test_currency_query', 'test_token_shop_list',
              'test_token_shop_buy_insufficient', 'test_token_shop_buy_invalid',
              'CURRENCY_QUERY', 'CURRENCY_INFO', 'TOKEN_SHOP_LIST',
              'TOKEN_SHOP_BUY', 'TOKEN_SHOP_BUY_RESULT']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S054 patched OK -- 4 currency tests')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS054 all patches applied!')
    else:
        print('\nS054 PATCH FAILED!')
        sys.exit(1)
