#pragma once

#include <cstdint>
#include <cstring>
#include "../Core/Entity.h"
#include "StatsComponents.h"

// ━━━ Session 14: Monster/NPC System Components ━━━
//
// MonsterComponent: "이 Entity는 몬스터다"
// 몬스터는 SessionComponent가 없음 (네트워크 클라이언트가 아님)
// InterestSystem/BroadcastSystem에서 자동 처리되지 않으므로,
// 몬스터 가시성은 수동으로 관리 (SendZoneMonsters, BroadcastMonsterRespawn)

enum class MonsterState : uint8_t {
    IDLE   = 0,  // 대기: 주변 플레이어 탐색
    ATTACK = 1,  // 공격: 타겟 공격 중
    DEAD   = 2,  // 사망: 리스폰 대기
};

struct MonsterComponent {
    uint32_t monster_id;          // 템플릿 ID (1=고블린, 2=늑대)
    char name[32];
    MonsterState state = MonsterState::IDLE;

    // 스폰 포인트 (사망 시 이 위치에서 리스폰)
    float spawn_x = 0, spawn_y = 0, spawn_z = 0;

    // AI 파라미터
    float aggro_range = 150.0f;   // 어그로 감지 범위

    // 사망/리스폰
    float death_timer = 0.0f;     // 리스폰까지 남은 시간
    float respawn_time = 5.0f;    // 리스폰 시간 (초)

    // 어그로 타겟
    Entity target_entity = 0;     // 현재 타겟 (0 = 없음)
};

// ━━━ 몬스터 스폰 테이블 ━━━

struct MonsterSpawnEntry {
    uint32_t monster_id;
    const char* name;
    int32_t level;
    int32_t hp, attack, defense;
    int32_t zone_id;
    float x, y, z;
    float aggro_range;
    float respawn_time;
};

// 하드코딩 스폰 테이블 (향후 CSV/DB로 대체 가능)
inline const MonsterSpawnEntry MONSTER_SPAWNS[] = {
    // Zone 1: 고블린 3마리 (Lv5, HP=100, ATK=15, DEF=5)
    {1, "Goblin",  5, 100, 15, 5,  1, 150.0f, 150.0f, 0.0f, 150.0f, 5.0f},
    {1, "Goblin",  5, 100, 15, 5,  1, 250.0f, 250.0f, 0.0f, 150.0f, 5.0f},
    {1, "Goblin",  5, 100, 15, 5,  1, 350.0f, 150.0f, 0.0f, 150.0f, 5.0f},
    // Zone 1: 늑대 2마리 (Lv10, HP=200, ATK=25, DEF=10)
    {2, "Wolf",   10, 200, 25, 10, 1, 400.0f, 300.0f, 0.0f, 200.0f, 8.0f},
    {2, "Wolf",   10, 200, 25, 10, 1, 300.0f, 400.0f, 0.0f, 200.0f, 8.0f},
};
constexpr int MONSTER_SPAWN_COUNT = sizeof(MONSTER_SPAWNS) / sizeof(MONSTER_SPAWNS[0]);

// ━━━ 몬스터 스탯 생성 헬퍼 ━━━
// 플레이어의 CreateStats(job, level)과 달리, 몬스터는 직접 스탯을 지정
inline StatsComponent CreateMonsterStats(int32_t level, int32_t hp, int32_t atk, int32_t def) {
    StatsComponent stats;
    stats.job = JobClass::WARRIOR;
    stats.level = level;
    stats.max_hp = hp;
    stats.hp = hp;
    stats.max_mp = 0;
    stats.mp = 0;
    stats.attack = atk;
    stats.defense = def;
    stats.exp_to_next = 999999;   // 몬스터는 레벨업 안 함
    stats.hp_regen_rate = 0;      // 자연회복 없음
    stats.mp_regen_rate = 0;
    stats.stats_dirty = false;
    return stats;
}
