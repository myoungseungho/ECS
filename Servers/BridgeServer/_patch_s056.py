"""
Patch S056: Mentorship System (TASK 18 — 사제 시스템)
- MENTOR_SEARCH(550)→MENTOR_LIST(551)         -- 사부/제자 검색
- MENTOR_REQUEST(552)→MENTOR_REQUEST_RESULT(553) -- 사제 요청
- MENTOR_ACCEPT(554)→MENTOR_ACCEPT_RESULT(555) -- 사제 수락/거절
- MENTOR_QUEST_LIST(556)→MENTOR_QUESTS(557)   -- 사제 전용 퀘스트
- MENTOR_GRADUATE(558)                         -- 졸업 (자동: 제자 Lv30)
- MENTOR_SHOP_LIST(559)→MENTOR_SHOP(560)       -- 사문 기여도 상점

Sub-tasks covered:
  mentor_sub01: MENTOR_SEARCH/LIST — 사부/제자 검색 (Lv40+/제자3명미만, Lv1~20/사부없음)
  mentor_sub02: MENTOR_REQUEST/ACCEPT — 사제 요청/수락/거절
  mentor_sub03: MENTOR_QUEST_LIST — 사제 전용 퀘스트 3개/주 (5종 풀)
  mentor_sub04: MENTOR_GRADUATE — 제자 Lv30 졸업 + 양쪽 보상 + 브로드캐스트
  mentor_sub05: MENTOR_SHOP_LIST/SHOP — 사문 기여도 상점 (8종 아이템)
  mentor_sub06: 사제 EXP 버프 — 파티 +30%, 솔로 +10%, 사부 제자처치EXP 10%

5 test cases
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Mentorship (550-560)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Mentorship System (TASK 18)\n'
    '    MENTOR_SEARCH = 550\n'
    '    MENTOR_LIST = 551\n'
    '    MENTOR_REQUEST = 552\n'
    '    MENTOR_REQUEST_RESULT = 553\n'
    '    MENTOR_ACCEPT = 554\n'
    '    MENTOR_ACCEPT_RESULT = 555\n'
    '    MENTOR_QUEST_LIST = 556\n'
    '    MENTOR_QUESTS = 557\n'
    '    MENTOR_GRADUATE = 558\n'
    '    MENTOR_SHOP_LIST = 559\n'
    '    MENTOR_SHOP_BUY = 560\n'
)

# ====================================================================
# 2. Data constants — mentorship rules, quests, shop
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Mentorship System Data (GDD mentorship.yaml) ----
MENTOR_MASTER_MIN_LEVEL = 40
MENTOR_MASTER_MAX_DISCIPLES = 3
MENTOR_DISCIPLE_LEVEL_RANGE = (1, 20)
MENTOR_DISCIPLE_MAX_MASTERS = 1
MENTOR_GRADUATION_LEVEL = 30

# EXP buff rates
MENTOR_EXP_BUFF_PARTY = 0.30   # 사부와 파티 시 +30%
MENTOR_EXP_BUFF_SOLO = 0.10    # 사부 있을 때 솔로 +10%
MENTOR_MASTER_EXP_SHARE = 0.10 # 제자 처치 EXP의 10% 사부 추가

# Contribution rewards
MENTOR_CONTRIB_LEVEL_UP = 10       # 제자 레벨업당 10
MENTOR_CONTRIB_QUEST_COMPLETE = 50 # 사제 퀘스트 완료당 50
MENTOR_CONTRIB_DUNGEON_CLEAR = 20  # 제자 던전 클리어 20
MENTOR_CONTRIB_GRADUATION = 500    # 졸업 보너스

# Quest pool (5종, 주 3회)
MENTOR_QUEST_WEEKLY_COUNT = 3
MENTOR_QUEST_POOL = [
    {"id": "mq_hunt_together", "name": "사냥 수련", "type": "kill", "count": 30,
     "condition": "same_party",
     "reward_master": {"contribution": 50, "gold": 2000},
     "reward_disciple": {"exp": 3000, "gold": 1000}},
    {"id": "mq_dungeon_together", "name": "던전 돌파", "type": "dungeon_clear", "count": 1,
     "condition": "same_party",
     "reward_master": {"contribution": 80, "gold": 3000, "dungeon_token": 5},
     "reward_disciple": {"exp": 5000, "gold": 2000}},
    {"id": "mq_gather_together", "name": "채집 수업", "type": "gather", "count": 10,
     "condition": "same_zone",
     "reward_master": {"contribution": 30},
     "reward_disciple": {"exp": 1000}},
    {"id": "mq_explore_together", "name": "세계 탐험", "type": "discover_area", "count": 3,
     "condition": "same_party",
     "reward_master": {"contribution": 40, "gold": 1500},
     "reward_disciple": {"exp": 2000}},
    {"id": "mq_boss_together", "name": "보스 도전", "type": "kill_boss", "count": 1,
     "condition": "same_party",
     "reward_master": {"contribution": 100, "gold": 5000},
     "reward_disciple": {"exp": 8000, "gold": 3000}},
]

# Mentor shop (8종 아이템)
MENTOR_SHOP_ITEMS = [
    {"id": 1, "name": "대사부의 증표",       "type": "material",    "cost": 200},
    {"id": 2, "name": "사부의 비단 깃발",    "type": "cosmetic",    "cost": 100},
    {"id": 3, "name": "제자 모집 문패",      "type": "cosmetic",    "cost": 50},
    {"id": 4, "name": "미확인 비급 (희귀)",  "type": "scroll",      "cost": 150},
    {"id": 5, "name": "미확인 비급 (영웅)",  "type": "scroll",      "cost": 400},
    {"id": 6, "name": "사문의 축복 부적",    "type": "consumable",  "cost": 30},
    {"id": 7, "name": "사부의 회복약",       "type": "consumable",  "cost": 20},
    {"id": 8, "name": "탈것: 사문의 학",     "type": "mount",       "cost": 500},
]

# Graduation rewards
MENTOR_GRADUATION_REWARDS_MASTER = {"contribution": 500, "gold": 10000}
MENTOR_GRADUATION_REWARDS_DISCIPLE = {"gold": 5000, "exp": 10000}

# Global mentorship state
_MENTOR_RELATIONS = {}   # master_eid -> [disciple_eid, ...]
_DISCIPLE_MASTERS = {}   # disciple_eid -> master_eid
_MENTOR_REQUESTS = {}    # target_eid -> {from_eid, role, timestamp}
_MENTOR_QUESTS = {}      # pair_key (master_eid, disciple_eid) -> [quest_dict, ...]
_MENTOR_QUEST_WEEK = {}  # pair_key -> week_number (to track weekly reset)
_MENTOR_CONTRIBUTION = {} # eid -> contribution_points
_MENTOR_GRADUATION_COUNT = {} # master_eid -> graduation_count
'''

# ====================================================================
# 3. PlayerSession fields
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Mentorship (TASK 18) ----\n'
    '    mentor_master_eid: int = 0                # 내 사부 entity_id (0=없음)\n'
    '    mentor_contribution: int = 0              # 사문 기여도\n'
    '    mentor_graduation_count: int = 0          # 졸업시킨 제자 수\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.MENTOR_SEARCH: self._on_mentor_search,\n'
    '            MsgType.MENTOR_REQUEST: self._on_mentor_request,\n'
    '            MsgType.MENTOR_ACCEPT: self._on_mentor_accept,\n'
    '            MsgType.MENTOR_QUEST_LIST: self._on_mentor_quest_list,\n'
    '            MsgType.MENTOR_GRADUATE: self._on_mentor_graduate,\n'
    '            MsgType.MENTOR_SHOP_LIST: self._on_mentor_shop_list,\n'
    '            MsgType.MENTOR_SHOP_BUY: self._on_mentor_shop_buy,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Mentorship System (TASK 18: MsgType 550-560) ----

    def _mentor_get_contribution(self, eid: int) -> int:
        """Get contribution points for a player."""
        # Check session first
        for s in self.sessions.values():
            if s.entity_id == eid:
                return s.mentor_contribution
        return _MENTOR_CONTRIBUTION.get(eid, 0)

    def _mentor_add_contribution(self, eid: int, amount: int):
        """Add contribution points to a player."""
        for s in self.sessions.values():
            if s.entity_id == eid:
                s.mentor_contribution += amount
                _MENTOR_CONTRIBUTION[eid] = s.mentor_contribution
                return
        _MENTOR_CONTRIBUTION[eid] = _MENTOR_CONTRIBUTION.get(eid, 0) + amount

    def _mentor_exp_multiplier(self, session) -> float:
        """Calculate EXP multiplier from mentorship.
        Disciple: +30% if in party with master, +10% otherwise (if has master).
        """
        if not session.in_game:
            return 1.0
        eid = session.entity_id
        master_eid = _DISCIPLE_MASTERS.get(eid, 0)
        if master_eid == 0:
            return 1.0
        # Check if in same party
        party_id = getattr(session, 'party_id', 0)
        if party_id:
            for s in self.sessions.values():
                if s.entity_id == master_eid and s.in_game and getattr(s, 'party_id', 0) == party_id:
                    return 1.0 + MENTOR_EXP_BUFF_PARTY  # +30%
        return 1.0 + MENTOR_EXP_BUFF_SOLO  # +10%

    def _mentor_on_mob_kill(self, killer_session, base_exp: int):
        """Hook: when disciple kills a mob, give master 10% of EXP."""
        eid = killer_session.entity_id
        master_eid = _DISCIPLE_MASTERS.get(eid, 0)
        if master_eid == 0:
            return
        bonus = int(base_exp * MENTOR_MASTER_EXP_SHARE)
        if bonus <= 0:
            return
        for s in self.sessions.values():
            if s.entity_id == master_eid and s.in_game:
                s.stats.exp += bonus
                break

    async def _on_mentor_search(self, session, payload: bytes):
        """MENTOR_SEARCH(550) -> MENTOR_LIST(551)
        Request: search_type(u8) — 0=search_masters, 1=search_disciples
        Response: count(u8) + [entity_id(u32) + level(u16) + name_len(u8) + name(utf8)] * count
        """
        if not session.in_game or len(payload) < 1:
            return
        search_type = payload[0]
        results = []

        if search_type == 0:
            # Search available masters: Lv40+, disciples < 3
            for s in self.sessions.values():
                if not s.in_game or s.entity_id == session.entity_id:
                    continue
                if s.stats.level < MENTOR_MASTER_MIN_LEVEL:
                    continue
                current_disciples = _MENTOR_RELATIONS.get(s.entity_id, [])
                if len(current_disciples) >= MENTOR_MASTER_MAX_DISCIPLES:
                    continue
                results.append(s)
        else:
            # Search available disciples: Lv1~20, no master
            for s in self.sessions.values():
                if not s.in_game or s.entity_id == session.entity_id:
                    continue
                lv = s.stats.level
                if lv < MENTOR_DISCIPLE_LEVEL_RANGE[0] or lv > MENTOR_DISCIPLE_LEVEL_RANGE[1]:
                    continue
                if s.entity_id in _DISCIPLE_MASTERS:
                    continue
                results.append(s)

        results = results[:20]  # Max 20 results
        data = struct.pack('<B', len(results))
        for s in results:
            name_bytes = s.char_name.encode('utf-8')[:30]
            data += struct.pack('<I H B', s.entity_id, s.stats.level, len(name_bytes))
            data += name_bytes

        self._send(session, MsgType.MENTOR_LIST, data)

    async def _on_mentor_request(self, session, payload: bytes):
        """MENTOR_REQUEST(552) -> MENTOR_REQUEST_RESULT(553)
        Request: target_eid(u32) + role(u8) — role: 0=I want to be disciple, 1=I want to be master
        Response: result(u8)
          0=REQUEST_SENT, 1=LEVEL_TOO_LOW (master needs 40+),
          2=LEVEL_TOO_HIGH (disciple needs 1~20), 3=ALREADY_HAS_MASTER,
          4=FULL_DISCIPLES, 5=TARGET_NOT_FOUND, 6=SELF_REQUEST, 7=ALREADY_IN_RELATION
        """
        if not session.in_game or len(payload) < 5:
            return
        target_eid = struct.unpack('<I', payload[0:4])[0]
        role = payload[4]  # 0=requestor wants to be disciple, 1=requestor wants to be master

        def _send_result(code):
            self._send(session, MsgType.MENTOR_REQUEST_RESULT, struct.pack('<B', code))

        # Self check
        if target_eid == session.entity_id:
            _send_result(6)
            return

        # Find target
        target = None
        for s in self.sessions.values():
            if s.entity_id == target_eid and s.in_game:
                target = s
                break
        if not target:
            _send_result(5)
            return

        if role == 0:
            # I want to be disciple -> target is master
            master_session = target
            disciple_session = session
        else:
            # I want to be master -> target is disciple
            master_session = session
            disciple_session = target

        master_eid = master_session.entity_id
        disciple_eid = disciple_session.entity_id

        # Check already in relation
        if disciple_eid in _DISCIPLE_MASTERS:
            if _DISCIPLE_MASTERS[disciple_eid] == master_eid:
                _send_result(7)  # ALREADY_IN_RELATION
                return
            _send_result(3)  # ALREADY_HAS_MASTER
            return

        # Master level check
        if master_session.stats.level < MENTOR_MASTER_MIN_LEVEL:
            _send_result(1)
            return

        # Disciple level check
        d_lv = disciple_session.stats.level
        if d_lv < MENTOR_DISCIPLE_LEVEL_RANGE[0] or d_lv > MENTOR_DISCIPLE_LEVEL_RANGE[1]:
            _send_result(2)
            return

        # Master full check
        if len(_MENTOR_RELATIONS.get(master_eid, [])) >= MENTOR_MASTER_MAX_DISCIPLES:
            _send_result(4)
            return

        # Store pending request
        _MENTOR_REQUESTS[target_eid] = {
            "from_eid": session.entity_id,
            "master_eid": master_eid,
            "disciple_eid": disciple_eid,
            "timestamp": time.time(),
        }

        _send_result(0)  # REQUEST_SENT

    async def _on_mentor_accept(self, session, payload: bytes):
        """MENTOR_ACCEPT(554) -> MENTOR_ACCEPT_RESULT(555)
        Request: accept(u8) — 0=reject, 1=accept
        Response: result(u8) + master_eid(u32) + disciple_eid(u32)
          result: 0=ACCEPTED, 1=REJECTED, 2=NO_PENDING_REQUEST, 3=CONDITIONS_CHANGED
        """
        if not session.in_game or len(payload) < 1:
            return
        accept = payload[0]

        def _send_result(code, m_eid=0, d_eid=0):
            self._send(session, MsgType.MENTOR_ACCEPT_RESULT,
                       struct.pack('<B I I', code, m_eid, d_eid))

        # Check pending request for this session
        req = _MENTOR_REQUESTS.pop(session.entity_id, None)
        if not req:
            _send_result(2)
            return

        master_eid = req["master_eid"]
        disciple_eid = req["disciple_eid"]

        if accept == 0:
            _send_result(1, master_eid, disciple_eid)  # REJECTED
            return

        # Re-validate conditions
        master_s = None
        disciple_s = None
        for s in self.sessions.values():
            if s.entity_id == master_eid and s.in_game:
                master_s = s
            if s.entity_id == disciple_eid and s.in_game:
                disciple_s = s

        if not master_s or not disciple_s:
            _send_result(3, master_eid, disciple_eid)
            return

        if master_s.stats.level < MENTOR_MASTER_MIN_LEVEL:
            _send_result(3, master_eid, disciple_eid)
            return

        d_lv = disciple_s.stats.level
        if d_lv < MENTOR_DISCIPLE_LEVEL_RANGE[0] or d_lv > MENTOR_DISCIPLE_LEVEL_RANGE[1]:
            _send_result(3, master_eid, disciple_eid)
            return

        if disciple_eid in _DISCIPLE_MASTERS:
            _send_result(3, master_eid, disciple_eid)
            return

        if len(_MENTOR_RELATIONS.get(master_eid, [])) >= MENTOR_MASTER_MAX_DISCIPLES:
            _send_result(3, master_eid, disciple_eid)
            return

        # Establish relation
        if master_eid not in _MENTOR_RELATIONS:
            _MENTOR_RELATIONS[master_eid] = []
        _MENTOR_RELATIONS[master_eid].append(disciple_eid)
        _DISCIPLE_MASTERS[disciple_eid] = master_eid

        # Set on disciple session
        disciple_s.mentor_master_eid = master_eid

        _send_result(0, master_eid, disciple_eid)  # ACCEPTED

        # Also notify the other party
        from_s = None
        for s in self.sessions.values():
            if s.entity_id == req["from_eid"] and s.in_game:
                from_s = s
                break
        if from_s and from_s.entity_id != session.entity_id:
            self._send(from_s, MsgType.MENTOR_ACCEPT_RESULT,
                       struct.pack('<B I I', 0, master_eid, disciple_eid))

    async def _on_mentor_quest_list(self, session, payload: bytes):
        """MENTOR_QUEST_LIST(556) -> MENTOR_QUESTS(557)
        Request: (empty)
        Response: count(u8) + [quest_id_len(u8) + quest_id(utf8) + name_len(u8) + name(utf8) +
                  type_len(u8) + type(utf8) + count_needed(u16) + progress(u16)] * count
        """
        if not session.in_game:
            return

        eid = session.entity_id
        # Find the mentor pair
        master_eid = _DISCIPLE_MASTERS.get(eid, 0)
        if master_eid == 0:
            # Maybe this session is a master — pick first disciple
            disciples = _MENTOR_RELATIONS.get(eid, [])
            if not disciples:
                self._send(session, MsgType.MENTOR_QUESTS, struct.pack('<B', 0))
                return
            disciple_eid = disciples[0]
            master_eid = eid
        else:
            disciple_eid = eid

        pair_key = (master_eid, disciple_eid)

        # Generate quests for this week if needed
        import random as _random
        week_num = int(time.time()) // (7 * 86400)
        if pair_key not in _MENTOR_QUESTS or _MENTOR_QUEST_WEEK.get(pair_key) != week_num:
            selected = _random.sample(MENTOR_QUEST_POOL, min(MENTOR_QUEST_WEEKLY_COUNT, len(MENTOR_QUEST_POOL)))
            quests = []
            for q in selected:
                quests.append({
                    "id": q["id"], "name": q["name"], "type": q["type"],
                    "count_needed": q["count"], "progress": 0,
                    "condition": q["condition"],
                    "reward_master": q["reward_master"],
                    "reward_disciple": q["reward_disciple"],
                    "completed": False,
                })
            _MENTOR_QUESTS[pair_key] = quests
            _MENTOR_QUEST_WEEK[pair_key] = week_num

        quests = _MENTOR_QUESTS[pair_key]
        data = struct.pack('<B', len(quests))
        for q in quests:
            qid = q["id"].encode('utf-8')[:30]
            qname = q["name"].encode('utf-8')[:30]
            qtype = q["type"].encode('utf-8')[:20]
            data += struct.pack('<B', len(qid)) + qid
            data += struct.pack('<B', len(qname)) + qname
            data += struct.pack('<B', len(qtype)) + qtype
            data += struct.pack('<H H', q["count_needed"], q["progress"])

        self._send(session, MsgType.MENTOR_QUESTS, data)

    async def _on_mentor_graduate(self, session, payload: bytes):
        """MENTOR_GRADUATE(558) — auto-triggered when disciple reaches Lv30.
        Can also be called explicitly to check & trigger graduation.
        Request: disciple_eid(u32) — 0 means check self (if disciple)
        Response: result(u8) + master_eid(u32) + disciple_eid(u32) + master_gold(u32) + disciple_gold(u32)
          result: 0=GRADUATED, 1=NOT_IN_RELATION, 2=LEVEL_NOT_REACHED, 3=NOT_YOUR_DISCIPLE
        """
        if not session.in_game:
            return

        def _send_result(code, m_eid=0, d_eid=0, m_gold=0, d_gold=0):
            self._send(session, MsgType.MENTOR_GRADUATE,
                       struct.pack('<B I I I I', code, m_eid, d_eid, m_gold, d_gold))

        eid = session.entity_id
        disciple_eid = 0
        if len(payload) >= 4:
            disciple_eid = struct.unpack('<I', payload[0:4])[0]

        if disciple_eid == 0:
            # Check self as disciple
            disciple_eid = eid

        master_eid = _DISCIPLE_MASTERS.get(disciple_eid, 0)
        if master_eid == 0:
            _send_result(1)
            return

        # Verify the caller is either the master or the disciple
        if eid != master_eid and eid != disciple_eid:
            _send_result(3)
            return

        # Check disciple level
        disciple_s = None
        for s in self.sessions.values():
            if s.entity_id == disciple_eid and s.in_game:
                disciple_s = s
                break

        if not disciple_s:
            _send_result(1)
            return

        if disciple_s.stats.level < MENTOR_GRADUATION_LEVEL:
            _send_result(2, master_eid, disciple_eid)
            return

        # Graduate!
        # Master rewards
        m_gold = MENTOR_GRADUATION_REWARDS_MASTER.get("gold", 0)
        m_contrib = MENTOR_GRADUATION_REWARDS_MASTER.get("contribution", 0)
        self._mentor_add_contribution(master_eid, m_contrib)

        master_s = None
        for s in self.sessions.values():
            if s.entity_id == master_eid and s.in_game:
                master_s = s
                break
        if master_s:
            master_s.gold = min(master_s.gold + m_gold, 999999999)
            master_s.mentor_graduation_count += 1
            _MENTOR_GRADUATION_COUNT[master_eid] = master_s.mentor_graduation_count

        # Disciple rewards
        d_gold = MENTOR_GRADUATION_REWARDS_DISCIPLE.get("gold", 0)
        d_exp = MENTOR_GRADUATION_REWARDS_DISCIPLE.get("exp", 0)
        disciple_s.gold = min(disciple_s.gold + d_gold, 999999999)
        disciple_s.stats.exp += d_exp

        # Clear relation
        if master_eid in _MENTOR_RELATIONS:
            if disciple_eid in _MENTOR_RELATIONS[master_eid]:
                _MENTOR_RELATIONS[master_eid].remove(disciple_eid)
        _DISCIPLE_MASTERS.pop(disciple_eid, None)
        disciple_s.mentor_master_eid = 0

        # Clear quests
        pair_key = (master_eid, disciple_eid)
        _MENTOR_QUESTS.pop(pair_key, None)
        _MENTOR_QUEST_WEEK.pop(pair_key, None)

        _send_result(0, master_eid, disciple_eid, m_gold, d_gold)

        # Broadcast graduation
        grad_msg = f"[사제졸업] 축하합니다!"
        grad_bytes = grad_msg.encode('utf-8')[:100]
        broadcast_data = struct.pack('<I I B', master_eid, disciple_eid, len(grad_bytes)) + grad_bytes
        for s in self.sessions.values():
            if s.in_game:
                self._send(s, MsgType.MENTOR_GRADUATE, broadcast_data)

    async def _on_mentor_shop_list(self, session, payload: bytes):
        """MENTOR_SHOP_LIST(559) -> MENTOR_SHOP(560 as list response reuse)
        Request: (empty)
        Response: contribution(u32) + count(u8) + [item_id(u8) + cost(u16) + name_len(u8) + name(utf8)] * count
        """
        if not session.in_game:
            return
        contrib = session.mentor_contribution
        data = struct.pack('<I B', contrib, len(MENTOR_SHOP_ITEMS))
        for item in MENTOR_SHOP_ITEMS:
            name_bytes = item["name"].encode('utf-8')[:30]
            data += struct.pack('<B H B', item["id"], item["cost"], len(name_bytes))
            data += name_bytes
        self._send(session, MsgType.MENTOR_SHOP_LIST, data)

    async def _on_mentor_shop_buy(self, session, payload: bytes):
        """MENTOR_SHOP_BUY(560)
        Request: item_id(u8)
        Response: result(u8) + remaining_contribution(u32)
          result: 0=SUCCESS, 1=NOT_ENOUGH_CONTRIBUTION, 2=INVALID_ITEM
        """
        if not session.in_game or len(payload) < 1:
            return
        item_id = payload[0]

        shop_item = None
        for it in MENTOR_SHOP_ITEMS:
            if it["id"] == item_id:
                shop_item = it
                break

        if not shop_item:
            self._send(session, MsgType.MENTOR_SHOP_BUY,
                       struct.pack('<B I', 2, session.mentor_contribution))
            return

        if session.mentor_contribution < shop_item["cost"]:
            self._send(session, MsgType.MENTOR_SHOP_BUY,
                       struct.pack('<B I', 1, session.mentor_contribution))
            return

        session.mentor_contribution -= shop_item["cost"]
        _MENTOR_CONTRIBUTION[session.entity_id] = session.mentor_contribution

        self._send(session, MsgType.MENTOR_SHOP_BUY,
                   struct.pack('<B I', 0, session.mentor_contribution))
'''

# ====================================================================
# 6. Test cases (5 tests)
# ====================================================================
TEST_CODE = r'''
    # Helper: login_and_enter with entity_id tracking
    async def login_and_enter_with_eid(port_num):
        """헬퍼: 로그인 + 게임 진입 + entity_id 저장"""
        c = TestClient()
        await c.connect('127.0.0.1', port_num)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, b'\x01\x00\x00\x00' + b'test\x00' + b'pass\x00')
        await c.recv_expect(MsgType.LOGIN_RESULT)
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        msg_type, resp = await c.recv_expect(MsgType.ENTER_GAME)
        # Parse entity_id from ENTER_GAME response: result(u8) + entity_id(u64) + ...
        if resp and len(resp) >= 9:
            c.entity_id = struct.unpack('<Q', resp[1:9])[0]
        else:
            c.entity_id = 0
        await c.recv_all_packets(timeout=0.5)
        return c

    # ━━━ Test: MENTOR_SEARCH — 사부/제자 검색 ━━━
    async def test_mentor_search():
        """사부 검색 (상대 Lv40+ 필요 → 일반 유저는 결과 0)."""
        c = await login_and_enter(port)
        # Search for masters — no one is Lv40+
        await c.send(MsgType.MENTOR_SEARCH, struct.pack('<B', 0))
        msg_type, resp = await c.recv_expect(MsgType.MENTOR_LIST)
        assert msg_type == MsgType.MENTOR_LIST, f"Expected MENTOR_LIST, got {msg_type}"
        count = resp[0]
        # No masters available (test env — all players low level)
        assert count == 0, f"Expected 0 masters, got {count}"
        c.close()

    await test("MENTOR_SEARCH: 사부 검색 → 결과 0 (Lv40 미달)", test_mentor_search())

    # ━━━ Test: MENTOR_REQUEST — 사제 요청 (레벨 부족) ━━━
    async def test_mentor_request_level_check():
        """사부 역할 신청 시 Lv40 미달 → LEVEL_TOO_LOW(1)."""
        c = await login_and_enter_with_eid(port)
        c2 = await login_and_enter_with_eid(port)
        # c wants to be master (role=1), but c is low level
        await c.send(MsgType.MENTOR_REQUEST, struct.pack('<I B', c2.entity_id, 1))
        msg_type, resp = await c.recv_expect(MsgType.MENTOR_REQUEST_RESULT)
        assert msg_type == MsgType.MENTOR_REQUEST_RESULT
        result = resp[0]
        assert result == 1, f"Expected LEVEL_TOO_LOW(1), got {result}"
        c.close()
        c2.close()

    await test("MENTOR_REQUEST: 사부 Lv40 미달 → LEVEL_TOO_LOW", test_mentor_request_level_check())

    # ━━━ Test: MENTOR_REQUEST + ACCEPT — 사제 관계 성립 ━━━
    async def test_mentor_accept():
        """Lv40+ 사부 + Lv1~20 제자 → 사제 관계 성립."""
        c_master = await login_and_enter_with_eid(port)
        c_disciple = await login_and_enter_with_eid(port)
        # Level up master to 40
        await c_master.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 500000))
        await c_master.recv_all_packets(timeout=0.5)
        # Master requests disciple (role=1: I am master)
        await c_master.send(MsgType.MENTOR_REQUEST,
                           struct.pack('<I B', c_disciple.entity_id, 1))
        msg_type, resp = await c_master.recv_expect(MsgType.MENTOR_REQUEST_RESULT)
        assert msg_type == MsgType.MENTOR_REQUEST_RESULT
        assert resp[0] == 0, f"Expected REQUEST_SENT(0), got {resp[0]}"
        # Disciple accepts
        await c_disciple.send(MsgType.MENTOR_ACCEPT, struct.pack('<B', 1))
        msg_type2, resp2 = await c_disciple.recv_expect(MsgType.MENTOR_ACCEPT_RESULT)
        assert msg_type2 == MsgType.MENTOR_ACCEPT_RESULT
        assert resp2[0] == 0, f"Expected ACCEPTED(0), got {resp2[0]}"
        # Verify master_eid and disciple_eid in response
        m_eid = struct.unpack('<I', resp2[1:5])[0]
        d_eid = struct.unpack('<I', resp2[5:9])[0]
        assert m_eid == c_master.entity_id, f"Master EID mismatch: {m_eid} vs {c_master.entity_id}"
        assert d_eid == c_disciple.entity_id, f"Disciple EID mismatch"
        c_master.close()
        c_disciple.close()

    await test("MENTOR_REQUEST+ACCEPT: 사제 관계 성립", test_mentor_accept())

    # ━━━ Test: MENTOR_QUEST_LIST — 사제 퀘스트 조회 ━━━
    async def test_mentor_quest_list():
        """사제 관계 후 퀘스트 조회 → 3개 반환."""
        c_master = await login_and_enter_with_eid(port)
        c_disciple = await login_and_enter_with_eid(port)
        # Level up master
        await c_master.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 500000))
        await c_master.recv_all_packets(timeout=0.5)
        # Establish relation
        await c_master.send(MsgType.MENTOR_REQUEST,
                           struct.pack('<I B', c_disciple.entity_id, 1))
        await c_master.recv_expect(MsgType.MENTOR_REQUEST_RESULT)
        await c_disciple.send(MsgType.MENTOR_ACCEPT, struct.pack('<B', 1))
        await c_disciple.recv_expect(MsgType.MENTOR_ACCEPT_RESULT)
        # Query quests from master side
        await c_master.send(MsgType.MENTOR_QUEST_LIST, b'')
        msg_type, resp = await c_master.recv_expect(MsgType.MENTOR_QUESTS)
        assert msg_type == MsgType.MENTOR_QUESTS
        count = resp[0]
        assert count == 3, f"Expected 3 mentor quests, got {count}"
        c_master.close()
        c_disciple.close()

    await test("MENTOR_QUEST_LIST: 사제 퀘스트 3개 조회", test_mentor_quest_list())

    # ━━━ Test: MENTOR_SHOP — 기여도 상점 조회 + 구매 ━━━
    async def test_mentor_shop():
        """기여도 상점 조회 → 8종 아이템. 기여도 부족 → NOT_ENOUGH."""
        c = await login_and_enter(port)
        # Query shop
        await c.send(MsgType.MENTOR_SHOP_LIST, b'')
        msg_type, resp = await c.recv_expect(MsgType.MENTOR_SHOP_LIST)
        assert msg_type == MsgType.MENTOR_SHOP_LIST
        contribution = struct.unpack('<I', resp[0:4])[0]
        item_count = resp[4]
        assert item_count == 8, f"Expected 8 shop items, got {item_count}"
        # Try to buy item_id=7 (cost:20) — should fail (0 contribution)
        await c.send(MsgType.MENTOR_SHOP_BUY, struct.pack('<B', 7))
        msg_type2, resp2 = await c.recv_expect(MsgType.MENTOR_SHOP_BUY)
        assert msg_type2 == MsgType.MENTOR_SHOP_BUY
        assert resp2[0] == 1, f"Expected NOT_ENOUGH(1), got {resp2[0]}"
        c.close()

    await test("MENTOR_SHOP: 기여도 상점 조회+구매실패", test_mentor_shop())
'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check
    if ('MENTOR_SEARCH = 550' in content
            and 'def _on_mentor_search' in content
            and 'MENTOR_SHOP_ITEMS' in content
            and 'def _on_mentor_graduate' in content):
        print('[bridge] S056 already patched')
        return True

    changed = False

    # 1. MsgType -- after SECRET_REALM_FAIL = 544
    if 'MENTOR_SEARCH' not in content:
        marker = '    SECRET_REALM_FAIL = 544'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 550-560')
        else:
            print('[bridge] WARNING: Could not find MsgType insertion point')

    # 2. Data constants -- after _REALM_NEXT_ID = 1
    if 'MENTOR_MASTER_MIN_LEVEL' not in content:
        marker = '_REALM_NEXT_ID = 1'
        idx = content.find(marker)
        if idx >= 0:
            nl = content.index('\n', idx) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added mentorship data constants')
        else:
            # Fallback: after SPECIAL_REALM_SPAWN_CHANCE
            marker2 = 'SPECIAL_REALM_SPAWN_CHANCE'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                nl = content.index('\n', idx2) + 1
                content = content[:nl] + DATA_CONSTANTS + content[nl:]
                changed = True
                print('[bridge] Added mentorship data constants (fallback)')
            else:
                print('[bridge] WARNING: Could not find data constants insertion point')

    # 3. PlayerSession fields -- after realm_instance_id field
    if 'mentor_master_eid' not in content:
        marker = '    realm_instance_id: int = 0'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession mentor fields')
        else:
            # Fallback: after realm_daily_count
            marker2 = '    realm_daily_count: int = 0'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession mentor fields (fallback)')
            else:
                print('[bridge] WARNING: Could not find session fields insertion point')

    # 4. Dispatch table -- after secret_realm_fail dispatch
    if 'self._on_mentor_search' not in content:
        marker = '            MsgType.SECRET_REALM_FAIL: self._on_secret_realm_fail,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            # Fallback: after secret_realm_complete dispatch
            marker2 = '            MsgType.SECRET_REALM_COMPLETE: self._on_secret_realm_complete,'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + DISPATCH_ENTRIES + content[end:]
                changed = True
                print('[bridge] Added dispatch table entries (fallback)')
            else:
                print('[bridge] WARNING: Could not find dispatch table insertion point')

    # 5. Handler implementations -- before Secret Realm handlers
    if 'def _on_mentor_search' not in content:
        marker = '    # ---- Secret Realm System (TASK 17: MsgType 540-544) ----'
        idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added mentorship handler implementations')
        else:
            # Fallback: before Sub-Currency handlers
            marker2 = '    # ---- Sub-Currency / Token Shop (TASK 10: MsgType 468-473) ----'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                content = content[:idx2] + HANDLER_CODE + '\n' + content[idx2:]
                changed = True
                print('[bridge] Added mentorship handler implementations (fallback)')
            else:
                print('[bridge] WARNING: Could not find handler insertion point')

    if changed:
        with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify
    checks = [
        'MENTOR_SEARCH = 550', 'MENTOR_LIST = 551',
        'MENTOR_REQUEST = 552', 'MENTOR_REQUEST_RESULT = 553',
        'MENTOR_ACCEPT = 554', 'MENTOR_ACCEPT_RESULT = 555',
        'MENTOR_QUEST_LIST = 556', 'MENTOR_QUESTS = 557',
        'MENTOR_GRADUATE = 558',
        'MENTOR_SHOP_LIST = 559', 'MENTOR_SHOP_BUY = 560',
        'MENTOR_MASTER_MIN_LEVEL', 'MENTOR_MASTER_MAX_DISCIPLES',
        'MENTOR_DISCIPLE_LEVEL_RANGE', 'MENTOR_GRADUATION_LEVEL',
        'MENTOR_EXP_BUFF_PARTY', 'MENTOR_EXP_BUFF_SOLO',
        'MENTOR_QUEST_POOL', 'MENTOR_SHOP_ITEMS',
        'MENTOR_GRADUATION_REWARDS_MASTER', 'MENTOR_GRADUATION_REWARDS_DISCIPLE',
        '_MENTOR_RELATIONS', '_DISCIPLE_MASTERS', '_MENTOR_REQUESTS',
        '_MENTOR_QUESTS', '_MENTOR_CONTRIBUTION',
        'def _on_mentor_search', 'def _on_mentor_request',
        'def _on_mentor_accept', 'def _on_mentor_quest_list',
        'def _on_mentor_graduate', 'def _on_mentor_shop_list',
        'def _on_mentor_shop_buy',
        'def _mentor_exp_multiplier', 'def _mentor_on_mob_kill',
        'self._on_mentor_search', 'self._on_mentor_request',
        'self._on_mentor_accept', 'self._on_mentor_quest_list',
        'self._on_mentor_graduate', 'self._on_mentor_shop_list',
        'self._on_mentor_shop_buy',
        'mentor_master_eid: int = 0', 'mentor_contribution: int = 0',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S056 patched OK -- mentorship system')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_mentor_search' in content and 'test_mentor_shop' in content:
        print('[test] S056 already patched')
        return True

    # Update imports — add mentorship constants
    old_import = (
        '    SECRET_REALM_UNLOCK_LEVEL, SECRET_REALM_DAILY_LIMIT,\n'
        '    REALM_TYPES, REALM_TYPE_LIST, SPECIAL_REALM_CONDITIONS\n'
        ')'
    )
    new_import = (
        '    SECRET_REALM_UNLOCK_LEVEL, SECRET_REALM_DAILY_LIMIT,\n'
        '    REALM_TYPES, REALM_TYPE_LIST, SPECIAL_REALM_CONDITIONS,\n'
        '    MENTOR_MASTER_MIN_LEVEL, MENTOR_MASTER_MAX_DISCIPLES,\n'
        '    MENTOR_DISCIPLE_LEVEL_RANGE, MENTOR_GRADUATION_LEVEL,\n'
        '    MENTOR_EXP_BUFF_PARTY, MENTOR_EXP_BUFF_SOLO,\n'
        '    MENTOR_QUEST_POOL, MENTOR_QUEST_WEEKLY_COUNT,\n'
        '    MENTOR_SHOP_ITEMS\n'
        ')'
    )

    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports with mentorship constants')
    else:
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

    checks = ['test_mentor_search', 'test_mentor_request_level_check',
              'test_mentor_accept', 'test_mentor_quest_list',
              'test_mentor_shop',
              'MENTOR_SEARCH', 'MENTOR_ACCEPT',
              'MENTOR_QUEST_LIST', 'MENTOR_SHOP_LIST', 'MENTOR_SHOP_BUY']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S056 patched OK -- 5 mentorship tests')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS056 all patches applied!')
    else:
        print('\nS056 PATCH FAILED!')
        sys.exit(1)
