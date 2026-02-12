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
#include <queue>
#include <chrono>
#include <thread>
#include <unordered_map>
#include <unordered_set>

// Message Bus Server - Session 18: Pub/Sub
//
// 서버들이 Bus에 접속하여 자신을 등록 (BUS_REGISTER)
// 토픽을 구독 (BUS_SUBSCRIBE) / 해제 (BUS_UNSUBSCRIBE)
// 메시지 발행 (BUS_PUBLISH) → Bus가 해당 토픽 구독자에게 전달 (BUS_MESSAGE)
// 우선순위 큐: CRITICAL(3) > HIGH(2) > NORMAL(1) > LOW(0)

constexpr uint16_t BUS_PORT = 9999;
constexpr int WORKER_THREADS = 2;
constexpr float TICK_RATE = 30.0f;
constexpr float TICK_INTERVAL = 1.0f / TICK_RATE;

IOCPServer* g_network = nullptr;

// ━━━ Server Registry ━━━

struct RegisteredServer {
    uint32_t server_id;
    uint64_t session_id;
    std::string name;
    std::unordered_set<std::string> subscriptions;
};

uint32_t g_next_server_id = 1;
std::vector<RegisteredServer> g_servers;
std::unordered_map<uint64_t, uint32_t> g_session_to_id;   // session_id -> server_id
std::unordered_map<uint32_t, int> g_id_to_index;           // server_id -> g_servers index

// ━━━ Topic Registry ━━━

std::unordered_map<std::string, std::unordered_set<uint32_t>> g_topic_subscribers;

// ━━━ Priority Message Queue ━━━

struct QueuedMessage {
    uint8_t priority;   // 0=LOW, 1=NORMAL, 2=HIGH, 3=CRITICAL
    std::string topic;
    uint32_t sender_id;
    std::vector<char> data;
};

struct ComparePriority {
    bool operator()(const QueuedMessage& a, const QueuedMessage& b) const {
        return a.priority < b.priority;  // higher priority = top
    }
};

std::priority_queue<QueuedMessage, std::vector<QueuedMessage>, ComparePriority> g_message_queue;

