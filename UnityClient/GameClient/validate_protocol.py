#!/usr/bin/env python3
"""
validate_protocol.py -- Protocol YAML <-> Unity Client 일치 검증기

protocol.yaml(Single Source of Truth)과 C# 클라이언트 코드를 비교하여
메시지 타입, 결과 코드 enum, Build/Parse 메서드의 일치 여부를 검증한다.

외부 의존성 없음 (PyYAML 불필요 -- regex로 직접 파싱).

사용법: python validate_protocol.py
종료 코드: 0 = FAIL 없음, 1 = FAIL 있음
"""

import io
import os
import re
import sys

# Windows 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ━━━ 경로 설정 ━━━

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_YAML = os.path.join(SCRIPT_DIR, "..", "..", "_comms", "agreements", "protocol.yaml")
PACKET_DEFINITIONS_CS = os.path.join(SCRIPT_DIR, "Assets", "Scripts", "Network", "PacketDefinitions.cs")
PACKET_BUILDER_CS = os.path.join(SCRIPT_DIR, "Assets", "Scripts", "Network", "PacketBuilder.cs")

# 세션 1~13까지 구현 완료 (Build/Parse 메서드 존재해야 함)
IMPLEMENTED_SESSION_MAX = 28

# 서버 전용 메시지 (클라이언트에 MsgType 불필요)
# - STATS(99): 서버 진단용 디버그 패킷
# - STAT_ADD_EXP(92), STAT_TAKE_DMG(93), STAT_HEAL(94): 서버 내부 ECS 뮤테이션 커맨드
# - TIMER_ADD(80), TIMER_INFO(81): 서버 내부 타이머 (클라이언트 미사용)
# - CONFIG_QUERY(82), CONFIG_RESP(83): 서버 내부 설정 (클라이언트 미사용)
SERVER_ONLY_MESSAGES = {
    "STATS",           # session 2, 서버 진단
    "STAT_ADD_EXP",    # session 12, 서버 내부
    "STAT_TAKE_DMG",   # session 12, 서버 내부
    "STAT_HEAL",       # session 12, 서버 내부
    "TIMER_ADD",       # session 11, 서버 내부
    "TIMER_INFO",      # session 11, 서버 내부
    "CONFIG_QUERY",    # session 11, 서버 내부
    "CONFIG_RESP",     # session 11, 서버 내부
    "FIELD_REGISTER",  # session 17, S2S
    "FIELD_HEARTBEAT", # session 17, S2S
}

# ━━━ 결과 카운터 ━━━

_pass_count = 0
_fail_count = 0
_info_count = 0
_details = []


def log_pass(msg):
    global _pass_count
    _pass_count += 1
    print(f"[PASS] {msg}")
    _details.append({"level": "PASS", "message": msg})


def log_fail(msg):
    global _fail_count
    _fail_count += 1
    print(f"[FAIL] {msg}")
    _details.append({"level": "FAIL", "message": msg})


def log_info(msg):
    global _info_count
    _info_count += 1
    print(f"[INFO] {msg}")
    _details.append({"level": "INFO", "message": msg})


# ━━━ 유틸리티 ━━━

