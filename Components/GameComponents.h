#pragma once

#include <cstdint>

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
};
