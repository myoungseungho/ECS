#pragma once

#include <cstdint>
#include <vector>
#include <deque>
#include "../Core/Entity.h"

// ━━━ Session 22: Matching Queue Components ━━━

// 매칭 큐 엔트리
struct MatchQueueEntry {
    Entity entity;
    int32_t dungeon_type;
    int32_t level;
    float wait_time;      // 대기 시간 (초)
};

// 매칭 결과 데이터
struct MatchResultData {
    uint32_t match_id;
    int32_t dungeon_type;
    std::vector<Entity> players;
    bool all_accepted = false;
    int accept_count = 0;
    float timeout = 15.0f;  // 수락 타임아웃 (초)
};

// 매칭 컴포넌트: "이 Entity는 매칭 큐에 있다"
struct MatchComponent {
    bool in_queue = false;
    int32_t dungeon_type = 0;
    uint32_t pending_match_id = 0;  // 매칭 발견 후 수락 대기 중
};

// 전역 매칭 시스템
inline std::deque<MatchQueueEntry> g_match_queue;
inline uint32_t g_next_match_id = 1;
inline std::unordered_map<uint32_t, MatchResultData> g_pending_matches;

// 큐에서 entity 제거
inline void RemoveFromMatchQueue(Entity e) {
    for (auto it = g_match_queue.begin(); it != g_match_queue.end(); ++it) {
        if (it->entity == e) { g_match_queue.erase(it); return; }
    }
}

// 큐에서 위치 조회
inline int GetQueuePosition(Entity e) {
    int pos = 1;
    for (auto& entry : g_match_queue) {
        if (entry.entity == e) return pos;
        pos++;
    }
    return 0;
}

enum class MatchResult : uint8_t {
    SUCCESS         = 0,
    ALREADY_IN_QUEUE = 1,
    NOT_IN_QUEUE    = 2,
    MATCH_NOT_FOUND = 3,
    ALREADY_ACCEPTED = 4,
    IN_INSTANCE     = 5,
};

// 매칭 상태
enum class MatchStatus : uint8_t {
    IDLE            = 0,
    IN_QUEUE        = 1,
    MATCH_FOUND     = 2,
    ENTERING        = 3,
};
