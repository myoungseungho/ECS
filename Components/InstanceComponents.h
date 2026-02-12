#pragma once

#include <cstdint>
#include <vector>
#include <unordered_map>
#include "../Core/Entity.h"

// ━━━ Session 21: Instance Dungeon Components ━━━

// 던전 타입 정의
struct DungeonTemplate {
    int32_t dungeon_type;
    char name[32];
    int32_t min_level;
    int32_t max_players;
    int32_t monster_count;
    int32_t monster_level;
    int32_t monster_hp;
};

constexpr int DUNGEON_TEMPLATE_COUNT = 3;
inline const DungeonTemplate DUNGEON_TEMPLATES[DUNGEON_TEMPLATE_COUNT] = {
    {1, "GoblinCave",   1,  4, 3, 5,  200},
    {2, "WolfDen",      10, 4, 4, 15, 500},
    {3, "DragonLair",   30, 4, 2, 40, 2000},
};

inline const DungeonTemplate* FindDungeonTemplate(int32_t type) {
    for (int i = 0; i < DUNGEON_TEMPLATE_COUNT; i++) {
        if (DUNGEON_TEMPLATES[i].dungeon_type == type) return &DUNGEON_TEMPLATES[i];
    }
    return nullptr;
}

// 인스턴스 데이터
struct InstanceData {
    uint32_t instance_id;
    int32_t dungeon_type;
    std::vector<Entity> players;
    std::vector<Entity> monsters;  // 인스턴스 내 몬스터 Entity
    bool active = true;

    bool HasPlayer(Entity e) const {
        for (auto p : players) if (p == e) return true;
        return false;
    }
    void RemovePlayer(Entity e) {
        for (auto it = players.begin(); it != players.end(); ++it) {
            if (*it == e) { players.erase(it); return; }
        }
    }
};

// 인스턴스 컴포넌트: "이 Entity는 인스턴스 던전 안에 있다"
struct InstanceComponent {
    uint32_t instance_id = 0;
    int32_t previous_zone = 0;   // 나갈 때 돌아갈 존
    float previous_x = 0, previous_y = 0, previous_z = 0;
};

// 인스턴스 몬스터 표시
struct InstanceMonsterComponent {
    uint32_t instance_id = 0;
};

// 전역 인스턴스 관리
inline uint32_t g_next_instance_id = 1;
inline std::unordered_map<uint32_t, InstanceData> g_instances;

inline InstanceData* FindInstance(uint32_t id) {
    auto it = g_instances.find(id);
    return (it != g_instances.end()) ? &it->second : nullptr;
}

enum class InstanceResult : uint8_t {
    SUCCESS             = 0,
    DUNGEON_NOT_FOUND   = 1,
    LEVEL_TOO_LOW       = 2,
    ALREADY_IN_INSTANCE = 3,
    NOT_IN_INSTANCE     = 4,
    INSTANCE_FULL       = 5,
};
