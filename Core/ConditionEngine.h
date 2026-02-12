#pragma once

// ━━━ Session 25: Condition Engine (복합 조건 평가기) ━━━
//
// AND/OR/NOT 조건 트리로 복합 게임 조건 평가.
// 퀘스트 선행조건, 스킬 사용 조건, 아이템 사용 조건 등에 활용.
//
// 예: "레벨 10 이상 AND (아이템 보유 OR 버프 보유)"
//   node[0] = AND, child_left=1, child_right=2
//   node[1] = LEVEL_GE(10)
//   node[2] = OR, child_left=3, child_right=4
//   node[3] = HAS_ITEM(item_id=1)
//   node[4] = HAS_BUFF(buff_id=1)
//
// 직렬화: [count(1)] [root(1)] [nodes: type(1) p1(4) p2(4) left(2) right(2) ...]
// 각 노드 = 13바이트

#include "Entity.h"
#include "World.h"
#include "../Components/StatsComponents.h"
#include "../Components/InventoryComponents.h"
#include "../Components/BuffComponents.h"
#include "../Components/ZoneComponents.h"
#include "../Components/PartyComponents.h"
#include "../Components/LoginComponents.h"

#include <cstdint>
#include <cstring>
#include <vector>

// 조건 타입
enum class ConditionType : uint8_t {
    ALWAYS_TRUE     = 0,   // 항상 참
    ALWAYS_FALSE    = 1,   // 항상 거짓

    // 논리 연산자 (자식 노드 필요)
    AND             = 10,  // child_left AND child_right
    OR              = 11,  // child_left OR child_right
    NOT             = 12,  // NOT child_left (child_right 무시)

    // 스탯 조건 (param1 = 비교값)
    LEVEL_GE        = 20,  // 레벨 >= param1
    LEVEL_LE        = 21,  // 레벨 <= param1
    HP_PERCENT_GE   = 22,  // HP% >= param1
    HP_PERCENT_LE   = 23,  // HP% <= param1

    // 아이템/버프 조건
    HAS_ITEM        = 30,  // 아이템 보유 (param1 = item_id, param2 = min_count, 0이면 1)
    HAS_BUFF        = 31,  // 버프 활성 (param1 = buff_id)

    // 위치/존
    IN_ZONE         = 40,  // 특정 존에 있는가 (param1 = zone_id)

    // 소셜
    HAS_PARTY       = 50,  // 파티 가입 상태인가
    PARTY_SIZE_GE   = 51,  // 파티 인원 >= param1

    // 직업
    CLASS_EQ        = 60,  // 직업 == param1

    // 퀘스트 (Session 28에서 활용)
    QUEST_STATE     = 70,  // 퀘스트 상태 (param1 = quest_id, param2 = required_state)
};

// 조건 노드 (트리의 각 노드)
struct ConditionNode {
    ConditionType type = ConditionType::ALWAYS_TRUE;
    int32_t param1 = 0;
    int32_t param2 = 0;
    int16_t child_left = -1;   // 자식 노드 인덱스 (-1 = 없음)
    int16_t child_right = -1;
};

constexpr int MAX_CONDITION_NODES = 16;
constexpr int CONDITION_NODE_SIZE = 13;  // 1 + 4 + 4 + 2 + 2 bytes

// 조건 트리 (플랫 배열)
struct ConditionTree {
    ConditionNode nodes[MAX_CONDITION_NODES];
    int count = 0;
    int root = 0;

    // 직렬화: 바이너리로 변환
    std::vector<char> Serialize() const {
        std::vector<char> buf;
        uint8_t cnt = static_cast<uint8_t>(count);
        uint8_t rt = static_cast<uint8_t>(root);
        buf.push_back(static_cast<char>(cnt));
        buf.push_back(static_cast<char>(rt));

        for (int i = 0; i < count; i++) {
            auto& n = nodes[i];
            buf.push_back(static_cast<char>(n.type));
            buf.insert(buf.end(), reinterpret_cast<const char*>(&n.param1),
                       reinterpret_cast<const char*>(&n.param1) + 4);
            buf.insert(buf.end(), reinterpret_cast<const char*>(&n.param2),
                       reinterpret_cast<const char*>(&n.param2) + 4);
            buf.insert(buf.end(), reinterpret_cast<const char*>(&n.child_left),
                       reinterpret_cast<const char*>(&n.child_left) + 2);
            buf.insert(buf.end(), reinterpret_cast<const char*>(&n.child_right),
                       reinterpret_cast<const char*>(&n.child_right) + 2);
        }
        return buf;
    }

    // 역직렬화: 바이너리 → 트리
    static ConditionTree Deserialize(const char* data, int len) {
        ConditionTree tree;
        if (len < 2) return tree;

        tree.count = static_cast<uint8_t>(data[0]);
        tree.root = static_cast<uint8_t>(data[1]);

        if (tree.count > MAX_CONDITION_NODES) tree.count = MAX_CONDITION_NODES;

        int offset = 2;
        for (int i = 0; i < tree.count && offset + CONDITION_NODE_SIZE <= len; i++) {
            auto& n = tree.nodes[i];
            n.type = static_cast<ConditionType>(static_cast<uint8_t>(data[offset]));
            offset++;
            std::memcpy(&n.param1, data + offset, 4); offset += 4;
            std::memcpy(&n.param2, data + offset, 4); offset += 4;
            std::memcpy(&n.child_left, data + offset, 2); offset += 2;
            std::memcpy(&n.child_right, data + offset, 2); offset += 2;
        }
        return tree;
    }
};

