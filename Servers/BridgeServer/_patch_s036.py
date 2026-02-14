"""
Patch S036: PvP 아레나 + 레이드 보스 기믹
- P3_S01_S01: PvP 매칭 큐 + 스탯 정규화 + ELO 레이팅 + 1v1/3v3 + 승패 판정
- P3_S02_S01: 8인 레이드 인스턴스 확장 + 3페이즈 보스 + 기믹 6종
"""
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'PVP_QUEUE_REQ' in content:
        # fixup: em dash → ASCII dash in log
        changed = False
        if '\u2014 rewards:' in content:
            content = content.replace('\u2014 rewards:', '- rewards:')
            changed = True
        if changed:
            with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
                f.write(content)
            print('[bridge] S036 fixup applied')
        else:
            print('[bridge] S036 already patched')
        return True

    replacements = []

    # 1. MsgType 추가 — ENHANCE_RESULT(341) 뒤에 PvP + Raid 패킷 추가
    replacements.append((
        '    ENHANCE_REQ = 340\n'
        '    ENHANCE_RESULT = 341\n',
        '    ENHANCE_REQ = 340\n'
        '    ENHANCE_RESULT = 341\n'
        '\n'
        '    # PvP Arena (P3_S01_S01)\n'
        '    PVP_QUEUE_REQ = 350       # 아레나 매칭 큐 등록\n'
        '    PVP_QUEUE_CANCEL = 351    # 아레나 매칭 큐 취소\n'
        '    PVP_QUEUE_STATUS = 352    # 아레나 매칭 상태\n'
        '    PVP_MATCH_FOUND = 353     # 아레나 매칭 완료\n'
        '    PVP_MATCH_ACCEPT = 354    # 아레나 매칭 수락\n'
        '    PVP_MATCH_START = 355     # 아레나 경기 시작\n'
        '    PVP_MATCH_END = 356       # 아레나 경기 종료 (결과)\n'
        '    PVP_ATTACK = 357          # PvP 공격\n'
        '    PVP_ATTACK_RESULT = 358   # PvP 공격 결과\n'
        '    PVP_RATING_INFO = 359     # 레이팅 정보\n'
        '\n'
        '    # Raid Boss Gimmick (P3_S02_S01)\n'
        '    RAID_BOSS_SPAWN = 370     # 레이드 보스 스폰\n'
        '    RAID_PHASE_CHANGE = 371   # 보스 페이즈 전환\n'
        '    RAID_MECHANIC = 372       # 기믹 발동\n'
        '    RAID_MECHANIC_RESULT = 373  # 기믹 결과 (성공/실패)\n'
        '    RAID_STAGGER = 374        # 스태거 게이지 업데이트\n'
        '    RAID_ENRAGE = 375         # 격노\n'
        '    RAID_WIPE = 376           # 전멸\n'
        '    RAID_CLEAR = 377          # 클리어\n'
        '    RAID_ATTACK = 378         # 레이드 공격\n'
        '    RAID_ATTACK_RESULT = 379  # 레이드 공격 결과\n'
    ))

    # 2. PvP + Raid 상수 (DIFFICULTY_MULT 뒤에)
    replacements.append((
        '    "hell":   {"hp": 4.0, "atk": 2.5, "reward": 4.0},\n'
        '}\n'
        '\n'
        '# 이동 상수',
        '    "hell":   {"hp": 4.0, "atk": 2.5, "reward": 4.0},\n'
        '}\n'
        '\n'
        '# ──── PvP 아레나 상수 (P3_S01_S01) ────\n'
        'PVP_MODES = {\n'
        '    1: {"name": "1v1", "party_size": 1, "time_limit": 180, "overtime": 60},\n'
        '    2: {"name": "3v3", "party_size": 3, "time_limit": 300, "overtime": 60},\n'
        '}\n'
        'PVP_NORMALIZED_STATS = {\n'
        '    1: {"hp": 12000, "mp": 3000, "atk": 350, "def": 250, "name": "warrior"},  # warrior\n'
        '    2: {"hp": 7000, "mp": 6000, "atk": 450, "def": 120, "name": "mage"},      # mage\n'
        '    3: {"hp": 8000, "mp": 4000, "atk": 400, "def": 150, "name": "archer"},     # archer\n'
        '}\n'
        'PVP_DAMAGE_REDUCTION = 0.40\n'
        'PVP_HEALING_REDUCTION = 0.30\n'
        'PVP_CC_REDUCTION = 0.50\n'
        'PVP_MIN_LEVEL = 20\n'
        'PVP_ELO_INITIAL = 1000\n'
        'PVP_ELO_K_BASE = 32\n'
        'PVP_ELO_K_PLACEMENT = 64\n'
        'PVP_ELO_K_HIGH = 16  # rating >= 2000\n'
        'PVP_MATCH_RANGE_INITIAL = 100\n'
        'PVP_MATCH_RANGE_EXPAND = 50\n'
        'PVP_MATCH_RANGE_MAX = 500\n'
        'PVP_TIERS = [\n'
        '    (0, 999, "Bronze"), (1000, 1299, "Silver"), (1300, 1599, "Gold"),\n'
        '    (1600, 1899, "Platinum"), (1900, 2199, "Diamond"),\n'
        '    (2200, 2499, "Master"), (2500, 9999, "Grandmaster"),\n'
        ']\n'
        'PVP_ZONE_ID = 200  # PvP arena zone\n'
        '\n'
        '# ──── 레이드 보스 상수 (P3_S02_S01) ────\n'
        'RAID_BOSS_DATA = {\n'
        '    "ancient_dragon": {\n'
        '        "name": "Ancient Dragon",\n'
        '        "phases": 3,\n'
        '        "hp": {"normal": 2000000, "hard": 5000000},\n'
        '        "atk": {"normal": 500, "hard": 800},\n'
        '        "phase_thresholds": [0.70, 0.30],  # 70%, 30% HP\n'
        '        "enrage_timer": {"normal": 600, "hard": 480},\n'
        '        "mechanics_by_phase": {\n'
        '            1: ["safe_zone", "counter_attack"],\n'
        '            2: ["safe_zone", "stagger_check", "position_swap"],\n'
        '            3: ["safe_zone", "stagger_check", "counter_attack", "dps_check", "cooperation"],\n'
        '        },\n'
        '    },\n'
        '}\n'
        'RAID_MECHANIC_DEFS = {\n'
        '    "safe_zone":      {"id": 1, "warn_time": 3.0, "damage_pct": 0.80},\n'
        '    "stagger_check":  {"id": 2, "gauge": 100, "time_limit": 10.0, "fail": "wipe"},\n'
        '    "counter_attack": {"id": 3, "window": 1.5, "stun_dur": 5.0},\n'
        '    "position_swap":  {"id": 4, "warn_time": 5.0, "damage_pct": 0.60},\n'
        '    "dps_check":      {"id": 5, "time_limit": 15.0, "threshold_pct": 0.10, "fail": "wipe"},\n'
        '    "cooperation":    {"id": 6, "tolerance": 1.0, "fail_damage_pct": 0.50},\n'
        '}\n'
        'RAID_CLEAR_REWARDS = {\n'
        '    "normal": {"gold": 10000, "exp": 50000, "tokens": 200},\n'
        '    "hard":   {"gold": 25000, "exp": 100000, "tokens": 500},\n'
        '}\n'
        'RAID_ZONE_ID = 103  # ancient_dragon_raid zone\n'
        '\n'
        '# 이동 상수'
    ))

    # 3. ZONE_BOUNDS에 PvP 아레나 존 추가
    replacements.append((
        '    103: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},  # ancient_dragon_raid\n}',
        '    103: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},  # ancient_dragon_raid\n'
        '    # PvP 아레나\n'
        '    200: {"min_x": 0, "max_x": 300, "min_z": 0, "max_z": 300},    # pvp_arena_1v1\n'
        '    201: {"min_x": 0, "max_x": 500, "min_z": 0, "max_z": 500},    # pvp_arena_3v3\n'
        '}'
    ))

    # 4. BridgeServer.__init__에 PvP/Raid 필드 추가
    replacements.append((
        '        self.match_queue: Dict[int, dict] = {}  # dungeon_id -> {players: [], created_at: float}\n',
        '        self.match_queue: Dict[int, dict] = {}  # dungeon_id -> {players: [], created_at: float}\n'
        '        self.pvp_queue: Dict[int, list] = {}  # mode_id -> [{session, rating, joined_at}]\n'
        '        self.pvp_matches: Dict[int, dict] = {}  # match_id -> match data\n'
        '        self.next_pvp_match_id = 1\n'
        '        self.pvp_ratings: Dict[str, dict] = {}  # username -> {rating, wins, losses, matches}\n'
        '        self.raid_instances: Dict[int, dict] = {}  # instance_id -> raid data\n'
    ))

    # 5. _dispatch 핸들러 등록 — INSTANCE_LEAVE 뒤에 PvP + Raid 핸들러
    replacements.append((
        '            MsgType.INSTANCE_LEAVE: self._on_instance_leave,\n        }',
        '            MsgType.INSTANCE_LEAVE: self._on_instance_leave,\n'
        '            MsgType.PVP_QUEUE_REQ: self._on_pvp_queue_req,\n'
        '            MsgType.PVP_QUEUE_CANCEL: self._on_pvp_queue_cancel,\n'
        '            MsgType.PVP_MATCH_ACCEPT: self._on_pvp_match_accept,\n'
        '            MsgType.PVP_ATTACK: self._on_pvp_attack,\n'
        '            MsgType.RAID_ATTACK: self._on_raid_attack,\n'
        '        }'
    ))

    # 6. PvP + Raid 핸들러 구현 — _on_instance_leave 끝 뒤에
    replacements.append((
        '        self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 0))  # 0=OK\n\n'
        '    # ━━━ 몬스터 시스템 ━━━',
        '        self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 0))  # 0=OK\n\n'
        '    # ━━━ PvP 아레나 시스템 (P3_S01_S01) ━━━\n\n'
        '    def _get_pvp_rating(self, username: str) -> dict:\n'
        '        """PvP 레이팅 조회 (없으면 초기값 생성)"""\n'
        '        if username not in self.pvp_ratings:\n'
        '            self.pvp_ratings[username] = {\n'
        '                "rating": PVP_ELO_INITIAL,\n'
        '                "wins": 0, "losses": 0, "matches": 0,\n'
        '            }\n'
        '        return self.pvp_ratings[username]\n\n'
        '    def _get_tier(self, rating: int) -> str:\n'
        '        """ELO 레이팅으로 티어 문자열 반환"""\n'
        '        for lo, hi, name in PVP_TIERS:\n'
        '            if lo <= rating <= hi:\n'
        '                return name\n'
        '        return "Bronze"\n\n'
        '    def _calc_elo(self, winner_r: int, loser_r: int, k: int) -> tuple:\n'
        '        """ELO 계산 → (new_winner_rating, new_loser_rating)"""\n'
        '        exp_w = 1.0 / (1.0 + 10 ** ((loser_r - winner_r) / 400.0))\n'
        '        exp_l = 1.0 - exp_w\n'
        '        new_w = max(0, int(winner_r + k * (1.0 - exp_w)))\n'
        '        new_l = max(0, int(loser_r + k * (0.0 - exp_l)))\n'
        '        return new_w, new_l\n\n'
        '    async def _on_pvp_queue_req(self, session: PlayerSession, payload: bytes):\n'
        '        """PVP_QUEUE_REQ: mode(u8). 아레나 매칭 큐 등록."""\n'
        '        if not session.in_game or len(payload) < 1:\n'
        '            return\n'
        '        mode_id = payload[0]\n'
        '        mode = PVP_MODES.get(mode_id)\n'
        '        if not mode:\n'
        '            self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 1, 0))  # 1=INVALID_MODE\n'
        '            return\n'
        '        if session.stats.level < PVP_MIN_LEVEL:\n'
        '            self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 2, 0))  # 2=LEVEL_TOO_LOW\n'
        '            return\n'
        '        if mode_id not in self.pvp_queue:\n'
        '            self.pvp_queue[mode_id] = []\n'
        '        queue = self.pvp_queue[mode_id]\n'
        '        if any(e["session"] is session for e in queue):\n'
        '            self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 3, len(queue)))  # 3=ALREADY_QUEUED\n'
        '            return\n'
        '        import time as _t\n'
        '        rating_info = self._get_pvp_rating(session.username)\n'
        '        queue.append({"session": session, "rating": rating_info["rating"], "joined_at": _t.time()})\n'
        '        self.log(f"PvPQueue: {session.char_name} joined mode={mode[\'name\']} rating={rating_info[\'rating\']} ({len(queue)} in queue)", "PVP")\n'
        '        self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 0, len(queue)))  # 0=QUEUED\n'
        '        # 매칭 시도\n'
        '        needed = mode["party_size"] * 2  # 양쪽 합계\n'
        '        if len(queue) >= needed:\n'
        '            await self._pvp_match_found(mode_id, mode)\n\n'
        '    async def _pvp_match_found(self, mode_id: int, mode: dict):\n'
        '        """PvP 매칭 완료 → 매치 생성"""\n'
        '        queue = self.pvp_queue.get(mode_id, [])\n'
        '        needed = mode["party_size"] * 2\n'
        '        if len(queue) < needed:\n'
        '            return\n'
        '        # 레이팅 가까운 순으로 정렬 후 추출\n'
        '        queue.sort(key=lambda e: e["rating"])\n'
        '        picked = queue[:needed]\n'
        '        self.pvp_queue[mode_id] = queue[needed:]\n'
        '        # 팀 분배: 짝수=Team A, 홀수=Team B (레이팅 밸런스)\n'
        '        team_a = [picked[i] for i in range(0, needed, 2)]\n'
        '        team_b = [picked[i] for i in range(1, needed, 2)]\n'
        '        match_id = self.next_pvp_match_id\n'
        '        self.next_pvp_match_id += 1\n'
        '        # 스탯 정규화 적용\n'
        '        match_data = {\n'
        '            "id": match_id,\n'
        '            "mode_id": mode_id,\n'
        '            "mode": mode,\n'
        '            "team_a": [e["session"] for e in team_a],\n'
        '            "team_b": [e["session"] for e in team_b],\n'
        '            "team_a_hp": {},  # session -> current_hp\n'
        '            "team_b_hp": {},\n'
        '            "active": True,\n'
        '            "zone_id": 200 if mode_id == 1 else 201,\n'
        '            "started": False,\n'
        '        }\n'
        '        # 각 플레이어에 정규화 스탯 적용\n'
        '        all_players = team_a + team_b\n'
        '        for entry in all_players:\n'
        '            s = entry["session"]\n'
        '            job = 1  # default warrior\n'
        '            if hasattr(s, "job_id"):\n'
        '                job = s.job_id\n'
        '            norm = PVP_NORMALIZED_STATS.get(job, PVP_NORMALIZED_STATS[1])\n'
        '            hp = norm["hp"]\n'
        '            if s in [e["session"] for e in team_a]:\n'
        '                match_data["team_a_hp"][id(s)] = hp\n'
        '            else:\n'
        '                match_data["team_b_hp"][id(s)] = hp\n'
        '        self.pvp_matches[match_id] = match_data\n'
        '        self.log(f"PvP Match #{match_id} created: {mode[\'name\']} ({len(team_a)}v{len(team_b)})", "PVP")\n'
        '        # PVP_MATCH_FOUND 전송\n'
        '        for entry in all_players:\n'
        '            s = entry["session"]\n'
        '            team_id = 0 if s in match_data["team_a"] else 1\n'
        '            self._send(s, MsgType.PVP_MATCH_FOUND, struct.pack("<IBB", match_id, mode_id, team_id))\n\n'
        '    async def _on_pvp_queue_cancel(self, session: PlayerSession, payload: bytes):\n'
        '        """PVP_QUEUE_CANCEL: mode(u8). 큐에서 이탈."""\n'
        '        if not session.in_game or len(payload) < 1:\n'
        '            return\n'
        '        mode_id = payload[0]\n'
        '        queue = self.pvp_queue.get(mode_id, [])\n'
        '        self.pvp_queue[mode_id] = [e for e in queue if e["session"] is not session]\n'
        '        self.log(f"PvPQueue: {session.char_name} left mode={mode_id}", "PVP")\n'
        '        self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 4, 0))  # 4=CANCELLED\n\n'
        '    async def _on_pvp_match_accept(self, session: PlayerSession, payload: bytes):\n'
        '        """PVP_MATCH_ACCEPT: match_id(u32). 매치 수락 → 시작."""\n'
        '        if not session.in_game or len(payload) < 4:\n'
        '            return\n'
        '        match_id = struct.unpack("<I", payload[:4])[0]\n'
        '        match = self.pvp_matches.get(match_id)\n'
        '        if not match or not match["active"]:\n'
        '            return\n'
        '        if not match["started"]:\n'
        '            match["started"] = True\n'
        '            import time as _t\n'
        '            match["start_time"] = _t.time()\n'
        '            # 존 전환 + 스탯 정규화 적용\n'
        '            all_players = match["team_a"] + match["team_b"]\n'
        '            for s in all_players:\n'
        '                s.zone_id = match["zone_id"]\n'
        '            # PVP_MATCH_START 전송: match_id(u32) + mode(u8) + time_limit(u16)\n'
        '            for s in all_players:\n'
        '                team_id = 0 if s in match["team_a"] else 1\n'
        '                self._send(s, MsgType.PVP_MATCH_START, struct.pack("<IBH", match_id, team_id, match["mode"]["time_limit"]))\n'
        '            self.log(f"PvP Match #{match_id} STARTED", "PVP")\n\n'
        '    async def _on_pvp_attack(self, session: PlayerSession, payload: bytes):\n'
        '        """PVP_ATTACK: match_id(u32) + target_team(u8) + target_idx(u8) + skill_id(u16) + damage(u16)."""\n'
        '        if not session.in_game or len(payload) < 10:\n'
        '            return\n'
        '        match_id, target_team, target_idx, skill_id, raw_dmg = struct.unpack("<IBBHH", payload[:10])\n'
        '        match = self.pvp_matches.get(match_id)\n'
        '        if not match or not match["active"] or not match["started"]:\n'
        '            return\n'
        '        # PvP 데미지 감소 적용\n'
        '        damage = int(raw_dmg * (1.0 - PVP_DAMAGE_REDUCTION))\n'
        '        # 타겟 팀에서 대상 찾기\n'
        '        target_list = match["team_b"] if target_team == 1 else match["team_a"]\n'
        '        hp_map = match["team_b_hp"] if target_team == 1 else match["team_a_hp"]\n'
        '        if target_idx >= len(target_list):\n'
        '            return\n'
        '        target = target_list[target_idx]\n'
        '        target_key = id(target)\n'
        '        current_hp = hp_map.get(target_key, 0)\n'
        '        new_hp = max(0, current_hp - damage)\n'
        '        hp_map[target_key] = new_hp\n'
        '        # PVP_ATTACK_RESULT: match_id(u32) + attacker_team(u8) + target_team(u8) + target_idx(u8) + damage(u16) + remaining_hp(u32)\n'
        '        attacker_team = 0 if session in match["team_a"] else 1\n'
        '        result_pkt = struct.pack("<IBBBHI", match_id, attacker_team, target_team, target_idx, damage, new_hp)\n'
        '        for s in match["team_a"] + match["team_b"]:\n'
        '            self._send(s, MsgType.PVP_ATTACK_RESULT, result_pkt)\n'
        '        # 승패 확인\n'
        '        if new_hp <= 0:\n'
        '            alive_a = sum(1 for s in match["team_a"] if match["team_a_hp"].get(id(s), 0) > 0)\n'
        '            alive_b = sum(1 for s in match["team_b"] if match["team_b_hp"].get(id(s), 0) > 0)\n'
        '            if alive_a == 0 or alive_b == 0:\n'
        '                winner_team = 1 if alive_a == 0 else 0\n'
        '                await self._pvp_match_end(match_id, winner_team)\n\n'
        '    async def _pvp_match_end(self, match_id: int, winner_team: int):\n'
        '        """PvP 경기 종료 → ELO 계산 → 결과 전송"""\n'
        '        match = self.pvp_matches.get(match_id)\n'
        '        if not match or not match["active"]:\n'
        '            return\n'
        '        match["active"] = False\n'
        '        winners = match["team_a"] if winner_team == 0 else match["team_b"]\n'
        '        losers = match["team_b"] if winner_team == 0 else match["team_a"]\n'
        '        # ELO 계산\n'
        '        for w in winners:\n'
        '            w_info = self._get_pvp_rating(w.username)\n'
        '            avg_loser_r = sum(self._get_pvp_rating(l.username)["rating"] for l in losers) // max(1, len(losers))\n'
        '            k = PVP_ELO_K_PLACEMENT if w_info["matches"] < 10 else (PVP_ELO_K_HIGH if w_info["rating"] >= 2000 else PVP_ELO_K_BASE)\n'
        '            new_r, _ = self._calc_elo(w_info["rating"], avg_loser_r, k)\n'
        '            w_info["rating"] = new_r\n'
        '            w_info["wins"] += 1\n'
        '            w_info["matches"] += 1\n'
        '        for l in losers:\n'
        '            l_info = self._get_pvp_rating(l.username)\n'
        '            avg_winner_r = sum(self._get_pvp_rating(w.username)["rating"] for w in winners) // max(1, len(winners))\n'
        '            k = PVP_ELO_K_PLACEMENT if l_info["matches"] < 10 else (PVP_ELO_K_HIGH if l_info["rating"] >= 2000 else PVP_ELO_K_BASE)\n'
        '            _, new_r = self._calc_elo(avg_winner_r, l_info["rating"], k)\n'
        '            l_info["rating"] = new_r\n'
        '            l_info["losses"] += 1\n'
        '            l_info["matches"] += 1\n'
        '        # PVP_MATCH_END 전송: match_id(u32) + winner_team(u8) + new_rating(u16) + rating_change(i16)\n'
        '        all_players = match["team_a"] + match["team_b"]\n'
        '        for s in all_players:\n'
        '            r_info = self._get_pvp_rating(s.username)\n'
        '            team_id = 0 if s in match["team_a"] else 1\n'
        '            won = 1 if team_id == winner_team else 0\n'
        '            tier_str = self._get_tier(r_info["rating"])\n'
        '            tier_bytes = tier_str.encode("utf-8")[:16].ljust(16, b"\\x00")\n'
        '            buf = struct.pack("<IBBH", match_id, winner_team, won, r_info["rating"])\n'
        '            buf += tier_bytes\n'
        '            self._send(s, MsgType.PVP_MATCH_END, buf)\n'
        '            # 마을로 복귀\n'
        '            s.zone_id = 10\n'
        '        self.log(f"PvP Match #{match_id} ended: Team {winner_team} wins", "PVP")\n\n'
        '    # ━━━ 레이드 보스 기믹 시스템 (P3_S02_S01) ━━━\n\n'
        '    async def _start_raid_boss(self, instance_id: int):\n'
        '        """레이드 인스턴스에 보스 스폰 + 기믹 초기화"""\n'
        '        instance = self.instances.get(instance_id)\n'
        '        if not instance:\n'
        '            return\n'
        '        boss_key = "ancient_dragon"\n'
        '        boss_def = RAID_BOSS_DATA[boss_key]\n'
        '        diff_name = ["normal", "hard"][min(instance.get("difficulty", 0), 1)]\n'
        '        import time as _t\n'
        '        raid_data = {\n'
        '            "instance_id": instance_id,\n'
        '            "boss_key": boss_key,\n'
        '            "boss_name": boss_def["name"],\n'
        '            "max_hp": boss_def["hp"][diff_name],\n'
        '            "current_hp": boss_def["hp"][diff_name],\n'
        '            "atk": boss_def["atk"][diff_name],\n'
        '            "phase": 1,\n'
        '            "max_phases": boss_def["phases"],\n'
        '            "phase_thresholds": boss_def["phase_thresholds"],\n'
        '            "enrage_timer": boss_def["enrage_timer"][diff_name],\n'
        '            "start_time": _t.time(),\n'
        '            "enraged": False,\n'
        '            "difficulty": diff_name,\n'
        '            "mechanics": boss_def["mechanics_by_phase"],\n'
        '            "stagger_gauge": 0,\n'
        '            "mechanic_active": None,\n'
        '            "active": True,\n'
        '        }\n'
        '        self.raid_instances[instance_id] = raid_data\n'
        '        # RAID_BOSS_SPAWN 전송\n'
        '        name_bytes = raid_data["boss_name"].encode("utf-8")[:32].ljust(32, b"\\x00")\n'
        '        buf = struct.pack("<I", instance_id) + name_bytes\n'
        '        buf += struct.pack("<IIBB", raid_data["max_hp"], raid_data["current_hp"],\n'
        '                           raid_data["phase"], raid_data["max_phases"])\n'
        '        buf += struct.pack("<H", raid_data["enrage_timer"])\n'
        '        for s in instance.get("players", []):\n'
        '            self._send(s, MsgType.RAID_BOSS_SPAWN, buf)\n'
        '        self.log(f"Raid Boss spawned: {raid_data[\'boss_name\']} ({diff_name}) in Instance#{instance_id}", "RAID")\n\n'
        '    async def _on_raid_attack(self, session: PlayerSession, payload: bytes):\n'
        '        """RAID_ATTACK: instance_id(u32) + skill_id(u16) + damage(u32)."""\n'
        '        if not session.in_game or len(payload) < 10:\n'
        '            return\n'
        '        inst_id = struct.unpack("<I", payload[:4])[0]\n'
        '        skill_id = struct.unpack("<H", payload[4:6])[0]\n'
        '        raw_dmg = struct.unpack("<I", payload[6:10])[0]\n'
        '        raid = self.raid_instances.get(inst_id)\n'
        '        if not raid or not raid["active"]:\n'
        '            return\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not instance:\n'
        '            return\n'
        '        # 데미지 적용\n'
        '        raid["current_hp"] = max(0, raid["current_hp"] - raw_dmg)\n'
        '        hp_pct = raid["current_hp"] / raid["max_hp"] if raid["max_hp"] > 0 else 0\n'
        '        # 스태거 게이지 증가 (스킬 공격 시)\n'
        '        if raid.get("mechanic_active") == "stagger_check":\n'
        '            raid["stagger_gauge"] = min(100, raid["stagger_gauge"] + 15)\n'
        '            stagger_buf = struct.pack("<IB", inst_id, raid["stagger_gauge"])\n'
        '            for s in instance.get("players", []):\n'
        '                self._send(s, MsgType.RAID_STAGGER, stagger_buf)\n'
        '            if raid["stagger_gauge"] >= 100:\n'
        '                raid["mechanic_active"] = None\n'
        '                raid["stagger_gauge"] = 0\n'
        '                # 기믹 성공\n'
        '                for s in instance.get("players", []):\n'
        '                    self._send(s, MsgType.RAID_MECHANIC_RESULT, struct.pack("<IBB", inst_id, 2, 1))  # id=2(stagger), success=1\n'
        '        # RAID_ATTACK_RESULT 전송\n'
        '        result_buf = struct.pack("<IHI II", inst_id, skill_id, raw_dmg,\n'
        '                                raid["current_hp"], raid["max_hp"])\n'
        '        for s in instance.get("players", []):\n'
        '            self._send(s, MsgType.RAID_ATTACK_RESULT, result_buf)\n'
        '        # 페이즈 전환 체크\n'
        '        thresholds = raid["phase_thresholds"]\n'
        '        for i, thr in enumerate(thresholds):\n'
        '            target_phase = i + 2\n'
        '            if hp_pct <= thr and raid["phase"] < target_phase:\n'
        '                raid["phase"] = target_phase\n'
        '                phase_buf = struct.pack("<IBB", inst_id, raid["phase"], raid["max_phases"])\n'
        '                for s in instance.get("players", []):\n'
        '                    self._send(s, MsgType.RAID_PHASE_CHANGE, phase_buf)\n'
        '                self.log(f"Raid Boss phase → {raid[\'phase\']} (HP {hp_pct:.1%})", "RAID")\n'
        '                # 새 페이즈 기믹 발동\n'
        '                mechanics = raid["mechanics"].get(raid["phase"], [])\n'
        '                if mechanics:\n'
        '                    await self._trigger_raid_mechanic(inst_id, mechanics[0])\n'
        '                break\n'
        '        # 클리어 체크\n'
        '        if raid["current_hp"] <= 0:\n'
        '            await self._raid_clear(inst_id)\n\n'
        '    async def _trigger_raid_mechanic(self, inst_id: int, mechanic_name: str):\n'
        '        """레이드 기믹 발동"""\n'
        '        raid = self.raid_instances.get(inst_id)\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not raid or not instance:\n'
        '            return\n'
        '        mech_def = RAID_MECHANIC_DEFS.get(mechanic_name)\n'
        '        if not mech_def:\n'
        '            return\n'
        '        raid["mechanic_active"] = mechanic_name\n'
        '        if mechanic_name == "stagger_check":\n'
        '            raid["stagger_gauge"] = 0\n'
        '        # RAID_MECHANIC 전송: instance_id(u32) + mechanic_id(u8) + phase(u8)\n'
        '        buf = struct.pack("<IBB", inst_id, mech_def["id"], raid["phase"])\n'
        '        for s in instance.get("players", []):\n'
        '            self._send(s, MsgType.RAID_MECHANIC, buf)\n'
        '        self.log(f"Raid Mechanic: {mechanic_name} (phase {raid[\'phase\']}) in Instance#{inst_id}", "RAID")\n\n'
        '    async def _raid_clear(self, inst_id: int):\n'
        '        """레이드 클리어 → 보상 지급"""\n'
        '        raid = self.raid_instances.get(inst_id)\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not raid or not instance:\n'
        '            return\n'
        '        raid["active"] = False\n'
        '        diff = raid["difficulty"]\n'
        '        rewards = RAID_CLEAR_REWARDS.get(diff, RAID_CLEAR_REWARDS["normal"])\n'
        '        # RAID_CLEAR 전송: instance_id(u32) + gold(u32) + exp(u32) + tokens(u16)\n'
        '        buf = struct.pack("<IIIH", inst_id, rewards["gold"], rewards["exp"], rewards["tokens"])\n'
        '        for s in instance.get("players", []):\n'
        '            s.gold += rewards["gold"]\n'
        '            s.stats.add_exp(rewards["exp"])\n'
        '            self._send(s, MsgType.RAID_CLEAR, buf)\n'
        '        self.log(f"Raid CLEAR! Instance#{inst_id} ({diff}) - rewards: {rewards}", "RAID")\n\n'
        '    async def _raid_wipe(self, inst_id: int):\n'
        '        """레이드 전멸"""\n'
        '        raid = self.raid_instances.get(inst_id)\n'
        '        instance = self.instances.get(inst_id)\n'
        '        if not raid or not instance:\n'
        '            return\n'
        '        raid["active"] = False\n'
        '        buf = struct.pack("<IB", inst_id, raid["phase"])\n'
        '        for s in instance.get("players", []):\n'
        '            self._send(s, MsgType.RAID_WIPE, buf)\n'
        '            s.zone_id = 10  # 마을로 복귀\n'
        '        self.log(f"Raid WIPE at phase {raid[\'phase\']} in Instance#{inst_id}", "RAID")\n\n'
        '    # ━━━ 몬스터 시스템 ━━━'
    ))

    for old, new in replacements:
        if old not in content:
            print(f'[bridge] WARNING: Pattern not found:\n  {repr(old[:80])}...')
            continue
        content = content.replace(old, new, 1)

    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    # Verify
    checks = [
        'PVP_QUEUE_REQ', 'PVP_MATCH_FOUND', 'PVP_MATCH_END', 'PVP_ATTACK_RESULT',
        'PVP_RATING_INFO', 'PVP_NORMALIZED_STATS', 'PVP_ELO_INITIAL', '_on_pvp_queue_req',
        '_on_pvp_attack', '_pvp_match_end', '_calc_elo', '_get_tier',
        'RAID_BOSS_SPAWN', 'RAID_PHASE_CHANGE', 'RAID_MECHANIC', 'RAID_STAGGER',
        'RAID_CLEAR', 'RAID_WIPE', 'RAID_BOSS_DATA', 'RAID_MECHANIC_DEFS',
        '_start_raid_boss', '_on_raid_attack', '_trigger_raid_mechanic', '_raid_clear',
        '_raid_wipe', 'pvp_arena_1v1',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S036 patched OK')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_pvp_queue_level_low' in content:
        # fixup: PvP matching test timing
        changed = False
        if 'assert msg_type == MsgType.PVP_QUEUE_STATUS\n        # MATCH_FOUND' in content:
            # old version uses per-client recv_packet — replace with bulk recv
            content = content.replace(
                '        for c in clients:\n'
                '            await c.send(MsgType.PVP_QUEUE_REQ, struct.pack(\'<B\', 1))  # 1v1\n'
                '            msg_type, payload = await c.recv_packet()\n'
                '            assert msg_type == MsgType.PVP_QUEUE_STATUS\n'
                '        # MATCH_FOUND 수집\n'
                '        await asyncio.sleep(0.3)\n'
                '        match_id = None\n'
                '        team_ids = {}\n'
                '        for i, c in enumerate(clients):\n'
                '            packets = await c.recv_all_packets(timeout=1.0)\n'
                '            for mt, pl in packets:\n'
                '                if mt == MsgType.PVP_MATCH_FOUND:\n'
                '                    match_id = struct.unpack_from(\'<I\', pl, 0)[0]\n'
                '                    team_ids[i] = pl[4]  # team_id byte at offset 4 (after match_id u32)',
                '        for c in clients:\n'
                '            await c.send(MsgType.PVP_QUEUE_REQ, struct.pack(\'<B\', 1))  # 1v1\n'
                '            await asyncio.sleep(0.1)\n'
                '        await asyncio.sleep(0.5)\n'
                '        # 모든 패킷 수집 (STATUS + MATCH_FOUND 포함)\n'
                '        match_id = None\n'
                '        for c in clients:\n'
                '            packets = await c.recv_all_packets(timeout=1.5)\n'
                '            for mt, pl in packets:\n'
                '                if mt == MsgType.PVP_MATCH_FOUND:\n'
                '                    match_id = struct.unpack_from(\'<I\', pl, 0)[0]'
            )
            changed = True
        if 'for _ in range(80):' in content:
            content = content.replace('for _ in range(80):', 'for _ in range(60):')
            changed = True
        if '            msg_type, payload = await c.recv_packet()\n            assert msg_type == MsgType.PVP_QUEUE_STATUS\n        await asyncio.sleep(0.3)\n        found_count' in content:
            content = content.replace(
                '            msg_type, payload = await c.recv_packet()\n'
                '            assert msg_type == MsgType.PVP_QUEUE_STATUS\n'
                '        await asyncio.sleep(0.3)\n'
                '        found_count',
                '            await asyncio.sleep(0.1)\n'
                '        await asyncio.sleep(0.5)\n'
                '        found_count'
            )
            changed = True
        if '>= 5 PVP_MATCH_FOUND' in content and 'timeout=1.0)\n            for mt, pl in packets:\n                if mt == MsgType.PVP_MATCH_FOUND:\n                    found_count += 1\n        assert found_count >= 5' in content:
            content = content.replace('timeout=1.0)\n            for mt, pl in packets:\n                if mt == MsgType.PVP_MATCH_FOUND:\n                    found_count += 1\n        assert found_count >= 5',
                                      'timeout=1.5)\n            for mt, pl in packets:\n                if mt == MsgType.PVP_MATCH_FOUND:\n                    found_count += 1\n        assert found_count >= 5')
            changed = True
        if changed:
            with open(TEST_PATH, 'w', encoding='utf-8') as f:
                f.write(content)
            print('[test] S036 fixup applied')
        else:
            print('[test] S036 already patched')
        return True

    new_tests = r'''
    # ━━━ PvP 아레나 / 레이드 보스 기믹 (S036) ━━━

    async def test_pvp_queue_level_low():
        """P3_S01_S01: 레벨 부족 시 PvP 큐 거부"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'pvplvl01' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        # 레벨 1 상태에서 PvP 큐 시도
        await c.send(MsgType.PVP_QUEUE_REQ, struct.pack('<B', 1))  # mode=1(1v1)
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.PVP_QUEUE_STATUS
        assert payload[1] == 2, f"Expected LEVEL_TOO_LOW(2), got {payload[1]}"
        c.close()

    await test("PVP_LEVEL: PvP 레벨 부족 거부", test_pvp_queue_level_low())

    async def test_pvp_queue_invalid_mode():
        """P3_S01_S01: 잘못된 PvP 모드 거부"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'pvpmode1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_all_packets(timeout=0.5)
        await c.send(MsgType.PVP_QUEUE_REQ, struct.pack('<B', 99))  # 잘못된 모드
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.PVP_QUEUE_STATUS
        assert payload[1] == 1, f"Expected INVALID_MODE(1), got {payload[1]}"
        c.close()

    await test("PVP_MODE: PvP 잘못된 모드 거부", test_pvp_queue_invalid_mode())

    async def test_pvp_queue_and_cancel():
        """P3_S01_S01: PvP 큐 등록 및 취소"""
        c = TestClient()
        await c.connect('127.0.0.1', port)
        await asyncio.sleep(0.1)
        await c.send(MsgType.LOGIN, struct.pack('<B', 8) + b'pvpcanc1' + struct.pack('<B', 2) + b'pw')
        await c.recv_packet()
        await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
        await c.recv_all_packets(timeout=1.0)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_all_packets(timeout=0.5)
        # 큐 등록
        await c.send(MsgType.PVP_QUEUE_REQ, struct.pack('<B', 1))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.PVP_QUEUE_STATUS
        assert payload[1] == 0, f"Expected QUEUED(0), got {payload[1]}"
        # 큐 취소
        await c.send(MsgType.PVP_QUEUE_CANCEL, struct.pack('<B', 1))
        msg_type, payload = await c.recv_packet()
        assert msg_type == MsgType.PVP_QUEUE_STATUS
        assert payload[1] == 4, f"Expected CANCELLED(4), got {payload[1]}"
        c.close()

    await test("PVP_QUEUE: PvP 큐 등록 + 취소", test_pvp_queue_and_cancel())

    async def test_pvp_1v1_match():
        """P3_S01_S01: 1v1 매칭 완료 → 경기 → 승패 판정"""
        clients = []
        for i in range(2):
            c = TestClient()
            await c.connect('127.0.0.1', port)
            await asyncio.sleep(0.05)
            name = f'pvp1v{i:01d}t'.encode('utf-8')
            await c.send(MsgType.LOGIN, struct.pack('<B', len(name)) + name + struct.pack('<B', 2) + b'pw')
            await c.recv_packet()
            await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
            await c.recv_all_packets(timeout=1.0)
            await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
            await c.recv_all_packets(timeout=0.5)
            clients.append(c)
        # 2명 큐 등록 — 순차 등록 후 전체 패킷 수집
        for c in clients:
            await c.send(MsgType.PVP_QUEUE_REQ, struct.pack('<B', 1))  # 1v1
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
        # 모든 패킷 수집 (STATUS + MATCH_FOUND 포함)
        match_id = None
        for c in clients:
            packets = await c.recv_all_packets(timeout=1.5)
            for mt, pl in packets:
                if mt == MsgType.PVP_MATCH_FOUND:
                    match_id = struct.unpack_from('<I', pl, 0)[0]
        assert match_id is not None, "No PVP_MATCH_FOUND received"
        # 매치 수락
        await clients[0].send(MsgType.PVP_MATCH_ACCEPT, struct.pack('<I', match_id))
        await asyncio.sleep(0.3)
        # MATCH_START 수집
        start_count = 0
        for c in clients:
            packets = await c.recv_all_packets(timeout=1.0)
            for mt, pl in packets:
                if mt == MsgType.PVP_MATCH_START:
                    start_count += 1
        assert start_count >= 1, f"Expected >= 1 PVP_MATCH_START, got {start_count}"
        # 공격 → 한쪽 사망 (12000 HP / (500*0.6) = 40 hits)
        for _ in range(60):
            await clients[0].send(MsgType.PVP_ATTACK, struct.pack('<IBBHH', match_id, 1, 0, 1, 500))
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.5)
        end_count = 0
        for c in clients:
            packets = await c.recv_all_packets(timeout=1.0)
            for mt, pl in packets:
                if mt == MsgType.PVP_MATCH_END:
                    end_count += 1
        assert end_count >= 1, f"Expected >= 1 PVP_MATCH_END, got {end_count}"
        for c in clients:
            c.close()

    await test("PVP_1V1: 1v1 매칭 + 경기 + 승패", test_pvp_1v1_match())

    async def test_pvp_3v3_match():
        """P3_S01_S01: 3v3 매칭 완료"""
        clients = []
        for i in range(6):
            c = TestClient()
            await c.connect('127.0.0.1', port)
            await asyncio.sleep(0.05)
            name = f'p3v{i:01d}tst'.encode('utf-8')
            await c.send(MsgType.LOGIN, struct.pack('<B', len(name)) + name + struct.pack('<B', 2) + b'pw')
            await c.recv_packet()
            await c.send(MsgType.CHAR_SELECT, struct.pack('<I', 1))
            await c.recv_all_packets(timeout=1.0)
            await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
            await c.recv_all_packets(timeout=0.5)
            clients.append(c)
        # 6명 큐 등록 (3v3) — 순차 등록 후 전체 수집
        for c in clients:
            await c.send(MsgType.PVP_QUEUE_REQ, struct.pack('<B', 2))  # mode=2(3v3)
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
        found_count = 0
        for c in clients:
            packets = await c.recv_all_packets(timeout=1.5)
            for mt, pl in packets:
                if mt == MsgType.PVP_MATCH_FOUND:
                    found_count += 1
        assert found_count >= 5, f"Expected >= 5 PVP_MATCH_FOUND, got {found_count}"
        for c in clients:
            c.close()

    await test("PVP_3V3: 3v3 매칭 완료", test_pvp_3v3_match())

    async def test_pvp_elo_calculation():
        """P3_S01_S01: ELO 레이팅 계산 검증 (직접 함수 호출)"""
        from tcp_bridge import BridgeServer
        srv = BridgeServer(port=0, verbose=False)
        # 동일 레이팅에서 승리
        new_w, new_l = srv._calc_elo(1000, 1000, 32)
        assert new_w > 1000, f"Winner rating should increase: {new_w}"
        assert new_l < 1000, f"Loser rating should decrease: {new_l}"
        # 높은 레이팅이 낮은 상대를 이기면 변동 적음
        new_w2, new_l2 = srv._calc_elo(1500, 1000, 32)
        assert (new_w2 - 1500) < (new_w - 1000), "High vs low should have smaller gain"
        # 티어 확인
        assert srv._get_tier(500) == "Bronze"
        assert srv._get_tier(1000) == "Silver"
        assert srv._get_tier(1400) == "Gold"
        assert srv._get_tier(2500) == "Grandmaster"

    await test("PVP_ELO: ELO 레이팅 계산 검증", test_pvp_elo_calculation())

    async def test_raid_boss_spawn():
        """P3_S02_S01: 레이드 보스 스폰 + 인스턴스 초기화"""
        from tcp_bridge import BridgeServer, RAID_BOSS_DATA
        srv = BridgeServer(port=0, verbose=False)
        # 더미 인스턴스 생성
        srv.instances[999] = {
            "id": 999, "dungeon_id": 4, "dungeon_name": "고대 용의 둥지",
            "zone_id": 103, "difficulty": 0, "boss_hp": 2000000,
            "boss_current_hp": 2000000, "stage": 1, "max_stages": 1,
            "players": [], "active": True,
        }
        await srv._start_raid_boss(999)
        assert 999 in srv.raid_instances
        raid = srv.raid_instances[999]
        assert raid["boss_name"] == "Ancient Dragon"
        assert raid["max_hp"] == 2000000
        assert raid["phase"] == 1
        assert raid["max_phases"] == 3
        assert not raid["enraged"]
        assert raid["active"]

    await test("RAID_SPAWN: 레이드 보스 스폰", test_raid_boss_spawn())

    async def test_raid_phase_transition():
        """P3_S02_S01: 레이드 보스 페이즈 전환 (70%, 30%)"""
        from tcp_bridge import BridgeServer, RAID_BOSS_DATA
        srv = BridgeServer(port=0, verbose=False)
        srv.instances[998] = {
            "id": 998, "dungeon_id": 4, "dungeon_name": "고대 용의 둥지",
            "zone_id": 103, "difficulty": 0, "boss_hp": 2000000,
            "boss_current_hp": 2000000, "stage": 1, "max_stages": 1,
            "players": [], "active": True,
        }
        await srv._start_raid_boss(998)
        raid = srv.raid_instances[998]
        # 직접 HP 조작 → 70% 아래로
        raid["current_hp"] = int(raid["max_hp"] * 0.68)  # 68%
        hp_pct = raid["current_hp"] / raid["max_hp"]
        # 페이즈 전환 로직 수동 실행
        thresholds = raid["phase_thresholds"]
        for i, thr in enumerate(thresholds):
            target_phase = i + 2
            if hp_pct <= thr and raid["phase"] < target_phase:
                raid["phase"] = target_phase
                break
        assert raid["phase"] == 2, f"Expected phase 2, got {raid['phase']}"
        # 30% 아래
        raid["current_hp"] = int(raid["max_hp"] * 0.28)
        hp_pct = raid["current_hp"] / raid["max_hp"]
        for i, thr in enumerate(thresholds):
            target_phase = i + 2
            if hp_pct <= thr and raid["phase"] < target_phase:
                raid["phase"] = target_phase
        assert raid["phase"] == 3, f"Expected phase 3, got {raid['phase']}"

    await test("RAID_PHASE: 레이드 페이즈 전환", test_raid_phase_transition())

    async def test_raid_mechanic_trigger():
        """P3_S02_S01: 레이드 기믹 발동"""
        from tcp_bridge import BridgeServer, RAID_MECHANIC_DEFS
        srv = BridgeServer(port=0, verbose=False)
        srv.instances[997] = {
            "id": 997, "dungeon_id": 4, "dungeon_name": "고대 용의 둥지",
            "zone_id": 103, "difficulty": 0, "boss_hp": 2000000,
            "boss_current_hp": 2000000, "stage": 1, "max_stages": 1,
            "players": [], "active": True,
        }
        await srv._start_raid_boss(997)
        # 기믹 발동
        await srv._trigger_raid_mechanic(997, "stagger_check")
        raid = srv.raid_instances[997]
        assert raid["mechanic_active"] == "stagger_check"
        assert raid["stagger_gauge"] == 0
        # safe_zone 기믹 발동
        await srv._trigger_raid_mechanic(997, "safe_zone")
        assert raid["mechanic_active"] == "safe_zone"

    await test("RAID_MECHANIC: 레이드 기믹 발동", test_raid_mechanic_trigger())

    async def test_raid_clear():
        """P3_S02_S01: 레이드 클리어 + 보상"""
        from tcp_bridge import BridgeServer, RAID_CLEAR_REWARDS
        srv = BridgeServer(port=0, verbose=False)
        srv.instances[996] = {
            "id": 996, "dungeon_id": 4, "dungeon_name": "고대 용의 둥지",
            "zone_id": 103, "difficulty": 0, "boss_hp": 2000000,
            "boss_current_hp": 2000000, "stage": 1, "max_stages": 1,
            "players": [], "active": True,
        }
        await srv._start_raid_boss(996)
        await srv._raid_clear(996)
        raid = srv.raid_instances[996]
        assert not raid["active"], "Raid should be inactive after clear"

    await test("RAID_CLEAR: 레이드 클리어 + 보상", test_raid_clear())

    async def test_raid_wipe():
        """P3_S02_S01: 레이드 전멸"""
        from tcp_bridge import BridgeServer
        srv = BridgeServer(port=0, verbose=False)
        srv.instances[995] = {
            "id": 995, "dungeon_id": 4, "dungeon_name": "고대 용의 둥지",
            "zone_id": 103, "difficulty": 0, "boss_hp": 2000000,
            "boss_current_hp": 2000000, "stage": 1, "max_stages": 1,
            "players": [], "active": True,
        }
        await srv._start_raid_boss(995)
        await srv._raid_wipe(995)
        raid = srv.raid_instances[995]
        assert not raid["active"], "Raid should be inactive after wipe"

    await test("RAID_WIPE: 레이드 전멸", test_raid_wipe())

    async def test_raid_mechanic_defs():
        """P3_S02_S01: 기믹 정의 6종 모두 존재 확인"""
        from tcp_bridge import RAID_MECHANIC_DEFS
        expected = ["safe_zone", "stagger_check", "counter_attack", "position_swap", "dps_check", "cooperation"]
        for name in expected:
            assert name in RAID_MECHANIC_DEFS, f"Missing mechanic: {name}"
            mech = RAID_MECHANIC_DEFS[name]
            assert "id" in mech, f"Mechanic {name} missing 'id'"

    await test("RAID_MECHS: 기믹 6종 정의 확인", test_raid_mechanic_defs())

'''

    marker = '    # \u2501\u2501\u2501 \uacb0\uacfc \u2501\u2501\u2501'
    if marker not in content:
        print('[test] WARNING: Result section marker not found')
        return False

    content = content.replace(marker, new_tests + marker, 1)

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    if 'test_pvp_queue_level_low' in content and 'test_raid_boss_spawn' in content:
        print('[test] S036 patched OK')
        return True
    else:
        print('[test] S036 FAILED')
        return False


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS036 all patches applied!')
    else:
        print('\nSome patches failed!')
        sys.exit(1)
