#pragma once

#include "../Core/Entity.h"
#include "../Core/System.h"
#include "../NetworkEngine/IOCPServer.h"

// InterestSystem: AOI(관심 영역) 관리
//
// 역할:
//   1. 이동한 Entity의 그리드 셀을 계산/갱신
//   2. 셀이 바뀌면 APPEAR/DISAPPEAR 패킷 발송
//
// 실행 순서:
//   NetworkSystem → MessageDispatch → [InterestSystem] → BroadcastSystem
//
// Session 3에서는 BroadcastSystem이 "전체"에게 보냈지만,
// Session 4부터는:
//   - InterestSystem이 셀 전환 시 APPEAR/DISAPPEAR 처리
//   - BroadcastSystem이 근처 셀에만 MOVE_BROADCAST 전송
class InterestSystem : public ISystem {
public:
    explicit InterestSystem(IOCPServer& server);

    void Update(World& world, float dt) override;
    const char* GetName() const override { return "InterestSystem"; }

private:
    IOCPServer& server_;

    // 한 Entity의 APPEAR 패킷을 특정 세션에 전송
    void SendAppear(Entity entity, float x, float y, float z, uint64_t to_session);
    // 한 Entity의 DISAPPEAR 패킷을 특정 세션에 전송
    void SendDisappear(Entity entity, uint64_t to_session);
};