def read_file(path):
    """파일 내용을 읽어 반환. 실패 시 None."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, IOError):
        return None


# ━━━ YAML 파싱 (의존성 없이 regex로) ━━━

def parse_yaml_messages(content):
    """
    protocol.yaml의 messages: 섹션에서 메시지 이름, id, session을 추출.
    반환: dict { name: { "id": int, "session": int } }
    """
    messages = {}
    in_messages = False
    current_msg = None

    for line in content.splitlines():
        stripped = line.strip()

        # 빈 줄/주석 무시
        if not stripped or stripped.startswith("#"):
            continue

        # 최상위 섹션 감지 (들여쓰기 없는 key:)
        if not line[0].isspace() and re.match(r"^[a-z_]+:", stripped):
            if stripped.startswith("messages:"):
                in_messages = True
                continue
            elif in_messages:
                # messages 섹션 종료
                break
            continue

        if not in_messages:
            continue

        # 메시지 이름 감지 (2칸 들여쓰기, 이름:)
        # 패턴: "  MESSAGE_NAME:" (payload 등 하위 키가 아닌 것)
        msg_match = re.match(r"^  ([A-Z][A-Z0-9_]+):\s*$", line)
        if msg_match:
            current_msg = msg_match.group(1)
            messages[current_msg] = {"id": None, "session": None}
            continue

        # id: 숫자
        if current_msg:
            id_match = re.match(r"^\s+id:\s*(\d+)", line)
            if id_match:
                messages[current_msg]["id"] = int(id_match.group(1))
                continue

            # session: 숫자
            session_match = re.match(r"^\s+session:\s*(\d+)", line)
            if session_match:
                messages[current_msg]["session"] = int(session_match.group(1))
                continue

    return messages


def parse_yaml_result_codes(content):
    """
    protocol.yaml의 result_codes: 섹션에서 enum 이름과 값을 추출.
    반환: dict { enum_name: { int_value: str_name, ... } }
    """
    enums = {}
    in_result_codes = False
    current_enum = None

    for line in content.splitlines():
        stripped = line.strip()

        # 빈 줄/주석 무시
        if not stripped or stripped.startswith("#"):
            continue

        # 최상위 섹션 감지
        if not line[0].isspace() and re.match(r"^[a-z_]+:", stripped):
            if stripped.startswith("result_codes:"):
                in_result_codes = True
                continue
            elif in_result_codes:
                break
            continue

        if not in_result_codes:
            continue

        # enum 이름 감지 (2칸 들여쓰기, PascalCase:)
        enum_match = re.match(r"^  ([A-Za-z][A-Za-z0-9_]+):\s*$", line)
        if enum_match:
            current_enum = enum_match.group(1)
            enums[current_enum] = {}
            continue

        # 값 감지 (4칸 들여쓰기, 숫자: 이름)
        if current_enum:
            value_match = re.match(r"^\s+(\d+):\s*(\w+)", line)
            if value_match:
                val = int(value_match.group(1))
                name = value_match.group(2)
                enums[current_enum][val] = name
                continue

    return enums


# ━━━ C# 파싱 ━━━

def parse_cs_msgtype_enum(content):
    """
    PacketDefinitions.cs에서 MsgType enum 값을 추출.
    반환: dict { name: int_value }
    """
    msg_types = {}

    # 줄 단위로 MsgType enum 블록을 탐색
    # (.*?\}) 패턴은 주석 내 {, } 문자에 혼동되므로 줄 기반 파싱 사용)
    in_enum = False
    brace_depth = 0

    for line in content.splitlines():
        stripped = line.strip()

        # enum 시작 감지
        if not in_enum:
            if re.search(r"public\s+enum\s+MsgType\s*:\s*ushort", line):
                in_enum = True
                if "{" in line:
                    brace_depth += line.count("{") - line.count("}")
                continue

        if in_enum:
            # 주석 제거 후 중괄호 추적
            code_part = re.sub(r"//.*$", "", line)
            brace_depth += code_part.count("{") - code_part.count("}")

            # enum 값 추출 (주석이 아닌 코드 부분에서)
            m = re.match(r"\s*(\w+)\s*=\s*(\d+)", code_part)
            if m:
                name = m.group(1)
                value = int(m.group(2))
                msg_types[name] = value

            # enum 블록 종료
            if brace_depth <= 0:
                break

    return msg_types


def parse_cs_result_enums(content):
    """
    PacketDefinitions.cs에서 result code enum 들을 추출.
    반환: dict { enum_name: { int_value: str_name, ... } }

    대상: LoginResult, AttackResult 등 byte enum
    """
    enums = {}

    # byte enum 블록 추출 (MsgType은 ushort이므로 제외됨)
    for m in re.finditer(
        r"public\s+enum\s+(\w+)\s*:\s*byte\s*\{(.*?)\}",
        content,
        re.DOTALL,
    ):
        enum_name = m.group(1)
        enum_body = m.group(2)
        values = {}

        for entry in re.finditer(r"(\w+)\s*=\s*(\d+)", enum_body):
            name = entry.group(1)
            val = int(entry.group(2))
            values[val] = name

        enums[enum_name] = values

    return enums


def parse_cs_builder_methods(content):
    """
    PacketBuilder.cs에서 Build 헬퍼 메서드와 Parse 메서드 이름을 추출.
    반환: { "build": set(메서드 이름), "parse": set(메서드 이름) }
    """
    build_methods = set()
    parse_methods = set()

    # public static 메서드 시그니처 추출
    # 반환 타입: 일반 타입(byte[], void 등) 또는 튜플 타입 ((Type1, Type2))
    for m in re.finditer(
        r"public\s+static\s+(?:\S+|\([^)]+\))\s+(\w+)\s*\(",
        content,
    ):
        name = m.group(1)
        # 기본 Build 메서드는 제외 (제네릭 빌더)
        if name == "Build":
            continue
        if name.startswith("Parse"):
            parse_methods.add(name)
        else:
            build_methods.add(name)

    return {"build": build_methods, "parse": parse_methods}


# ━━━ 메시지 이름 -> Build/Parse 메서드 이름 매핑 ━━━

# YAML 메시지 이름을 C# Build/Parse 메서드 이름으로 변환하는 매핑
# C2S 메시지 -> Build 메서드, S2C 메시지 -> Parse 메서드
# 매핑은 코드 컨벤션 기반 (PascalCase 변환)

def yaml_name_to_pascal(name):
    """
    YAML 메시지 이름(UPPER_SNAKE)을 PascalCase로 변환.
    예: GATE_ROUTE_REQ -> GateRouteReq, LOGIN_RESULT -> LoginResult
    """
    parts = name.lower().split("_")
    return "".join(p.capitalize() for p in parts)


# 알려진 매핑 (컨벤션이 불규칙한 것들)
# key = YAML 메시지 이름, value = (method_type, method_name)
# method_type: "build" 또는 "parse"
KNOWN_METHOD_MAP = {
    # C2S Build 메서드
    "ECHO":            ("build", None),          # Build(MsgType.ECHO, ...) 직접 사용
    "PING":            ("build", None),          # Build(MsgType.PING) 직접 사용
    "MOVE":            ("build", "Move"),
    "POS_QUERY":       ("build", None),          # Build(MsgType.POS_QUERY) 직접 사용
    "CHANNEL_JOIN":    ("build", "ChannelJoin"),
    "ZONE_ENTER":      ("build", "ZoneEnter"),
    "HANDOFF_REQUEST": ("build", None),
    "HANDOFF_RESTORE": ("build", None),
    "GHOST_QUERY":     ("build", None),
    "LOGIN":           ("build", "Login"),
    "CHAR_LIST_REQ":   ("build", "CharListReq"),
    "CHAR_SELECT":     ("build", "CharSelect"),
    "GATE_ROUTE_REQ":  ("build", "GateRouteReq"),
    "STAT_QUERY":      ("build", "StatQuery"),
    "STAT_ADD_EXP":    ("build", None),          # 아직 헬퍼 없음 (Build 직접)
    "STAT_TAKE_DMG":   ("build", None),          # 아직 헬퍼 없음
    "STAT_HEAL":       ("build", None),          # 아직 헬퍼 없음
    "ATTACK_REQ":      ("build", "AttackReq"),
    "RESPAWN_REQ":     ("build", "RespawnReq"),
    "TIMER_ADD":       ("build", None),
    "CONFIG_QUERY":    ("build", None),

    # S2C Parse 메서드
    "STATS":             ("parse", None),          # 범용 진단
    "MOVE_BROADCAST":    ("parse", "ParseEntityPosition"),
    "APPEAR":            ("parse", "ParseEntityPosition"),  # 동일 파서 공유
    "DISAPPEAR":         ("parse", "ParseDisappear"),
    "CHANNEL_INFO":      ("parse", "ParseIntResponse"),
    "ZONE_INFO":         ("parse", "ParseIntResponse"),
    "HANDOFF_DATA":      ("parse", None),
    "HANDOFF_RESULT":    ("parse", None),
    "GHOST_INFO":        ("parse", None),
    "LOGIN_RESULT":      ("parse", "ParseLoginResult"),
    "CHAR_LIST_RESP":    ("parse", "ParseCharListResp"),
    "ENTER_GAME":        ("parse", "ParseEnterGame"),
    "GATE_ROUTE_RESP":   ("parse", "ParseGateRouteResp"),
    "STAT_SYNC":         ("parse", "ParseStatSync"),
    "ATTACK_RESULT":     ("parse", "ParseAttackResult"),
    "COMBAT_DIED":       ("parse", "ParseCombatDied"),
    "RESPAWN_RESULT":    ("parse", "ParseRespawnResult"),
    "TIMER_INFO":        ("parse", None),
    "CONFIG_RESP":       ("parse", None),

    # Session 14: Monsters
    "MONSTER_SPAWN":     ("parse", "ParseMonsterSpawn"),
    "MONSTER_RESPAWN":   ("parse", "ParseMonsterRespawn"),

    # Session 16: Zone Transfer
    "ZONE_TRANSFER_REQ":    ("build", "ZoneTransferReq"),
    "ZONE_TRANSFER_RESULT": ("parse", "ParseZoneTransferResult"),

    # Session 17: Gate Server (server-internal, skip Build/Parse check)
    "FIELD_REGISTER":       ("build", None),
    "FIELD_HEARTBEAT":      ("build", None),
    "GATE_SERVER_LIST":     ("build", None),
    "GATE_SERVER_LIST_RESP": ("parse", None),

    # Session 19: Skills
    "SKILL_LIST_REQ":  ("build", "SkillListReq"),
    "SKILL_LIST_RESP": ("parse", "ParseSkillListResp"),
    "SKILL_USE":       ("build", "SkillUse"),
    "SKILL_RESULT":    ("parse", "ParseSkillResult"),

    # Session 20: Party
    "PARTY_CREATE":    ("build", "PartyCreate"),
    "PARTY_INVITE":    ("build", "PartyInvite"),
    "PARTY_ACCEPT":    ("build", "PartyAccept"),
    "PARTY_LEAVE":     ("build", "PartyLeave"),
    "PARTY_INFO":      ("parse", "ParsePartyInfo"),
    "PARTY_KICK":      ("build", "PartyKick"),

    # Session 21: Instanced Dungeons
    "INSTANCE_CREATE":       ("build", "InstanceCreate"),
    "INSTANCE_ENTER":        ("parse", "ParseInstanceEnter"),
    "INSTANCE_LEAVE":        ("build", "InstanceLeave"),
    "INSTANCE_LEAVE_RESULT": ("parse", "ParseInstanceLeaveResult"),
    "INSTANCE_INFO":         ("parse", "ParseInstanceInfo"),

    # Session 22: Matchmaking
    "MATCH_ENQUEUE":   ("build", "MatchEnqueue"),
    "MATCH_DEQUEUE":   ("build", "MatchDequeue"),
    "MATCH_FOUND":     ("parse", "ParseMatchFound"),
    "MATCH_ACCEPT":    ("build", "MatchAccept"),
    "MATCH_STATUS":    ("parse", "ParseMatchStatus"),

    # Session 23: Inventory
    "INVENTORY_REQ":    ("build", "InventoryReq"),
    "INVENTORY_RESP":   ("parse", "ParseInventoryResp"),
    "ITEM_ADD":         ("build", "ItemAdd"),
    "ITEM_ADD_RESULT":  ("parse", "ParseItemAddResult"),
    "ITEM_USE":         ("build", "ItemUse"),
    "ITEM_USE_RESULT":  ("parse", "ParseItemUseResult"),
    "ITEM_EQUIP":       ("build", "ItemEquip"),
    "ITEM_UNEQUIP":     ("build", "ItemUnequip"),
    "ITEM_EQUIP_RESULT": ("parse", "ParseItemEquipResult"),

    # Session 24: Buffs
    "BUFF_LIST_REQ":    ("build", "BuffListReq"),
    "BUFF_LIST_RESP":   ("parse", "ParseBuffListResp"),
    "BUFF_APPLY_REQ":   ("build", "BuffApplyReq"),
    "BUFF_RESULT":      ("parse", "ParseBuffResult"),
    "BUFF_REMOVE_REQ":  ("build", "BuffRemoveReq"),
    "BUFF_REMOVE_RESP": ("parse", "ParseBuffRemoveResp"),

    # Session 25: Condition Engine (complex payload, no helper needed)
    "CONDITION_EVAL":   ("build", None),
    "CONDITION_RESULT": ("parse", None),

    # Session 26: Spatial Queries (complex payload, no build helper)
    "SPATIAL_QUERY_REQ":  ("build", None),
    "SPATIAL_QUERY_RESP": ("parse", "ParseSpatialQueryResp"),

    # Session 27: Loot
    "LOOT_ROLL_REQ":    ("build", "LootRollReq"),
    "LOOT_RESULT":      ("parse", "ParseLootResult"),

    # Session 28: Quests
    "QUEST_LIST_REQ":        ("build", "QuestListReq"),
    "QUEST_LIST_RESP":       ("parse", "ParseQuestListResp"),
    "QUEST_ACCEPT":          ("build", "QuestAccept"),
    "QUEST_ACCEPT_RESULT":   ("parse", "ParseQuestAcceptResult"),
    "QUEST_PROGRESS":        ("build", "QuestProgress"),
    "QUEST_COMPLETE":        ("build", "QuestComplete"),
    "QUEST_COMPLETE_RESULT": ("parse", "ParseQuestCompleteResult"),
}


# ━━━ enum 값 정규화 ━━━

def normalize_enum_value(name):
    """
    C# enum 값과 YAML enum 값을 비교하기 위해 정규화.
    PascalCase -> UPPER_SNAKE_CASE 변환.
    예: AccountNotFound -> ACCOUNT_NOT_FOUND
        SUCCESS -> SUCCESS
    """
    # 이미 UPPER_SNAKE인 경우 그대로
    if name == name.upper():
        return name

    # PascalCase -> UPPER_SNAKE
    result = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
    return result.upper()


# ━━━ 검사 항목 ━━━

def check_msgtype_sync(yaml_messages, cs_msg_types):
    """YAML 메시지와 C# MsgType enum 동기화 검사."""
    print("--- MsgType 동기화 검사 ---\n")

    # 1. YAML에 있는 메시지가 C#에도 있는지 확인
    for name, info in sorted(yaml_messages.items(), key=lambda x: x[1]["id"] or 0):
        msg_id = info["id"]
        session = info["session"]

        if name in cs_msg_types:
            cs_id = cs_msg_types[name]
            if cs_id == msg_id:
                log_pass(f"MsgType {name}({msg_id}) -- yaml <-> client 일치")
            else:
                log_fail(
                    f"MsgType {name} -- ID 불일치: yaml={msg_id}, client={cs_id}"
                )
        else:
            if name in SERVER_ONLY_MESSAGES:
                log_info(
                    f"MsgType {name}({msg_id}) -- 서버 전용 패킷 (클라이언트 불필요)"
                )
            elif session is not None and session > IMPLEMENTED_SESSION_MAX:
                log_info(
                    f"MsgType {name}({msg_id}) -- yaml에만 있음 (세션 {session}, 미구현)"
                )
            else:
                log_fail(
                    f"MsgType {name}({msg_id}) -- yaml에 있지만 client MsgType에 없음 (세션 {session})"
                )

    print()

    # 2. C#에 있는데 YAML에 없는 메시지
    yaml_names = set(yaml_messages.keys())
    for name, cs_id in sorted(cs_msg_types.items(), key=lambda x: x[1]):
        if name not in yaml_names:
            log_fail(f"MsgType {name}({cs_id}) -- client에 있지만 yaml에 없음")


