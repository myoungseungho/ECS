#pragma once

#include <cmath>
#include <climits>

// ━━━ Grid AOI (Session 4) ━━━
//
// 월드를 정사각형 셀로 나눈다.
// 같은 셀 또는 인접 8셀 안의 Entity만 서로 보인다.
//
//   ┌───┬───┬───┬───┐
//   │0,2│1,2│2,2│3,2│
//   ├───┼───┼───┼───┤
//   │0,1│1,1│2,1│3,1│  ← A가 (1,1)에 있으면
//   ├───┼───┼───┼───┤     주변 3x3 = 9칸이 A의 AOI
//   │0,0│1,0│2,0│3,0│
//   └───┴───┴───┴───┘
//
// 셀 크기 500이면:
//   좌표 (100, 200) → 셀 (0, 0)
//   좌표 (600, 100) → 셀 (1, 0)
//   좌표 (9999,9999) → 셀 (19, 19)

constexpr float GRID_CELL_SIZE = 500.0f;

// 좌표 → 셀 인덱스 변환
inline int ToCell(float coord) {
    return static_cast<int>(std::floor(coord / GRID_CELL_SIZE));
}

// 두 셀이 인접한지 (같은 셀 포함, 3x3 범위)
inline bool IsNearbyCell(int cx1, int cy1, int cx2, int cy2) {
    return std::abs(cx1 - cx2) <= 1 && std::abs(cy1 - cy2) <= 1;
}

// GridCellComponent: "이 Entity는 현재 어느 셀에 있다"
// InterestSystem이 PositionComponent에서 계산하여 자동 부착/갱신
struct GridCellComponent {
    int cell_x = 0;
    int cell_y = 0;

    // 이전 셀 (전환 감지용)
    // INT_MIN = "아직 셀에 배치된 적 없음" (첫 진입)
    int prev_cell_x = INT_MIN;
    int prev_cell_y = INT_MIN;

    // 이번 틱에 셀이 바뀌었는지 (InterestSystem이 설정)
    bool cell_changed = false;
};
