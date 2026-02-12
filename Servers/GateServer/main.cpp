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
#include <unordered_map>

// Gate Server - Session 17: Dynamic Load Balancing
//
// Field 서버가 Gate에 접속하여 자신을 등록 (FIELD_REGISTER)
// 주기적으로 CCU를 보고 (FIELD_HEARTBEAT)
// Gate는 실시간 CCU 기반으로 클라이언트를 가장 한가한 서버로 라우팅
// 하트비트 타임아웃으로 죽은 서버 자동 감지

constexpr uint16_t GATE_PORT = 8888;
constexpr int WORKER_THREADS = 2;
constexpr float TICK_RATE = 30.0f;
constexpr float TICK_INTERVAL = 1.0f / TICK_RATE;

// 하트비트 타임아웃 (초) - 이 시간 동안 하트비트가 없으면 TIMEOUT 판정
constexpr float HEARTBEAT_TIMEOUT = 6.0f;

IOCPServer* g_network = nullptr;

// ━━━ Field Server Registry ━━━

enum class ServerStatus : uint8_t {
    UNKNOWN = 0,
    ALIVE   = 1,
    TIMEOUT = 2,
    FULL    = 3,
};

struct FieldServerInfo {
    std::string host;
    uint16_t port = 0;
    uint32_t current_ccu = 0;
    uint32_t max_ccu = 500;
    ServerStatus status = ServerStatus::UNKNOWN;
    uint64_t session_id = 0;     // Gate측 세션 ID
    double last_heartbeat = 0.0; // 마지막 하트비트 시간
    char name[32] = {};
};

std::vector<FieldServerInfo> g_field_servers;
std::unordered_map<uint64_t, int> g_field_session_map;  // session_id -> server index

double GetTimeSec() {  // Windows API의 GetCurrentTime과 충돌 방지
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration<double>(now.time_since_epoch()).count();
}

// ━━━ FIELD_REGISTER 핸들러 ━━━
// Field서버가 Gate에 접속 후 자신을 등록
// 페이로드: [port(2) max_ccu(4) name_len(1) name(N)]
void OnFieldRegister(World& world, Entity entity, const char* payload, int len) {
    if (len < 7) return;

    auto& session = world.GetComponent<SessionComponent>(entity);

    uint16_t field_port = 0;
    uint32_t max_ccu = 0;
    std::memcpy(&field_port, payload, 2);
    std::memcpy(&max_ccu, payload + 2, 4);
    uint8_t name_len = static_cast<uint8_t>(payload[6]);

    char name[32] = {};
    if (name_len > 0 && name_len < 32 && len >= 7 + name_len) {
        std::memcpy(name, payload + 7, name_len);
    }

    // 이미 등록된 포트인지 확인 (재접속 케이스)
    int idx = -1;
    for (int i = 0; i < static_cast<int>(g_field_servers.size()); i++) {
        if (g_field_servers[i].port == field_port) {
            idx = i;
            break;
        }
    }

    if (idx < 0) {
        // 신규 등록
        FieldServerInfo info;
        info.host = "127.0.0.1";
        info.port = field_port;
        info.max_ccu = max_ccu;
        info.current_ccu = 0;
        info.status = ServerStatus::ALIVE;
        info.session_id = session.session_id;
        info.last_heartbeat = GetTimeSec();
        std::strncpy(info.name, name, 31);
        idx = static_cast<int>(g_field_servers.size());
        g_field_servers.push_back(info);
    } else {
        // 재접속: 기존 엔트리 업데이트
        auto& info = g_field_servers[idx];
        info.status = ServerStatus::ALIVE;
        info.session_id = session.session_id;
        info.max_ccu = max_ccu;
        info.current_ccu = 0;
        info.last_heartbeat = GetTimeSec();
        std::strncpy(info.name, name, 31);
    }

    g_field_session_map[session.session_id] = idx;

    // 응답: FIELD_REGISTER_ACK [result(1) server_index(4)]
    char resp[5];
    resp[0] = 0;  // success
    int32_t server_index = idx;
    std::memcpy(resp + 1, &server_index, 4);
    auto pkt = BuildPacket(MsgType::FIELD_REGISTER_ACK, resp, 5);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Gate] Field registered: %s:%d (idx=%d, max_ccu=%d)\n",
           g_field_servers[idx].host.c_str(), field_port, idx, max_ccu);
}

// ━━━ FIELD_HEARTBEAT 핸들러 ━━━
// Field서버가 주기적으로 보내는 상태 보고
// 페이로드: [port(2) ccu(4) max_ccu(4)]
void OnFieldHeartbeat(World& world, Entity entity, const char* payload, int len) {
    if (len < 10) return;

    auto& session = world.GetComponent<SessionComponent>(entity);

    uint16_t field_port = 0;
    uint32_t ccu = 0;
    uint32_t max_ccu = 0;
    std::memcpy(&field_port, payload, 2);
    std::memcpy(&ccu, payload + 2, 4);
    std::memcpy(&max_ccu, payload + 6, 4);

    auto it = g_field_session_map.find(session.session_id);
    if (it == g_field_session_map.end()) return;

    int idx = it->second;
    if (idx < 0 || idx >= static_cast<int>(g_field_servers.size())) return;

    auto& info = g_field_servers[idx];
    info.current_ccu = ccu;
    info.max_ccu = max_ccu;
    info.last_heartbeat = GetTimeSec();

    // CCU가 max에 도달하면 FULL, 아니면 ALIVE
    if (ccu >= max_ccu) {
        info.status = ServerStatus::FULL;
    } else {
        info.status = ServerStatus::ALIVE;
    }
}

