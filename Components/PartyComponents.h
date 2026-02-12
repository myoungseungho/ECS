#pragma once

#include <cstdint>
#include <vector>
#include <unordered_map>
#include "../Core/Entity.h"

// ━━━ Session 20: Party System Components ━━━

constexpr int MAX_PARTY_MEMBERS = 4;

struct PartyData {
    uint32_t party_id;
    Entity leader;
    std::vector<Entity> members;   // leader 포함

    bool IsFull() const { return static_cast<int>(members.size()) >= MAX_PARTY_MEMBERS; }
    bool IsMember(Entity e) const {
        for (auto m : members) if (m == e) return true;
        return false;
    }
    bool IsLeader(Entity e) const { return leader == e; }

    void RemoveMember(Entity e) {
        for (auto it = members.begin(); it != members.end(); ++it) {
            if (*it == e) { members.erase(it); return; }
        }
    }
};

// 파티 컴포넌트: "이 Entity는 파티에 소속되어 있다"
struct PartyComponent {
    uint32_t party_id = 0;
};

// 파티 초대 대기
struct PartyInviteComponent {
    uint32_t party_id = 0;
    Entity inviter = 0;
};

// 전역 파티 관리자
inline uint32_t g_next_party_id = 1;
inline std::unordered_map<uint32_t, PartyData> g_parties;

inline PartyData* FindParty(uint32_t party_id) {
    auto it = g_parties.find(party_id);
    return (it != g_parties.end()) ? &it->second : nullptr;
}

inline uint32_t FindEntityParty(Entity e) {
    for (auto& [id, party] : g_parties) {
        if (party.IsMember(e)) return id;
    }
    return 0;
}

// 파티 결과
enum class PartyResult : uint8_t {
    SUCCESS         = 0,
    ALREADY_IN_PARTY = 1,
    PARTY_FULL      = 2,
    NOT_IN_PARTY    = 3,
    NOT_LEADER      = 4,
    TARGET_IN_PARTY = 5,
    PARTY_NOT_FOUND = 6,
    INVALID_TARGET  = 7,
};
