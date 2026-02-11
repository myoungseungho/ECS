#pragma once

#include "../Core/Entity.h"

// ━━━ Ghost Entity (Session 8) ━━━
//
// Ghost = 다른 존(서버)에 있는 Entity의 "그림자"
// 서버 경계에서 인접 서버의 캐릭터를 표현
//
// 시나리오:
//   Zone 1의 플레이어 A가 경계 근처로 이동
//   → Zone 2에 Ghost(A) 생성
//   → Zone 2의 플레이어 B에게 Ghost가 보임
//   → A가 경계에서 멀어지면 Ghost 파괴
//
// Ghost Entity 구성:
//   GhostComponent + PositionComponent + ZoneComponent + ChannelComponent
//   (SessionComponent 없음 → InterestSystem/BroadcastSystem이 무시)

struct GhostComponent {
    Entity origin_entity;   // 원본 Entity (실제 플레이어)
    int origin_zone;        // 원본이 있는 존
};

// ━━━ 존 경계 설정 ━━━

// 경계 판정 기준 좌표
constexpr float GHOST_BOUNDARY_THRESHOLD = 300.0f;

// 존 인접 관계: zone_id → 인접 zone_id (0 = 인접 없음)
inline int GetAdjacentZone(int zone_id) {
    switch (zone_id) {
        case 1: return 2;   // Zone 1 ↔ Zone 2
        case 2: return 1;
        default: return 0;
    }
}

// 경계 지역 판정
// Zone 1 (스폰 100,100): 좌표 큰 쪽 = Zone 2 방향
// Zone 2 (스폰 500,500): 좌표 작은 쪽 = Zone 1 방향
inline bool IsNearBoundary(float x, float y, int zone_id) {
    switch (zone_id) {
        case 1: return x > GHOST_BOUNDARY_THRESHOLD || y > GHOST_BOUNDARY_THRESHOLD;
        case 2: return x < GHOST_BOUNDARY_THRESHOLD || y < GHOST_BOUNDARY_THRESHOLD;
        default: return false;
    }
}
