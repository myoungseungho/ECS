#pragma once

#include "../Core/Entity.h"
#include "../Core/System.h"
#include "../NetworkEngine/IOCPServer.h"
#include <unordered_map>

// NetworkSystem: IOCP 이벤트를 ECS 세계로 가져오는 System
//
// 매 틱마다:
//   1. IOCPServer.PollEvents()로 이벤트 꺼냄
//   2. CONNECTED    → Entity 생성 + SessionComponent 부착
//   3. DATA_RECEIVED → RecvBufferComponent에 적재 + 에코 응답 (Session 1)
//   4. DISCONNECTED → Entity 파괴
//
// OOP였다면: class EchoServer { void OnRecv(Session* s, char* data); }
// ECS에서는: NetworkSystem이 SessionComponent를 가진 Entity를 다룸
class NetworkSystem : public ISystem {
public:
    // 외부에서 IOCPServer를 받음 (System은 상태를 가지면 안 되지만,
    // 네트워크 엔진은 ECS 바깥 인프라이므로 참조만 보관)
    explicit NetworkSystem(IOCPServer& server);

    void Update(World& world, float dt) override;
    const char* GetName() const override { return "NetworkSystem"; }

    // session_id → Entity 매핑 (어떤 세션이 어떤 Entity인지)
    Entity GetEntityBySession(uint64_t session_id) const;

private:
    IOCPServer& server_;

    // session_id → Entity 매핑 테이블
    std::unordered_map<uint64_t, Entity> session_to_entity_;
};
