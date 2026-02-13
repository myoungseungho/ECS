#pragma once

#include <cstdint>
#include <cmath>

// PositionComponent: "이 Entity는 위치가 있다"
// OOP: class Player { float x, y, z; }  (Player 클래스 안에 섞임)
// ECS: Entity에 PositionComponent를 붙이면 "위치를 가진 놈"
//
// position_dirty: 이번 틱에서 위치가 변경되었는지
// BroadcastSystem이 dirty인 Entity만 브로드캐스트하고 플래그를 끈다
struct PositionComponent {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    bool position_dirty = false;  // 이번 틱에 이동했는지

    // Session 35: 이동 검증용 (Model C)
    float last_valid_x = 0.0f;    // 마지막 검증된 위치
    float last_valid_y = 0.0f;
    float last_valid_z = 0.0f;
    uint32_t last_move_time = 0;  // 마지막 이동 시각 (ms, 서버 기준)
    int32_t violation_count = 0;  // 연속 위반 횟수
};

// Session 35: 이동 규칙 (서버+클라 공유)
namespace MovementRules {
    constexpr float BASE_SPEED        = 200.0f;   // 기본 이동속도 (units/sec)
    constexpr float SPRINT_MULTIPLIER = 1.5f;     // 달리기 배율
    constexpr float MOUNT_MULTIPLIER  = 2.0f;     // 탈것 배율
    constexpr float TOLERANCE         = 1.5f;     // 서버 검증 여유값 (50% — 네트워크 지터 허용)
    constexpr int   UPDATE_RATE_HZ    = 10;       // 초당 위치 전송 횟수
    constexpr float CORRECTION_DIST   = 50.0f;    // 이 거리 이상 차이나면 보정
    constexpr int   MAX_VIOLATIONS    = 5;        // 연속 위반 허용 횟수 (초과 시 킥)
    constexpr float MAX_VALID_COORD   = 10000.0f; // 좌표 최대값
}

// Session 35: 존별 경계 데이터
struct ZoneBounds {
    int zone_id;
    float min_x, min_y;
    float max_x, max_y;
};

constexpr int ZONE_BOUNDS_COUNT = 3;
inline const ZoneBounds ZONE_BOUNDS_TABLE[ZONE_BOUNDS_COUNT] = {
    { 1,    0.0f,    0.0f,  1000.0f, 1000.0f },  // Zone 1: 마을
    { 2,    0.0f,    0.0f,  2000.0f, 2000.0f },  // Zone 2: 사냥터
    { 3,    0.0f,    0.0f,  3000.0f, 3000.0f },  // Zone 3: 던전
};

inline const ZoneBounds* GetZoneBounds(int zone_id) {
    for (int i = 0; i < ZONE_BOUNDS_COUNT; i++) {
        if (ZONE_BOUNDS_TABLE[i].zone_id == zone_id) return &ZONE_BOUNDS_TABLE[i];
    }
    return nullptr;
}

// 두 점 사이 2D 거리
inline float Distance2D(float x1, float y1, float x2, float y2) {
    float dx = x2 - x1;
    float dy = y2 - y1;
    return std::sqrt(dx * dx + dy * dy);
}
