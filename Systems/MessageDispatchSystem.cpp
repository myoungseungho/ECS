#include "MessageDispatchSystem.h"
#include "../Core/World.h"
#include "../Components/NetworkComponents.h"
#include "../Components/PacketComponents.h"
#include <cstdio>
#include <cstring>
#include <string>

MessageDispatchSystem::MessageDispatchSystem(IOCPServer& server)
    : server_(server) {}

void MessageDispatchSystem::RegisterHandler(MsgType type, Handler handler) {
    handlers_[static_cast<uint16_t>(type)] = std::move(handler);
}

void MessageDispatchSystem::Update(World& world, float dt) {
    // SessionComponent + RecvBufferComponent를 가진 모든 Entity 순회
    world.ForEach<SessionComponent, RecvBufferComponent>(
        [this, &world](Entity entity, SessionComponent& session, RecvBufferComponent& recv) {
            if (!session.connected) return;
            if (recv.buffer.empty()) return;

            ProcessBuffer(world, entity);
        }
    );
}

void MessageDispatchSystem::ProcessBuffer(World& world, Entity entity) {
    auto& recv = world.GetComponent<RecvBufferComponent>(entity);
    auto& session = world.GetComponent<SessionComponent>(entity);

    // 버퍼에 완성 패킷이 있는 한 계속 꺼냄
    while (true) {
        int buf_size = static_cast<int>(recv.buffer.size());

        // 헤더도 못 읽을 만큼 작으면 대기
        if (buf_size < PACKET_HEADER_SIZE) break;

        // 길이 필드 읽기 (little-endian)
        uint32_t packet_len = 0;
        std::memcpy(&packet_len, recv.buffer.data(), 4);

        // 유효성 검사
        if (packet_len < PACKET_HEADER_SIZE || packet_len > MAX_PACKET_SIZE) {
            printf("[Dispatch] Invalid packet length %u from session %llu, disconnecting\n",
                   packet_len, session.session_id);
            // 잘못된 패킷 → 버퍼 비우고 연결 끊기
            recv.buffer.clear();
            server_.Disconnect(session.session_id);
            return;
        }

        // 아직 완성 패킷이 안 됨 (더 받아야 함)
        if (static_cast<uint32_t>(buf_size) < packet_len) break;

        // ━━━ 완성 패킷 하나 추출 ━━━

        // 헤더 파싱
        PacketHeader header;
        std::memcpy(&header, recv.buffer.data(), PACKET_HEADER_SIZE);

        // 페이로드
        const char* payload = recv.buffer.data() + PACKET_HEADER_SIZE;
        int payload_len = static_cast<int>(packet_len - PACKET_HEADER_SIZE);

        // 핸들러 찾기
        auto it = handlers_.find(header.msg_type);
        if (it != handlers_.end()) {
            printf("[Dispatch] MsgType=%u, payload=%d bytes, entity=%llu\n",
                   header.msg_type, payload_len, entity);
            it->second(world, entity, payload, payload_len);
        } else {
            printf("[Dispatch] Unknown MsgType=%u from session %llu (ignored)\n",
                   header.msg_type, session.session_id);
            // 미등록 타입 → 무시 (서버 크래시 안 함, 연결도 유지)
        }

        // 처리한 패킷을 버퍼에서 제거
        recv.buffer.erase(recv.buffer.begin(), recv.buffer.begin() + packet_len);
    }
}