// ━━━ BUS_REGISTER ━━━
// 페이로드: [name_len(1) name(N)]
void OnBusRegister(World& world, Entity entity, const char* payload, int len) {
    if (len < 1) return;
    auto& session = world.GetComponent<SessionComponent>(entity);

    uint8_t name_len = static_cast<uint8_t>(payload[0]);
    char name[64] = {};
    if (name_len > 0 && name_len < 64 && len >= 1 + name_len) {
        std::memcpy(name, payload + 1, name_len);
    }

    // 이미 등록된 세션인지 확인
    auto it = g_session_to_id.find(session.session_id);
    if (it != g_session_to_id.end()) {
        char resp[5];
        resp[0] = 0;
        uint32_t sid = it->second;
        std::memcpy(resp + 1, &sid, 4);
        auto pkt = BuildPacket(MsgType::BUS_REGISTER_ACK, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    uint32_t server_id = g_next_server_id++;

    RegisteredServer srv;
    srv.server_id = server_id;
    srv.session_id = session.session_id;
    srv.name = name;

    int idx = static_cast<int>(g_servers.size());
    g_servers.push_back(srv);
    g_session_to_id[session.session_id] = server_id;
    g_id_to_index[server_id] = idx;

    // BUS_REGISTER_ACK: [result(1) server_id(4)]
    char resp[5];
    resp[0] = 0;  // success
    std::memcpy(resp + 1, &server_id, 4);
    auto pkt = BuildPacket(MsgType::BUS_REGISTER_ACK, resp, 5);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Bus] Server registered: '%s' (id=%d)\n", name, server_id);
}

// ━━━ BUS_SUBSCRIBE ━━━
// 페이로드: [topic_len(1) topic(N)]
void OnBusSubscribe(World& world, Entity entity, const char* payload, int len) {
    if (len < 1) return;
    auto& session = world.GetComponent<SessionComponent>(entity);

    auto it = g_session_to_id.find(session.session_id);
    if (it == g_session_to_id.end()) return;

    uint32_t server_id = it->second;

    uint8_t topic_len = static_cast<uint8_t>(payload[0]);
    if (topic_len == 0 || len < 1 + topic_len) return;

    std::string topic(payload + 1, topic_len);

    // 토픽 구독자에 추가
    g_topic_subscribers[topic].insert(server_id);

    // 서버의 구독 목록에 추가
    auto idx_it = g_id_to_index.find(server_id);
    if (idx_it != g_id_to_index.end()) {
        g_servers[idx_it->second].subscriptions.insert(topic);
    }

    // BUS_SUB_ACK: [result(1) topic_len(1) topic(N)]
    int resp_size = 1 + 1 + topic_len;
    std::vector<char> resp(resp_size);
    resp[0] = 0;  // success
    resp[1] = static_cast<char>(topic_len);
    std::memcpy(resp.data() + 2, topic.c_str(), topic_len);

    auto pkt = BuildPacket(MsgType::BUS_SUB_ACK, resp.data(), resp_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Bus] Server %d subscribed to '%s'\n", server_id, topic.c_str());
}

// ━━━ BUS_UNSUBSCRIBE ━━━
// 페이로드: [topic_len(1) topic(N)]
void OnBusUnsubscribe(World& world, Entity entity, const char* payload, int len) {
    if (len < 1) return;
    auto& session = world.GetComponent<SessionComponent>(entity);

    auto it = g_session_to_id.find(session.session_id);
    if (it == g_session_to_id.end()) return;

    uint32_t server_id = it->second;

    uint8_t topic_len = static_cast<uint8_t>(payload[0]);
    if (topic_len == 0 || len < 1 + topic_len) return;

    std::string topic(payload + 1, topic_len);

    // 토픽에서 제거
    auto topic_it = g_topic_subscribers.find(topic);
    if (topic_it != g_topic_subscribers.end()) {
        topic_it->second.erase(server_id);
        if (topic_it->second.empty()) {
            g_topic_subscribers.erase(topic_it);
        }
    }

    // 서버의 구독 목록에서 제거
    auto idx_it = g_id_to_index.find(server_id);
    if (idx_it != g_id_to_index.end()) {
        g_servers[idx_it->second].subscriptions.erase(topic);
    }

    printf("[Bus] Server %d unsubscribed from '%s'\n", server_id, topic.c_str());
}

// ━━━ BUS_PUBLISH ━━━
// 페이로드: [priority(1) topic_len(1) topic(N) data_len(2) data(N)]
void OnBusPublish(World& world, Entity entity, const char* payload, int len) {
    if (len < 4) return;  // priority(1) + topic_len(1) + data_len(2) 최소
    auto& session = world.GetComponent<SessionComponent>(entity);

    auto it = g_session_to_id.find(session.session_id);
    if (it == g_session_to_id.end()) return;

    uint32_t sender_id = it->second;

    uint8_t priority = static_cast<uint8_t>(payload[0]);
    uint8_t topic_len = static_cast<uint8_t>(payload[1]);
    if (len < 2 + topic_len + 2) return;

    std::string topic(payload + 2, topic_len);

    uint16_t data_len = 0;
    std::memcpy(&data_len, payload + 2 + topic_len, 2);

    if (len < 2 + topic_len + 2 + data_len) return;

    std::vector<char> data(data_len);
    if (data_len > 0) {
        std::memcpy(data.data(), payload + 2 + topic_len + 2, data_len);
    }

    // 우선순위 큐에 적재
    QueuedMessage msg;
    msg.priority = priority;
    msg.topic = topic;
    msg.sender_id = sender_id;
    msg.data = std::move(data);

    g_message_queue.push(std::move(msg));
}

// ━━━ 메시지 큐 처리 (매 틱마다) ━━━
void ProcessMessageQueue() {
    while (!g_message_queue.empty()) {
        auto msg = g_message_queue.top();
        g_message_queue.pop();

        // 해당 토픽의 구독자 조회
        auto topic_it = g_topic_subscribers.find(msg.topic);
        if (topic_it == g_topic_subscribers.end()) continue;

        // BUS_MESSAGE 패킷 조립
        // [priority(1) sender_id(4) topic_len(1) topic(N) data_len(2) data(N)]
        uint8_t topic_len = static_cast<uint8_t>(msg.topic.size());
        uint16_t data_len = static_cast<uint16_t>(msg.data.size());
        int payload_size = 1 + 4 + 1 + topic_len + 2 + data_len;
        std::vector<char> payload(payload_size);

        int off = 0;
        payload[off++] = static_cast<char>(msg.priority);
        std::memcpy(payload.data() + off, &msg.sender_id, 4); off += 4;
        payload[off++] = static_cast<char>(topic_len);
        std::memcpy(payload.data() + off, msg.topic.c_str(), topic_len); off += topic_len;
        std::memcpy(payload.data() + off, &data_len, 2); off += 2;
        if (data_len > 0) {
            std::memcpy(payload.data() + off, msg.data.data(), data_len);
        }

        auto pkt = BuildPacket(MsgType::BUS_MESSAGE, payload.data(), payload_size);

        // 구독자에게 전달 (자기 자신 제외)
        for (uint32_t sub_id : topic_it->second) {
            if (sub_id == msg.sender_id) continue;

            auto idx_it = g_id_to_index.find(sub_id);
            if (idx_it == g_id_to_index.end()) continue;

            auto& srv = g_servers[idx_it->second];
            g_network->SendTo(srv.session_id, pkt.data(), static_cast<int>(pkt.size()));
        }
    }
}

// ━━━ main ━━━
int main(int argc, char* argv[]) {
    uint16_t bus_port = BUS_PORT;
    if (argc > 1) {
        bus_port = static_cast<uint16_t>(std::atoi(argv[1]));
    }

    printf("======================================\n");
    printf("  ECS Message Bus - Session 18\n");
    printf("  Topic-based Pub/Sub\n");
    printf("======================================\n\n");

    // ━━━ 네트워크 + ECS ━━━
    IOCPServer network;
    g_network = &network;

    if (!network.Start(bus_port, WORKER_THREADS)) {
        printf("Failed to start message bus!\n");
        return 1;
    }

    World world;
    world.AddSystem<NetworkSystem>(network);

    auto& dispatch = world.AddSystemAndGet<MessageDispatchSystem>(network);
    dispatch.RegisterHandler(MsgType::BUS_REGISTER, OnBusRegister);
    dispatch.RegisterHandler(MsgType::BUS_SUBSCRIBE, OnBusSubscribe);
    dispatch.RegisterHandler(MsgType::BUS_UNSUBSCRIBE, OnBusUnsubscribe);
    dispatch.RegisterHandler(MsgType::BUS_PUBLISH, OnBusPublish);

    printf("[Bus] Listening on port %d\n\n", bus_port);

    // ━━━ 메인 루프 ━━━
    auto prev_time = std::chrono::high_resolution_clock::now();

    while (network.IsRunning()) {
        auto now = std::chrono::high_resolution_clock::now();
        float dt = std::chrono::duration<float>(now - prev_time).count();

        if (dt >= TICK_INTERVAL) {
            prev_time = now;
            world.Update(dt);
            ProcessMessageQueue();
        } else {
            auto sleep_ms = static_cast<int>((TICK_INTERVAL - dt) * 1000.0f);
            if (sleep_ms > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
            }
        }
    }

    printf("[Bus] Shutting down...\n");
    g_network = nullptr;
    return 0;
}