def check_result_code_enums(yaml_enums, cs_enums):
    """YAML result_codes와 C# byte enum 동기화 검사."""
    print("\n--- Result Code Enum 검사 ---\n")

    for enum_name, yaml_values in sorted(yaml_enums.items()):
        if enum_name not in cs_enums:
            # EnterGameResult는 C#에서 class로 구현되어 enum이 아닐 수 있음
            log_info(f"enum {enum_name} -- yaml에 있지만 client에 byte enum 없음 (미구현 또는 다른 형태)")
            continue

        cs_values = cs_enums[enum_name]
        yaml_count = len(yaml_values)
        cs_count = len(cs_values)

        all_match = True

        # YAML 값과 C# 값 비교
        all_keys = sorted(set(yaml_values.keys()) | set(cs_values.keys()))
        for val in all_keys:
            yaml_name = yaml_values.get(val)
            cs_name = cs_values.get(val)

            if yaml_name is None:
                log_fail(f"enum {enum_name} -- 값 {val}: client={cs_name}, yaml에 없음")
                all_match = False
            elif cs_name is None:
                log_fail(f"enum {enum_name} -- 값 {val}: yaml={yaml_name}, client에 없음")
                all_match = False
            else:
                # 정규화하여 비교
                norm_yaml = normalize_enum_value(yaml_name)
                norm_cs = normalize_enum_value(cs_name)
                if norm_yaml != norm_cs:
                    log_fail(
                        f"enum {enum_name} -- 값 {val} 불일치: "
                        f"client={cs_name}, yaml={yaml_name}"
                    )
                    all_match = False

        if all_match:
            log_pass(f"enum {enum_name} -- {yaml_count}개 값 전부 일치")


