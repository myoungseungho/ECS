#pragma once

// windows.h의 min/max 매크로가 std::numeric_limits와 충돌하므로 비활성화
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <cstdint>
#include <limits>

// Entity = 그냥 ID. 데이터도 로직도 없음.
// OOP의 "객체"가 아니라 "번호표"일 뿐.
using Entity = uint64_t;

constexpr Entity INVALID_ENTITY = std::numeric_limits<Entity>::max();
