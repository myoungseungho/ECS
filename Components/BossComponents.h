#pragma once

#include <cstdint>
#include <cstring>

// ━━━ Session 34: Boss Mechanics Components ━━━
//
// 보스 몬스터: 패턴/페이즈 기반 AI
// - HP% 기반 페이즈 전환 (100→70→40%)
// - 페이즈별 특수 공격 + ATK 배율
// - 인레이지 타이머 (전투 시간 초과 시 ATK 급증)
// - 처치 시 특별 루트 드롭

// 보스 특수 공격 타입
enum class BossAttackType : uint8_t {
    GROUND_SLAM  = 0,   // 지면 강타: 근거리 AoE
    FIRE_BREATH  = 1,   // 화염 브레스: 전방 광역
    TAIL_SWIPE   = 2,   // 꼬리 휘두르기: 후방 타격
    SUMMON_ADDS  = 3,   // 소환: 미니언 소환
    STOMP        = 4,   // 밟기: 전체 데미지 (약)
    DARK_NOVA    = 5,   // 암흑 폭발: 전체 고데미지
};

// 보스 페이즈 정의
struct BossPhase {
    float hp_threshold;         // 이 HP% 이하면 활성화 (1.0=시작, 0.7=2페이즈, 0.4=3페이즈)
    int32_t atk_multiplier;     // ATK 배율 (100=1.0x, 150=1.5x, 200=2.0x)
    float special_cooldown;     // 특수 공격 쿨다운 (초)
    BossAttackType special;     // 이 페이즈의 특수 공격
    int32_t special_damage;     // 특수 공격 데미지
};

// 보스 템플릿
struct BossTemplate {
    int32_t boss_id;
    char name[32];
    int32_t level;
    int32_t hp;
    int32_t attack;
    int32_t defense;
    int phase_count;
    BossPhase phases[4];        // 최대 4페이즈
    float enrage_time;          // 인레이지까지 시간 (초)
    int32_t enrage_atk_bonus;   // 인레이지 시 ATK 추가 (%)
    int32_t loot_table_id;
    int32_t zone_id;
    float spawn_x, spawn_y, spawn_z;
};

// 보스 컴포넌트 (Entity에 부착)
struct BossComponent {
    int32_t boss_id;
    int current_phase = 0;
    float enrage_timer = 0.0f;    // 전투 시작부터 경과 시간
    bool is_enraged = false;
    float special_timer = 0.0f;   // 특수 공격 쿨다운 카운터
    bool combat_started = false;  // 전투 시작 여부
};

// 보스 페이즈 변경 결과
enum class BossEventType : uint8_t {
    PHASE_CHANGE    = 0,
    SPECIAL_ATTACK  = 1,
    ENRAGE          = 2,
    DEFEATED        = 3,
};

// ━━━ 보스 데이터 ━━━
constexpr int BOSS_COUNT = 3;
inline const BossTemplate BOSS_TEMPLATES[BOSS_COUNT] = {
    // Ancient Golem (Zone 2) — Lv25, 3000HP
    {
        100, "AncientGolem", 25, 3000, 50, 30,
        2, // 2 phases
        {
            {1.0f, 100, 8.0f, BossAttackType::GROUND_SLAM, 80},     // Phase 1: 기본
            {0.5f, 150, 5.0f, BossAttackType::STOMP, 120},           // Phase 2: 강화 (HP 50%)
            {}, {}
        },
        180.0f,   // 3분 인레이지
        50,       // 인레이지 시 ATK +50%
        3,        // 루트 테이블 3 (보스용)
        2, 600.0f, 600.0f, 0.0f
    },
    // Dragon (Zone 3) — Lv30, 5000HP
    {
        101, "Dragon", 30, 5000, 70, 40,
        3, // 3 phases
        {
            {1.0f, 100, 10.0f, BossAttackType::FIRE_BREATH, 100},   // Phase 1: 화염
            {0.7f, 130, 7.0f,  BossAttackType::TAIL_SWIPE, 150},    // Phase 2: 꼬리 (HP 70%)
            {0.4f, 180, 4.0f,  BossAttackType::FIRE_BREATH, 250},   // Phase 3: 연속 화염 (HP 40%)
            {}
        },
        240.0f,   // 4분 인레이지
        80,       // 인레이지 시 ATK +80%
        4,        // 루트 테이블 4
        3, 300.0f, 300.0f, 0.0f
    },
    // Demon King (Zone 3) — Lv40, 8000HP
    {
        102, "DemonKing", 40, 8000, 90, 50,
        3, // 3 phases
        {
            {1.0f, 100, 12.0f, BossAttackType::DARK_NOVA, 120},     // Phase 1: 암흑
            {0.7f, 150, 8.0f,  BossAttackType::SUMMON_ADDS, 0},     // Phase 2: 소환 (HP 70%)
            {0.4f, 200, 5.0f,  BossAttackType::DARK_NOVA, 300},     // Phase 3: 전력 (HP 40%)
            {}
        },
        300.0f,   // 5분 인레이지
        100,      // 인레이지 시 ATK +100%
        5,        // 루트 테이블 5
        3, 500.0f, 500.0f, 0.0f
    },
};

inline const BossTemplate* FindBossTemplate(int32_t boss_id) {
    for (int i = 0; i < BOSS_COUNT; i++) {
        if (BOSS_TEMPLATES[i].boss_id == boss_id) return &BOSS_TEMPLATES[i];
    }
    return nullptr;
}
