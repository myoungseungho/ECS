#pragma once

// ━━━ Session 28: Quest System Components ━━━
//
// 퀘스트 상태 머신 + 목표(Kill/Collect/Move) + 선행 조건 + 보상
//
// 상태 전이: NONE → ACCEPTED → IN_PROGRESS → COMPLETE → REWARDED
//   - ACCEPTED: 퀘스트 수락 직후 (목표 진행 0)
//   - IN_PROGRESS: 목표 진행 중 (progress > 0, < target)
//   - COMPLETE: 목표 달성 (progress >= target)
//   - REWARDED: 보상 수령 완료

#include <cstdint>
#include <cstring>

// 퀘스트 상태
enum class QuestState : uint8_t {
    NONE        = 0,  // 미수락
    ACCEPTED    = 1,  // 수락됨
    IN_PROGRESS = 2,  // 진행 중
    COMPLETE    = 3,  // 목표 달성
    REWARDED    = 4,  // 보상 완료
};

// 퀘스트 목표 타입
enum class ObjectiveType : uint8_t {
    KILL        = 1,  // 몬스터 처치 (param = monster_id, 0이면 아무 몬스터)
    COLLECT     = 2,  // 아이템 수집 (param = item_id)
    REACH_ZONE  = 3,  // 특정 존 도달 (param = zone_id)
};

// 퀘스트 보상
struct QuestReward {
    int32_t exp = 0;
    int32_t item_id = 0;
    int16_t item_count = 0;
    int32_t buff_id = 0;
};

// 퀘스트 템플릿 (데이터 테이블)
struct QuestTemplate {
    int32_t quest_id;
    char name[32];

    // 목표
    ObjectiveType objective_type;
    int32_t objective_param;   // monster_id, item_id, zone_id
    int32_t objective_target;  // 목표 수량

    // 선행 조건 (다른 퀘스트 완료 필요, 0이면 없음)
    int32_t prerequisite_quest_id;

    // 레벨 조건
    int32_t min_level;

    // 보상
    QuestReward reward;
};

constexpr int QUEST_TEMPLATE_COUNT = 5;
inline const QuestTemplate QUEST_TEMPLATES[QUEST_TEMPLATE_COUNT] = {
    // 퀘스트 1: 초보자 사냥 (아무 몬스터 3마리)
    {1, "Beginner Hunt",
     ObjectiveType::KILL, 0, 3,
     0, 1,
     {100, 1, 3, 0}},  // 100 EXP, HP포션 x3

    // 퀘스트 2: 특정 몬스터 처치 (monster_id=1 를 2마리)
    {2, "Goblin Slayer",
     ObjectiveType::KILL, 1, 2,
     0, 5,
     {200, 10, 1, 0}},  // 200 EXP, Iron Sword x1

    // 퀘스트 3: 아이템 수집 (HP포션 3개)
    {3, "Potion Collector",
     ObjectiveType::COLLECT, 1, 3,
     0, 1,
     {50, 2, 5, 0}},   // 50 EXP, MP포션 x5

    // 퀘스트 4: 특정 존 도달 (zone 2)
    {4, "Explorer",
     ObjectiveType::REACH_ZONE, 2, 1,
     0, 1,
     {150, 0, 0, 1}},  // 150 EXP, Strength 버프

    // 퀘스트 5: 연쇄 퀘스트 (퀘스트 1 완료 후)
    {5, "Advanced Hunt",
     ObjectiveType::KILL, 0, 5,
     1, 5,
     {500, 11, 1, 0}},  // 500 EXP, Steel Sword x1
};

inline const QuestTemplate* FindQuestTemplate(int32_t quest_id) {
    for (int i = 0; i < QUEST_TEMPLATE_COUNT; i++) {
        if (QUEST_TEMPLATES[i].quest_id == quest_id) return &QUEST_TEMPLATES[i];
    }
    return nullptr;
}

// 활성 퀘스트 인스턴스
struct ActiveQuest {
    int32_t quest_id = 0;
    QuestState state = QuestState::NONE;
    int32_t progress = 0;       // 현재 진행도
    int32_t target = 0;         // 목표치
    ObjectiveType obj_type = ObjectiveType::KILL;
    int32_t obj_param = 0;

    bool IsActive() const { return quest_id > 0 && state != QuestState::NONE; }
};