// ━━━ 조건 평가기 ━━━
// World와 Entity 상태를 기반으로 조건 트리를 평가

struct ConditionContext {
    World* world = nullptr;
    Entity entity = 0;
};

// 개별 노드 평가 (재귀)
inline bool EvaluateConditionNode(const ConditionTree& tree, int node_idx,
                                   const ConditionContext& ctx) {
    if (node_idx < 0 || node_idx >= tree.count) return false;
    const auto& node = tree.nodes[node_idx];

    switch (node.type) {
        case ConditionType::ALWAYS_TRUE:
            return true;
        case ConditionType::ALWAYS_FALSE:
            return false;

        // 논리 연산자
        case ConditionType::AND:
            return EvaluateConditionNode(tree, node.child_left, ctx) &&
                   EvaluateConditionNode(tree, node.child_right, ctx);
        case ConditionType::OR:
            return EvaluateConditionNode(tree, node.child_left, ctx) ||
                   EvaluateConditionNode(tree, node.child_right, ctx);
        case ConditionType::NOT:
            return !EvaluateConditionNode(tree, node.child_left, ctx);

        // 스탯 조건
        case ConditionType::LEVEL_GE: {
            if (!ctx.world->HasComponent<StatsComponent>(ctx.entity)) return false;
            return ctx.world->GetComponent<StatsComponent>(ctx.entity).level >= node.param1;
        }
        case ConditionType::LEVEL_LE: {
            if (!ctx.world->HasComponent<StatsComponent>(ctx.entity)) return false;
            return ctx.world->GetComponent<StatsComponent>(ctx.entity).level <= node.param1;
        }
        case ConditionType::HP_PERCENT_GE: {
            if (!ctx.world->HasComponent<StatsComponent>(ctx.entity)) return false;
            auto& s = ctx.world->GetComponent<StatsComponent>(ctx.entity);
            if (s.max_hp <= 0) return false;
            int pct = (s.hp * 100) / s.max_hp;
            return pct >= node.param1;
        }
        case ConditionType::HP_PERCENT_LE: {
            if (!ctx.world->HasComponent<StatsComponent>(ctx.entity)) return false;
            auto& s = ctx.world->GetComponent<StatsComponent>(ctx.entity);
            if (s.max_hp <= 0) return false;
            int pct = (s.hp * 100) / s.max_hp;
            return pct <= node.param1;
        }

        // 아이템/버프
        case ConditionType::HAS_ITEM: {
            if (!ctx.world->HasComponent<InventoryComponent>(ctx.entity)) return false;
            auto& inv = ctx.world->GetComponent<InventoryComponent>(ctx.entity);
            int min_count = (node.param2 > 0) ? node.param2 : 1;
            for (int i = 0; i < MAX_INVENTORY_SLOTS; i++) {
                if (inv.slots[i].item_id == node.param1 && inv.slots[i].count >= min_count)
                    return true;
            }
            return false;
        }
        case ConditionType::HAS_BUFF: {
            if (!ctx.world->HasComponent<BuffComponent>(ctx.entity)) return false;
            auto& bc = ctx.world->GetComponent<BuffComponent>(ctx.entity);
            for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
                if (bc.buffs[i].active && bc.buffs[i].buff_id == node.param1)
                    return true;
            }
            return false;
        }

        // 존
        case ConditionType::IN_ZONE: {
            if (!ctx.world->HasComponent<ZoneComponent>(ctx.entity)) return false;
            return ctx.world->GetComponent<ZoneComponent>(ctx.entity).zone_id == node.param1;
        }

        // 파티
        case ConditionType::HAS_PARTY: {
            return ctx.world->HasComponent<PartyComponent>(ctx.entity);
        }
        case ConditionType::PARTY_SIZE_GE: {
            // PartyComponent만으로는 파티 인원을 알 수 없음 → 같은 party_id를 가진 엔티티 수 세기
            if (!ctx.world->HasComponent<PartyComponent>(ctx.entity)) return false;
            int32_t pid = ctx.world->GetComponent<PartyComponent>(ctx.entity).party_id;
            int count = 0;
            ctx.world->ForEach<PartyComponent>([&](Entity e, PartyComponent& pc) {
                if (pc.party_id == pid) count++;
            });
            return count >= node.param1;
        }

        // 직업
        case ConditionType::CLASS_EQ: {
            if (!ctx.world->HasComponent<StatsComponent>(ctx.entity)) return false;
            return static_cast<int>(ctx.world->GetComponent<StatsComponent>(ctx.entity).job)
                   == node.param1;
        }

        // 퀘스트 상태 (Session 28에서 구현 - 여기서는 stub)
        case ConditionType::QUEST_STATE:
            // QuestComponent가 있으면 체크, 없으면 false
            return false;  // Session 28에서 구현

        default:
            return false;
    }
}

// 조건 트리 전체 평가 (루트 노드부터)
inline bool EvaluateCondition(const ConditionTree& tree, World& world, Entity entity) {
    if (tree.count <= 0) return true;  // 빈 트리 = 무조건 통과

    ConditionContext ctx;
    ctx.world = &world;
    ctx.entity = entity;
    return EvaluateConditionNode(tree, tree.root, ctx);
}
