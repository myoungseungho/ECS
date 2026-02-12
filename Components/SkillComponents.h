#pragma once

#include <cstdint>
#include <cstring>
#include <unordered_map>

// ━━━ Session 19+33: Skill System Components (확장) ━━━

// 스킬 효과 타입 (Session 33 추가)
enum class SkillEffect : uint8_t {
    DAMAGE       = 0,  // 단일 타겟 공격
    SELF_HEAL    = 1,  // 자힐
    SELF_BUFF    = 2,  // 자기 버프 (ATK/DEF 증가)
    AOE_DAMAGE   = 3,  // 범위 공격 (주변 적 모두)
    DOT_DAMAGE   = 4,  // 도트 데미지 (지속 피해)
};

// 스킬 정의 (데이터 테이블)
struct SkillData {
    int32_t skill_id;
    char name[16];
    int32_t cooldown_ms;        // 쿨다운 (밀리초)
    int32_t damage_multiplier;  // 데미지 배율 (100 = 1.0x)
    int32_t mp_cost;
    float range;
    uint8_t job_class;          // 0=공용, 1=전사, 2=궁수, 3=마법사
    SkillEffect effect;         // 스킬 효과 타입 (Session 33)
    int32_t effect_value;       // 효과 부가값 (버프량, DoT 틱수 등)
    int32_t min_level;          // 습득 가능 최소 레벨 (Session 33)
};

