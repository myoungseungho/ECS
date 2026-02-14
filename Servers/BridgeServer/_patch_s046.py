"""
Patch S046: Tripod & Scroll System (TASK 15)
- TRIPOD_LIST_REQ(520)->TRIPOD_LIST(521) -- 트라이포드/비급 현황 조회
- TRIPOD_EQUIP(522)->TRIPOD_EQUIP_RESULT(523) -- 트라이포드 장착/변경
- SCROLL_DISCOVER(524) -- 비급 사용(해금) + 서버→클라 알림
- Tripod data table (warrior/archer/mage 8skills * 3tiers)
- Scroll drop logic on boss/elite kill
- 5 test cases
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Tripod (520-524)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Tripod & Scroll System (TASK 15)\n'
    '    TRIPOD_LIST_REQ = 520\n'
    '    TRIPOD_LIST = 521\n'
    '    TRIPOD_EQUIP = 522\n'
    '    TRIPOD_EQUIP_RESULT = 523\n'
    '    SCROLL_DISCOVER = 524\n'
)

# ====================================================================
# 2. Tripod data table (GDD tripod.yaml)
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Tripod & Scroll Data (GDD tripod.yaml) ----
# Tier unlock levels: tier1=Lv10, tier2=Lv20, tier3=Lv30
TRIPOD_TIER_UNLOCK = {1: 10, 2: 20, 3: 30}

# Full tripod table: skill_id -> {tier -> [options]}
# Each option: {id, name, effect_type, effect_value}
# effect_type: "range_up", "penetrate", "cast_speed", "bleed_dot", "knockback",
#              "multi_hit", "element_convert", "invincible", "damage_up", "aoe_up",
#              "duration_up", "cooldown_down", "slow_enhance", "crit_up", "heal_up"
TRIPOD_TABLE = {
    # ---- Warrior (skill 2-9) ----
    2: {  # slash
        1: [
            {"id": "slash_t1_1", "name": "wide_slash", "effect_type": "range_up", "effect_value": 0.30},
            {"id": "slash_t1_2", "name": "penetrate", "effect_type": "penetrate", "effect_value": 5},
            {"id": "slash_t1_3", "name": "quick_draw", "effect_type": "cast_speed", "effect_value": 0.40},
        ],
        2: [
            {"id": "slash_t2_1", "name": "bleed_slash", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "slash_t2_2", "name": "crush_blow", "effect_type": "knockback", "effect_value": 0.30},
            {"id": "slash_t2_3", "name": "chain_slash", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "slash_t3_1", "name": "flame_dance", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "slash_t3_2", "name": "invincible_slash", "effect_type": "invincible", "effect_value": 1},
        ],
    },
    3: {  # guard
        1: [
            {"id": "guard_t1_1", "name": "iron_wall", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "guard_t1_2", "name": "counter", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "guard_t1_3", "name": "quick_guard", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "guard_t2_1", "name": "thorns", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "guard_t2_2", "name": "shield_bash", "effect_type": "knockback", "effect_value": 0.50},
            {"id": "guard_t2_3", "name": "heal_guard", "effect_type": "heal_up", "effect_value": 0.10},
        ],
        3: [
            {"id": "guard_t3_1", "name": "absolute_defense", "effect_type": "invincible", "effect_value": 1},
            {"id": "guard_t3_2", "name": "guardian_aura", "effect_type": "aoe_up", "effect_value": 0.50},
        ],
    },
    4: {  # charge
        1: [
            {"id": "charge_t1_1", "name": "long_charge", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "charge_t1_2", "name": "armor_charge", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "charge_t1_3", "name": "fast_charge", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "charge_t2_1", "name": "stun_extend", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "charge_t2_2", "name": "aoe_charge", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "charge_t2_3", "name": "chain_charge", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "charge_t3_1", "name": "thunder_charge", "effect_type": "element_convert", "effect_value": "lightning"},
            {"id": "charge_t3_2", "name": "unstoppable", "effect_type": "invincible", "effect_value": 1},
        ],
    },
    5: {  # war_cry
        1: [
            {"id": "warcry_t1_1", "name": "wide_cry", "effect_type": "aoe_up", "effect_value": 0.30},
            {"id": "warcry_t1_2", "name": "long_cry", "effect_type": "duration_up", "effect_value": 5.0},
            {"id": "warcry_t1_3", "name": "def_cry", "effect_type": "damage_up", "effect_value": 0.15},
        ],
        2: [
            {"id": "warcry_t2_1", "name": "battle_shout", "effect_type": "crit_up", "effect_value": 0.10},
            {"id": "warcry_t2_2", "name": "heal_shout", "effect_type": "heal_up", "effect_value": 0.05},
            {"id": "warcry_t2_3", "name": "speed_shout", "effect_type": "cast_speed", "effect_value": 0.20},
        ],
        3: [
            {"id": "warcry_t3_1", "name": "berserker_rage", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "warcry_t3_2", "name": "guardian_oath", "effect_type": "heal_up", "effect_value": 0.15},
        ],
    },
    6: {  # wind_slash
        1: [
            {"id": "windslash_t1_1", "name": "gale_force", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "windslash_t1_2", "name": "wide_wind", "effect_type": "aoe_up", "effect_value": 0.30},
            {"id": "windslash_t1_3", "name": "wind_pierce", "effect_type": "penetrate", "effect_value": 3},
        ],
        2: [
            {"id": "windslash_t2_1", "name": "tornado", "effect_type": "aoe_up", "effect_value": 0.80},
            {"id": "windslash_t2_2", "name": "crit_wind", "effect_type": "crit_up", "effect_value": 0.15},
            {"id": "windslash_t2_3", "name": "double_wind", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "windslash_t3_1", "name": "storm_blade", "effect_type": "element_convert", "effect_value": "wind"},
            {"id": "windslash_t3_2", "name": "vacuum_slash", "effect_type": "knockback", "effect_value": 1.0},
        ],
    },
    7: {  # stun_blow
        1: [
            {"id": "stunblow_t1_1", "name": "heavy_blow", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "stunblow_t1_2", "name": "quick_blow", "effect_type": "cooldown_down", "effect_value": 3.0},
            {"id": "stunblow_t1_3", "name": "wide_blow", "effect_type": "aoe_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "stunblow_t2_1", "name": "stun_extend", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "stunblow_t2_2", "name": "armor_break", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "stunblow_t2_3", "name": "ground_slam", "effect_type": "knockback", "effect_value": 0.80},
        ],
        3: [
            {"id": "stunblow_t3_1", "name": "earthquake", "effect_type": "element_convert", "effect_value": "earth"},
            {"id": "stunblow_t3_2", "name": "execute", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    8: {  # blade_dance
        1: [
            {"id": "bladedance_t1_1", "name": "spin_extend", "effect_type": "multi_hit", "effect_value": 7},
            {"id": "bladedance_t1_2", "name": "move_dance", "effect_type": "cast_speed", "effect_value": 0.30},
            {"id": "bladedance_t1_3", "name": "crit_dance", "effect_type": "crit_up", "effect_value": 0.15},
        ],
        2: [
            {"id": "bladedance_t2_1", "name": "blood_dance", "effect_type": "bleed_dot", "effect_value": 0.15},
            {"id": "bladedance_t2_2", "name": "wide_dance", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "bladedance_t2_3", "name": "fury_dance", "effect_type": "damage_up", "effect_value": 0.40},
        ],
        3: [
            {"id": "bladedance_t3_1", "name": "inferno_dance", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "bladedance_t3_2", "name": "phantom_dance", "effect_type": "invincible", "effect_value": 1},
        ],
    },
    9: {  # earth_shaker
        1: [
            {"id": "earthshaker_t1_1", "name": "wide_quake", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "earthshaker_t1_2", "name": "fast_slam", "effect_type": "cast_speed", "effect_value": 0.30},
            {"id": "earthshaker_t1_3", "name": "heavy_slam", "effect_type": "damage_up", "effect_value": 0.25},
        ],
        2: [
            {"id": "earthshaker_t2_1", "name": "aftershock", "effect_type": "bleed_dot", "effect_value": 0.25},
            {"id": "earthshaker_t2_2", "name": "fissure", "effect_type": "penetrate", "effect_value": 8},
            {"id": "earthshaker_t2_3", "name": "stun_quake", "effect_type": "duration_up", "effect_value": 1.5},
        ],
        3: [
            {"id": "earthshaker_t3_1", "name": "volcanic_eruption", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "earthshaker_t3_2", "name": "world_breaker", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    # ---- Archer (skill 21-28) ----
    21: {  # arrow_rain
        1: [
            {"id": "arrowrain_t1_1", "name": "dense_rain", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "arrowrain_t1_2", "name": "wide_rain", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "arrowrain_t1_3", "name": "quick_rain", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "arrowrain_t2_1", "name": "poison_rain", "effect_type": "bleed_dot", "effect_value": 0.15},
            {"id": "arrowrain_t2_2", "name": "slow_rain", "effect_type": "slow_enhance", "effect_value": 0.30},
            {"id": "arrowrain_t2_3", "name": "barrage", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "arrowrain_t3_1", "name": "meteor_shower", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "arrowrain_t3_2", "name": "frozen_rain", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    22: {  # quick_shot
        1: [
            {"id": "quickshot_t1_1", "name": "triple_shot", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "quickshot_t1_2", "name": "precise_shot", "effect_type": "crit_up", "effect_value": 0.20},
            {"id": "quickshot_t1_3", "name": "long_shot", "effect_type": "range_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "quickshot_t2_1", "name": "explosive_shot", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "quickshot_t2_2", "name": "poison_shot", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "quickshot_t2_3", "name": "ricochet", "effect_type": "penetrate", "effect_value": 3},
        ],
        3: [
            {"id": "quickshot_t3_1", "name": "lightning_shot", "effect_type": "element_convert", "effect_value": "lightning"},
            {"id": "quickshot_t3_2", "name": "phantom_shot", "effect_type": "damage_up", "effect_value": 0.80},
        ],
    },
    23: {  # evasion_shot
        1: [
            {"id": "evasionshot_t1_1", "name": "long_evade", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "evasionshot_t1_2", "name": "counter_shot", "effect_type": "damage_up", "effect_value": 0.40},
            {"id": "evasionshot_t1_3", "name": "fast_evade", "effect_type": "cooldown_down", "effect_value": 2.0},
        ],
        2: [
            {"id": "evasionshot_t2_1", "name": "smoke_bomb", "effect_type": "slow_enhance", "effect_value": 0.50},
            {"id": "evasionshot_t2_2", "name": "double_evade", "effect_type": "multi_hit", "effect_value": 2},
            {"id": "evasionshot_t2_3", "name": "stealth_evade", "effect_type": "invincible", "effect_value": 1},
        ],
        3: [
            {"id": "evasionshot_t3_1", "name": "wind_step", "effect_type": "element_convert", "effect_value": "wind"},
            {"id": "evasionshot_t3_2", "name": "shadow_step", "effect_type": "cooldown_down", "effect_value": 5.0},
        ],
    },
    24: {  # trap
        1: [
            {"id": "trap_t1_1", "name": "big_trap", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "trap_t1_2", "name": "quick_trap", "effect_type": "cast_speed", "effect_value": 0.40},
            {"id": "trap_t1_3", "name": "damage_trap", "effect_type": "damage_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "trap_t2_1", "name": "poison_trap", "effect_type": "bleed_dot", "effect_value": 0.25},
            {"id": "trap_t2_2", "name": "stun_trap", "effect_type": "duration_up", "effect_value": 2.0},
            {"id": "trap_t2_3", "name": "multi_trap", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "trap_t3_1", "name": "ice_trap", "effect_type": "element_convert", "effect_value": "ice"},
            {"id": "trap_t3_2", "name": "explosive_trap", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    25: {  # snipe
        1: [
            {"id": "snipe_t1_1", "name": "quick_aim", "effect_type": "cast_speed", "effect_value": 0.50},
            {"id": "snipe_t1_2", "name": "heavy_snipe", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "snipe_t1_3", "name": "long_snipe", "effect_type": "range_up", "effect_value": 0.50},
        ],
        2: [
            {"id": "snipe_t2_1", "name": "armor_pierce", "effect_type": "penetrate", "effect_value": 10},
            {"id": "snipe_t2_2", "name": "headshot", "effect_type": "crit_up", "effect_value": 0.30},
            {"id": "snipe_t2_3", "name": "double_snipe", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "snipe_t3_1", "name": "death_shot", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "snipe_t3_2", "name": "lightning_snipe", "effect_type": "element_convert", "effect_value": "lightning"},
        ],
    },
    26: {  # multi_shot
        1: [
            {"id": "multishot_t1_1", "name": "extra_arrows", "effect_type": "multi_hit", "effect_value": 7},
            {"id": "multishot_t1_2", "name": "wide_spread", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "multishot_t1_3", "name": "fast_volley", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "multishot_t2_1", "name": "fire_arrows", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "multishot_t2_2", "name": "crit_volley", "effect_type": "crit_up", "effect_value": 0.15},
            {"id": "multishot_t2_3", "name": "pierce_volley", "effect_type": "penetrate", "effect_value": 5},
        ],
        3: [
            {"id": "multishot_t3_1", "name": "arrow_storm", "effect_type": "damage_up", "effect_value": 0.80},
            {"id": "multishot_t3_2", "name": "ice_volley", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    27: {  # piercing_arrow
        1: [
            {"id": "piercing_t1_1", "name": "long_pierce", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "piercing_t1_2", "name": "heavy_pierce", "effect_type": "damage_up", "effect_value": 0.25},
            {"id": "piercing_t1_3", "name": "multi_pierce", "effect_type": "penetrate", "effect_value": 8},
        ],
        2: [
            {"id": "piercing_t2_1", "name": "bleed_arrow", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "piercing_t2_2", "name": "crit_pierce", "effect_type": "crit_up", "effect_value": 0.20},
            {"id": "piercing_t2_3", "name": "chain_pierce", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "piercing_t3_1", "name": "thunder_arrow", "effect_type": "element_convert", "effect_value": "lightning"},
            {"id": "piercing_t3_2", "name": "void_arrow", "effect_type": "damage_up", "effect_value": 1.2},
        ],
    },
    28: {  # arrow_storm
        1: [
            {"id": "arrowstorm_t1_1", "name": "wide_storm", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "arrowstorm_t1_2", "name": "heavy_storm", "effect_type": "damage_up", "effect_value": 0.25},
            {"id": "arrowstorm_t1_3", "name": "fast_storm", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "arrowstorm_t2_1", "name": "poison_storm", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "arrowstorm_t2_2", "name": "slow_storm", "effect_type": "slow_enhance", "effect_value": 0.40},
            {"id": "arrowstorm_t2_3", "name": "crit_storm", "effect_type": "crit_up", "effect_value": 0.15},
        ],
        3: [
            {"id": "arrowstorm_t3_1", "name": "meteor_rain", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "arrowstorm_t3_2", "name": "blizzard_arrows", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    # ---- Mage (skill 41-48) ----
    41: {  # fireball
        1: [
            {"id": "fireball_t1_1", "name": "big_fireball", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "fireball_t1_2", "name": "fast_fireball", "effect_type": "cast_speed", "effect_value": 0.40},
            {"id": "fireball_t1_3", "name": "heavy_fireball", "effect_type": "damage_up", "effect_value": 0.25},
        ],
        2: [
            {"id": "fireball_t2_1", "name": "triple_fireball", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "fireball_t2_2", "name": "burn_fireball", "effect_type": "bleed_dot", "effect_value": 0.25},
            {"id": "fireball_t2_3", "name": "piercing_fire", "effect_type": "penetrate", "effect_value": 5},
        ],
        3: [
            {"id": "fireball_t3_1", "name": "inferno", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "fireball_t3_2", "name": "ice_convert", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    42: {  # ice_bolt
        1: [
            {"id": "icebolt_t1_1", "name": "multi_bolt", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "icebolt_t1_2", "name": "heavy_bolt", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "icebolt_t1_3", "name": "long_bolt", "effect_type": "range_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "icebolt_t2_1", "name": "freeze_bolt", "effect_type": "duration_up", "effect_value": 2.0},
            {"id": "icebolt_t2_2", "name": "shatter", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "icebolt_t2_3", "name": "ice_spread", "effect_type": "aoe_up", "effect_value": 0.50},
        ],
        3: [
            {"id": "icebolt_t3_1", "name": "absolute_zero", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "icebolt_t3_2", "name": "fire_convert", "effect_type": "element_convert", "effect_value": "fire"},
        ],
    },
    43: {  # mana_shield
        1: [
            {"id": "manashield_t1_1", "name": "strong_shield", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "manashield_t1_2", "name": "efficient_shield", "effect_type": "cooldown_down", "effect_value": 3.0},
            {"id": "manashield_t1_3", "name": "quick_shield", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "manashield_t2_1", "name": "reflect_shield", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "manashield_t2_2", "name": "aoe_shield", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "manashield_t2_3", "name": "regen_shield", "effect_type": "heal_up", "effect_value": 0.05},
        ],
        3: [
            {"id": "manashield_t3_1", "name": "divine_barrier", "effect_type": "invincible", "effect_value": 1},
            {"id": "manashield_t3_2", "name": "mana_explosion", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    44: {  # lightning
        1: [
            {"id": "lightning_t1_1", "name": "chain_lightning", "effect_type": "penetrate", "effect_value": 5},
            {"id": "lightning_t1_2", "name": "heavy_bolt", "effect_type": "damage_up", "effect_value": 0.25},
            {"id": "lightning_t1_3", "name": "wide_bolt", "effect_type": "aoe_up", "effect_value": 0.40},
        ],
        2: [
            {"id": "lightning_t2_1", "name": "stun_extend", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "lightning_t2_2", "name": "overcharge", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "lightning_t2_3", "name": "ball_lightning", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "lightning_t3_1", "name": "thunder_god", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "lightning_t3_2", "name": "ice_convert", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    45: {  # blizzard
        1: [
            {"id": "blizzard_t1_1", "name": "wide_blizzard", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "blizzard_t1_2", "name": "deep_freeze", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "blizzard_t1_3", "name": "fast_blizzard", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "blizzard_t2_1", "name": "shatter_blizzard", "effect_type": "damage_up", "effect_value": 0.40},
            {"id": "blizzard_t2_2", "name": "slow_field", "effect_type": "slow_enhance", "effect_value": 0.50},
            {"id": "blizzard_t2_3", "name": "ice_spikes", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "blizzard_t3_1", "name": "ice_age", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "blizzard_t3_2", "name": "fire_convert", "effect_type": "element_convert", "effect_value": "fire"},
        ],
    },
    46: {  # teleport
        1: [
            {"id": "teleport_t1_1", "name": "long_teleport", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "teleport_t1_2", "name": "fast_teleport", "effect_type": "cooldown_down", "effect_value": 3.0},
            {"id": "teleport_t1_3", "name": "safe_teleport", "effect_type": "invincible", "effect_value": 1},
        ],
        2: [
            {"id": "teleport_t2_1", "name": "blink_strike", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "teleport_t2_2", "name": "double_blink", "effect_type": "multi_hit", "effect_value": 2},
            {"id": "teleport_t2_3", "name": "decoy", "effect_type": "slow_enhance", "effect_value": 0.30},
        ],
        3: [
            {"id": "teleport_t3_1", "name": "dimension_rift", "effect_type": "aoe_up", "effect_value": 1.0},
            {"id": "teleport_t3_2", "name": "time_warp", "effect_type": "cooldown_down", "effect_value": 8.0},
        ],
    },
    47: {  # meteor
        1: [
            {"id": "meteor_t1_1", "name": "fast_meteor", "effect_type": "cast_speed", "effect_value": 0.40},
            {"id": "meteor_t1_2", "name": "wide_meteor", "effect_type": "aoe_up", "effect_value": 0.30},
            {"id": "meteor_t1_3", "name": "heavy_meteor", "effect_type": "damage_up", "effect_value": 0.25},
        ],
        2: [
            {"id": "meteor_t2_1", "name": "meteor_shower", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "meteor_t2_2", "name": "burn_field", "effect_type": "bleed_dot", "effect_value": 0.30},
            {"id": "meteor_t2_3", "name": "stun_impact", "effect_type": "duration_up", "effect_value": 1.5},
        ],
        3: [
            {"id": "meteor_t3_1", "name": "apocalypse", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "meteor_t3_2", "name": "ice_comet", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    48: {  # holy_light
        1: [
            {"id": "holylight_t1_1", "name": "wide_heal", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "holylight_t1_2", "name": "strong_heal", "effect_type": "heal_up", "effect_value": 0.30},
            {"id": "holylight_t1_3", "name": "fast_heal", "effect_type": "cast_speed", "effect_value": 0.40},
        ],
        2: [
            {"id": "holylight_t2_1", "name": "regen", "effect_type": "duration_up", "effect_value": 5.0},
            {"id": "holylight_t2_2", "name": "cleanse", "effect_type": "heal_up", "effect_value": 0.50},
            {"id": "holylight_t2_3", "name": "shield_heal", "effect_type": "damage_up", "effect_value": 0.30},
        ],
        3: [
            {"id": "holylight_t3_1", "name": "divine_blessing", "effect_type": "heal_up", "effect_value": 1.0},
            {"id": "holylight_t3_2", "name": "holy_nova", "effect_type": "damage_up", "effect_value": 0.80},
        ],
    },
}

# Scroll drop rates by monster type (GDD tripod.yaml acquisition)
SCROLL_DROP_RATES = {
    "normal": 0.0,
    "elite": 0.05,       # 5%
    "dungeon_boss": 0.15, # 15%
    "raid_boss": 0.30,    # 30%
}

# Skill -> class mapping (for class-restricted scroll drops)
SKILL_CLASS_MAP = {
    2: "warrior", 3: "warrior", 4: "warrior", 5: "warrior",
    6: "warrior", 7: "warrior", 8: "warrior", 9: "warrior",
    21: "archer", 22: "archer", 23: "archer", 24: "archer",
    25: "archer", 26: "archer", 27: "archer", 28: "archer",
    41: "mage", 42: "mage", 43: "mage", 44: "mage",
    45: "mage", 46: "mage", 47: "mage", 48: "mage",
}

# Class -> skill list
CLASS_SKILLS = {
    "warrior": [2, 3, 4, 5, 6, 7, 8, 9],
    "archer": [21, 22, 23, 24, 25, 26, 27, 28],
    "mage": [41, 42, 43, 44, 45, 46, 47, 48],
}
'''

# ====================================================================
# 3. PlayerSession fields for tripod/scroll
# ====================================================================
SESSION_FIELDS = (
    '    # Tripod & Scroll System (TASK 15)\n'
    '    tripod_unlocked: dict = field(default_factory=dict)  # {skill_id: {tier: [unlocked_option_ids]}}\n'
    '    tripod_equipped: dict = field(default_factory=dict)  # {skill_id: {tier: option_id}}\n'
    '    scroll_collection: set = field(default_factory=set)  # set of discovered scroll_ids\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '\n'
    '            MsgType.TRIPOD_LIST_REQ: self._on_tripod_list_req,\n'
    '            MsgType.TRIPOD_EQUIP: self._on_tripod_equip,\n'
    '            MsgType.SCROLL_DISCOVER: self._on_scroll_discover,'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Tripod & Scroll System (TASK 15: MsgType 520-524) ----

    async def _on_tripod_list_req(self, session: PlayerSession, payload: bytes):
        """TRIPOD_LIST_REQ(520): no payload needed.
        Returns all unlocked tripods + equipped selections for the character's class.
        Response format: skill_count(u8) + [skill_id(u16) + tier_count(u8) + [tier(u8) + unlocked_count(u8) + [option_idx(u8)] + equipped_idx(u8)]]"""
        if not session.in_game:
            return

        # Determine class from char_class
        class_name = session.char_class if hasattr(session, 'char_class') and session.char_class else "warrior"
        class_skills = CLASS_SKILLS.get(class_name, CLASS_SKILLS.get("warrior", []))

        parts = []
        skill_entries = []
        for skill_id in class_skills:
            if skill_id not in TRIPOD_TABLE:
                continue
            skill_tiers = TRIPOD_TABLE[skill_id]
            tier_data = []
            for tier in [1, 2, 3]:
                if tier not in skill_tiers:
                    continue
                # Check unlock level requirement
                req_level = TRIPOD_TIER_UNLOCK.get(tier, 99)
                if session.stats.level < req_level:
                    continue
                # Get unlocked options for this skill+tier
                unlocked = session.tripod_unlocked.get(skill_id, {}).get(tier, [])
                # Get equipped option
                equipped_id = session.tripod_equipped.get(skill_id, {}).get(tier, "")
                # Map option_id to index
                options = skill_tiers[tier]
                unlocked_indices = []
                equipped_idx = 0xFF  # none
                for oi, opt in enumerate(options):
                    if opt["id"] in unlocked:
                        unlocked_indices.append(oi)
                    if opt["id"] == equipped_id:
                        equipped_idx = oi
                tier_data.append((tier, unlocked_indices, equipped_idx))
            if tier_data:
                skill_entries.append((skill_id, tier_data))

        # Build response
        parts.append(struct.pack("<B", len(skill_entries)))
        for skill_id, tier_data in skill_entries:
            parts.append(struct.pack("<HB", skill_id, len(tier_data)))
            for tier, unlocked_indices, equipped_idx in tier_data:
                parts.append(struct.pack("<BB", tier, len(unlocked_indices)))
                for idx in unlocked_indices:
                    parts.append(struct.pack("<B", idx))
                parts.append(struct.pack("<B", equipped_idx))

        self._send(session, MsgType.TRIPOD_LIST, b"".join(parts))
        total_unlocked = sum(
            len(opts) for sk in session.tripod_unlocked.values() for opts in sk.values()
        )
        self.log(f"TripodList: {session.char_name} class={class_name} unlocked={total_unlocked}", "TRIPOD")

    async def _on_tripod_equip(self, session: PlayerSession, payload: bytes):
        """TRIPOD_EQUIP(522): skill_id(u16) + tier(u8) + option_idx(u8).
        Result codes: 0=ok, 1=not_in_game, 2=invalid_skill, 3=tier_locked, 4=not_unlocked, 5=need_lower_tier"""
        if not session.in_game:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 1))
            return
        if len(payload) < 4:
            return
        skill_id = struct.unpack_from("<H", payload, 0)[0]
        tier = payload[2]
        option_idx = payload[3]

        # Validate skill exists in tripod table
        if skill_id not in TRIPOD_TABLE or tier not in TRIPOD_TABLE[skill_id]:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 2))
            return

        # Check tier level requirement
        req_level = TRIPOD_TIER_UNLOCK.get(tier, 99)
        if session.stats.level < req_level:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 3))
            return

        # Check that lower tier has an equipped option (tier 2 needs tier 1, tier 3 needs tier 2)
        if tier > 1:
            lower_tier = tier - 1
            if lower_tier in TRIPOD_TABLE.get(skill_id, {}):
                lower_equipped = session.tripod_equipped.get(skill_id, {}).get(lower_tier, "")
                if not lower_equipped:
                    self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 5))
                    return

        # Check option exists and is unlocked
        options = TRIPOD_TABLE[skill_id][tier]
        if option_idx >= len(options):
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 4))
            return
        option_id = options[option_idx]["id"]
        unlocked = session.tripod_unlocked.get(skill_id, {}).get(tier, [])
        if option_id not in unlocked:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 4))
            return

        # Equip
        if skill_id not in session.tripod_equipped:
            session.tripod_equipped[skill_id] = {}
        session.tripod_equipped[skill_id][tier] = option_id

        self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 0))
        opt_name = options[option_idx]["name"]
        self.log(f"TripodEquip: {session.char_name} skill={skill_id} tier={tier} -> {opt_name}", "TRIPOD")

    async def _on_scroll_discover(self, session: PlayerSession, payload: bytes):
        """SCROLL_DISCOVER(524): scroll_item_slot(u8).
        Uses a scroll item from inventory to permanently unlock a tripod option.
        Response (broadcast to self): SCROLL_DISCOVER(524) with result.
        Format: result(u8) + skill_id(u16) + tier(u8) + option_idx(u8)
        Result: 0=ok, 1=not_in_game, 2=no_item, 3=already_unlocked, 4=wrong_class"""
        if not session.in_game:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 1))
            return
        if len(payload) < 1:
            return
        slot_idx = payload[0]

        # Validate inventory slot
        if slot_idx >= len(session.inventory) or session.inventory[slot_idx].item_id == 0:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 2))
            return

        # Scroll items have item_id in range 9000-9999 (convention)
        # Format: 9000 + skill_id * 10 + tier * 3 + option_idx
        # Simplified: just use item_id to lookup in a reverse map
        item_id = session.inventory[slot_idx].item_id
        scroll_info = self._resolve_scroll(item_id)
        if scroll_info is None:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 2))
            return

        skill_id, tier, option_idx, option_id = scroll_info

        # Check class restriction
        class_name = session.char_class if hasattr(session, 'char_class') and session.char_class else "warrior"
        skill_class = SKILL_CLASS_MAP.get(skill_id, "")
        if skill_class and skill_class != class_name:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 4))
            return

        # Check if already unlocked
        unlocked = session.tripod_unlocked.get(skill_id, {}).get(tier, [])
        if option_id in unlocked:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 3))
            return

        # Consume scroll item
        session.inventory[slot_idx].count -= 1
        if session.inventory[slot_idx].count <= 0:
            session.inventory[slot_idx].item_id = 0
            session.inventory[slot_idx].count = 0

        # Unlock tripod option
        if skill_id not in session.tripod_unlocked:
            session.tripod_unlocked[skill_id] = {}
        if tier not in session.tripod_unlocked[skill_id]:
            session.tripod_unlocked[skill_id][tier] = []
        session.tripod_unlocked[skill_id][tier].append(option_id)

        # Add to scroll collection (for codex)
        session.scroll_collection.add(option_id)

        # Send success response
        self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<BHBB", 0, skill_id, tier, option_idx))
        opt_name = TRIPOD_TABLE[skill_id][tier][option_idx]["name"]
        self.log(f"ScrollDiscover: {session.char_name} unlocked skill={skill_id} tier={tier} option={opt_name}", "TRIPOD")

    def _resolve_scroll(self, item_id):
        """Resolve a scroll item_id to (skill_id, tier, option_idx, option_id).
        Scroll item_id convention: base 9000.
        Encoding: 9000 + (skill_idx_in_table * 100) + (tier * 10) + option_idx
        where skill_idx_in_table is position in sorted TRIPOD_TABLE keys.
        Returns None if not a valid scroll."""
        if item_id < 9000 or item_id >= 9000 + len(TRIPOD_TABLE) * 100 + 40:
            return None
        offset = item_id - 9000
        # Decode: skill_pos * 100 + tier * 10 + option_idx
        skill_pos = offset // 100
        remainder = offset % 100
        tier = remainder // 10
        option_idx = remainder % 10

        sorted_skills = sorted(TRIPOD_TABLE.keys())
        if skill_pos >= len(sorted_skills):
            return None
        skill_id = sorted_skills[skill_pos]
        if tier < 1 or tier > 3:
            return None
        if tier not in TRIPOD_TABLE[skill_id]:
            return None
        options = TRIPOD_TABLE[skill_id][tier]
        if option_idx >= len(options):
            return None
        return (skill_id, tier, option_idx, options[option_idx]["id"])

    def _generate_scroll_item_id(self, skill_id, tier, option_idx):
        """Generate a scroll item_id from skill_id + tier + option_idx."""
        sorted_skills = sorted(TRIPOD_TABLE.keys())
        if skill_id not in sorted_skills:
            return None
        skill_pos = sorted_skills.index(skill_id)
        return 9000 + skill_pos * 100 + tier * 10 + option_idx

    def _try_scroll_drop(self, session, monster_type="normal"):
        """Roll for scroll drop on monster kill. Returns scroll item_id or None.
        Called from monster kill handler. Class-filtered."""
        import random as _rng
        drop_rate = SCROLL_DROP_RATES.get(monster_type, 0.0)
        if drop_rate <= 0 or _rng.random() > drop_rate:
            return None

        # Pick random skill for this player's class
        class_name = session.char_class if hasattr(session, 'char_class') and session.char_class else "warrior"
        skills = CLASS_SKILLS.get(class_name, [])
        if not skills:
            return None

        skill_id = _rng.choice(skills)
        if skill_id not in TRIPOD_TABLE:
            return None

        # Pick random tier (weighted: tier1=50%, tier2=35%, tier3=15%)
        tier_roll = _rng.random()
        if tier_roll < 0.50:
            tier = 1
        elif tier_roll < 0.85:
            tier = 2
        else:
            tier = 3

        if tier not in TRIPOD_TABLE[skill_id]:
            tier = 1  # fallback

        options = TRIPOD_TABLE[skill_id][tier]
        option_idx = _rng.randint(0, len(options) - 1)

        return self._generate_scroll_item_id(skill_id, tier, option_idx)

'''

# ====================================================================
# 6. Test cases
# ====================================================================
TEST_CODE = r'''
    # ---- TASK 15: Tripod & Scroll Tests (S046) ----

    async def test_scroll_discover_and_unlock():
        """비급 사용: 스크롤 아이템으로 트라이포드 해금."""
        c = await login_and_enter(port)
        # Generate a scroll item_id for warrior skill 2 (slash), tier 1, option 0
        # skill_pos for skill_id=2: sorted keys = [2,3,4,5,6,7,8,9,21,...] -> pos=0
        # item_id = 9000 + 0*100 + 1*10 + 0 = 9010
        scroll_item_id = 9010
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', scroll_item_id, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        # Use scroll from slot 0
        await c.send(MsgType.SCROLL_DISCOVER, struct.pack('<B', 0))
        msg_type, resp = await c.recv_expect(MsgType.SCROLL_DISCOVER)
        assert msg_type == MsgType.SCROLL_DISCOVER, f"Expected SCROLL_DISCOVER, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        skill_id = struct.unpack_from('<H', resp, 1)[0]
        assert skill_id == 2, f"Expected skill_id=2, got {skill_id}"
        tier = resp[3]
        assert tier == 1, f"Expected tier=1, got {tier}"
        c.close()

    await test("SCROLL_DISCOVER: 비급 사용 -> 트라이포드 해금", test_scroll_discover_and_unlock())

    async def test_scroll_already_unlocked():
        """비급 중복 사용: 이미 해금된 옵션은 실패."""
        c = await login_and_enter(port)
        scroll_item_id = 9010
        # 첫 사용: 해금
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', scroll_item_id, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        await c.send(MsgType.SCROLL_DISCOVER, struct.pack('<B', 0))
        await c.recv_expect(MsgType.SCROLL_DISCOVER)
        # 두 번째 사용: 중복
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', scroll_item_id, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        await c.send(MsgType.SCROLL_DISCOVER, struct.pack('<B', 0))
        msg_type, resp = await c.recv_expect(MsgType.SCROLL_DISCOVER)
        assert msg_type == MsgType.SCROLL_DISCOVER
        result = resp[0]
        assert result == 3, f"Expected ALREADY_UNLOCKED(3), got {result}"
        c.close()

    await test("SCROLL_DISCOVER: 중복 해금 차단", test_scroll_already_unlocked())

    async def test_tripod_equip():
        """트라이포드 장착: 해금 후 장착."""
        c = await login_and_enter(port)
        # 먼저 해금
        scroll_item_id = 9010  # skill=2, tier=1, option=0
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', scroll_item_id, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        await c.send(MsgType.SCROLL_DISCOVER, struct.pack('<B', 0))
        await c.recv_expect(MsgType.SCROLL_DISCOVER)
        # 장착: skill_id=2, tier=1, option_idx=0
        await c.send(MsgType.TRIPOD_EQUIP, struct.pack('<HBB', 2, 1, 0))
        msg_type, resp = await c.recv_expect(MsgType.TRIPOD_EQUIP_RESULT)
        assert msg_type == MsgType.TRIPOD_EQUIP_RESULT, f"Expected TRIPOD_EQUIP_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        c.close()

    await test("TRIPOD_EQUIP: 트라이포드 장착 성공", test_tripod_equip())

    async def test_tripod_equip_not_unlocked():
        """트라이포드 장착 실패: 미해금 옵션."""
        c = await login_and_enter(port)
        # 해금 없이 바로 장착 시도: skill=2, tier=1, option=2 (미해금)
        await c.send(MsgType.TRIPOD_EQUIP, struct.pack('<HBB', 2, 1, 2))
        msg_type, resp = await c.recv_expect(MsgType.TRIPOD_EQUIP_RESULT)
        assert msg_type == MsgType.TRIPOD_EQUIP_RESULT
        result = resp[0]
        assert result == 4, f"Expected NOT_UNLOCKED(4), got {result}"
        c.close()

    await test("TRIPOD_EQUIP_FAIL: 미해금 옵션 장착 시도", test_tripod_equip_not_unlocked())

    async def test_tripod_list():
        """트라이포드 목록 조회."""
        c = await login_and_enter(port)
        # 먼저 하나 해금 + 장착
        scroll_item_id = 9010
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', scroll_item_id, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        await c.send(MsgType.SCROLL_DISCOVER, struct.pack('<B', 0))
        await c.recv_expect(MsgType.SCROLL_DISCOVER)
        await c.send(MsgType.TRIPOD_EQUIP, struct.pack('<HBB', 2, 1, 0))
        await c.recv_expect(MsgType.TRIPOD_EQUIP_RESULT)
        # 목록 조회
        await c.send(MsgType.TRIPOD_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.TRIPOD_LIST)
        assert msg_type == MsgType.TRIPOD_LIST, f"Expected TRIPOD_LIST, got {msg_type}"
        skill_count = resp[0]
        assert skill_count >= 1, f"Expected at least 1 skill with tripod data, got {skill_count}"
        c.close()

    await test("TRIPOD_LIST: 트라이포드 목록 조회", test_tripod_list())
'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check
    if 'TRIPOD_LIST_REQ = 520' in content and 'def _on_tripod_list_req' in content:
        print('[bridge] S046 already patched')
        return True

    changed = False

    # 1. MsgType -- after AUCTION_BID_RESULT = 397
    if 'TRIPOD_LIST_REQ' not in content:
        marker = '    AUCTION_BID_RESULT = 397'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 520-524')
        else:
            print('[bridge] WARNING: Could not find AUCTION_BID_RESULT = 397')

    # 2. Data constants -- after DAILY_GOLD_CAPS closing brace
    if 'TRIPOD_TABLE' not in content:
        marker = '"total": 100000,\n}'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx + len(marker) - 1) + 1
            content = content[:end] + DATA_CONSTANTS + content[end:]
            changed = True
            print('[bridge] Added tripod data constants + TRIPOD_TABLE')
        else:
            # Fallback: after DAILY_GOLD_CAPS dict
            marker2 = 'DAILY_GOLD_CAPS = {'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                # Find closing }
                brace_count = 0
                for ci in range(idx2, len(content)):
                    if content[ci] == '{':
                        brace_count += 1
                    elif content[ci] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = content.index('\n', ci) + 1
                            content = content[:end] + DATA_CONSTANTS + content[end:]
                            changed = True
                            print('[bridge] Added tripod data (fallback)')
                            break

    # 3. PlayerSession fields -- after daily_gold_reset_date
    if 'tripod_unlocked' not in content:
        marker = '    daily_gold_reset_date: str = ""       # last reset date (YYYY-MM-DD)'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession tripod fields')
        else:
            # Fallback after auction_listings
            marker2 = '    auction_listings: int = 0'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession tripod fields (fallback)')

    # 4. Dispatch table -- after auction_bid dispatch
    if 'self._on_tripod_list_req' not in content:
        marker = '            MsgType.AUCTION_BID: self._on_auction_bid,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            print('[bridge] WARNING: Could not find auction_bid dispatch entry')

    # 5. Handler implementations -- before Auction House handlers
    if 'def _on_tripod_list_req' not in content:
        marker = '    # ---- Auction House System (TASK 3: MsgType 390-397) ----'
        idx = content.find(marker)
        if idx < 0:
            # Try before crafting
            marker = '    # ---- Crafting/Gathering/Cooking/Enchanting System'
            idx = content.find(marker)
        if idx < 0:
            marker = '    def _clean_expired_auctions'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added tripod handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    if changed:
        with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

    # Verify
    checks = [
        'TRIPOD_LIST_REQ = 520', 'TRIPOD_TABLE', 'TRIPOD_TIER_UNLOCK',
        'SCROLL_DROP_RATES', 'SKILL_CLASS_MAP', 'CLASS_SKILLS',
        'def _on_tripod_list_req', 'def _on_tripod_equip',
        'def _on_scroll_discover', 'def _resolve_scroll',
        'def _try_scroll_drop', 'self._on_tripod_list_req',
        'tripod_unlocked', 'tripod_equipped', 'scroll_collection',
    ]
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S046 patched OK -- 3 tripod handlers + scroll resolve + drop logic + full tripod table')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_scroll_discover_and_unlock' in content:
        print('[test] S046 already patched')
        return True

    # Update imports to add tripod constants
    old_import = (
        '    AUCTION_TAX_RATE, AUCTION_LISTING_FEE,\n'
        '    AUCTION_MAX_LISTINGS, DAILY_GOLD_CAPS\n'
        ')'
    )
    new_import = (
        '    AUCTION_TAX_RATE, AUCTION_LISTING_FEE,\n'
        '    AUCTION_MAX_LISTINGS, DAILY_GOLD_CAPS,\n'
        '    TRIPOD_TABLE, TRIPOD_TIER_UNLOCK,\n'
        '    SCROLL_DROP_RATES, SKILL_CLASS_MAP, CLASS_SKILLS\n'
        ')'
    )
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports')

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

    checks = ['test_scroll_discover_and_unlock', 'test_scroll_already_unlocked',
              'test_tripod_equip', 'test_tripod_equip_not_unlocked', 'test_tripod_list']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S046 patched OK -- 5 tripod/scroll tests added')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS046 all patches applied!')
    else:
        print('\nS046 PATCH FAILED!')
        sys.exit(1)