constexpr int MAX_ACTIVE_QUESTS = 8;

// 퀘스트 컴포넌트
struct QuestComponent {
    ActiveQuest quests[MAX_ACTIVE_QUESTS];

    // 빈 슬롯 찾기
    int FindEmptySlot() const {
        for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
            if (!quests[i].IsActive()) return i;
        }
        return -1;
    }

    // quest_id로 찾기
    int FindQuest(int32_t quest_id) const {
        for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
            if (quests[i].quest_id == quest_id && quests[i].IsActive()) return i;
        }
        return -1;
    }

    // 퀘스트 상태 확인 (완료/보상 포함)
    QuestState GetQuestState(int32_t quest_id) const {
        for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
            if (quests[i].quest_id == quest_id) return quests[i].state;
        }
        return QuestState::NONE;
    }

    // 활성 퀘스트 수
    int ActiveCount() const {
        int c = 0;
        for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
            if (quests[i].IsActive()) c++;
        }
        return c;
    }

    // 퀘스트 수락
    int AcceptQuest(int32_t quest_id) {
        auto* tmpl = FindQuestTemplate(quest_id);
        if (!tmpl) return -1;

        // 이미 수락했는지
        if (FindQuest(quest_id) >= 0) return -2;

        int slot = FindEmptySlot();
        if (slot < 0) return -3;

        auto& q = quests[slot];
        q.quest_id = quest_id;
        q.state = QuestState::ACCEPTED;
        q.progress = 0;
        q.target = tmpl->objective_target;
        q.obj_type = tmpl->objective_type;
        q.obj_param = tmpl->objective_param;
        return slot;
    }

    // Kill 목표 진행 (몬스터 처치 시 호출)
    void OnMonsterKilled(int32_t monster_id) {
        for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
            auto& q = quests[i];
            if (!q.IsActive()) continue;
            if (q.state != QuestState::ACCEPTED && q.state != QuestState::IN_PROGRESS) continue;
            if (q.obj_type != ObjectiveType::KILL) continue;

            // param == 0 이면 아무 몬스터, 아니면 특정 monster_id
            if (q.obj_param == 0 || q.obj_param == monster_id) {
                q.progress++;
                q.state = QuestState::IN_PROGRESS;
                if (q.progress >= q.target) {
                    q.state = QuestState::COMPLETE;
                }
            }
        }
    }

    // Collect 목표 체크 (아이템 보유량 확인)
    void CheckCollectObjectives(const struct InventoryComponent& inv);

    // Reach Zone 체크
    void CheckZoneObjectives(int32_t current_zone) {
        for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
            auto& q = quests[i];
            if (!q.IsActive()) continue;
            if (q.state != QuestState::ACCEPTED && q.state != QuestState::IN_PROGRESS) continue;
            if (q.obj_type != ObjectiveType::REACH_ZONE) continue;

            if (q.obj_param == current_zone) {
                q.progress = q.target;
                q.state = QuestState::COMPLETE;
            }
        }
    }
};

// Collect 목표 체크 구현 (InventoryComponent 의존)
#include "InventoryComponents.h"
inline void QuestComponent::CheckCollectObjectives(const InventoryComponent& inv) {
    for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
        auto& q = quests[i];
        if (!q.IsActive()) continue;
        if (q.state != QuestState::ACCEPTED && q.state != QuestState::IN_PROGRESS) continue;
        if (q.obj_type != ObjectiveType::COLLECT) continue;

        int total = 0;
        for (int s = 0; s < MAX_INVENTORY_SLOTS; s++) {
            if (inv.slots[s].item_id == q.obj_param) {
                total += inv.slots[s].count;
            }
        }
        q.progress = total;
        if (q.progress >= q.target) {
            q.state = QuestState::COMPLETE;
        } else if (q.progress > 0) {
            q.state = QuestState::IN_PROGRESS;
        }
    }
}

// 퀘스트 결과 코드
enum class QuestResult : uint8_t {
    SUCCESS              = 0,
    QUEST_NOT_FOUND      = 1,
    ALREADY_ACCEPTED     = 2,
    QUEST_FULL           = 3,
    PREREQUISITE_NOT_MET = 4,
    LEVEL_TOO_LOW        = 5,
    NOT_COMPLETE         = 6,
    NOT_ACCEPTED         = 7,
    ALREADY_REWARDED     = 8,
};
