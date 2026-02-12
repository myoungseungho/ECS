#pragma once

#include <cstdint>

// ━━━ Session 24: Buff/Debuff System Components ━━━

constexpr int MAX_ACTIVE_BUFFS = 10;

// 버프 타입
enum class BuffType : uint8_t {
    ATK_UP      = 1,  // 공격력 증가
    DEF_UP      = 2,  // 방어력 증가
    SPEED_UP    = 3,  // 이속 증가
    REGEN       = 4,  // HP 지속 회복
    POISON      = 5,  // 독 (HP 지속 감소)
    ATK_DOWN    = 6,  // 공격력 감소
};

// 버프 정의 테이블
struct BuffTemplate {
    int32_t buff_id;
    char name[20];
    BuffType type;
    int32_t value;          // 효과 수치 (ATK+20, 틱당 10 등)
    int32_t duration_ms;    // 지속시간 (밀리초)
    int32_t tick_ms;        // 틱 간격 (밀리초, 0이면 틱 없음)
    int32_t max_stacks;
};

constexpr int BUFF_TEMPLATE_COUNT = 6;
inline const BuffTemplate BUFF_TEMPLATES[BUFF_TEMPLATE_COUNT] = {
    {1, "Strength",   BuffType::ATK_UP,   20,  10000, 0,    1},
    {2, "IronSkin",   BuffType::DEF_UP,   15,  10000, 0,    1},
    {3, "Haste",      BuffType::SPEED_UP, 30,  8000,  0,    1},
    {4, "Regenerate", BuffType::REGEN,    10,  10000, 2000, 1},
    {5, "Poison",     BuffType::POISON,   8,   6000,  1000, 3},
    {6, "Weaken",     BuffType::ATK_DOWN, 10,  8000,  0,    1},
};

inline const BuffTemplate* FindBuffTemplate(int32_t id) {
    for (int i = 0; i < BUFF_TEMPLATE_COUNT; i++) {
        if (BUFF_TEMPLATES[i].buff_id == id) return &BUFF_TEMPLATES[i];
    }
    return nullptr;
}

// 활성 버프 인스턴스
struct ActiveBuff {
    int32_t buff_id = 0;
    float remaining = 0;     // 남은 시간 (초)
    float tick_timer = 0;    // 다음 틱까지 남은 시간
    int32_t stacks = 0;
    bool active = false;
};

// 버프 컴포넌트: "이 Entity에 적용된 버프/디버프 목록"
struct BuffComponent {
    ActiveBuff buffs[MAX_ACTIVE_BUFFS];

    // 버프 추가 (이미 있으면 갱신/스택)
    int ApplyBuff(int32_t buff_id) {
        auto* tmpl = FindBuffTemplate(buff_id);
        if (!tmpl) return -1;

        // 기존 버프 찾기
        for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
            if (buffs[i].active && buffs[i].buff_id == buff_id) {
                // 스택 추가 또는 갱신
                if (buffs[i].stacks < tmpl->max_stacks) {
                    buffs[i].stacks++;
                }
                buffs[i].remaining = tmpl->duration_ms / 1000.0f;  // 시간 리셋
                return i;
            }
        }

        // 빈 슬롯에 새 버프
        for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
            if (!buffs[i].active) {
                buffs[i].buff_id = buff_id;
                buffs[i].remaining = tmpl->duration_ms / 1000.0f;
                buffs[i].tick_timer = (tmpl->tick_ms > 0) ? tmpl->tick_ms / 1000.0f : 0;
                buffs[i].stacks = 1;
                buffs[i].active = true;
                return i;
            }
        }
        return -1;  // 슬롯 없음
    }

    // 버프 제거
    void RemoveBuff(int32_t buff_id) {
        for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
            if (buffs[i].active && buffs[i].buff_id == buff_id) {
                buffs[i] = {};
                return;
            }
        }
    }

    // 활성 버프 수
    int ActiveCount() const {
        int c = 0;
        for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
            if (buffs[i].active) c++;
        }
        return c;
    }

    // 스탯 보너스 계산 (ATK 보너스)
    int32_t GetAttackBonus() const {
        int32_t bonus = 0;
        for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
            if (!buffs[i].active) continue;
            auto* tmpl = FindBuffTemplate(buffs[i].buff_id);
            if (!tmpl) continue;
            if (tmpl->type == BuffType::ATK_UP) bonus += tmpl->value * buffs[i].stacks;
            if (tmpl->type == BuffType::ATK_DOWN) bonus -= tmpl->value * buffs[i].stacks;
        }
        return bonus;
    }

    // 스탯 보너스 계산 (DEF 보너스)
    int32_t GetDefenseBonus() const {
        int32_t bonus = 0;
        for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
            if (!buffs[i].active) continue;
            auto* tmpl = FindBuffTemplate(buffs[i].buff_id);
            if (!tmpl) continue;
            if (tmpl->type == BuffType::DEF_UP) bonus += tmpl->value * buffs[i].stacks;
        }
        return bonus;
    }
};

enum class BuffResult : uint8_t {
    SUCCESS         = 0,
    BUFF_NOT_FOUND  = 1,
    NO_SLOT         = 2,
    NOT_ACTIVE      = 3,
};
