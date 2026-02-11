#include "NetworkSystem.h"
#include "../Core/World.h"
#include "../Components/NetworkComponents.h"
#include <cstdio>
#include <cstring>
#include <string>

NetworkSystem::NetworkSystem(IOCPServer& server)
    : server_(server) {}

void NetworkSystem::Update(World& world, float dt) {
    // 1. IOCP 이벤트 꺼내기
    auto events = server_.PollEvents();

    for (auto& event : events) {
        switch (event.type) {

        case IOCPEvent::Type::CONNECTED: {
            // Entity 생성 + SessionComponent 부착
            Entity entity = world.CreateEntity();

            SessionComponent session;
            session.session_id = event.session_id;
            session.connected = true;
            world.AddComponent(entity, session);

            // 수신 버퍼도 붙여줌
            world.AddComponent(entity, RecvBufferComponent{});

            // 매핑 저장
            session_to_entity_[event.session_id] = entity;

            printf("[NetworkSystem] Entity %llu created for session %llu\n",
                   entity, event.session_id);
            break;
        }

        case IOCPEvent::Type::DATA_RECEIVED: {
            auto it = session_to_entity_.find(event.session_id);
            if (it == session_to_entity_.end()) break;

            Entity entity = it->second;
            if (!world.IsAlive(entity)) break;

            // RecvBufferComponent에 날 바이트 적재만 함
            // 패킷 조립/처리는 MessageDispatchSystem이 담당 (Session 2)
            auto& recv = world.GetComponent<RecvBufferComponent>(entity);
            recv.buffer.insert(recv.buffer.end(),
                               event.data.begin(), event.data.end());
            break;
        }

        case IOCPEvent::Type::DISCONNECTED: {
            auto it = session_to_entity_.find(event.session_id);
            if (it == session_to_entity_.end()) break;

            Entity entity = it->second;

            printf("[NetworkSystem] Entity %llu destroyed (session %llu disconnected)\n",
                   entity, event.session_id);

            world.DestroyEntity(entity);
            session_to_entity_.erase(it);
            break;
        }

        }
    }
}

Entity NetworkSystem::GetEntityBySession(uint64_t session_id) const {
    auto it = session_to_entity_.find(session_id);
    if (it != session_to_entity_.end()) return it->second;
    return INVALID_ENTITY;
}