def check_build_parse_methods(yaml_messages, builder_methods):
    """
    구현된 세션(1~13)의 메시지에 대해 Build/Parse 헬퍼 메서드 존재 여부 검사.
    """
    print("\n--- Build/Parse 메서드 검사 (세션 1~{}) ---\n".format(IMPLEMENTED_SESSION_MAX))

    build_set = builder_methods["build"]
    parse_set = builder_methods["parse"]

    for name, info in sorted(yaml_messages.items(), key=lambda x: x[1]["id"] or 0):
        session = info["session"]
        if session is None or session > IMPLEMENTED_SESSION_MAX:
            continue

        # server2server 메시지는 클라이언트에 불필요
        # KNOWN_METHOD_MAP에 없으면 검사 스킵
        if name not in KNOWN_METHOD_MAP:
            continue

        method_type, method_name = KNOWN_METHOD_MAP[name]

        # method_name이 None이면 Build() 직접 호출 또는 아직 헬퍼 불필요
        if method_name is None:
            continue

        if method_type == "build":
            if method_name in build_set:
                log_pass(f"Build 메서드 {method_name}() -- {name} 전송 가능")
            else:
                log_fail(f"Build 메서드 {method_name}() 누락 -- {name} 전송 불가")
        elif method_type == "parse":
            if method_name in parse_set:
                log_pass(f"Parse 메서드 {method_name}() -- {name} 파싱 가능")
            else:
                log_fail(f"Parse 메서드 {method_name}() 누락 -- {name} 파싱 불가")


