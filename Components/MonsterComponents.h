#pragma once

#include <cstdint>
#include <cstring>
#include "../Core/Entity.h"
#include "StatsComponents.h"

// ━━━ Session 14: Monster/NPC System Components ━━━
// ━━━ Session 36: Enhanced Monster AI + Aggro Table ━━━
//
// MonsterComponent: "이 Entity는 몬스터다"
// 몬스터는 SessionComponent가 없음 (네트워크 클라이언트가 아님)
// InterestSystem/BroadcastSystem에서 자동 처리되지 않으므로,
// 몬스터 가시성은 수동으로 관리 (SendZoneMonsters, BroadcastMonsterRespawn)

// Session 36: 6상태 FSM
enum class MonsterState : uint8_t {
    IDLE    = 0,  // 대기: 주변 플레이어 탐색, 주기적 순찰 전환
    PATROL  = 1,  // 순찰: 스폰 주변 랜덤 이동
    CHASE   = 2,  // 추적: 어그로 타겟에게 이동
    ATTACK  = 3,  // 공격: 타겟 공격 중 (사거리 내)
    RETURN  = 4,  // 귀환: 스폰으로 복귀 + HP 회복
    DEAD    = 5,  // 사망: 리스폰 대기
};

// Session 36: 몬스터 AI 상수
namespace MonsterAI {
    constexpr float MOVE_SPEED              = 80.0f;    // 기본 이동속도 (units/sec)
    constexpr float PATROL_RADIUS           = 100.0f;   // 순찰 반경 (스폰 기준)
    constexpr float PATROL_MIN_WAIT         = 2.0f;     // 최소 순찰 대기시간 (초)
    constexpr float PATROL_MAX_WAIT         = 5.0f;     // 최대 순찰 대기시간 (초)
    constexpr float LEASH_RANGE             = 500.0f;   // 귀환 트리거 거리 (스폰 기준)
    constexpr float CHASE_SPEED_MULT        = 1.3f;     // 추적 시 속도 배율
    constexpr float RETURN_HEAL_RATE        = 0.1f;     // 귀환 중 HP 회복 (초당 max_hp의 10%)
    constexpr float MOVE_BROADCAST_INTERVAL = 0.2f;     // 이동 위치 브로드캐스트 간격 (초)
    constexpr float ARRIVAL_THRESHOLD       = 10.0f;    // 목적지 도착 판정 거리
}

// Session 36: 어그로 엔트리
struct AggroEntry {
    Entity entity = 0;
    float threat = 0.0f;
};

constexpr int MAX_AGGRO_ENTRIES = 8;

struct MonsterComponent {
    uint32_t monster_id;          // 템플릿 ID (1=고블린, 2=늑대, 3=오크, 4=곰)
    char name[32];
    MonsterState state = MonsterState::IDLE;

    // 스폰 포인트 (사망 시 이 위치에서 리스폰)
    float spawn_x = 0, spawn_y = 0, spawn_z = 0;

    // AI 파라미터
    float aggro_range = 150.0f;   // 어그로 감지 범위

    // 사망/리스폰
    float death_timer = 0.0f;     // 리스폰까지 남은 시간
    float respawn_time = 5.0f;    // 리스폰 시간 (초)

    // 어그로 타겟 (Session 36: aggro_table의 최상위 타겟과 동기화)
    Entity target_entity = 0;     // 현재 타겟 (0 = 없음)

    // 루트 테이블 (LootComponents.h의 LOOT_TABLES 참조)
    int32_t loot_table_id = 0;    // 0 = 드롭 없음

    // ━━━ Session 36: 확장 AI 필드 ━━━

    // 순찰
    float patrol_timer = 0.0f;        // IDLE에서 PATROL까지 남은 시간
    float patrol_target_x = 0.0f;     // 순찰 목표 좌표
    float patrol_target_y = 0.0f;

    // 이동 브로드캐스트
    float move_broadcast_timer = 0.0f;

    // 이동속도
    float move_speed = MonsterAI::MOVE_SPEED;