// 전역 스킬 테이블 (Session 33: 8→21개 확장)
constexpr int SKILL_TABLE_SIZE = 21;
inline const SkillData SKILL_TABLE[SKILL_TABLE_SIZE] = {
    // ━━━ 공용 스킬 (job_class=0) ━━━
    {1,  "BasicAttack",  1000, 100, 0,   200.0f, 0, SkillEffect::DAMAGE,     0,  1},  // 기본 공격
    {2,  "Heal",         5000, 0,   30,  0.0f,   0, SkillEffect::SELF_HEAL,  50, 1},  // 자힐 (+50 base)
    {3,  "Dash",         3000, 150, 5,   150.0f, 0, SkillEffect::DAMAGE,     0,  5},  // 대시 공격
    {4,  "Provoke",      8000, 50,  10,  300.0f, 0, SkillEffect::DAMAGE,     0,  10}, // 도발 (약한 데미지)

    // ━━━ 전사 스킬 (job_class=1) ━━━
    {10, "Slash",        2000, 200, 10,  200.0f, 1, SkillEffect::DAMAGE,     0,  1},  // 베기
    {11, "PowerStrike",  5000, 350, 25,  200.0f, 1, SkillEffect::DAMAGE,     0,  10}, // 강타
    {12, "ShieldBash",   4000, 180, 15,  150.0f, 1, SkillEffect::DAMAGE,     0,  5},  // 방패 강타
    {13, "Whirlwind",    6000, 250, 30,  250.0f, 1, SkillEffect::AOE_DAMAGE, 0,  15}, // 회전 베기 (AoE)
    {14, "Warcry",       15000, 0,  20,  0.0f,   1, SkillEffect::SELF_BUFF,  20, 20}, // 함성 (ATK+20%)

    // ━━━ 궁수 스킬 (job_class=2) ━━━
    {20, "ArrowShot",    1500, 180, 8,   500.0f, 2, SkillEffect::DAMAGE,     0,  1},  // 화살
    {21, "MultiShot",    4000, 250, 20,  400.0f, 2, SkillEffect::AOE_DAMAGE, 0,  10}, // 다중 사격 (AoE)
    {22, "PoisonArrow",  5000, 120, 18,  500.0f, 2, SkillEffect::DOT_DAMAGE, 3,  5},  // 독화살 (3틱 DoT)
    {23, "RainOfArrows", 8000, 300, 35,  450.0f, 2, SkillEffect::AOE_DAMAGE, 0,  15}, // 화살 비 (AoE)
    {24, "Snipe",        10000,500, 40,  800.0f, 2, SkillEffect::DAMAGE,     0,  20}, // 저격 (원거리 고데미지)

    // ━━━ 마법사 스킬 (job_class=3) ━━━
    {30, "Fireball",     2500, 280, 15,  450.0f, 3, SkillEffect::DAMAGE,     0,  1},  // 파이어볼
    {31, "IceBolt",      3500, 320, 22,  400.0f, 3, SkillEffect::DAMAGE,     0,  5},  // 아이스볼트
    {32, "Thunder",      4000, 400, 30,  500.0f, 3, SkillEffect::DAMAGE,     0,  10}, // 선더 (고데미지)
    {33, "Blizzard",     8000, 350, 45,  400.0f, 3, SkillEffect::AOE_DAMAGE, 0,  15}, // 블리자드 (AoE)
    {34, "ManaShield",   20000, 0,  50,  0.0f,   3, SkillEffect::SELF_BUFF,  30, 20}, // 마나실드 (DEF+30%)
    {35, "Meteor",       12000,600, 60,  500.0f, 3, SkillEffect::AOE_DAMAGE, 0,  25}, // 메테오 (궁극기)
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
    SkillCooldown cooldowns[24];  // 최대 24개 스킬 쿨다운 추적 (확장: 16→24)
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
        if (cooldown_count < 24) {
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

// ━━━ Session 33: 스킬 레벨 시스템 ━━━

// 개별 스킬 레벨 정보
struct SkillLevelEntry {
    int32_t skill_id;
    uint8_t level;  // 1~5
};

// 스킬 레벨 컴포넌트: "이 Entity의 스킬 레벨 정보"
constexpr int MAX_LEARNED_SKILLS = 12;
struct SkillLevelComponent {
    SkillLevelEntry skills[MAX_LEARNED_SKILLS];
    int skill_count = 0;
    int32_t skill_points = 0;     // 사용 가능한 스킬 포인트
    int32_t total_spent = 0;      // 총 사용한 포인트

    uint8_t GetSkillLevel(int32_t skill_id) const {
        for (int i = 0; i < skill_count; i++) {
            if (skills[i].skill_id == skill_id) return skills[i].level;
        }
        return 0;  // 미습득
    }

    bool LearnOrUpgrade(int32_t skill_id) {
        // 이미 배운 스킬이면 레벨업
        for (int i = 0; i < skill_count; i++) {
            if (skills[i].skill_id == skill_id) {
                if (skills[i].level >= 5) return false;  // 만렙
                if (skill_points <= 0) return false;
                skills[i].level++;
                skill_points--;
                total_spent++;
                return true;
            }
        }
        // 새로 배우기
        if (skill_count >= MAX_LEARNED_SKILLS) return false;
        if (skill_points <= 0) return false;
        skills[skill_count++] = {skill_id, 1};
        skill_points--;
        total_spent++;
        return true;
    }

    void AddSkillPoints(int32_t amount) {
        skill_points += amount;
    }
};

// 스킬 레벨별 스케일링 (레벨 1~5)
constexpr float SKILL_LEVEL_DMG_SCALE[6]  = {0.0f, 1.0f, 1.2f, 1.4f, 1.6f, 2.0f};
constexpr float SKILL_LEVEL_MP_SCALE[6]   = {0.0f, 1.0f, 0.9f, 0.85f, 0.8f, 0.75f};
constexpr float SKILL_LEVEL_CD_SCALE[6]   = {0.0f, 1.0f, 1.0f, 0.95f, 0.9f, 0.85f};

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
    LEVEL_TOO_LOW   = 8,   // Session 33: 캐릭터 레벨 부족
    NO_SKILL_POINTS = 9,   // Session 33: 스킬 포인트 부족
    SKILL_MAX_LEVEL = 10,  // Session 33: 이미 만렙
};

// 스킬 레벨업 결과
enum class SkillLevelUpResult : uint8_t {
    SUCCESS          = 0,
    NO_SKILL_POINTS  = 1,
    SKILL_NOT_FOUND  = 2,
    MAX_LEVEL        = 3,
    LEVEL_TOO_LOW    = 4,  // 캐릭터 레벨 부족
    SLOTS_FULL       = 5,  // 스킬 슬롯 가득
};
