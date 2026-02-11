#include "../../Core/World.h"
#include "../../NetworkEngine/IOCPServer.h"
#include "../../Systems/NetworkSystem.h"
#include "../../Systems/MessageDispatchSystem.h"
#include "../../Components/NetworkComponents.h"
#include "../../Components/PacketComponents.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <chrono>
#include <thread>

// 게이트 서버 설정
constexpr uint16_t GATE_PORT = 8888;
constexpr int WORKER_THREADS = 2;
constexpr float TICK_RATE = 30.0f;
constexpr float TICK_INTERVAL = 1.0f / TICK_RATE;

// 전역 네트워크 포인터
IOCPServer* g_network = nullptr;

// ━━━ 게임서버 목록 (로드밸런싱 대상) ━━━

struct GameServerEntry {
    std::string host;
    uint16_t port;
    int routed_count;  // 이 서버로 보낸 클라이언트 수
};

std::vector<GameServerEntry> g_game_servers;

// ━━━ 핸들러 ━━━

// GATE_ROUTE_REQ 핸들러: 가장 한가한 게임서버 배정
// 응답: GATE_ROUTE_RESP [result(1: 0=성공)] [port(2 uint16)] [ip_len(1)] [ip(N)]
void OnGateRouteReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    if (g_game_servers.empty()) {
        char resp[1] = {1};  // 실패: 서버 없음
        auto pkt = BuildPacket(MsgType::GATE_ROUTE_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // Least-connections: 가장 적게 보낸 서버 선택
    int best = 0;
    for (int i = 1; i < static_cast<int>(g_game_servers.size()); i++) {
        if (g_game_servers[i].routed_count < g_game_servers[best].routed_count) {
            best = i;
        }
    }

    g_game_servers[best].routed_count++;
    auto& srv = g_game_servers[best];

    // 응답 조립
    uint8_t ip_len = static_cast<uint8_t>(srv.host.size());
    int resp_size = 1 + 2 + 1 + ip_len;
    std::vector<char> resp(resp_size);
    resp[0] = 0;  // 성공
    std::memcpy(resp.data() + 1, &srv.port, 2);
    resp[3] = static_cast<char>(ip_len);
    std::memcpy(resp.data() + 4, srv.host.c_str(), ip_len);

    auto pkt = BuildPacket(MsgType::GATE_ROUTE_RESP, resp.data(), resp_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Gate] -> %s:%d (load: %d)\n",
           srv.host.c_str(), srv.port, srv.routed_count);
}

int main(int argc, char* argv[]) {
    // 사용법: GateServer.exe [port1] [port2] ...
    // 기본값: 7777 7778
    if (argc > 1) {
        for (int i = 1; i < argc; i++) {
            GameServerEntry entry;
            entry.host = "127.0.0.1";
            entry.port = static_cast<uint16_t>(std::atoi(argv[i]));
            entry.routed_count = 0;
            g_game_servers.push_back(entry);
        }
    } else {
        g_game_servers.push_back({"127.0.0.1", 7777, 0});
        g_game_servers.push_back({"127.0.0.1", 7778, 0});
    }

    printf("======================================\n");
    printf("  ECS Gate Server - Session 10\n");
    printf("  Load Balancing Gateway\n");
    printf("======================================\n\n");

    printf("[Gate] Game servers:\n");
    for (auto& s : g_game_servers) {
        printf("  - %s:%d\n", s.host.c_str(), s.port);
    }
    printf("\n");

    // ━━━ 네트워크 + ECS ━━━
    IOCPServer network;
    g_network = &network;

    if (!network.Start(GATE_PORT, WORKER_THREADS)) {
        printf("Failed to start gate server!\n");
        return 1;
    }

    World world;

    world.AddSystem<NetworkSystem>(network);

    auto& dispatch = world.AddSystemAndGet<MessageDispatchSystem>(network);
    dispatch.RegisterHandler(MsgType::GATE_ROUTE_REQ, OnGateRouteReq);

    printf("[Gate] Listening on port %d\n\n", GATE_PORT);

    // ━━━ 게임 루프 ━━━
    auto prev_time = std::chrono::high_resolution_clock::now();

    while (network.IsRunning()) {
        auto now = std::chrono::high_resolution_clock::now();
        float dt = std::chrono::duration<float>(now - prev_time).count();

        if (dt >= TICK_INTERVAL) {
            prev_time = now;
            world.Update(dt);
        } else {
            auto sleep_ms = static_cast<int>((TICK_INTERVAL - dt) * 1000.0f);
            if (sleep_ms > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
            }
        }
    }

    printf("[Gate] Server shutting down...\n");
    g_network = nullptr;
    return 0;
}
