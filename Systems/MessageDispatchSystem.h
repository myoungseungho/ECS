#pragma once

#include "../Core/Entity.h"
#include "../Core/System.h"
#include "../NetworkEngine/IOCPServer.h"
#include "../Components/PacketComponents.h"
#include <functional>
#include <unordered_map>

// MessageDispatchSystem: RecvBuffer에서 완성 패킷을 꺼내 타입별 핸들러를 호출
//
// Session 1에서는 NetworkSystem이 에코까지 직접 했지만,
// Session 2부터는 역할 분리:
//   NetworkSystem  = IOCP → RecvBuffer (날 바이트 적재만)
//   이 System      = RecvBuffer → 패킷 조립 → 타입별 핸들러
//
// OOP였다면: switch(packet.type) { case MOVE: OnMove(); break; ... }
// ECS에서는: 핸들러를 등록하면 System이 자동으로 호출해줌
//
// 핸들러 시그니처:
//   void handler(World& world, Entity entity, const char* payload, int payload_len)
//   - entity: 이 패킷을 보낸 클라이언트의 Entity
//   - payload: 헤더 뒤의 실제 데이터
//   - payload_len: 페이로드 바이트 수

class MessageDispatchSystem : public ISystem {
public:
    // 핸들러 타입
    using Handler = std::function<void(World&, Entity, const char*, int)>;

    explicit MessageDispatchSystem(IOCPServer& server);

    void Update(World& world, float dt) override;
    const char* GetName() const override { return "MessageDispatchSystem"; }

    // 메시지 타입별 핸들러 등록
    void RegisterHandler(MsgType type, Handler handler);

private:
    IOCPServer& server_;
    std::unordered_map<uint16_t, Handler> handlers_;

    // RecvBuffer에서 완성 패킷을 꺼내 처리
    void ProcessBuffer(World& world, Entity entity);
};
