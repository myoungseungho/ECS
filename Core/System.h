#pragma once

// 전방 선언
class World;

// System = 순수 로직. 상태(멤버 변수) 없음.
// Update()에서 World를 통해 Component를 쿼리하고 처리.
class ISystem {
public:
    virtual ~ISystem() = default;

    // 매 틱마다 호출. dt = 경과 시간(초)
    virtual void Update(World& world, float dt) = 0;

    // System 이름 (디버깅용)
    virtual const char* GetName() const = 0;
};
