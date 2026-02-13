#pragma once

// ━━━ Session 37: GameConfig - 런타임 설정 캐시 ━━━
//
// 목적: constexpr 하드코딩 → 데이터 파일에서 로드 → 런타임 변경 가능
//
// 구조:
//   constexpr (컴파일타임 기본값)
//       ↓ 폴백
//   GameConfig (런타임 캐시)
//       ↑ 로드
//   JSON/CSV 파일 (data/*.json, data/*.csv)
//       ↑ 핫리로드
//   ADMIN_RELOAD 패킷 or 콘솔 명령
//
// 사용법:
//   // 기존: MonsterAI::LEASH_RANGE (constexpr 500.0f)
//   // 변경: g_gameConfig->monster_ai.leash_range (런타임 변경 가능, 기본값 500.0f)
//
//   // 리로드:
//   g_config->Reload("monster_ai");  // 파일에서 다시 읽기
//   g_gameConfig->ApplyFrom(g_config);  // GameConfig에 반영
//
// 원칙:
//   1. 파일 없으면 → constexpr 기본값 사용 (개발 편의)
//   2. 파일 있으면 → 파일 값이 기본값을 덮어씀
//   3. 핫리로드 → 파일 다시 읽기 → ApplyFrom() → 다음 틱부터 새 값 적용

#include "ConfigLoader.h"
#include <cstdint>
#include <cstdio>

// ━━━ 기본값 (constexpr) — 파일 없을 때 폴백 ━━━
// 기존 MonsterAI:: / MovementRules:: 네임스페이스의 값들

namespace Defaults {
    namespace MonsterAI {
        constexpr float MOVE_SPEED              = 80.0f;
        constexpr float PATROL_RADIUS           = 100.0f;
        constexpr float PATROL_MIN_WAIT         = 2.0f;
        constexpr float PATROL_MAX_WAIT         = 5.0f;
        constexpr float LEASH_RANGE             = 500.0f;
        constexpr float CHASE_SPEED_MULT        = 1.3f;
        constexpr float RETURN_HEAL_RATE        = 0.1f;
        constexpr float MOVE_BROADCAST_INTERVAL = 0.2f;
        constexpr float ARRIVAL_THRESHOLD       = 10.0f;
        constexpr float ATTACK_RANGE            = 200.0f;
        constexpr float ATTACK_COOLDOWN         = 2.0f;
        constexpr int   MAX_AGGRO_ENTRIES       = 8;
    }

    namespace Movement {
        constexpr float BASE_SPEED        = 200.0f;
        constexpr float SPRINT_MULTIPLIER = 1.5f;
        constexpr float MOUNT_MULTIPLIER  = 2.0f;
        constexpr float TOLERANCE         = 1.5f;
        constexpr int   UPDATE_RATE_HZ    = 10;
        constexpr float CORRECTION_DIST   = 50.0f;
        constexpr int   MAX_VIOLATIONS    = 5;
        constexpr float MAX_VALID_COORD   = 10000.0f;
    }
}

// ━━━ 런타임 설정 구조체 ━━━

struct MonsterAIConfig {
    float move_speed              = Defaults::MonsterAI::MOVE_SPEED;
    float patrol_radius           = Defaults::MonsterAI::PATROL_RADIUS;
    float patrol_min_wait         = Defaults::MonsterAI::PATROL_MIN_WAIT;
    float patrol_max_wait         = Defaults::MonsterAI::PATROL_MAX_WAIT;
    float leash_range             = Defaults::MonsterAI::LEASH_RANGE;
    float chase_speed_mult        = Defaults::MonsterAI::CHASE_SPEED_MULT;
    float return_heal_rate        = Defaults::MonsterAI::RETURN_HEAL_RATE;
    float move_broadcast_interval = Defaults::MonsterAI::MOVE_BROADCAST_INTERVAL;
    float arrival_threshold       = Defaults::MonsterAI::ARRIVAL_THRESHOLD;
    float attack_range            = Defaults::MonsterAI::ATTACK_RANGE;
    float attack_cooldown         = Defaults::MonsterAI::ATTACK_COOLDOWN;
    int   max_aggro_entries       = Defaults::MonsterAI::MAX_AGGRO_ENTRIES;
};