# ━━━ 메인 ━━━

def run_all_checks():
    """모든 검사를 실행하고 결과를 반환."""
    global _pass_count, _fail_count, _info_count, _details
    _pass_count = 0
    _fail_count = 0
    _info_count = 0
    _details = []

    print("━━━ Protocol YAML <-> Client 검증 시작 ━━━\n")

    # --- 파일 읽기 ---

    yaml_content = read_file(PROTOCOL_YAML)
    if yaml_content is None:
        log_fail(f"protocol.yaml 파일을 찾을 수 없음: {os.path.abspath(PROTOCOL_YAML)}")
        print(f"\n━━━ 결과: {_pass_count} PASS, {_fail_count} FAIL, {_info_count} INFO ━━━")
        return {"passed": _pass_count, "failed": _fail_count, "info": _info_count, "all_passed": False}

    definitions_content = read_file(PACKET_DEFINITIONS_CS)
    if definitions_content is None:
        log_fail(f"PacketDefinitions.cs 파일을 찾을 수 없음: {os.path.abspath(PACKET_DEFINITIONS_CS)}")
        print(f"\n━━━ 결과: {_pass_count} PASS, {_fail_count} FAIL, {_info_count} INFO ━━━")
        return {"passed": _pass_count, "failed": _fail_count, "info": _info_count, "all_passed": False}

    builder_content = read_file(PACKET_BUILDER_CS)
    if builder_content is None:
        log_fail(f"PacketBuilder.cs 파일을 찾을 수 없음: {os.path.abspath(PACKET_BUILDER_CS)}")
        print(f"\n━━━ 결과: {_pass_count} PASS, {_fail_count} FAIL, {_info_count} INFO ━━━")
        return {"passed": _pass_count, "failed": _fail_count, "info": _info_count, "all_passed": False}

    # --- 파싱 ---

    yaml_messages = parse_yaml_messages(yaml_content)
    yaml_enums = parse_yaml_result_codes(yaml_content)
    cs_msg_types = parse_cs_msgtype_enum(definitions_content)
    cs_enums = parse_cs_result_enums(definitions_content)
    builder_methods = parse_cs_builder_methods(builder_content)

    # --- 검사 실행 ---

    check_msgtype_sync(yaml_messages, cs_msg_types)
    check_result_code_enums(yaml_enums, cs_enums)
    check_build_parse_methods(yaml_messages, builder_methods)

    # --- 요약 ---

    print(f"\n━━━ 결과: {_pass_count} PASS, {_fail_count} FAIL, {_info_count} INFO ━━━")

    return {
        "passed": _pass_count,
        "failed": _fail_count,
        "info": _info_count,
        "all_passed": _fail_count == 0,
        "details": list(_details),
    }


def main():
    result = run_all_checks()
    sys.exit(0 if result["all_passed"] else 1)


if __name__ == "__main__":
    main()
