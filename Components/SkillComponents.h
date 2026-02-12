#pragma once

#include <cstdint>
#include <cstring>
#include <unordered_map>

// ━━━ Session 19: Skill System Components ━━━

// 스킬 정의 (데이터 테이블)
struct SkillData {
    int32_t skill_id;
    char name[16];
    int32_t cooldown_ms;        // 쿨다운 (밀리초)
    int32_t damage_multiplier;  // 데미지 배율 (100 = 1.0x)
    int32_t mp_cost;
    float range;
    uint8_t job_class;          // 0=공용, 1=전사, 2=궁수, 3=마법사
};

// 전역 스킬 테이블
constexpr int SKILL_TABLE_SIZE = 8;
inline const SkillData SKILL_TABLE[SKILL_TABLE_SIZE] = {
    // 공용 스킬
    {1, "BasicAttack",  1000, 100, 0,   200.0f, 0},   // 기본 공격
    {2, "Heal",         5000, 0,   30,  0.0f,   0},    // 자힐 (대상: 자기)
    // 전사
    {10, "Slash",       2000, 200, 10,  200.0f, 1},    // 베기
    {11, "PowerStrike", 5000, 350, 25,  200.0f, 1},    // 강타
    // 궁수
    {20, "ArrowShot",   1500, 180, 8,   500.0f, 2},    // 화살
    {21, "MultiShot",   4000, 250, 20,  400.0f, 2},    // 다중 사격
    // 마법사
    {30, "Fireball",    2500, 280, 15,  450.0f, 3},    // 파이어볼
    {31, "IceBolt",     3500, 320, 22,  400.0f, 3},    // 아이스볼트
};

inline const SkillData* FindSkill(int32_t skill_id) {
    for (int i = 0; i < SKILL_TABLE_SIZE; i++) {
        if (SKILL_TABLE[i].skill_id == skill_id) return &SKILL_TABLE[i];
    }
    return nullptr;
}

// 스킬 쿨다운 상태
struct SkillCooldown {
    int32_t skill_id;
    float remaining;  // 남은 쿨다운 (초)
};

// 스킬 컴포넌트: "이 Entity는 스킬을 사용할 수 있다"
struct SkillComponent {
    SkillCooldown cooldowns[16];  // 최대 16개 스킬 쿨다운 추적
    int cooldown_count = 0;

    float GetCooldown(int32_t skill_id) const {
        for (int i = 0; i < cooldown_count; i++) {
            if (cooldowns[i].skill_id == skill_id) return cooldowns[i].remaining;
        }
        return 0.0f;
    }

    void SetCooldown(int32_t skill_id, float seconds) {
        for (int i = 0; i < cooldown_count; i++) {
            if (cooldowns[i].skill_id == skill_id) {
                cooldowns[i].remaining = seconds;
                return;
            }
        }
        if (cooldown_count < 16) {
            cooldowns[cooldown_count++] = {skill_id, seconds};
        }
    }

    void TickCooldowns(float dt) {
        for (int i = 0; i < cooldown_count; i++) {
            if (cooldowns[i].remaining > 0) {
                cooldowns[i].remaining -= dt;
                if (cooldowns[i].remaining < 0) cooldowns[i].remaining = 0;
            }
        }
    }
};

// 스킬 사용 결과
enum class SkillResult : uint8_t {
    SUCCESS         = 0,
    SKILL_NOT_FOUND = 1,
    COOLDOWN        = 2,
    NO_MP           = 3,
    OUT_OF_RANGE    = 4,
    TARGET_DEAD     = 5,
    CASTER_DEAD     = 6,
    INVALID_TARGET  = 7,
};
