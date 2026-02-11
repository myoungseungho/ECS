#pragma once

#include "../Core/Entity.h"
#include "../Core/System.h"
#include "../NetworkEngine/IOCPServer.h"

// BroadcastSystem: 이번 틱에 위치가 바뀐(dirty) Entity를 찾아,
//                  다른 모든 Entity에게 알려주는 System
//
// 실행 순서:
//   NetworkSystem → MessageDispatch (여기서 OnMove가 위치 변경 + dirty 설정)
//   → BroadcastSystem (dirty Entity 찾아서 전파 + dirty 해제)
//
// Session 3: 모든 Entity에게 전파 (= 전체 브로드캐스트)
// Session 4: AOI(관심 영역) 안의 Entity에게만 전파
//
// 핵심 원칙: 자기 자신에게는 안 보냄 (S3-SELF-NO-ECHO)
class BroadcastSystem : public ISystem {
public:
    explicit BroadcastSystem(IOCPServer& server);

    void Update(World& world, float dt) override;
    const char* GetName() const override { return "BroadcastSystem"; }

private:
    IOCPServer& server_;
};
