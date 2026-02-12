#pragma once

// ━━━ Session 27: Loot/Drop Table System ━━━
//
// 가중치 기반 확률 드롭 테이블.
// 몬스터 처치, 퀘스트 보상, 상자 열기 등에 사용.
//
// 드롭 테이블 구조:
//   각 엔트리 = { item_id, min_count, max_count, weight }
//   weight 합계 기준 확률. weight=0이면 보장 드롭.
//
// 예: 고블린 드롭 테이블
//   { HP포션, 1, 2, 50 }   → 50%
//   { 가죽,   1, 1, 30 }   → 30%
//   { 없음,   0, 0, 20 }   → 20% (꽝)

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <vector>

// 드롭 엔트리
struct DropEntry {
    int32_t item_id;       // 0 = 드롭 없음 (꽝)
    int16_t min_count;
    int16_t max_count;
    int32_t weight;        // 가중치 (0 = 보장 드롭, 항상 포함)
};

// 드롭 테이블 템플릿
struct LootTable {
    int32_t table_id;
    char name[24];
    int roll_count;              // 롤 횟수 (몇 번 굴리는지)
    DropEntry entries[8];        // 최대 8개 엔트리
    int entry_count;
};

// 드롭 결과
struct LootResult {
    int32_t item_id;
    int16_t count;
};

// 전역 드롭 테이블
constexpr int LOOT_TABLE_COUNT = 4;
inline const LootTable LOOT_TABLES[LOOT_TABLE_COUNT] = {
    // 테이블 1: 기본 몬스터 (1회 롤)
    {1, "BasicMonster", 1,
     {{1, 1, 2, 50}, {2, 1, 1, 30}, {0, 0, 0, 20}},
     3},

    // 테이블 2: 엘리트 몬스터 (2회 롤)
    {2, "EliteMonster", 2,
     {{1, 2, 5, 40}, {10, 1, 1, 20}, {20, 1, 1, 15}, {3, 1, 3, 15}, {0, 0, 0, 10}},
     5},

    // 테이블 3: 보스 (3회 롤 + 보장 드롭)
    {3, "BossMonster", 3,
     {{11, 1, 1, 0}, {21, 1, 1, 30}, {3, 3, 5, 40}, {1, 5, 10, 30}},
     4},

    // 테이블 4: 보물 상자 (1회 롤)
    {4, "TreasureChest", 1,
     {{10, 1, 1, 25}, {11, 1, 1, 15}, {20, 1, 1, 25}, {21, 1, 1, 15}, {3, 2, 5, 20}},
     5},
};

inline const LootTable* FindLootTable(int32_t table_id) {
    for (int i = 0; i < LOOT_TABLE_COUNT; i++) {
        if (LOOT_TABLES[i].table_id == table_id) return &LOOT_TABLES[i];
    }
    return nullptr;
}

// 드롭 롤 실행
inline std::vector<LootResult> RollLoot(const LootTable& table) {
    std::vector<LootResult> results;

    // 보장 드롭 (weight == 0) 먼저 추가
    for (int i = 0; i < table.entry_count; i++) {
        auto& e = table.entries[i];
        if (e.weight == 0 && e.item_id > 0) {
            int16_t cnt = e.min_count;
            if (e.max_count > e.min_count) {
                cnt += static_cast<int16_t>(rand() % (e.max_count - e.min_count + 1));
            }
            results.push_back({e.item_id, cnt});
        }
    }

    // 가중치 롤
    // 가중치 합계 계산 (weight > 0인 것만)
    int total_weight = 0;
    for (int i = 0; i < table.entry_count; i++) {
        if (table.entries[i].weight > 0) total_weight += table.entries[i].weight;
    }

    if (total_weight <= 0) return results;

    for (int r = 0; r < table.roll_count; r++) {
        int roll = rand() % total_weight;
        int cumulative = 0;

        for (int i = 0; i < table.entry_count; i++) {
            auto& e = table.entries[i];
            if (e.weight <= 0) continue;

            cumulative += e.weight;
            if (roll < cumulative) {
                if (e.item_id > 0) {
                    int16_t cnt = e.min_count;
                    if (e.max_count > e.min_count) {
                        cnt += static_cast<int16_t>(rand() % (e.max_count - e.min_count + 1));
                    }
                    results.push_back({e.item_id, cnt});
                }
                // item_id == 0 이면 꽝 (아무것도 추가 안 함)
                break;
            }
        }
    }

    return results;
}
