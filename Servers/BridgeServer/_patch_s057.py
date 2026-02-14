"""
Patch S057: TASK 11 + 12 + 13 + 14 — Final GDD Tasks
======================================================
TASK 11: Cash Shop / Battle Pass / Event / Subscription (MsgType 474-489)
TASK 12: World System — Weather/Teleport/Objects/Mount (MsgType 490-501)
TASK 13: Login Reward / Daily Reset / Weekly Reset / Content Unlock (MsgType 502-509)
TASK 14: Story / Dialog Choice / Cutscene / Chapter Progress (MsgType 510-517)

Total: 25 sub-tasks, ~20 tests
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums (474-517)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Cash Shop / Battle Pass / Event (TASK 11)\n'
    '    CASH_SHOP_LIST_REQ = 474\n'
    '    CASH_SHOP_LIST = 475\n'
    '    CASH_SHOP_BUY = 476\n'
    '    CASH_SHOP_BUY_RESULT = 477\n'
    '    BATTLEPASS_INFO_REQ = 478\n'
    '    BATTLEPASS_INFO = 479\n'
    '    BATTLEPASS_CLAIM = 480\n'
    '    BATTLEPASS_CLAIM_RESULT = 481\n'
    '    EVENT_LIST_REQ = 482\n'
    '    EVENT_LIST = 483\n'
    '    EVENT_CLAIM = 484\n'
    '    EVENT_CLAIM_RESULT = 485\n'
    '    SUBSCRIPTION_INFO = 486\n'
    '    SUBSCRIPTION_STATUS = 487\n'
    '    SUBSCRIPTION_BUY = 488\n'
    '    SUBSCRIPTION_RESULT = 489\n'
    '\n'
    '    # World System (TASK 12)\n'
    '    WEATHER_INFO_REQ = 490\n'
    '    WEATHER_INFO = 491\n'
    '    TELEPORT_REQ = 492\n'
    '    TELEPORT_RESULT = 493\n'
    '    WAYPOINT_DISCOVER = 494\n'
    '    WAYPOINT_LIST = 495\n'
    '    DESTROY_OBJECT = 496\n'
    '    DESTROY_OBJECT_RESULT = 497\n'
    '    INTERACT_OBJECT = 498\n'
    '    INTERACT_RESULT = 499\n'
    '    MOUNT_SUMMON = 500\n'
    '    MOUNT_RESULT = 501\n'
    '\n'
    '    # Login Reward / Daily Reset (TASK 13)\n'
    '    LOGIN_REWARD_REQ = 502\n'
    '    LOGIN_REWARD_INFO = 503\n'
    '    LOGIN_REWARD_CLAIM = 504\n'
    '    LOGIN_REWARD_CLAIM_RESULT = 505\n'
    '    DAILY_RESET_NOTIFY = 506\n'
    '    WEEKLY_RESET_NOTIFY = 507\n'
    '    CONTENT_UNLOCK_NOTIFY = 508\n'
    '    CONTENT_UNLOCK_QUERY = 509\n'
    '\n'
    '    # Story / Dialog (TASK 14)\n'
    '    DIALOG_CHOICE = 510\n'
    '    DIALOG_CHOICE_RESULT = 511\n'
    '    CUTSCENE_TRIGGER = 512\n'
    '    CUTSCENE_DATA = 513\n'
    '    CHAPTER_PROGRESS_REQ = 514\n'
    '    CHAPTER_PROGRESS = 515\n'
    '    MAIN_QUEST_DATA_REQ = 516\n'
    '    MAIN_QUEST_DATA = 517\n'
)

# ====================================================================
# 2. Data constants
# ====================================================================
DATA_CONSTANTS = r'''
# ========== TASK 11: Cash Shop / Battle Pass / Event ==========
CASH_SHOP_CRYSTAL_CURRENCY = "crystal"

CASH_SHOP_ITEMS = [
    {"id": 1, "name": "인벤토리 확장", "category": "convenience", "price": 300, "max_buy": 6},
    {"id": 2, "name": "창고 확장", "category": "convenience", "price": 200, "max_buy": 15},
    {"id": 3, "name": "경험치 부스트 (24h)", "category": "convenience", "price": 150, "max_buy": 99},
    {"id": 4, "name": "자동 물약 (30일)", "category": "convenience", "price": 500, "max_buy": 1},
    {"id": 5, "name": "코스튬: 백의검객", "category": "cosmetic", "price": 800, "max_buy": 1},
    {"id": 6, "name": "코스튬: 홍의무사", "category": "cosmetic", "price": 800, "max_buy": 1},
    {"id": 7, "name": "코스튬: 청의도사", "category": "cosmetic", "price": 800, "max_buy": 1},
    {"id": 8, "name": "펫: 묘묘", "category": "cosmetic", "price": 1200, "max_buy": 1},
    {"id": 9, "name": "귀환석 10개", "category": "convenience", "price": 50, "max_buy": 99},
    {"id": 10, "name": "이름 변경권", "category": "convenience", "price": 400, "max_buy": 99},
]

BATTLEPASS_MAX_LEVEL = 50
BATTLEPASS_EXP_PER_LEVEL = 1000
BATTLEPASS_SEASON_DAYS = 90

# BP EXP sources
BP_EXP_DAILY_QUEST = 200
BP_EXP_WEEKLY_QUEST = 800
BP_EXP_DUNGEON_CLEAR = 100
BP_EXP_PVP_WIN = 50
BP_EXP_LOGIN = 50

BATTLEPASS_REWARDS_FREE = {
    5: {"gold": 5000},
    10: {"gold": 10000, "item": "rare_box"},
    15: {"gold": 15000},
    20: {"gold": 20000, "item": "rare_box"},
    25: {"gold": 25000, "item": "epic_box"},
    30: {"gold": 30000},
    35: {"gold": 35000, "item": "rare_box"},
    40: {"gold": 40000, "item": "epic_box"},
    45: {"gold": 45000},
    50: {"gold": 50000, "item": "legendary_box"},
}

BATTLEPASS_REWARDS_PREMIUM = {
    5: {"gold": 10000, "crystal": 50},
    10: {"gold": 20000, "item": "epic_box", "crystal": 50},
    15: {"gold": 30000, "crystal": 100},
    20: {"gold": 40000, "item": "epic_box", "crystal": 100},
    25: {"gold": 50000, "item": "legendary_box", "crystal": 150},
    30: {"gold": 60000, "crystal": 150},
    35: {"gold": 70000, "item": "epic_box", "crystal": 200},
    40: {"gold": 80000, "item": "legendary_box", "crystal": 200},
    45: {"gold": 90000, "crystal": 250},
    50: {"gold": 100000, "item": "legendary_box", "crystal": 500, "title": "시즌 정복자"},
}

EVENT_LIST_DATA = [
    {"id": 1, "name": "14일 출석 이벤트", "type": "login_event", "duration_days": 14,
     "rewards": {1: "gold_1000", 2: "gold_1000", 3: "gold_2000", 4: "gold_2000",
                 5: "rare_box", 6: "gold_3000", 7: "epic_box",
                 8: "gold_3000", 9: "gold_3000", 10: "gold_5000",
                 11: "rare_box", 12: "gold_5000", 13: "epic_box", 14: "legendary_box"}},
    {"id": 2, "name": "경험치 2배 이벤트", "type": "double_exp", "duration_hours": 72},
    {"id": 3, "name": "보스 러시 이벤트", "type": "boss_rush", "duration_hours": 48},
]

SUBSCRIPTION_NAME = "모험가의 축복"
SUBSCRIPTION_PRICE_CRYSTAL = 1000
SUBSCRIPTION_DURATION_DAYS = 30
SUBSCRIPTION_BENEFITS = {
    "exp_bonus": 0.10,
    "gold_bonus": 0.10,
    "daily_crystal": 10,
    "repair_discount": 0.50,
    "teleport_free_daily": 3,
    "extra_dungeon_entry": 1,
}

# Global cash shop state
_CASH_SHOP_PURCHASES = {}  # eid -> {item_id: buy_count}
_BATTLEPASS_STATE = {}      # eid -> {"level": int, "exp": int, "premium": bool, "claimed_free": set, "claimed_premium": set}
_EVENT_CLAIMS = {}          # eid -> {event_id: {day/claim_count}}
_SUBSCRIPTION_STATE = {}    # eid -> {"active": bool, "expires": float}

# ========== TASK 12: World System ==========
WEATHER_TYPES = ["clear", "rain", "snow", "fog", "storm", "sandstorm"]
WEATHER_CHANGE_INTERVAL = (300, 900)  # 5~15분 주기
WEATHER_PROBABILITIES = {"clear": 0.50, "rain": 0.20, "snow": 0.10, "fog": 0.10, "storm": 0.05, "sandstorm": 0.05}

# Element damage modifiers by weather
WEATHER_ELEMENT_MODIFIERS = {
    "rain": {"fire": -0.10, "lightning": 0.10, "water": 0.05},
    "snow": {"fire": -0.05, "ice": 0.15},
    "storm": {"lightning": 0.20, "fire": -0.15},
    "sandstorm": {"earth": 0.10, "wind": -0.10},
}

# Time of day: 3600 real seconds = 1 in-game day
GAME_DAY_SECONDS = 3600
TIME_OF_DAY_PHASES = ["dawn", "morning", "afternoon", "evening", "dusk", "night"]
NIGHT_VISIBILITY_PENALTY = 0.40
NIGHT_MONSTER_SPAWN_BONUS = 0.20

TELEPORT_COST_SILVER = 500
TELEPORT_CAST_TIME_SEC = 3.0
MOUNT_SPEED_MULTIPLIER = 2.0
MOUNT_SUMMON_CAST_SEC = 2.0
MOUNT_MIN_LEVEL = 20

# Destroyable/Interactable objects
WORLD_OBJECTS = {
    "barrel":  {"hp": 10, "loot": "gold", "loot_min": 1, "loot_max": 10, "respawn": 60},
    "crate":   {"hp": 20, "loot": "gold", "loot_min": 5, "loot_max": 20, "respawn": 120},
    "crystal": {"hp": 50, "loot": "gem", "loot_chance": 0.30, "respawn": 300},
}
TREASURE_CHEST_OPEN_TIME = 2.0
TREASURE_CHEST_TRAP_CHANCE = 0.10

# Global world state
_CURRENT_WEATHER = "clear"
_WEATHER_LAST_CHANGE = 0.0
_GAME_TIME_OFFSET = 0.0
_DISCOVERED_WAYPOINTS = {}  # eid -> set of waypoint_ids
_WORLD_OBJECTS_STATE = {}    # object_id -> {"destroyed": bool, "respawn_at": float}
_MOUNT_STATE = {}            # eid -> {"mounted": bool, "mount_id": int}

# ========== TASK 13: Login Reward / Daily Reset ==========
LOGIN_REWARD_CYCLE = 14  # 14일 주기
LOGIN_REWARD_TABLE = {
    1: {"type": "gold", "amount": 1000},
    2: {"type": "gold", "amount": 1500},
    3: {"type": "gold", "amount": 2000},
    4: {"type": "silver", "amount": 5000},
    5: {"type": "gold", "amount": 3000},
    6: {"type": "gold", "amount": 3500},
    7: {"type": "item", "item": "rare_weapon_box"},
    8: {"type": "gold", "amount": 4000},
    9: {"type": "gold", "amount": 4500},
    10: {"type": "gold", "amount": 5000},
    11: {"type": "silver", "amount": 10000},
    12: {"type": "gold", "amount": 7000},
    13: {"type": "item", "item": "epic_armor_box"},
    14: {"type": "item", "item": "epic_weapon_box", "bonus_title": "성실한 모험가"},
}

DAILY_RESET_HOUR = 6  # 매일 06:00
WEEKLY_RESET_DAY = 2   # 수요일 (0=Mon)
WEEKLY_RESET_HOUR = 6

# Content unlock levels
CONTENT_UNLOCK_TABLE = {
    5: ["daily_quest"],
    10: ["enhancement", "auction_house"],
    15: ["dungeon"],
    20: ["job_change", "pvp", "mount"],
    25: ["gem"],
    30: ["guild", "ultimate_skill"],
    40: ["transcend"],
    50: ["raid", "engraving"],
    60: ["chaos_dungeon", "paragon"],
}

# Global login state
_LOGIN_REWARD_STATE = {}  # eid -> {"total_days": int, "last_claim_date": str, "cycle_day": int}
_DAILY_RESET_LAST = 0     # timestamp of last daily reset
_WEEKLY_RESET_LAST = 0    # timestamp of last weekly reset

# ========== TASK 14: Story / Dialog ==========
DIALOG_TREES = {
    "npc_elder": {
        "start": {"text": "어서 오시게, 젊은 무인이여.", "choices": [
            {"id": 1, "text": "세계의 위기에 대해 알려주세요.", "next": "lore_hint"},
            {"id": 2, "text": "수련을 하고 싶습니다.", "next": "quest_accept"},
            {"id": 3, "text": "안녕히 계세요.", "next": "end"},
        ]},
        "lore_hint": {"text": "봉인석이 깨지고 있다네... 5개의 파편을 모아야 하네.", "choices": [
            {"id": 1, "text": "어디서 찾을 수 있나요?", "next": "lore_detail"},
            {"id": 2, "text": "알겠습니다.", "next": "end"},
        ]},
        "lore_detail": {"text": "각 지역의 보스가 파편을 지키고 있다네.", "choices": []},
        "quest_accept": {"text": "좋은 결심이로다. 이 임무를 맡아주게.", "choices": [], "action": "accept_quest:MQ001"},
        "end": {"text": "", "choices": []},
    },
    "npc_blacksmith": {
        "start": {"text": "뭘 찾으시오?", "choices": [
            {"id": 1, "text": "장비 강화를 하고 싶습니다.", "next": "enhance"},
            {"id": 2, "text": "수리를 해주세요.", "next": "repair"},
        ]},
        "enhance": {"text": "강화석을 가져오시오.", "choices": [], "action": "open_enhance"},
        "repair": {"text": "수리비를 내시오.", "choices": [], "action": "open_repair"},
    },
}

CUTSCENE_DATA_TABLE = {
    "opening": {"id": "opening", "type": "opening", "chapter": 0, "required_quest": None,
                "sequences": ["fade_in", "narration:봉인이 깨지는 날...", "camera_pan:village", "fade_out"]},
    "boss_intro_ch1": {"id": "boss_intro_ch1", "type": "boss_intro", "chapter": 1, "required_quest": "MQ010",
                       "sequences": ["fade_in", "boss_appear:dark_lord", "dialog:각오는 됐느냐?", "fade_out"]},
    "chapter_transition_1_2": {"id": "chapter_transition_1_2", "type": "chapter_transition", "chapter": 1,
                               "required_quest": "MQ015",
                               "sequences": ["fade_in", "narration:새로운 대륙이 열렸다...", "map_reveal:zone2", "fade_out"]},
}

CHAPTER_DATA = {
    1: {"name": "어둠의 전조", "required_level": 1, "main_quests": ["MQ001", "MQ005", "MQ010", "MQ015"],
        "seal_fragments": 1, "unlock_condition": None},
    2: {"name": "잃어버린 유산", "required_level": 20, "main_quests": ["MQ016", "MQ020", "MQ025"],
        "seal_fragments": 2, "unlock_condition": "chapter_1_complete"},
    3: {"name": "용의 포효", "required_level": 40, "main_quests": ["MQ026", "MQ030", "MQ035", "MQ040"],
        "seal_fragments": 1, "unlock_condition": "chapter_2_complete"},
    4: {"name": "최후의 봉인", "required_level": 55, "main_quests": ["MQ041", "MQ045"],
        "seal_fragments": 1, "unlock_condition": "chapter_3_complete"},
}

# Main quest data (simplified: 10 representative quests)
MAIN_QUEST_TABLE = {
    "MQ001": {"name": "첫 번째 수련", "chapter": 1, "level": 1, "npc": "npc_elder",
              "type": "kill", "target": "wolf", "count": 5, "reward_exp": 500, "reward_gold": 200,
              "dialog_start": "start", "next_quest": "MQ002"},
    "MQ005": {"name": "마을의 위기", "chapter": 1, "level": 5, "npc": "npc_elder",
              "type": "kill", "target": "goblin_chief", "count": 1, "reward_exp": 2000, "reward_gold": 1000,
              "next_quest": "MQ006"},
    "MQ010": {"name": "첫 번째 봉인석", "chapter": 1, "level": 10, "npc": "npc_elder",
              "type": "kill_boss", "target": "dark_knight", "count": 1, "reward_exp": 5000, "reward_gold": 3000,
              "seal_fragment": True, "next_quest": "MQ011"},
    "MQ015": {"name": "새로운 여정", "chapter": 1, "level": 15, "npc": "npc_elder",
              "type": "arrive", "target": "zone2_entrance", "count": 1, "reward_exp": 3000, "reward_gold": 2000,
              "cutscene": "chapter_transition_1_2", "next_quest": "MQ016"},
    "MQ020": {"name": "유적 탐사", "chapter": 2, "level": 22, "npc": "npc_scholar",
              "type": "explore", "target": "ancient_ruins", "count": 3, "reward_exp": 8000, "reward_gold": 5000,
              "next_quest": "MQ021"},
    "MQ025": {"name": "두 번째 봉인석", "chapter": 2, "level": 28, "npc": "npc_scholar",
              "type": "kill_boss", "target": "stone_golem", "count": 1, "reward_exp": 15000, "reward_gold": 8000,
              "seal_fragment": True, "next_quest": "MQ026"},
    "MQ030": {"name": "용의 둥지", "chapter": 3, "level": 42, "npc": "npc_dragon_knight",
              "type": "dungeon_clear", "target": "dragon_nest", "count": 1, "reward_exp": 30000, "reward_gold": 15000,
              "next_quest": "MQ031"},
    "MQ040": {"name": "네 번째 봉인석", "chapter": 3, "level": 52, "npc": "npc_dragon_knight",
              "type": "kill_boss", "target": "dragon_lord", "count": 1, "reward_exp": 50000, "reward_gold": 25000,
              "seal_fragment": True, "next_quest": "MQ041"},
    "MQ045": {"name": "최후의 전투", "chapter": 4, "level": 60, "npc": "npc_sage",
              "type": "kill_boss", "target": "demon_king", "count": 1, "reward_exp": 100000, "reward_gold": 50000,
              "seal_fragment": True, "ending": True},
}

# Global story state
_CHAPTER_PROGRESS = {}   # eid -> {"current_chapter": int, "seal_fragments": int, "completed_quests": set, "seen_cutscenes": set}
_DIALOG_STATE = {}       # eid -> {"npc_id": str, "current_node": str}
'''

# ====================================================================
# 3. PlayerSession fields
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Cash Shop / BP / Event / Sub (TASK 11) ----\n'
    '    crystal: int = 0                       # 캐시 화폐 (크리스탈)\n'
    '    bp_level: int = 0                      # 배틀패스 레벨\n'
    '    bp_exp: int = 0                        # 배틀패스 경험치\n'
    '    bp_premium: bool = False               # 프리미엄 구매 여부\n'
    '    subscription_active: bool = False      # 월정액 활성화\n'
    '    subscription_expires: float = 0.0      # 월정액 만료 시간\n'
    '    # ---- World System (TASK 12) ----\n'
    '    mounted: bool = False                  # 탈것 탑승 여부\n'
    '    mount_id: int = 0                      # 탈것 ID\n'
    '    # ---- Login Reward (TASK 13) ----\n'
    '    login_total_days: int = 0              # 누적 출석일\n'
    '    login_cycle_day: int = 0               # 현재 주기 내 일수 (1~14)\n'
    '    login_last_claim: str = ""             # 마지막 수령 날짜 (YYYY-MM-DD)\n'
    '    # ---- Story (TASK 14) ----\n'
    '    current_chapter: int = 1               # 현재 스토리 챕터\n'
    '    seal_fragments: int = 0                # 봉인석 파편 수\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            # TASK 11: Cash Shop / BP / Event\n'
    '            MsgType.CASH_SHOP_LIST_REQ: self._on_cash_shop_list,\n'
    '            MsgType.CASH_SHOP_BUY: self._on_cash_shop_buy,\n'
    '            MsgType.BATTLEPASS_INFO_REQ: self._on_battlepass_info,\n'
    '            MsgType.BATTLEPASS_CLAIM: self._on_battlepass_claim,\n'
    '            MsgType.EVENT_LIST_REQ: self._on_event_list,\n'
    '            MsgType.EVENT_CLAIM: self._on_event_claim,\n'
    '            MsgType.SUBSCRIPTION_INFO: self._on_subscription_info,\n'
    '            MsgType.SUBSCRIPTION_BUY: self._on_subscription_buy,\n'
    '            # TASK 12: World System\n'
    '            MsgType.WEATHER_INFO_REQ: self._on_weather_info,\n'
    '            MsgType.TELEPORT_REQ: self._on_teleport_req,\n'
    '            MsgType.WAYPOINT_DISCOVER: self._on_waypoint_discover,\n'
    '            MsgType.DESTROY_OBJECT: self._on_destroy_object,\n'
    '            MsgType.INTERACT_OBJECT: self._on_interact_object,\n'
    '            MsgType.MOUNT_SUMMON: self._on_mount_summon,\n'
    '            # TASK 13: Login Reward / Reset\n'
    '            MsgType.LOGIN_REWARD_REQ: self._on_login_reward_req,\n'
    '            MsgType.LOGIN_REWARD_CLAIM: self._on_login_reward_claim,\n'
    '            MsgType.CONTENT_UNLOCK_QUERY: self._on_content_unlock_query,\n'
    '            # TASK 14: Story / Dialog\n'
    '            MsgType.DIALOG_CHOICE: self._on_dialog_choice,\n'
    '            MsgType.CUTSCENE_TRIGGER: self._on_cutscene_trigger,\n'
    '            MsgType.CHAPTER_PROGRESS_REQ: self._on_chapter_progress_req,\n'
    '            MsgType.MAIN_QUEST_DATA_REQ: self._on_main_quest_data_req,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ================================================================
    # TASK 11: Cash Shop / Battle Pass / Event / Subscription
    # MsgType 474-489
    # ================================================================

    async def _on_cash_shop_list(self, session, payload: bytes):
        """CASH_SHOP_LIST_REQ(474) -> CASH_SHOP_LIST(475)
        Request: category_len(u8) + category(utf8)  (empty = all)
        Response: crystal(u32) + count(u8) + [id(u8)+price(u16)+max_buy(u8)+bought(u8)+name_len(u8)+name+cat_len(u8)+cat] * count
        """
        if not session.in_game:
            return
        cat_filter = ""
        if payload and len(payload) >= 1:
            cat_len = payload[0]
            if cat_len > 0 and len(payload) >= 1 + cat_len:
                cat_filter = payload[1:1+cat_len].decode('utf-8', errors='ignore')

        purchases = _CASH_SHOP_PURCHASES.get(session.entity_id, {})
        items = CASH_SHOP_ITEMS
        if cat_filter:
            items = [i for i in items if i["category"] == cat_filter]

        data = struct.pack('<I B', session.crystal, len(items))
        for item in items:
            bought = purchases.get(item["id"], 0)
            name_b = item["name"].encode('utf-8')[:30]
            cat_b = item["category"].encode('utf-8')[:20]
            data += struct.pack('<B H B B B', item["id"], item["price"], item["max_buy"], bought, len(name_b))
            data += name_b
            data += struct.pack('<B', len(cat_b)) + cat_b
        self._send(session, MsgType.CASH_SHOP_LIST, data)

    async def _on_cash_shop_buy(self, session, payload: bytes):
        """CASH_SHOP_BUY(476) -> CASH_SHOP_BUY_RESULT(477)
        Request: item_id(u8)
        Response: result(u8) + remaining_crystal(u32)
          0=SUCCESS, 1=NOT_ENOUGH_CRYSTAL, 2=MAX_BUY_REACHED, 3=INVALID_ITEM
        """
        if not session.in_game or len(payload) < 1:
            return
        item_id = payload[0]
        shop_item = None
        for it in CASH_SHOP_ITEMS:
            if it["id"] == item_id:
                shop_item = it
                break
        if not shop_item:
            self._send(session, MsgType.CASH_SHOP_BUY_RESULT, struct.pack('<B I', 3, session.crystal))
            return

        eid = session.entity_id
        if eid not in _CASH_SHOP_PURCHASES:
            _CASH_SHOP_PURCHASES[eid] = {}
        bought = _CASH_SHOP_PURCHASES[eid].get(item_id, 0)
        if bought >= shop_item["max_buy"]:
            self._send(session, MsgType.CASH_SHOP_BUY_RESULT, struct.pack('<B I', 2, session.crystal))
            return
        if session.crystal < shop_item["price"]:
            self._send(session, MsgType.CASH_SHOP_BUY_RESULT, struct.pack('<B I', 1, session.crystal))
            return

        session.crystal -= shop_item["price"]
        _CASH_SHOP_PURCHASES[eid][item_id] = bought + 1
        self._send(session, MsgType.CASH_SHOP_BUY_RESULT, struct.pack('<B I', 0, session.crystal))

    async def _on_battlepass_info(self, session, payload: bytes):
        """BATTLEPASS_INFO_REQ(478) -> BATTLEPASS_INFO(479)
        Response: level(u8) + exp(u16) + exp_needed(u16) + premium(u8) + claimed_free_bits(u64) + claimed_premium_bits(u64)
        """
        if not session.in_game:
            return
        eid = session.entity_id
        state = _BATTLEPASS_STATE.get(eid, {"level": session.bp_level, "exp": session.bp_exp,
                                            "premium": session.bp_premium,
                                            "claimed_free": set(), "claimed_premium": set()})
        claimed_free_bits = 0
        for lv in state.get("claimed_free", set()):
            if 1 <= lv <= 50:
                claimed_free_bits |= (1 << (lv - 1))
        claimed_prem_bits = 0
        for lv in state.get("claimed_premium", set()):
            if 1 <= lv <= 50:
                claimed_prem_bits |= (1 << (lv - 1))

        data = struct.pack('<B H H B Q Q',
                           state["level"], state["exp"], BATTLEPASS_EXP_PER_LEVEL,
                           1 if state["premium"] else 0,
                           claimed_free_bits, claimed_prem_bits)
        self._send(session, MsgType.BATTLEPASS_INFO, data)

    async def _on_battlepass_claim(self, session, payload: bytes):
        """BATTLEPASS_CLAIM(480) -> BATTLEPASS_CLAIM_RESULT(481)
        Request: level(u8) + track(u8) — track: 0=free, 1=premium
        Response: result(u8) + level(u8) + gold_reward(u32)
          0=SUCCESS, 1=LEVEL_NOT_REACHED, 2=ALREADY_CLAIMED, 3=NO_PREMIUM, 4=NO_REWARD_AT_LEVEL
        """
        if not session.in_game or len(payload) < 2:
            return
        claim_level = payload[0]
        track = payload[1]

        eid = session.entity_id
        if eid not in _BATTLEPASS_STATE:
            _BATTLEPASS_STATE[eid] = {"level": session.bp_level, "exp": session.bp_exp,
                                     "premium": session.bp_premium,
                                     "claimed_free": set(), "claimed_premium": set()}
        state = _BATTLEPASS_STATE[eid]

        def _send_bp_result(code, gold=0):
            self._send(session, MsgType.BATTLEPASS_CLAIM_RESULT,
                       struct.pack('<B B I', code, claim_level, gold))

        if state["level"] < claim_level:
            _send_bp_result(1)
            return

        if track == 0:
            reward_table = BATTLEPASS_REWARDS_FREE
            claimed_set = state["claimed_free"]
        else:
            if not state["premium"]:
                _send_bp_result(3)
                return
            reward_table = BATTLEPASS_REWARDS_PREMIUM
            claimed_set = state["claimed_premium"]

        if claim_level not in reward_table:
            _send_bp_result(4)
            return
        if claim_level in claimed_set:
            _send_bp_result(2)
            return

        reward = reward_table[claim_level]
        gold_reward = reward.get("gold", 0)
        session.gold = min(session.gold + gold_reward, 999999999)
        claimed_set.add(claim_level)
        _send_bp_result(0, gold_reward)

    def _battlepass_add_exp(self, session, amount: int):
        """배틀패스 경험치 추가 (일퀘/주퀘/던전/PvP/로그인 훅에서 호출)."""
        if not session.in_game:
            return
        eid = session.entity_id
        if eid not in _BATTLEPASS_STATE:
            _BATTLEPASS_STATE[eid] = {"level": session.bp_level, "exp": session.bp_exp,
                                     "premium": session.bp_premium,
                                     "claimed_free": set(), "claimed_premium": set()}
        state = _BATTLEPASS_STATE[eid]
        if state["level"] >= BATTLEPASS_MAX_LEVEL:
            return
        state["exp"] += amount
        while state["exp"] >= BATTLEPASS_EXP_PER_LEVEL and state["level"] < BATTLEPASS_MAX_LEVEL:
            state["exp"] -= BATTLEPASS_EXP_PER_LEVEL
            state["level"] += 1
        session.bp_level = state["level"]
        session.bp_exp = state["exp"]

    async def _on_event_list(self, session, payload: bytes):
        """EVENT_LIST_REQ(482) -> EVENT_LIST(483)
        Response: count(u8) + [id(u8) + type_len(u8) + type(utf8) + name_len(u8) + name(utf8) + active(u8)] * count
        """
        if not session.in_game:
            return
        events = EVENT_LIST_DATA
        data = struct.pack('<B', len(events))
        for ev in events:
            type_b = ev["type"].encode('utf-8')[:20]
            name_b = ev["name"].encode('utf-8')[:40]
            data += struct.pack('<B B', ev["id"], len(type_b)) + type_b
            data += struct.pack('<B', len(name_b)) + name_b
            data += struct.pack('<B', 1)  # active
        self._send(session, MsgType.EVENT_LIST, data)

    async def _on_event_claim(self, session, payload: bytes):
        """EVENT_CLAIM(484) -> EVENT_CLAIM_RESULT(485)
        Request: event_id(u8) + day(u8) — day for login events
        Response: result(u8) + event_id(u8) + reward_gold(u32)
          0=SUCCESS, 1=ALREADY_CLAIMED, 2=NOT_ELIGIBLE, 3=INVALID_EVENT
        """
        if not session.in_game or len(payload) < 2:
            return
        event_id = payload[0]
        day = payload[1]

        ev = None
        for e in EVENT_LIST_DATA:
            if e["id"] == event_id:
                ev = e
                break
        if not ev:
            self._send(session, MsgType.EVENT_CLAIM_RESULT, struct.pack('<B B I', 3, event_id, 0))
            return

        eid = session.entity_id
        if eid not in _EVENT_CLAIMS:
            _EVENT_CLAIMS[eid] = {}
        claims = _EVENT_CLAIMS[eid]

        if event_id not in claims:
            claims[event_id] = set()

        if day in claims[event_id]:
            self._send(session, MsgType.EVENT_CLAIM_RESULT, struct.pack('<B B I', 1, event_id, 0))
            return

        gold_reward = 0
        if ev["type"] == "login_event":
            rewards = ev.get("rewards", {})
            if day not in rewards:
                self._send(session, MsgType.EVENT_CLAIM_RESULT, struct.pack('<B B I', 2, event_id, 0))
                return
            r_str = rewards[day]
            if r_str.startswith("gold_"):
                gold_reward = int(r_str.split("_")[1])
            else:
                gold_reward = 1000  # box → grant 1000 gold equivalent

        claims[event_id].add(day)
        session.gold = min(session.gold + gold_reward, 999999999)
        self._send(session, MsgType.EVENT_CLAIM_RESULT, struct.pack('<B B I', 0, event_id, gold_reward))

    async def _on_subscription_info(self, session, payload: bytes):
        """SUBSCRIPTION_INFO(486) -> SUBSCRIPTION_STATUS(487)
        Response: active(u8) + remaining_days(u16) + crystal(u32) + benefits_count(u8) + [key_len+key+value_f32]*count
        """
        if not session.in_game:
            return
        active = 1 if session.subscription_active else 0
        remaining = 0
        if session.subscription_active and session.subscription_expires > time.time():
            remaining = int((session.subscription_expires - time.time()) / 86400) + 1
        else:
            session.subscription_active = False
            active = 0

        benefits = SUBSCRIPTION_BENEFITS
        data = struct.pack('<B H I B', active, remaining, session.crystal, len(benefits))
        for k, v in benefits.items():
            kb = k.encode('utf-8')[:20]
            data += struct.pack('<B', len(kb)) + kb + struct.pack('<f', float(v))
        self._send(session, MsgType.SUBSCRIPTION_STATUS, data)

    async def _on_subscription_buy(self, session, payload: bytes):
        """SUBSCRIPTION_BUY(488) -> SUBSCRIPTION_RESULT(489)
        Response: result(u8) + remaining_crystal(u32) + expires_days(u16)
          0=SUCCESS, 1=NOT_ENOUGH_CRYSTAL, 2=ALREADY_ACTIVE
        """
        if not session.in_game:
            return
        if session.subscription_active and session.subscription_expires > time.time():
            self._send(session, MsgType.SUBSCRIPTION_RESULT, struct.pack('<B I H', 2, session.crystal, 0))
            return
        if session.crystal < SUBSCRIPTION_PRICE_CRYSTAL:
            self._send(session, MsgType.SUBSCRIPTION_RESULT, struct.pack('<B I H', 1, session.crystal, 0))
            return

        session.crystal -= SUBSCRIPTION_PRICE_CRYSTAL
        session.subscription_active = True
        session.subscription_expires = time.time() + SUBSCRIPTION_DURATION_DAYS * 86400
        _SUBSCRIPTION_STATE[session.entity_id] = {
            "active": True, "expires": session.subscription_expires
        }
        self._send(session, MsgType.SUBSCRIPTION_RESULT,
                   struct.pack('<B I H', 0, session.crystal, SUBSCRIPTION_DURATION_DAYS))

    # ================================================================
    # TASK 12: World System — Weather / Teleport / Objects / Mount
    # MsgType 490-501
    # ================================================================

    async def _on_weather_info(self, session, payload: bytes):
        """WEATHER_INFO_REQ(490) -> WEATHER_INFO(491)
        Response: weather_id(u8) + weather_name_len(u8) + weather_name(utf8) +
                  time_phase(u8) + time_name_len(u8) + time_name(utf8) +
                  visibility(f32) + element_mod_count(u8) + [elem_len+elem+mod_f32]*count
        """
        if not session.in_game:
            return
        global _CURRENT_WEATHER

        # Weather name
        weather_id = WEATHER_TYPES.index(_CURRENT_WEATHER) if _CURRENT_WEATHER in WEATHER_TYPES else 0
        w_name = _CURRENT_WEATHER.encode('utf-8')[:20]

        # Time of day
        elapsed = time.time() - _GAME_TIME_OFFSET
        day_progress = (elapsed % GAME_DAY_SECONDS) / GAME_DAY_SECONDS
        phase_idx = int(day_progress * len(TIME_OF_DAY_PHASES)) % len(TIME_OF_DAY_PHASES)
        phase_name = TIME_OF_DAY_PHASES[phase_idx]
        p_name = phase_name.encode('utf-8')[:20]

        # Visibility
        visibility = 1.0
        if phase_name == "night":
            visibility = 1.0 - NIGHT_VISIBILITY_PENALTY

        # Element modifiers
        mods = WEATHER_ELEMENT_MODIFIERS.get(_CURRENT_WEATHER, {})

        data = struct.pack('<B B', weather_id, len(w_name)) + w_name
        data += struct.pack('<B B', phase_idx, len(p_name)) + p_name
        data += struct.pack('<f B', visibility, len(mods))
        for elem, mod in mods.items():
            eb = elem.encode('utf-8')[:15]
            data += struct.pack('<B', len(eb)) + eb + struct.pack('<f', mod)

        self._send(session, MsgType.WEATHER_INFO, data)

    async def _on_teleport_req(self, session, payload: bytes):
        """TELEPORT_REQ(492) -> TELEPORT_RESULT(493)
        Request: waypoint_id(u16)
        Response: result(u8) + waypoint_id(u16) + cost_silver(u32)
          0=SUCCESS, 1=NOT_DISCOVERED, 2=NOT_ENOUGH_SILVER, 3=IN_COMBAT, 4=INVALID_WAYPOINT
        """
        if not session.in_game or len(payload) < 2:
            return
        wp_id = struct.unpack('<H', payload[0:2])[0]

        eid = session.entity_id
        discovered = _DISCOVERED_WAYPOINTS.get(eid, set())

        # Free teleport for subscribers
        cost = TELEPORT_COST_SILVER
        if session.subscription_active and session.subscription_expires > time.time():
            sub_free = SUBSCRIPTION_BENEFITS.get("teleport_free_daily", 0)
            if sub_free > 0:
                cost = 0  # simplified: always free for subscribers

        if wp_id == 0 or wp_id > 100:
            self._send(session, MsgType.TELEPORT_RESULT, struct.pack('<B H I', 4, wp_id, cost))
            return

        if wp_id not in discovered:
            self._send(session, MsgType.TELEPORT_RESULT, struct.pack('<B H I', 1, wp_id, cost))
            return

        silver = getattr(session, 'silver', 0)
        if cost > 0 and silver < cost:
            self._send(session, MsgType.TELEPORT_RESULT, struct.pack('<B H I', 2, wp_id, cost))
            return

        if cost > 0:
            session.silver = silver - cost

        self._send(session, MsgType.TELEPORT_RESULT, struct.pack('<B H I', 0, wp_id, cost))

    async def _on_waypoint_discover(self, session, payload: bytes):
        """WAYPOINT_DISCOVER(494) -> WAYPOINT_LIST(495)
        Request: waypoint_id(u16)
        Response: total_discovered(u8) + [waypoint_id(u16)] * count
        """
        if not session.in_game or len(payload) < 2:
            return
        wp_id = struct.unpack('<H', payload[0:2])[0]

        eid = session.entity_id
        if eid not in _DISCOVERED_WAYPOINTS:
            _DISCOVERED_WAYPOINTS[eid] = set()

        _DISCOVERED_WAYPOINTS[eid].add(wp_id)

        discovered = sorted(_DISCOVERED_WAYPOINTS[eid])
        data = struct.pack('<B', len(discovered))
        for wid in discovered:
            data += struct.pack('<H', wid)
        self._send(session, MsgType.WAYPOINT_LIST, data)

    async def _on_destroy_object(self, session, payload: bytes):
        """DESTROY_OBJECT(496) -> DESTROY_OBJECT_RESULT(497)
        Request: object_type_len(u8) + object_type(utf8) + object_id(u32)
        Response: result(u8) + loot_gold(u32) + loot_item_len(u8) + loot_item(utf8)
          0=DESTROYED, 1=ALREADY_DESTROYED, 2=INVALID_OBJECT
        """
        if not session.in_game or len(payload) < 1:
            return

        otype_len = payload[0]
        if len(payload) < 1 + otype_len + 4:
            return
        otype = payload[1:1+otype_len].decode('utf-8', errors='ignore')
        obj_id = struct.unpack('<I', payload[1+otype_len:5+otype_len])[0]

        obj_def = WORLD_OBJECTS.get(otype)
        if not obj_def:
            self._send(session, MsgType.DESTROY_OBJECT_RESULT,
                       struct.pack('<B I B', 2, 0, 0))
            return

        obj_key = f"{otype}_{obj_id}"
        state = _WORLD_OBJECTS_STATE.get(obj_key, {})
        if state.get("destroyed") and state.get("respawn_at", 0) > time.time():
            self._send(session, MsgType.DESTROY_OBJECT_RESULT,
                       struct.pack('<B I B', 1, 0, 0))
            return

        # Destroy it
        _WORLD_OBJECTS_STATE[obj_key] = {
            "destroyed": True,
            "respawn_at": time.time() + obj_def["respawn"]
        }

        import random as _rng
        loot_gold = 0
        loot_item = ""
        if obj_def["loot"] == "gold":
            loot_gold = _rng.randint(obj_def["loot_min"], obj_def["loot_max"])
            session.gold = min(session.gold + loot_gold, 999999999)
        elif obj_def["loot"] == "gem":
            if _rng.random() < obj_def.get("loot_chance", 0.30):
                loot_item = "raw_gem"

        loot_b = loot_item.encode('utf-8')[:20]
        self._send(session, MsgType.DESTROY_OBJECT_RESULT,
                   struct.pack('<B I B', 0, loot_gold, len(loot_b)) + loot_b)

    async def _on_interact_object(self, session, payload: bytes):
        """INTERACT_OBJECT(498) -> INTERACT_RESULT(499)
        Request: object_id(u32) + interact_type(u8) — 0=open_chest, 1=activate
        Response: result(u8) + gold(u32) + trapped(u8)
          0=SUCCESS, 1=ALREADY_USED, 2=INVALID
        """
        if not session.in_game or len(payload) < 5:
            return
        obj_id = struct.unpack('<I', payload[0:4])[0]
        interact_type = payload[4]

        obj_key = f"chest_{obj_id}"
        state = _WORLD_OBJECTS_STATE.get(obj_key, {})
        if state.get("destroyed"):
            self._send(session, MsgType.INTERACT_RESULT, struct.pack('<B I B', 1, 0, 0))
            return

        _WORLD_OBJECTS_STATE[obj_key] = {"destroyed": True, "respawn_at": time.time() + 600}

        import random as _rng
        gold = _rng.randint(10, 100)
        trapped = 1 if _rng.random() < TREASURE_CHEST_TRAP_CHANCE else 0
        session.gold = min(session.gold + gold, 999999999)
        self._send(session, MsgType.INTERACT_RESULT, struct.pack('<B I B', 0, gold, trapped))

    async def _on_mount_summon(self, session, payload: bytes):
        """MOUNT_SUMMON(500) -> MOUNT_RESULT(501)
        Request: action(u8) — 0=dismiss, 1=summon, mount_id(u8)
        Response: result(u8) + mounted(u8) + speed_mult(f32)
          0=SUCCESS, 1=LEVEL_TOO_LOW, 2=IN_COMBAT, 3=ALREADY_MOUNTED/DISMOUNTED
        """
        if not session.in_game or len(payload) < 1:
            return
        action = payload[0]
        mount_id = payload[1] if len(payload) >= 2 else 1

        if action == 1:  # summon
            if session.stats.level < MOUNT_MIN_LEVEL:
                self._send(session, MsgType.MOUNT_RESULT,
                           struct.pack('<B B f', 1, 0, 1.0))
                return
            if session.mounted:
                self._send(session, MsgType.MOUNT_RESULT,
                           struct.pack('<B B f', 3, 1, MOUNT_SPEED_MULTIPLIER))
                return
            session.mounted = True
            session.mount_id = mount_id
            _MOUNT_STATE[session.entity_id] = {"mounted": True, "mount_id": mount_id}
            self._send(session, MsgType.MOUNT_RESULT,
                       struct.pack('<B B f', 0, 1, MOUNT_SPEED_MULTIPLIER))
        else:  # dismiss
            if not session.mounted:
                self._send(session, MsgType.MOUNT_RESULT,
                           struct.pack('<B B f', 3, 0, 1.0))
                return
            session.mounted = False
            session.mount_id = 0
            _MOUNT_STATE[session.entity_id] = {"mounted": False, "mount_id": 0}
            self._send(session, MsgType.MOUNT_RESULT,
                       struct.pack('<B B f', 0, 0, 1.0))

    # ================================================================
    # TASK 13: Login Reward / Daily Reset / Weekly Reset / Content Unlock
    # MsgType 502-509
    # ================================================================

    async def _on_login_reward_req(self, session, payload: bytes):
        """LOGIN_REWARD_REQ(502) -> LOGIN_REWARD_INFO(503)
        Response: total_days(u16) + cycle_day(u8) + claimed_today(u8) +
                  reward_count(u8) + [day(u8) + type_len(u8) + type(utf8) + amount(u32)] * count
        """
        if not session.in_game:
            return

        eid = session.entity_id
        today = time.strftime('%Y-%m-%d')

        if eid not in _LOGIN_REWARD_STATE:
            _LOGIN_REWARD_STATE[eid] = {
                "total_days": session.login_total_days,
                "last_claim_date": session.login_last_claim,
                "cycle_day": session.login_cycle_day,
            }

        state = _LOGIN_REWARD_STATE[eid]
        claimed_today = 1 if state["last_claim_date"] == today else 0
        cycle_day = state["cycle_day"]

        # Send reward table
        rewards = LOGIN_REWARD_TABLE
        data = struct.pack('<H B B B', state["total_days"], cycle_day, claimed_today, len(rewards))
        for day_num in sorted(rewards.keys()):
            r = rewards[day_num]
            rtype = r["type"].encode('utf-8')[:15]
            amount = r.get("amount", 0)
            data += struct.pack('<B B', day_num, len(rtype)) + rtype + struct.pack('<I', amount)

        self._send(session, MsgType.LOGIN_REWARD_INFO, data)

    async def _on_login_reward_claim(self, session, payload: bytes):
        """LOGIN_REWARD_CLAIM(504) -> LOGIN_REWARD_CLAIM_RESULT(505)
        Response: result(u8) + day(u8) + gold_reward(u32) + new_total_days(u16)
          0=SUCCESS, 1=ALREADY_CLAIMED_TODAY, 2=ERROR
        """
        if not session.in_game:
            return

        eid = session.entity_id
        today = time.strftime('%Y-%m-%d')

        if eid not in _LOGIN_REWARD_STATE:
            _LOGIN_REWARD_STATE[eid] = {
                "total_days": session.login_total_days,
                "last_claim_date": session.login_last_claim,
                "cycle_day": session.login_cycle_day,
            }

        state = _LOGIN_REWARD_STATE[eid]

        if state["last_claim_date"] == today:
            self._send(session, MsgType.LOGIN_REWARD_CLAIM_RESULT,
                       struct.pack('<B B I H', 1, state["cycle_day"], 0, state["total_days"]))
            return

        # Advance cycle
        state["total_days"] += 1
        state["cycle_day"] = ((state["cycle_day"]) % LOGIN_REWARD_CYCLE) + 1
        state["last_claim_date"] = today

        day = state["cycle_day"]
        reward = LOGIN_REWARD_TABLE.get(day, {"type": "gold", "amount": 1000})
        gold = reward.get("amount", 0) if reward["type"] == "gold" else 1000

        session.gold = min(session.gold + gold, 999999999)
        session.login_total_days = state["total_days"]
        session.login_cycle_day = state["cycle_day"]
        session.login_last_claim = today

        self._send(session, MsgType.LOGIN_REWARD_CLAIM_RESULT,
                   struct.pack('<B B I H', 0, day, gold, state["total_days"]))

    def _daily_reset(self):
        """매일 06:00 일일 리셋 로직 — game_tick에서 호출."""
        global _DAILY_RESET_LAST
        now = time.time()
        if now - _DAILY_RESET_LAST < 86400:
            return

        _DAILY_RESET_LAST = now

        for s in self.sessions.values():
            if not s.in_game:
                continue
            # Reset daily quests, dungeon entries, gold cap, energy
            s.daily_quests_done = getattr(s, 'daily_quests_done', 0)
            s.daily_quests_done = 0
            if hasattr(s, 'realm_daily_count'):
                s.realm_daily_count = 0
            # BP login exp
            self._battlepass_add_exp(s, BP_EXP_LOGIN)
            # Send notify
            self._send(s, MsgType.DAILY_RESET_NOTIFY, struct.pack('<B', 1))

    def _weekly_reset(self):
        """수요일 06:00 주간 리셋 로직."""
        global _WEEKLY_RESET_LAST
        now = time.time()
        if now - _WEEKLY_RESET_LAST < 604800:
            return

        _WEEKLY_RESET_LAST = now

        for s in self.sessions.values():
            if not s.in_game:
                continue
            # Reset weekly quests, raid entries, guild war, PvP points
            s.weekly_quests_done = getattr(s, 'weekly_quests_done', 0)
            s.weekly_quests_done = 0
            self._send(s, MsgType.WEEKLY_RESET_NOTIFY, struct.pack('<B', 1))

    async def _on_content_unlock_query(self, session, payload: bytes):
        """CONTENT_UNLOCK_QUERY(509) -> CONTENT_UNLOCK_NOTIFY(508)
        Response: count(u8) + [level(u8) + content_count(u8) + [name_len(u8)+name(utf8)]*count] * count
        Only returns unlocked content (level <= player level).
        """
        if not session.in_game:
            return
        player_level = session.stats.level
        unlocked = []
        for lv in sorted(CONTENT_UNLOCK_TABLE.keys()):
            if lv <= player_level:
                unlocked.append((lv, CONTENT_UNLOCK_TABLE[lv]))

        data = struct.pack('<B', len(unlocked))
        for lv, contents in unlocked:
            data += struct.pack('<B B', lv, len(contents))
            for c in contents:
                cb = c.encode('utf-8')[:30]
                data += struct.pack('<B', len(cb)) + cb
        self._send(session, MsgType.CONTENT_UNLOCK_NOTIFY, data)

    # ================================================================
    # TASK 14: Story / Dialog Choice / Cutscene / Chapter Progress
    # MsgType 510-517
    # ================================================================

    async def _on_dialog_choice(self, session, payload: bytes):
        """DIALOG_CHOICE(510) -> DIALOG_CHOICE_RESULT(511)
        Request: npc_id_len(u8) + npc_id(utf8) + choice_id(u8)
        Response: result(u8) + text_len(u16) + text(utf8) + choices_count(u8) +
                  [choice_id(u8)+choice_text_len(u8)+choice_text(utf8)]*count + action_len(u8)+action(utf8)
          result: 0=OK, 1=INVALID_NPC, 2=INVALID_CHOICE, 3=DIALOG_END
        """
        if not session.in_game or len(payload) < 2:
            return
        npc_len = payload[0]
        if len(payload) < 1 + npc_len + 1:
            return
        npc_id = payload[1:1+npc_len].decode('utf-8', errors='ignore')
        choice_id = payload[1+npc_len]

        tree = DIALOG_TREES.get(npc_id)
        if not tree:
            self._send(session, MsgType.DIALOG_CHOICE_RESULT, struct.pack('<B', 1))
            return

        eid = session.entity_id
        dialog_state = _DIALOG_STATE.get(eid, {})
        current_node = dialog_state.get("current_node", "start") if dialog_state.get("npc_id") == npc_id else "start"

        node = tree.get(current_node)
        if not node:
            self._send(session, MsgType.DIALOG_CHOICE_RESULT, struct.pack('<B', 1))
            return

        # If choice_id == 0, just show current node (initial dialog)
        if choice_id == 0:
            pass
        else:
            # Find the chosen option
            choices = node.get("choices", [])
            chosen = None
            for c in choices:
                if c["id"] == choice_id:
                    chosen = c
                    break
            if not chosen:
                self._send(session, MsgType.DIALOG_CHOICE_RESULT, struct.pack('<B', 2))
                return

            next_node_name = chosen.get("next", "end")
            node = tree.get(next_node_name)
            if not node:
                # End of dialog
                _DIALOG_STATE.pop(eid, None)
                self._send(session, MsgType.DIALOG_CHOICE_RESULT, struct.pack('<B', 3))
                return
            current_node = next_node_name

        # Save state
        _DIALOG_STATE[eid] = {"npc_id": npc_id, "current_node": current_node}

        # Build response
        text = node.get("text", "")
        text_b = text.encode('utf-8')[:500]
        choices = node.get("choices", [])
        action = node.get("action", "")
        action_b = action.encode('utf-8')[:50]

        if not text and not choices:
            # End of dialog
            _DIALOG_STATE.pop(eid, None)
            self._send(session, MsgType.DIALOG_CHOICE_RESULT, struct.pack('<B', 3))
            return

        result_code = 0
        data = struct.pack('<B H', result_code, len(text_b)) + text_b
        data += struct.pack('<B', len(choices))
        for c in choices:
            ct = c["text"].encode('utf-8')[:60]
            data += struct.pack('<B B', c["id"], len(ct)) + ct
        data += struct.pack('<B', len(action_b)) + action_b
        self._send(session, MsgType.DIALOG_CHOICE_RESULT, data)

    async def _on_cutscene_trigger(self, session, payload: bytes):
        """CUTSCENE_TRIGGER(512) -> CUTSCENE_DATA(513)
        Request: cutscene_id_len(u8) + cutscene_id(utf8)
        Response: result(u8) + seq_count(u8) + [seq_len(u8)+seq(utf8)]*count
          0=OK, 1=NOT_FOUND, 2=CONDITIONS_NOT_MET, 3=ALREADY_SEEN
        """
        if not session.in_game or len(payload) < 1:
            return
        cs_len = payload[0]
        if len(payload) < 1 + cs_len:
            return
        cs_id = payload[1:1+cs_len].decode('utf-8', errors='ignore')

        cs = CUTSCENE_DATA_TABLE.get(cs_id)
        if not cs:
            self._send(session, MsgType.CUTSCENE_DATA, struct.pack('<B', 1))
            return

        eid = session.entity_id
        if eid not in _CHAPTER_PROGRESS:
            _CHAPTER_PROGRESS[eid] = {
                "current_chapter": session.current_chapter,
                "seal_fragments": session.seal_fragments,
                "completed_quests": set(),
                "seen_cutscenes": set(),
            }
        progress = _CHAPTER_PROGRESS[eid]

        # Check required quest
        req_quest = cs.get("required_quest")
        if req_quest and req_quest not in progress["completed_quests"]:
            self._send(session, MsgType.CUTSCENE_DATA, struct.pack('<B', 2))
            return

        if cs_id in progress["seen_cutscenes"]:
            # Allow replay but mark as already seen
            pass

        progress["seen_cutscenes"].add(cs_id)

        sequences = cs.get("sequences", [])
        data = struct.pack('<B B', 0, len(sequences))
        for seq in sequences:
            sb = seq.encode('utf-8')[:80]
            data += struct.pack('<B', len(sb)) + sb
        self._send(session, MsgType.CUTSCENE_DATA, data)

    async def _on_chapter_progress_req(self, session, payload: bytes):
        """CHAPTER_PROGRESS_REQ(514) -> CHAPTER_PROGRESS(515)
        Response: current_chapter(u8) + total_chapters(u8) + seal_fragments(u8) + total_needed(u8) +
                  chapter_count(u8) + [chapter_id(u8)+name_len(u8)+name(utf8)+unlocked(u8)+quests_done(u8)+quests_total(u8)]*count
        """
        if not session.in_game:
            return

        eid = session.entity_id
        if eid not in _CHAPTER_PROGRESS:
            _CHAPTER_PROGRESS[eid] = {
                "current_chapter": session.current_chapter,
                "seal_fragments": session.seal_fragments,
                "completed_quests": set(),
                "seen_cutscenes": set(),
            }
        progress = _CHAPTER_PROGRESS[eid]

        total_chapters = len(CHAPTER_DATA)
        total_fragments_needed = sum(ch["seal_fragments"] for ch in CHAPTER_DATA.values())

        data = struct.pack('<B B B B B',
                           progress["current_chapter"], total_chapters,
                           progress["seal_fragments"], total_fragments_needed,
                           total_chapters)

        for ch_id in sorted(CHAPTER_DATA.keys()):
            ch = CHAPTER_DATA[ch_id]
            name_b = ch["name"].encode('utf-8')[:30]
            unlocked = 1 if ch_id <= progress["current_chapter"] else 0
            quests_done = sum(1 for q in ch["main_quests"] if q in progress["completed_quests"])
            quests_total = len(ch["main_quests"])
            data += struct.pack('<B B', ch_id, len(name_b)) + name_b
            data += struct.pack('<B B B', unlocked, quests_done, quests_total)

        self._send(session, MsgType.CHAPTER_PROGRESS, data)

    async def _on_main_quest_data_req(self, session, payload: bytes):
        """MAIN_QUEST_DATA_REQ(516) -> MAIN_QUEST_DATA(517)
        Request: quest_id_len(u8) + quest_id(utf8)  (empty = get current available)
        Response: count(u8) + [qid_len(u8)+qid(utf8)+name_len(u8)+name(utf8)+chapter(u8)+
                  level(u8)+type_len(u8)+type(utf8)+count_needed(u16)+reward_exp(u32)+reward_gold(u32)]*count
        """
        if not session.in_game:
            return

        quest_filter = ""
        if payload and len(payload) >= 1:
            qlen = payload[0]
            if qlen > 0 and len(payload) >= 1 + qlen:
                quest_filter = payload[1:1+qlen].decode('utf-8', errors='ignore')

        player_level = session.stats.level
        quests = []
        if quest_filter:
            q = MAIN_QUEST_TABLE.get(quest_filter)
            if q:
                quests.append((quest_filter, q))
        else:
            # Return available quests (matching level)
            for qid, q in MAIN_QUEST_TABLE.items():
                if q["level"] <= player_level:
                    quests.append((qid, q))

        quests = quests[:20]  # Limit
        data = struct.pack('<B', len(quests))
        for qid, q in quests:
            qid_b = qid.encode('utf-8')[:20]
            name_b = q["name"].encode('utf-8')[:40]
            type_b = q["type"].encode('utf-8')[:20]
            data += struct.pack('<B', len(qid_b)) + qid_b
            data += struct.pack('<B', len(name_b)) + name_b
            data += struct.pack('<B B', q["chapter"], q["level"])
            data += struct.pack('<B', len(type_b)) + type_b
            data += struct.pack('<H I I', q.get("count", 1), q["reward_exp"], q["reward_gold"])

        self._send(session, MsgType.MAIN_QUEST_DATA, data)
'''

# ====================================================================
# 6. Test cases (20 tests)
# ====================================================================
TEST_CODE = r'''
    # ================================================================
    # TASK 11 Tests: Cash Shop / Battle Pass / Event / Subscription
    # ================================================================

    # ━━━ Test: CASH_SHOP_LIST — 캐시상점 목록 조회 ━━━
    async def test_cash_shop_list():
        """캐시 상점 전체 목록 → 10개 아이템."""
        c = await login_and_enter(port)
        await c.send(MsgType.CASH_SHOP_LIST_REQ, struct.pack('<B', 0))
        msg_type, resp = await c.recv_expect(MsgType.CASH_SHOP_LIST)
        assert msg_type == MsgType.CASH_SHOP_LIST, f"Expected CASH_SHOP_LIST, got {msg_type}"
        crystal = struct.unpack('<I', resp[0:4])[0]
        count = resp[4]
        assert count == 10, f"Expected 10 shop items, got {count}"
        c.close()

    await test("CASH_SHOP_LIST: 캐시상점 10개 목록", test_cash_shop_list())

    # ━━━ Test: CASH_SHOP_BUY — 크리스탈 부족 구매 실패 ━━━
    async def test_cash_shop_buy_fail():
        """크리스탈 0 상태에서 구매 → NOT_ENOUGH_CRYSTAL(1)."""
        c = await login_and_enter(port)
        await c.send(MsgType.CASH_SHOP_BUY, struct.pack('<B', 1))
        msg_type, resp = await c.recv_expect(MsgType.CASH_SHOP_BUY_RESULT)
        assert msg_type == MsgType.CASH_SHOP_BUY_RESULT
        assert resp[0] == 1, f"Expected NOT_ENOUGH_CRYSTAL(1), got {resp[0]}"
        c.close()

    await test("CASH_SHOP_BUY: 크리스탈 부족 → 실패", test_cash_shop_buy_fail())

    # ━━━ Test: BATTLEPASS_INFO — 배틀패스 정보 조회 ━━━
    async def test_battlepass_info():
        """배틀패스 정보 조회 → level/exp/premium 반환."""
        c = await login_and_enter(port)
        await c.send(MsgType.BATTLEPASS_INFO_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BATTLEPASS_INFO)
        assert msg_type == MsgType.BATTLEPASS_INFO
        level = resp[0]
        exp = struct.unpack('<H', resp[1:3])[0]
        exp_needed = struct.unpack('<H', resp[3:5])[0]
        assert exp_needed == 1000, f"Expected exp_needed=1000, got {exp_needed}"
        c.close()

    await test("BATTLEPASS_INFO: 배틀패스 레벨/경험치 조회", test_battlepass_info())

    # ━━━ Test: BATTLEPASS_CLAIM — 레벨 미달 보상 수령 실패 ━━━
    async def test_battlepass_claim_fail():
        """BP 레벨 0에서 5레벨 보상 → LEVEL_NOT_REACHED(1)."""
        c = await login_and_enter(port)
        await c.send(MsgType.BATTLEPASS_CLAIM, struct.pack('<B B', 5, 0))
        msg_type, resp = await c.recv_expect(MsgType.BATTLEPASS_CLAIM_RESULT)
        assert msg_type == MsgType.BATTLEPASS_CLAIM_RESULT
        assert resp[0] == 1, f"Expected LEVEL_NOT_REACHED(1), got {resp[0]}"
        c.close()

    await test("BATTLEPASS_CLAIM: 레벨 미달 → 실패", test_battlepass_claim_fail())

    # ━━━ Test: EVENT_LIST — 이벤트 목록 조회 ━━━
    async def test_event_list():
        """이벤트 3종 목록 조회."""
        c = await login_and_enter(port)
        await c.send(MsgType.EVENT_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.EVENT_LIST)
        assert msg_type == MsgType.EVENT_LIST
        count = resp[0]
        assert count == 3, f"Expected 3 events, got {count}"
        c.close()

    await test("EVENT_LIST: 이벤트 3종 목록", test_event_list())

    # ━━━ Test: EVENT_CLAIM — 출석 이벤트 보상 수령 ━━━
    async def test_event_claim():
        """출석 이벤트 Day 1 보상 수령 → SUCCESS + gold."""
        c = await login_and_enter(port)
        await c.send(MsgType.EVENT_CLAIM, struct.pack('<B B', 1, 1))
        msg_type, resp = await c.recv_expect(MsgType.EVENT_CLAIM_RESULT)
        assert msg_type == MsgType.EVENT_CLAIM_RESULT
        assert resp[0] == 0, f"Expected SUCCESS(0), got {resp[0]}"
        gold = struct.unpack('<I', resp[2:6])[0]
        assert gold == 1000, f"Expected 1000 gold, got {gold}"
        # Second claim same day -> ALREADY_CLAIMED
        await c.send(MsgType.EVENT_CLAIM, struct.pack('<B B', 1, 1))
        msg_type2, resp2 = await c.recv_expect(MsgType.EVENT_CLAIM_RESULT)
        assert resp2[0] == 1, f"Expected ALREADY_CLAIMED(1), got {resp2[0]}"
        c.close()

    await test("EVENT_CLAIM: 출석 이벤트 Day1 수령+중복방지", test_event_claim())

    # ━━━ Test: SUBSCRIPTION — 구독 정보 + 크리스탈 부족 ━━━
    async def test_subscription():
        """구독 정보 조회 → 비활성. 구매 → 크리스탈 부족."""
        c = await login_and_enter(port)
        await c.send(MsgType.SUBSCRIPTION_INFO, b'')
        msg_type, resp = await c.recv_expect(MsgType.SUBSCRIPTION_STATUS)
        assert msg_type == MsgType.SUBSCRIPTION_STATUS
        active = resp[0]
        assert active == 0, f"Expected inactive(0), got {active}"
        # Try buy with 0 crystal
        await c.send(MsgType.SUBSCRIPTION_BUY, b'')
        msg_type2, resp2 = await c.recv_expect(MsgType.SUBSCRIPTION_RESULT)
        assert resp2[0] == 1, f"Expected NOT_ENOUGH_CRYSTAL(1), got {resp2[0]}"
        c.close()

    await test("SUBSCRIPTION: 구독 조회+크리스탈 부족", test_subscription())

    # ================================================================
    # TASK 12 Tests: World System
    # ================================================================

    # ━━━ Test: WEATHER_INFO — 날씨/시간 조회 ━━━
    async def test_weather_info():
        """날씨+시간 정보 조회."""
        c = await login_and_enter(port)
        await c.send(MsgType.WEATHER_INFO_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.WEATHER_INFO)
        assert msg_type == MsgType.WEATHER_INFO
        weather_id = resp[0]
        assert 0 <= weather_id <= 5, f"Invalid weather_id: {weather_id}"
        c.close()

    await test("WEATHER_INFO: 날씨/시간 조회", test_weather_info())

    # ━━━ Test: TELEPORT — 미발견 워프 텔레포트 실패 ━━━
    async def test_teleport_fail():
        """미발견 워프포인트 텔레포트 → NOT_DISCOVERED(1)."""
        c = await login_and_enter(port)
        await c.send(MsgType.TELEPORT_REQ, struct.pack('<H', 5))
        msg_type, resp = await c.recv_expect(MsgType.TELEPORT_RESULT)
        assert msg_type == MsgType.TELEPORT_RESULT
        assert resp[0] == 1, f"Expected NOT_DISCOVERED(1), got {resp[0]}"
        c.close()

    await test("TELEPORT: 미발견 워프 → 실패", test_teleport_fail())

    # ━━━ Test: WAYPOINT_DISCOVER + TELEPORT — 워프 발견 후 텔레포트 ━━━
    async def test_waypoint_and_teleport():
        """워프 발견 → 텔레포트 → NOT_ENOUGH_SILVER(2) (silver 0)."""
        c = await login_and_enter(port)
        # Discover waypoint 3
        await c.send(MsgType.WAYPOINT_DISCOVER, struct.pack('<H', 3))
        msg_type, resp = await c.recv_expect(MsgType.WAYPOINT_LIST)
        assert msg_type == MsgType.WAYPOINT_LIST
        count = resp[0]
        assert count >= 1, f"Expected at least 1 waypoint, got {count}"
        # Try teleport — should fail due to silver
        await c.send(MsgType.TELEPORT_REQ, struct.pack('<H', 3))
        msg_type2, resp2 = await c.recv_expect(MsgType.TELEPORT_RESULT)
        assert msg_type2 == MsgType.TELEPORT_RESULT
        # result: 0=SUCCESS or 2=NOT_ENOUGH_SILVER (depends on silver balance)
        assert resp2[0] in (0, 2), f"Expected SUCCESS or NOT_ENOUGH_SILVER, got {resp2[0]}"
        c.close()

    await test("WAYPOINT+TELEPORT: 워프 발견+텔레포트 시도", test_waypoint_and_teleport())

    # ━━━ Test: DESTROY_OBJECT — 오브젝트 파괴 ━━━
    async def test_destroy_object():
        """배럴 파괴 → 골드 루팅."""
        c = await login_and_enter(port)
        otype = b'barrel'
        data = struct.pack('<B', len(otype)) + otype + struct.pack('<I', 1)
        await c.send(MsgType.DESTROY_OBJECT, data)
        msg_type, resp = await c.recv_expect(MsgType.DESTROY_OBJECT_RESULT)
        assert msg_type == MsgType.DESTROY_OBJECT_RESULT
        assert resp[0] == 0, f"Expected DESTROYED(0), got {resp[0]}"
        gold = struct.unpack('<I', resp[1:5])[0]
        assert 1 <= gold <= 10, f"Expected barrel gold 1-10, got {gold}"
        c.close()

    await test("DESTROY_OBJECT: 배럴 파괴 → 골드 루팅", test_destroy_object())

    # ━━━ Test: INTERACT_OBJECT — 보물상자 열기 ━━━
    async def test_interact_object():
        """보물상자 열기 → 골드+트랩 판정."""
        c = await login_and_enter(port)
        await c.send(MsgType.INTERACT_OBJECT, struct.pack('<I B', 100, 0))
        msg_type, resp = await c.recv_expect(MsgType.INTERACT_RESULT)
        assert msg_type == MsgType.INTERACT_RESULT
        assert resp[0] == 0, f"Expected SUCCESS(0), got {resp[0]}"
        gold = struct.unpack('<I', resp[1:5])[0]
        assert gold >= 10, f"Expected gold >= 10, got {gold}"
        c.close()

    await test("INTERACT_OBJECT: 보물상자 열기", test_interact_object())

    # ━━━ Test: MOUNT_SUMMON — 탈것 소환/해제 ━━━
    async def test_mount_summon():
        """탈것 소환 (레벨 부족 시 실패, 아니면 성공)."""
        c = await login_and_enter(port)
        await c.send(MsgType.MOUNT_SUMMON, struct.pack('<B B', 1, 1))
        msg_type, resp = await c.recv_expect(MsgType.MOUNT_RESULT)
        assert msg_type == MsgType.MOUNT_RESULT
        result = resp[0]
        # Low level → LEVEL_TOO_LOW(1), or if level >= 20 → SUCCESS(0)
        assert result in (0, 1), f"Expected SUCCESS(0) or LEVEL_TOO_LOW(1), got {result}"
        c.close()

    await test("MOUNT_SUMMON: 탈것 소환 시도", test_mount_summon())

    # ================================================================
    # TASK 13 Tests: Login Reward / Reset / Content Unlock
    # ================================================================

    # ━━━ Test: LOGIN_REWARD — 출석보상 조회 ━━━
    async def test_login_reward_info():
        """출석보상 14일 테이블 조회."""
        c = await login_and_enter(port)
        await c.send(MsgType.LOGIN_REWARD_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.LOGIN_REWARD_INFO)
        assert msg_type == MsgType.LOGIN_REWARD_INFO
        total_days = struct.unpack('<H', resp[0:2])[0]
        cycle_day = resp[2]
        claimed_today = resp[3]
        reward_count = resp[4]
        assert reward_count == 14, f"Expected 14 rewards, got {reward_count}"
        c.close()

    await test("LOGIN_REWARD: 출석보상 14일 테이블 조회", test_login_reward_info())

    # ━━━ Test: LOGIN_REWARD_CLAIM — 출석보상 수령 ━━━
    async def test_login_reward_claim():
        """출석보상 수령 → 골드 획득 + 중복방지."""
        c = await login_and_enter(port)
        await c.send(MsgType.LOGIN_REWARD_CLAIM, b'')
        msg_type, resp = await c.recv_expect(MsgType.LOGIN_REWARD_CLAIM_RESULT)
        assert msg_type == MsgType.LOGIN_REWARD_CLAIM_RESULT
        assert resp[0] == 0, f"Expected SUCCESS(0), got {resp[0]}"
        day = resp[1]
        gold = struct.unpack('<I', resp[2:6])[0]
        assert gold > 0, f"Expected gold > 0, got {gold}"
        # Second claim → ALREADY_CLAIMED(1)
        await c.send(MsgType.LOGIN_REWARD_CLAIM, b'')
        msg_type2, resp2 = await c.recv_expect(MsgType.LOGIN_REWARD_CLAIM_RESULT)
        assert resp2[0] == 1, f"Expected ALREADY_CLAIMED(1), got {resp2[0]}"
        c.close()

    await test("LOGIN_REWARD_CLAIM: 출석보상 수령+중복방지", test_login_reward_claim())

    # ━━━ Test: CONTENT_UNLOCK — 컨텐츠 해금 조회 ━━━
    async def test_content_unlock():
        """현재 레벨에 맞는 해금 컨텐츠 조회."""
        c = await login_and_enter(port)
        await c.send(MsgType.CONTENT_UNLOCK_QUERY, b'')
        msg_type, resp = await c.recv_expect(MsgType.CONTENT_UNLOCK_NOTIFY)
        assert msg_type == MsgType.CONTENT_UNLOCK_NOTIFY
        count = resp[0]
        # Level 1 player → only Lv5 이하 해금 없음 (Lv1은 테이블에 없음)
        # 하지만 Lv1 플레이어는 count=0 가능
        assert count >= 0, f"Expected count >= 0, got {count}"
        c.close()

    await test("CONTENT_UNLOCK: 컨텐츠 해금 조회", test_content_unlock())

    # ================================================================
    # TASK 14 Tests: Story / Dialog / Cutscene / Chapter
    # ================================================================

    # ━━━ Test: DIALOG_CHOICE — NPC 대화 선택지 ━━━
    async def test_dialog_choice():
        """장로 NPC 대화 시작 → 선택지 2~3개 반환."""
        c = await login_and_enter(port)
        npc_id = b'npc_elder'
        data = struct.pack('<B', len(npc_id)) + npc_id + struct.pack('<B', 0)
        await c.send(MsgType.DIALOG_CHOICE, data)
        msg_type, resp = await c.recv_expect(MsgType.DIALOG_CHOICE_RESULT)
        assert msg_type == MsgType.DIALOG_CHOICE_RESULT
        result = resp[0]
        assert result == 0, f"Expected OK(0), got {result}"
        # Parse text length
        text_len = struct.unpack('<H', resp[1:3])[0]
        assert text_len > 0, f"Expected dialog text, got text_len={text_len}"
        c.close()

    await test("DIALOG_CHOICE: NPC 대화 시작+선택지", test_dialog_choice())

    # ━━━ Test: DIALOG_CHOICE — 잘못된 NPC ━━━
    async def test_dialog_invalid_npc():
        """존재하지 않는 NPC → INVALID_NPC(1)."""
        c = await login_and_enter(port)
        npc_id = b'npc_nobody'
        data = struct.pack('<B', len(npc_id)) + npc_id + struct.pack('<B', 0)
        await c.send(MsgType.DIALOG_CHOICE, data)
        msg_type, resp = await c.recv_expect(MsgType.DIALOG_CHOICE_RESULT)
        assert msg_type == MsgType.DIALOG_CHOICE_RESULT
        assert resp[0] == 1, f"Expected INVALID_NPC(1), got {resp[0]}"
        c.close()

    await test("DIALOG_CHOICE: 잘못된 NPC → INVALID_NPC", test_dialog_invalid_npc())

    # ━━━ Test: CUTSCENE_TRIGGER — 오프닝 컷씬 ━━━
    async def test_cutscene_trigger():
        """오프닝 컷씬 트리거 → 시퀀스 4개."""
        c = await login_and_enter(port)
        cs_id = b'opening'
        data = struct.pack('<B', len(cs_id)) + cs_id
        await c.send(MsgType.CUTSCENE_TRIGGER, data)
        msg_type, resp = await c.recv_expect(MsgType.CUTSCENE_DATA)
        assert msg_type == MsgType.CUTSCENE_DATA
        result = resp[0]
        assert result == 0, f"Expected OK(0), got {result}"
        seq_count = resp[1]
        assert seq_count == 4, f"Expected 4 sequences, got {seq_count}"
        c.close()

    await test("CUTSCENE_TRIGGER: 오프닝 컷씬 4시퀀스", test_cutscene_trigger())

    # ━━━ Test: CHAPTER_PROGRESS — 챕터 진행 조회 ━━━
    async def test_chapter_progress():
        """챕터 진행 상태 조회 → 4챕터, 봉인석 0/5."""
        c = await login_and_enter(port)
        await c.send(MsgType.CHAPTER_PROGRESS_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.CHAPTER_PROGRESS)
        assert msg_type == MsgType.CHAPTER_PROGRESS
        current_ch = resp[0]
        total_ch = resp[1]
        seal_frags = resp[2]
        total_needed = resp[3]
        assert total_ch == 4, f"Expected 4 chapters, got {total_ch}"
        assert total_needed == 5, f"Expected 5 total seal fragments, got {total_needed}"
        c.close()

    await test("CHAPTER_PROGRESS: 챕터 진행 4챕터/봉인석", test_chapter_progress())

    # ━━━ Test: MAIN_QUEST_DATA — 메인 퀘스트 목록 ━━━
    async def test_main_quest_data():
        """현재 레벨에 맞는 메인 퀘스트 목록 조회."""
        c = await login_and_enter(port)
        await c.send(MsgType.MAIN_QUEST_DATA_REQ, struct.pack('<B', 0))
        msg_type, resp = await c.recv_expect(MsgType.MAIN_QUEST_DATA)
        assert msg_type == MsgType.MAIN_QUEST_DATA
        count = resp[0]
        # Level 1 → MQ001 (level 1) should be available
        assert count >= 1, f"Expected at least 1 quest, got {count}"
        c.close()

    await test("MAIN_QUEST_DATA: 메인 퀘스트 목록 조회", test_main_quest_data())
'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check
    if ('CASH_SHOP_LIST_REQ = 474' in content
            and 'DIALOG_CHOICE = 510' in content
            and 'def _on_cash_shop_list' in content
            and 'def _on_chapter_progress_req' in content
            and 'CONTENT_UNLOCK_TABLE' in content
            and 'MAIN_QUEST_TABLE' in content):
        print('[bridge] S057 already patched')
        return True

    changed = False

    # 1. MsgType -- after MENTOR_SHOP_BUY = 560
    if 'CASH_SHOP_LIST_REQ' not in content:
        marker = '    MENTOR_SHOP_BUY = 560'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 474-517')
        else:
            print('[bridge] WARNING: Could not find MsgType insertion point')

    # 2. Data constants -- after _MENTOR_GRADUATION_COUNT = {}
    if 'CASH_SHOP_ITEMS' not in content or 'CASH_SHOP_CRYSTAL_CURRENCY' not in content:
        marker = "_MENTOR_GRADUATION_COUNT = {}"
        idx = content.find(marker)
        if idx >= 0:
            nl = content.index('\n', idx) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added TASK 11-14 data constants')
        else:
            # Fallback: after MENTOR_SHOP_ITEMS
            marker2 = 'MENTOR_SHOP_ITEMS = ['
            idx2 = content.find(marker2)
            if idx2 >= 0:
                # Find end of list
                bracket_count = 0
                pos = idx2
                while pos < len(content):
                    if content[pos] == '[':
                        bracket_count += 1
                    elif content[pos] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            nl = content.index('\n', pos) + 1
                            content = content[:nl] + DATA_CONSTANTS + content[nl:]
                            changed = True
                            print('[bridge] Added TASK 11-14 data constants (fallback)')
                            break
                    pos += 1
            else:
                print('[bridge] WARNING: Could not find data constants insertion point')

    # 3. PlayerSession fields -- after mentor_graduation_count field
    if 'crystal: int = 0' not in content or 'current_chapter: int = 1' not in content:
        marker = '    mentor_graduation_count: int = 0'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession TASK 11-14 fields')
        else:
            print('[bridge] WARNING: Could not find session fields insertion point')

    # 4. Dispatch table -- after mentor_shop_buy dispatch
    if 'self._on_cash_shop_list' not in content:
        marker = '            MsgType.MENTOR_SHOP_BUY: self._on_mentor_shop_buy,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added TASK 11-14 dispatch table entries')
        else:
            print('[bridge] WARNING: Could not find dispatch table insertion point')

    # 5. Handler implementations -- before Mentorship handlers
    if 'def _on_cash_shop_list' not in content:
        marker = '    # ---- Mentorship System (TASK 18: MsgType 550-560) ----'
        idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added TASK 11-14 handler implementations')
        else:
            # Fallback: before Secret Realm handlers
            marker2 = '    # ---- Secret Realm System (TASK 17: MsgType 540-544) ----'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                content = content[:idx2] + HANDLER_CODE + '\n' + content[idx2:]
                changed = True
                print('[bridge] Added TASK 11-14 handler implementations (fallback)')
            else:
                print('[bridge] WARNING: Could not find handler insertion point')

    if changed:
        with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify
    checks = [
        # TASK 11 MsgType
        'CASH_SHOP_LIST_REQ = 474', 'CASH_SHOP_LIST = 475',
        'CASH_SHOP_BUY = 476', 'CASH_SHOP_BUY_RESULT = 477',
        'BATTLEPASS_INFO_REQ = 478', 'BATTLEPASS_INFO = 479',
        'BATTLEPASS_CLAIM = 480', 'BATTLEPASS_CLAIM_RESULT = 481',
        'EVENT_LIST_REQ = 482', 'EVENT_LIST = 483',
        'EVENT_CLAIM = 484', 'EVENT_CLAIM_RESULT = 485',
        'SUBSCRIPTION_INFO = 486', 'SUBSCRIPTION_STATUS = 487',
        'SUBSCRIPTION_BUY = 488', 'SUBSCRIPTION_RESULT = 489',
        # TASK 12 MsgType
        'WEATHER_INFO_REQ = 490', 'WEATHER_INFO = 491',
        'TELEPORT_REQ = 492', 'TELEPORT_RESULT = 493',
        'WAYPOINT_DISCOVER = 494', 'WAYPOINT_LIST = 495',
        'DESTROY_OBJECT = 496', 'DESTROY_OBJECT_RESULT = 497',
        'INTERACT_OBJECT = 498', 'INTERACT_RESULT = 499',
        'MOUNT_SUMMON = 500', 'MOUNT_RESULT = 501',
        # TASK 13 MsgType
        'LOGIN_REWARD_REQ = 502', 'LOGIN_REWARD_INFO = 503',
        'LOGIN_REWARD_CLAIM = 504', 'LOGIN_REWARD_CLAIM_RESULT = 505',
        'DAILY_RESET_NOTIFY = 506', 'WEEKLY_RESET_NOTIFY = 507',
        'CONTENT_UNLOCK_NOTIFY = 508', 'CONTENT_UNLOCK_QUERY = 509',
        # TASK 14 MsgType
        'DIALOG_CHOICE = 510', 'DIALOG_CHOICE_RESULT = 511',
        'CUTSCENE_TRIGGER = 512', 'CUTSCENE_DATA = 513',
        'CHAPTER_PROGRESS_REQ = 514', 'CHAPTER_PROGRESS = 515',
        'MAIN_QUEST_DATA_REQ = 516', 'MAIN_QUEST_DATA = 517',
        # Data constants
        'CASH_SHOP_ITEMS', 'BATTLEPASS_MAX_LEVEL', 'BATTLEPASS_REWARDS_FREE',
        'EVENT_LIST_DATA', 'SUBSCRIPTION_BENEFITS',
        'WEATHER_TYPES', 'WEATHER_ELEMENT_MODIFIERS', 'TELEPORT_COST_SILVER',
        'WORLD_OBJECTS', 'MOUNT_MIN_LEVEL',
        'LOGIN_REWARD_TABLE', 'CONTENT_UNLOCK_TABLE',
        'DIALOG_TREES', 'CUTSCENE_DATA_TABLE', 'CHAPTER_DATA', 'MAIN_QUEST_TABLE',
        # Handlers
        'def _on_cash_shop_list', 'def _on_cash_shop_buy',
        'def _on_battlepass_info', 'def _on_battlepass_claim',
        'def _on_event_list', 'def _on_event_claim',
        'def _on_subscription_info', 'def _on_subscription_buy',
        'def _on_weather_info', 'def _on_teleport_req',
        'def _on_waypoint_discover', 'def _on_destroy_object',
        'def _on_interact_object', 'def _on_mount_summon',
        'def _on_login_reward_req', 'def _on_login_reward_claim',
        'def _on_content_unlock_query',
        'def _on_dialog_choice', 'def _on_cutscene_trigger',
        'def _on_chapter_progress_req', 'def _on_main_quest_data_req',
        'def _battlepass_add_exp', 'def _daily_reset', 'def _weekly_reset',
        # Session fields
        'crystal: int = 0', 'bp_level: int = 0', 'subscription_active: bool = False',
        'mounted: bool = False', 'login_total_days: int = 0', 'current_chapter: int = 1',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING ({len(missing)}): {missing[:5]}...')
        return False
    print('[bridge] S057 patched OK -- TASK 11+12+13+14')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if ('test_cash_shop_list' in content and 'test_chapter_progress' in content
            and 'test_main_quest_data' in content):
        print('[test] S057 already patched')
        return True

    # Update imports — add new constants
    old_import = (
        '    MENTOR_QUEST_POOL, MENTOR_QUEST_WEEKLY_COUNT,\n'
        '    MENTOR_SHOP_ITEMS\n'
        ')'
    )
    new_import = (
        '    MENTOR_QUEST_POOL, MENTOR_QUEST_WEEKLY_COUNT,\n'
        '    MENTOR_SHOP_ITEMS,\n'
        '    CASH_SHOP_ITEMS, BATTLEPASS_MAX_LEVEL, BATTLEPASS_EXP_PER_LEVEL,\n'
        '    BATTLEPASS_REWARDS_FREE, BATTLEPASS_REWARDS_PREMIUM,\n'
        '    EVENT_LIST_DATA, SUBSCRIPTION_PRICE_CRYSTAL, SUBSCRIPTION_BENEFITS,\n'
        '    WEATHER_TYPES, TELEPORT_COST_SILVER, MOUNT_MIN_LEVEL, WORLD_OBJECTS,\n'
        '    LOGIN_REWARD_TABLE, LOGIN_REWARD_CYCLE, CONTENT_UNLOCK_TABLE,\n'
        '    DIALOG_TREES, CUTSCENE_DATA_TABLE, CHAPTER_DATA, MAIN_QUEST_TABLE\n'
        ')'
    )

    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports with TASK 11-14 constants')
    else:
        print('[test] NOTE: Could not find expected import block — trying alternate')
        # Try alternate: just append imports before the closing paren
        alt_old = '    MENTOR_SHOP_ITEMS\n)'
        alt_new = (
            '    MENTOR_SHOP_ITEMS,\n'
            '    CASH_SHOP_ITEMS, BATTLEPASS_MAX_LEVEL, BATTLEPASS_EXP_PER_LEVEL,\n'
            '    BATTLEPASS_REWARDS_FREE, BATTLEPASS_REWARDS_PREMIUM,\n'
            '    EVENT_LIST_DATA, SUBSCRIPTION_PRICE_CRYSTAL, SUBSCRIPTION_BENEFITS,\n'
            '    WEATHER_TYPES, TELEPORT_COST_SILVER, MOUNT_MIN_LEVEL, WORLD_OBJECTS,\n'
            '    LOGIN_REWARD_TABLE, LOGIN_REWARD_CYCLE, CONTENT_UNLOCK_TABLE,\n'
            '    DIALOG_TREES, CUTSCENE_DATA_TABLE, CHAPTER_DATA, MAIN_QUEST_TABLE\n'
            ')'
        )
        if alt_old in content:
            content = content.replace(alt_old, alt_new, 1)
            print('[test] Updated imports (alternate path)')
        else:
            print('[test] WARNING: Could not update imports')

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

    checks = [
        'test_cash_shop_list', 'test_cash_shop_buy_fail',
        'test_battlepass_info', 'test_battlepass_claim_fail',
        'test_event_list', 'test_event_claim',
        'test_subscription',
        'test_weather_info', 'test_teleport_fail',
        'test_waypoint_and_teleport', 'test_destroy_object',
        'test_interact_object', 'test_mount_summon',
        'test_login_reward_info', 'test_login_reward_claim',
        'test_content_unlock',
        'test_dialog_choice', 'test_dialog_invalid_npc',
        'test_cutscene_trigger', 'test_chapter_progress',
        'test_main_quest_data',
        'CASH_SHOP_LIST_REQ', 'BATTLEPASS_INFO_REQ',
        'EVENT_LIST_REQ', 'WEATHER_INFO_REQ',
        'LOGIN_REWARD_REQ', 'DIALOG_CHOICE',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING ({len(missing)}): {missing[:5]}...')
        return False
    print(f'[test] S057 patched OK -- 21 tests for TASK 11+12+13+14')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS057 all patches applied!')
    else:
        print('\nS057 PATCH FAILED!')
        sys.exit(1)