struct MovementConfig {
    float base_speed        = Defaults::Movement::BASE_SPEED;
    float sprint_multiplier = Defaults::Movement::SPRINT_MULTIPLIER;
    float mount_multiplier  = Defaults::Movement::MOUNT_MULTIPLIER;
    float tolerance         = Defaults::Movement::TOLERANCE;
    int   update_rate_hz    = Defaults::Movement::UPDATE_RATE_HZ;
    float correction_dist   = Defaults::Movement::CORRECTION_DIST;
    int   max_violations    = Defaults::Movement::MAX_VIOLATIONS;
    float max_valid_coord   = Defaults::Movement::MAX_VALID_COORD;
};

// ━━━ GameConfig: 전체 런타임 설정 ━━━

struct GameConfig {
    MonsterAIConfig monster_ai;
    MovementConfig  movement;

    uint32_t version = 0;       // ConfigLoader 버전과 동기화
    uint32_t reload_count = 0;  // 리로드 횟수 추적

    // ConfigLoader에서 값 적용 (없는 키는 기본값 유지)
    void ApplyFrom(const ConfigLoader* config) {
        if (!config) return;

        // Monster AI (JSON)
        auto* mai = config->GetSettings("monster_ai");
        if (mai) {
            monster_ai.move_speed              = mai->GetFloat("move_speed",              Defaults::MonsterAI::MOVE_SPEED);
            monster_ai.patrol_radius           = mai->GetFloat("patrol_radius",           Defaults::MonsterAI::PATROL_RADIUS);
            monster_ai.patrol_min_wait         = mai->GetFloat("patrol_min_wait",         Defaults::MonsterAI::PATROL_MIN_WAIT);
            monster_ai.patrol_max_wait         = mai->GetFloat("patrol_max_wait",         Defaults::MonsterAI::PATROL_MAX_WAIT);
            monster_ai.leash_range             = mai->GetFloat("leash_range",             Defaults::MonsterAI::LEASH_RANGE);
            monster_ai.chase_speed_mult        = mai->GetFloat("chase_speed_mult",        Defaults::MonsterAI::CHASE_SPEED_MULT);
            monster_ai.return_heal_rate        = mai->GetFloat("return_heal_rate",        Defaults::MonsterAI::RETURN_HEAL_RATE);
            monster_ai.move_broadcast_interval = mai->GetFloat("move_broadcast_interval", Defaults::MonsterAI::MOVE_BROADCAST_INTERVAL);
            monster_ai.arrival_threshold       = mai->GetFloat("arrival_threshold",       Defaults::MonsterAI::ARRIVAL_THRESHOLD);
            monster_ai.attack_range            = mai->GetFloat("attack_range",            Defaults::MonsterAI::ATTACK_RANGE);
            monster_ai.attack_cooldown         = mai->GetFloat("attack_cooldown",         Defaults::MonsterAI::ATTACK_COOLDOWN);
            monster_ai.max_aggro_entries        = mai->GetInt("max_aggro_entries",         Defaults::MonsterAI::MAX_AGGRO_ENTRIES);
            printf("[GameConfig] monster_ai applied (leash=%.0f, chase_mult=%.1f, patrol_r=%.0f)\n",
                   monster_ai.leash_range, monster_ai.chase_speed_mult, monster_ai.patrol_radius);
        }

        // Movement Rules (JSON)
        auto* mv = config->GetSettings("movement_rules");
        if (mv) {
            movement.base_speed        = mv->GetFloat("base_speed",        Defaults::Movement::BASE_SPEED);
            movement.sprint_multiplier = mv->GetFloat("sprint_multiplier", Defaults::Movement::SPRINT_MULTIPLIER);
            movement.mount_multiplier  = mv->GetFloat("mount_multiplier",  Defaults::Movement::MOUNT_MULTIPLIER);
            movement.tolerance         = mv->GetFloat("tolerance",         Defaults::Movement::TOLERANCE);
            movement.update_rate_hz    = mv->GetInt("update_rate_hz",      Defaults::Movement::UPDATE_RATE_HZ);
            movement.correction_dist   = mv->GetFloat("correction_dist",   Defaults::Movement::CORRECTION_DIST);
            movement.max_violations    = mv->GetInt("max_violations",      Defaults::Movement::MAX_VIOLATIONS);
            movement.max_valid_coord   = mv->GetFloat("max_valid_coord",   Defaults::Movement::MAX_VALID_COORD);
            printf("[GameConfig] movement applied (base_speed=%.0f, tolerance=%.1f)\n",
                   movement.base_speed, movement.tolerance);
        }

        version = config->GetVersion();
        reload_count++;
        printf("[GameConfig] Applied (version=%u, reload_count=%u)\n", version, reload_count);
    }
};