    // 어그로 테이블
    AggroEntry aggro_table[MAX_AGGRO_ENTRIES] = {};
    int aggro_count = 0;

    // ━━━ 어그로 테이블 조작 ━━━

    void AddThreat(Entity e, float amount) {
        for (int i = 0; i < aggro_count; i++) {
            if (aggro_table[i].entity == e) {
                aggro_table[i].threat += amount;
                return;
            }
        }
        if (aggro_count < MAX_AGGRO_ENTRIES) {
            aggro_table[aggro_count].entity = e;
            aggro_table[aggro_count].threat = amount;
            aggro_count++;
        } else {
            int min_idx = 0;
            for (int i = 1; i < MAX_AGGRO_ENTRIES; i++) {
                if (aggro_table[i].threat < aggro_table[min_idx].threat) min_idx = i;
            }
            if (amount > aggro_table[min_idx].threat) {
                aggro_table[min_idx].entity = e;
                aggro_table[min_idx].threat = amount;
            }
        }
    }

    Entity GetTopThreat() const {
        Entity top = 0;
        float max_threat = 0.0f;
        for (int i = 0; i < aggro_count; i++) {
            if (aggro_table[i].threat > max_threat) {
                max_threat = aggro_table[i].threat;
                top = aggro_table[i].entity;
            }
        }
        return top;
    }

    void RemoveThreat(Entity e) {
        for (int i = 0; i < aggro_count; i++) {
            if (aggro_table[i].entity == e) {
                aggro_table[i] = aggro_table[aggro_count - 1];
                aggro_table[aggro_count - 1] = {};
                aggro_count--;
                return;
            }
        }
    }

    void ClearAggro() {
        for (int i = 0; i < MAX_AGGRO_ENTRIES; i++) {
            aggro_table[i] = {};
        }
        aggro_count = 0;
    }

    float GetThreat(Entity e) const {
        for (int i = 0; i < aggro_count; i++) {
            if (aggro_table[i].entity == e) return aggro_table[i].threat;
        }
        return 0.0f;
    }
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
    int32_t loot_table_id;       // LootComponents.h 테이블 ID (0 = 드롭 없음)
};

// 하드코딩 스폰 테이블 (향후 CSV/DB로 대체 가능)
inline const MonsterSpawnEntry MONSTER_SPAWNS[] = {
    // Zone 1: 고블린 3마리 (Lv5, HP=100, ATK=15, DEF=5)
    {1, "Goblin",  5, 100, 15, 5,  1, 150.0f, 150.0f, 0.0f, 150.0f, 5.0f, 1},
    {1, "Goblin",  5, 100, 15, 5,  1, 250.0f, 250.0f, 0.0f, 150.0f, 5.0f, 1},
    {1, "Goblin",  5, 100, 15, 5,  1, 350.0f, 150.0f, 0.0f, 150.0f, 5.0f, 1},
    // Zone 1: 늑대 2마리 (Lv10, HP=200, ATK=25, DEF=10)
    {2, "Wolf",   10, 200, 25, 10, 1, 400.0f, 300.0f, 0.0f, 200.0f, 8.0f, 1},
    {2, "Wolf",   10, 200, 25, 10, 1, 300.0f, 400.0f, 0.0f, 200.0f, 8.0f, 1},
    // Zone 2: 오크 2마리 (Lv15, HP=300, ATK=35, DEF=15)
    {3, "Orc",    15, 300, 35, 15, 2, 520.0f, 480.0f, 0.0f, 200.0f, 8.0f, 2},
    {3, "Orc",    15, 300, 35, 15, 2, 580.0f, 520.0f, 0.0f, 200.0f, 8.0f, 2},
    // Zone 2: 곰 2마리 (Lv20, HP=400, ATK=45, DEF=20)
    {4, "Bear",   20, 400, 45, 20, 2, 450.0f, 550.0f, 0.0f, 250.0f, 10.0f, 2},
    {4, "Bear",   20, 400, 45, 20, 2, 550.0f, 450.0f, 0.0f, 250.0f, 10.0f, 2},
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
