#pragma once

#include <cstdint>
#include <cstring>
#include <algorithm>

// ━━━ Session 12: Stats System Components ━━━
//
// 모든 "능력치가 있는" Entity에 부착
// HP/MP/Attack/Defense/Level/EXP
//
// OOP: class Character { int hp, mp, atk, def; void TakeDamage(); }
// ECS: StatsComponent는 순수 데이터, StatsSystem이 로직 처리

// 직업별 기본 스탯 테이블
enum class JobClass : int32_t {
    WARRIOR = 0,    // 전사: HP 높음, ATK 높음
    ARCHER  = 1,    // 궁수: 밸런스
    MAGE    = 2,    // 마법사: MP 높음, DEF 낮음
};

// 스탯 컴포넌트: "이 Entity는 능력치가 있다"
struct StatsComponent {
    // 기본 스탯
    int32_t level = 1;
    int32_t exp = 0;
    int32_t exp_to_next = 100;     // 다음 레벨까지 필요 EXP

    // HP/MP (현재값 / 최대값)
    int32_t hp = 100;
    int32_t max_hp = 100;
    int32_t mp = 50;
    int32_t max_mp = 50;

    // 공격/방어
    int32_t attack = 10;
    int32_t defense = 5;

    // 직업
    JobClass job = JobClass::WARRIOR;

    // HP/MP 자연회복 (초당)
    float hp_regen_rate = 1.0f;     // 초당 HP 회복량
    float mp_regen_rate = 0.5f;     // 초당 MP 회복량
    float regen_accumulator = 0.0f; // 회복 누적 (소수점 처리)

    // dirty 플래그 (변경 시 클라이언트에 동기화)
    bool stats_dirty = false;

    // ━━━ 직업+레벨 기반 스탯 계산 ━━━
    void RecalculateFromLevel() {
        switch (job) {
            case JobClass::WARRIOR:
                max_hp = 80 + level * 20;       // Lv1=100, Lv50=1080
                max_mp = 30 + level * 5;        // Lv1=35,  Lv50=280
                attack = 8 + level * 2;         // Lv1=10,  Lv50=108
                defense = 3 + level * 2;        // Lv1=5,   Lv50=103
                hp_regen_rate = 1.0f + level * 0.1f;
                mp_regen_rate = 0.3f + level * 0.05f;
                break;
            case JobClass::ARCHER:
                max_hp = 60 + level * 15;       // Lv1=75,  Lv50=810
                max_mp = 40 + level * 8;        // Lv1=48,  Lv50=440
                attack = 6 + level * 3;         // Lv1=9,   Lv50=156
                defense = 2 + level * 1;        // Lv1=3,   Lv50=52
                hp_regen_rate = 0.8f + level * 0.08f;
                mp_regen_rate = 0.5f + level * 0.06f;
                break;
            case JobClass::MAGE:
                max_hp = 50 + level * 10;       // Lv1=60,  Lv50=550
                max_mp = 60 + level * 12;       // Lv1=72,  Lv50=660
                attack = 5 + level * 4;         // Lv1=9,   Lv50=205
                defense = 1 + level * 1;        // Lv1=2,   Lv50=51
                hp_regen_rate = 0.5f + level * 0.05f;
                mp_regen_rate = 1.0f + level * 0.1f;
                break;
        }
        exp_to_next = level * level * 10 + 100;  // Lv1=110, Lv10=1100, Lv50=25100
        stats_dirty = true;
    }

    // ━━━ 레벨업 처리 ━━━
    // 반환: true면 레벨업 발생
    bool AddExp(int32_t amount) {
        exp += amount;
        bool leveled = false;
        while (exp >= exp_to_next && level < 99) {
            exp -= exp_to_next;
            level++;
            RecalculateFromLevel();
            // 레벨업 시 HP/MP 전회복
            hp = max_hp;
            mp = max_mp;
            leveled = true;
        }
        if (level >= 99) {
            exp = 0;  // 만렙이면 EXP 고정
        }
        stats_dirty = true;
        return leveled;
    }

    // ━━━ 데미지 처리 ━━━
    // 반환: 실제 받은 데미지 (방어력 적용 후)
    int32_t TakeDamage(int32_t raw_damage) {
        int32_t actual = std::max(1, raw_damage - defense);  // 최소 1 데미지
        hp = std::max(0, hp - actual);
        stats_dirty = true;
        return actual;
    }

    // ━━━ 힐 처리 ━━━
    int32_t Heal(int32_t amount) {
        int32_t old_hp = hp;
        hp = std::min(max_hp, hp + amount);
        stats_dirty = true;
        return hp - old_hp;  // 실제 회복량
    }

    // ━━━ MP 소모 ━━━
    bool UseMp(int32_t cost) {
        if (mp < cost) return false;
        mp -= cost;
        stats_dirty = true;
        return true;
    }

    // 살아있는지
    bool IsAlive() const { return hp > 0; }
};

// ━━━ 스탯 초기화 헬퍼 ━━━
// 직업+레벨로 StatsComponent를 세팅하는 팩토리 함수
inline StatsComponent CreateStats(JobClass job, int32_t level) {
    StatsComponent stats;
    stats.job = job;
    stats.level = level;
    stats.RecalculateFromLevel();
    stats.hp = stats.max_hp;
    stats.mp = stats.max_mp;
    stats.stats_dirty = true;
    return stats;
}