// ━━━ GATE_ROUTE_REQ 핸들러 (동적 버전) ━━━
// 클라이언트가 게임서버 배정 요청 → 가장 한가한 ALIVE 서버로 라우팅
void OnGateRouteReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    // 가장 한가한 ALIVE 서버 탐색
    int best = -1;
    for (int i = 0; i < static_cast<int>(g_field_servers.size()); i++) {
        auto& s = g_field_servers[i];
        if (s.status != ServerStatus::ALIVE) continue;
        if (s.current_ccu >= s.max_ccu) continue;

        if (best < 0 || s.current_ccu < g_field_servers[best].current_ccu) {
            best = i;
        }
    }

    if (best < 0) {
        // 사용 가능한 서버 없음
        char resp[1] = {1};
        auto pkt = BuildPacket(MsgType::GATE_ROUTE_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        printf("[Gate] Route FAILED: no available servers\n");
        return;
    }

    auto& srv = g_field_servers[best];

    // GATE_ROUTE_RESP: [result(1)] [port(2)] [ip_len(1)] [ip(N)]
    uint8_t ip_len = static_cast<uint8_t>(srv.host.size());
    int resp_size = 1 + 2 + 1 + ip_len;
    std::vector<char> resp(resp_size);
    resp[0] = 0;  // success
    std::memcpy(resp.data() + 1, &srv.port, 2);
    resp[3] = static_cast<char>(ip_len);
    std::memcpy(resp.data() + 4, srv.host.c_str(), ip_len);

    auto pkt = BuildPacket(MsgType::GATE_ROUTE_RESP, resp.data(), resp_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    // 예측 CCU 증가 (하트비트 전까지 라우팅 분산 보장)
    srv.current_ccu++;

    printf("[Gate] -> %s:%d (ccu: %d/%d)\n",
           srv.host.c_str(), srv.port, srv.current_ccu, srv.max_ccu);
}

// ━━━ GATE_SERVER_LIST 핸들러 (모니터링/테스트용) ━━━
// 응답: [count(1) {port(2) ccu(4) max_ccu(4) status(1)}...]
// 엔트리당 11바이트
void OnGateServerList(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    uint8_t count = static_cast<uint8_t>(g_field_servers.size());
    int resp_size = 1 + count * 11;
    std::vector<char> resp(resp_size);
    resp[0] = static_cast<char>(count);

    for (int i = 0; i < count; i++) {
        auto& s = g_field_servers[i];
        int off = 1 + i * 11;
        std::memcpy(resp.data() + off, &s.port, 2);
        std::memcpy(resp.data() + off + 2, &s.current_ccu, 4);
        std::memcpy(resp.data() + off + 6, &s.max_ccu, 4);
        resp[off + 10] = static_cast<char>(s.status);
    }

    auto pkt = BuildPacket(MsgType::GATE_SERVER_LIST_RESP, resp.data(), resp_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// ━━━ 하트비트 타임아웃 체크 ━━━
void CheckHeartbeatTimeout() {
    double now = GetTimeSec();
    for (auto& s : g_field_servers) {
        if (s.status == ServerStatus::ALIVE || s.status == ServerStatus::FULL) {
            if (now - s.last_heartbeat > HEARTBEAT_TIMEOUT) {
                printf("[Gate] TIMEOUT: %s:%d (%.1fs since last heartbeat)\n",
                       s.host.c_str(), s.port, now - s.last_heartbeat);
                s.status = ServerStatus::TIMEOUT;
                s.current_ccu = 0;
            }
        }
    }
}

// ━━━ main ━━━
int main(int argc, char* argv[]) {
    uint16_t gate_port = GATE_PORT;
    if (argc > 1) {
        gate_port = static_cast<uint16_t>(std::atoi(argv[1]));
    }

    printf("======================================\n");
    printf("  ECS Gate Server - Session 17\n");
    printf("  Dynamic Load Balancing\n");
    printf("======================================\n\n");

    // ━━━ 네트워크 + ECS ━━━
    IOCPServer network;
    g_network = &network;

    if (!network.Start(gate_port, WORKER_THREADS)) {
        printf("Failed to start gate server!\n");
        return 1;
    }

    World world;
    world.AddSystem<NetworkSystem>(network);

    auto& dispatch = world.AddSystemAndGet<MessageDispatchSystem>(network);
    dispatch.RegisterHandler(MsgType::GATE_ROUTE_REQ, OnGateRouteReq);
    dispatch.RegisterHandler(MsgType::FIELD_REGISTER, OnFieldRegister);
    dispatch.RegisterHandler(MsgType::FIELD_HEARTBEAT, OnFieldHeartbeat);
    dispatch.RegisterHandler(MsgType::GATE_SERVER_LIST, OnGateServerList);

    printf("[Gate] Listening on port %d (dynamic mode)\n", gate_port);
    printf("[Gate] Heartbeat timeout: %.0fs\n\n", HEARTBEAT_TIMEOUT);

    // ━━━ 게임 루프 ━━━
    auto prev_time = std::chrono::high_resolution_clock::now();
    float timeout_check_timer = 0.0f;

    while (network.IsRunning()) {
        auto now = std::chrono::high_resolution_clock::now();
        float dt = std::chrono::duration<float>(now - prev_time).count();

        if (dt >= TICK_INTERVAL) {
            prev_time = now;
            world.Update(dt);

            // 1초마다 타임아웃 체크
            timeout_check_timer += dt;
            if (timeout_check_timer >= 1.0f) {
                timeout_check_timer = 0.0f;
                CheckHeartbeatTimeout();
            }
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
