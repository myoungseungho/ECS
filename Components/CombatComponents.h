#pragma once

#include <cstdint>
#include <cmath>
#include "../Core/Entity.h"
#include "GameComponents.h"

// ━━━ Session 13: Combat System Components ━━━
//
// 전투 가능한 Entity에 부착
// 공격 사거리, 쿨타임 관리
//
// OOP: class Character { void Attack(Character* target); float cooldown; }
// ECS: CombatComponent는 순수 데이터, 핸들러가 전투 로직 처리

// 공격 결과 코드
enum class AttackResult : uint8_t {
    SUCCESS             = 0,  // 공격 성공
    TARGET_NOT_FOUND    = 1,  // 타겟 없음
    TARGET_DEAD         = 2,  // 타겟 이미 사망
    OUT_OF_RANGE        = 3,  // 사거리 밖
    COOLDOWN_NOT_READY  = 4,  // 쿨타임 미완료
    ATTACKER_DEAD       = 5,  // 공격자 사망 상태
    SELF_ATTACK         = 6,  // 자기 자신 공격 불가
};

// 전투 컴포넌트: "이 Entity는 전투할 수 있다"
struct CombatComponent {
    float attack_range = 200.0f;       // 공격 사거리
    float attack_cooldown = 1.5f;      // 공격 쿨타임 (초)
    float cooldown_remaining = 0.0f;   // 남은 쿨타임
};

// ━━━ 전투 유틸리티 ━━━

// 두 위치 간 거리 계산
inline float DistanceBetween(const PositionComponent& a, const PositionComponent& b) {
    float dx = a.x - b.x;
    float dy = a.y - b.y;
    float dz = a.z - b.z;
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

// 킬 EXP 보상 공식: 대상 레벨 * 10
inline int32_t CalcKillExp(int32_t target_level) {
    return target_level * 10;
}
