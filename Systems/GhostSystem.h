#pragma once

#include "../Core/Entity.h"
#include "../Core/System.h"
#include "../NetworkEngine/IOCPServer.h"

// GhostSystem: 서버 경계 Ghost Entity 관리 (Session 8)
//
// 역할:
//   1. 경계 근처 Entity 감지 → 인접 존에 Ghost 생성 + APPEAR
//   2. Ghost 위치를 원본과 동기화 + MOVE_BROADCAST
//   3. 원본이 경계 이탈/사망 시 Ghost 파괴 + DISAPPEAR
//
// Ghost Entity = GhostComponent + PositionComponent + ZoneComponent + ChannelComponent
//   (SessionComponent 없음 → 기존 System들이 자동 무시)
//
// 실행 순서:
//   Network → Dispatch → Interest → Broadcast → [GhostSystem]

class GhostSystem : public ISystem {
public:
    explicit GhostSystem(IOCPServer& server);

    void Update(World& world, float dt) override;
    const char* GetName() const override { return "GhostSystem"; }

private:
    IOCPServer& server_;

    // Ghost의 APPEAR를 인접 존의 실제 플레이어에게 전송
    void SendGhostAppear(World& world, Entity ghost, float x, float y, float z);
    // Ghost의 DISAPPEAR를 인접 존의 실제 플레이어에게 전송
    void SendGhostDisappear(World& world, Entity ghost);
    // Ghost의 위치 변경을 인접 존의 실제 플레이어에게 전송
    void SendGhostMoveBroadcast(World& world, Entity ghost, float x, float y, float z);
};
