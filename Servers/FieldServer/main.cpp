#include "../../Core/World.h"
#include "../../NetworkEngine/IOCPServer.h"
#include "../../Systems/NetworkSystem.h"
#include "../../Systems/MessageDispatchSystem.h"
#include "../../Systems/InterestSystem.h"
#include "../../Systems/BroadcastSystem.h"
#include "../../Components/NetworkComponents.h"
#include "../../Components/PacketComponents.h"
#include "../../Components/GameComponents.h"
#include "../../Components/SpatialComponents.h"
#include "../../Components/ChannelComponents.h"    // Session 5
#include "../../Components/ZoneComponents.h"       // Session 6
#include "../../Core/Serializer.h"                 // Session 7
#include "../../Components/GhostComponents.h"      // Session 8
#include "../../Systems/GhostSystem.h"             // Session 8
#include "../../Components/LoginComponents.h"      // Session 9
#include "../../Components/TimerComponents.h"      // Session 11
#include "../../Core/EventBus.h"                   // Session 11
#include "../../Core/ConfigLoader.h"               // Session 11
#include "../../Systems/TimerSystem.h"             // Session 11
#include "../../Components/StatsComponents.h"      // Session 12
#include "../../Systems/StatsSystem.h"             // Session 12
#include "../../Components/CombatComponents.h"     // Session 13
#include "../../Systems/CombatSystem.h"            // Session 13
#include "../../Components/MonsterComponents.h"    // Session 14
#include "../../Systems/MonsterAISystem.h"         // Session 14
#include "../../NetworkEngine/TCPClient.h"          // Session 17
#include "../../Components/SkillComponents.h"       // Session 19
#include "../../Components/PartyComponents.h"       // Session 20
#include "../../Components/InstanceComponents.h"    // Session 21
#include "../../Components/MatchComponents.h"       // Session 22
#include "../../Components/InventoryComponents.h"   // Session 23
#include "../../Components/BuffComponents.h"        // Session 24
#include "../../Core/ConditionEngine.h"              // Session 25
#include "../../Components/LootComponents.h"         // Session 27
#include "../../Components/QuestComponents.h"        // Session 28

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <chrono>
#include <thread>
#include <algorithm>

// 서버 설정
constexpr uint16_t SERVER_PORT = 7777;
constexpr int WORKER_THREADS = 2;
constexpr float TICK_RATE = 30.0f;  // 초당 30틱
constexpr float TICK_INTERVAL = 1.0f / TICK_RATE;

// 전역 포인터 (핸들러에서 접근용)
IOCPServer* g_network = nullptr;
EventBus* g_eventBus = nullptr;           // Session 11
ConfigLoader* g_config = nullptr;         // Session 11
int g_total_events_fired = 0;             // Session 11: 이벤트 발행 카운터
constexpr float HEARTBEAT_INTERVAL = 2.0f; // Session 17: Gate 하트비트 주기 (초)

// Session 14: 전방 선언
void SpawnMonsters(World& world);
void SendZoneMonsters(World& world, Entity player_entity);

// ━━━ 메시지 핸들러 ━━━

// ECHO 핸들러: 페이로드를 그대로 돌려줌
void OnEcho(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    auto resp = BuildPacket(MsgType::ECHO, payload, len);
    g_network->SendTo(session.session_id, resp.data(), static_cast<int>(resp.size()));
}

// PING 핸들러: "PONG" 문자열로 응답
void OnPing(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    const char* pong = "PONG";
    auto resp = BuildPacket(MsgType::PING, pong, 4);
    g_network->SendTo(session.session_id, resp.data(), static_cast<int>(resp.size()));
}

// STATS 핸들러: ECS 내부 상태 응답 (테스트/진단용)
void OnStats(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    std::string stats =
        "entity_count=" + std::to_string(world.GetEntityCount()) + "|"
        "has_session_comp=" + std::to_string(
            world.HasComponent<SessionComponent>(entity) ? 1 : 0) + "|"
        "has_recv_comp=" + std::to_string(
            world.HasComponent<RecvBufferComponent>(entity) ? 1 : 0) + "|"
        "has_position_comp=" + std::to_string(
            world.HasComponent<PositionComponent>(entity) ? 1 : 0);

    auto resp = BuildPacket(MsgType::STATS, stats.c_str(), static_cast<int>(stats.size()));
    g_network->SendTo(session.session_id, resp.data(), static_cast<int>(resp.size()));
}

// MOVE 핸들러 (Session 3): 위치 갱신 + dirty 표시
// 페이로드: [x(4 float)] [y(4 float)] [z(4 float)] = 12바이트
void OnMove(World& world, Entity entity, const char* payload, int len) {
    if (len < 12) {
        printf("[Move] Invalid payload size: %d (need 12)\n", len);
        return;
    }

    // PositionComponent가 없으면 붙여줌 (첫 이동 시)
    if (!world.HasComponent<PositionComponent>(entity)) {
        world.AddComponent(entity, PositionComponent{});
    }

    auto& pos = world.GetComponent<PositionComponent>(entity);
    std::memcpy(&pos.x, payload, 4);
    std::memcpy(&pos.y, payload + 4, 4);
    std::memcpy(&pos.z, payload + 8, 4);
    pos.position_dirty = true;  // BroadcastSystem이 이번 틱에 전파할 것

    printf("[Move] Entity %llu -> (%.1f, %.1f, %.1f)\n", entity, pos.x, pos.y, pos.z);
}

// POS_QUERY 핸들러 (Session 3): 내 현재 위치 조회
// 응답: [x(4 float)] [y(4 float)] [z(4 float)]
void OnPosQuery(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    if (!world.HasComponent<PositionComponent>(entity)) {
        // 아직 이동한 적 없음 → (0,0,0) 응답
        PositionComponent zero{};
        char buf[12];
        std::memcpy(buf, &zero.x, 4);
        std::memcpy(buf + 4, &zero.y, 4);
        std::memcpy(buf + 8, &zero.z, 4);
        auto resp = BuildPacket(MsgType::POS_QUERY, buf, 12);
        g_network->SendTo(session.session_id, resp.data(), static_cast<int>(resp.size()));
        return;
    }

    auto& pos = world.GetComponent<PositionComponent>(entity);
    char buf[12];
    std::memcpy(buf, &pos.x, 4);
    std::memcpy(buf + 4, &pos.y, 4);
    std::memcpy(buf + 8, &pos.z, 4);
    auto resp = BuildPacket(MsgType::POS_QUERY, buf, 12);
    g_network->SendTo(session.session_id, resp.data(), static_cast<int>(resp.size()));
}

// CHANNEL_JOIN 핸들러 (Session 5): 채널 입장 또는 채널 변경
// 페이로드: [channel_id(4 int)]
//
// 동작:
//   첫 입장: ChannelComponent 부착 + 근처 같은 채널+존 Entity에게 APPEAR
//   채널 변경: 기존 채널 DISAPPEAR → 새 채널 APPEAR
//   확인: CHANNEL_INFO 응답
void OnChannelJoin(World& world, Entity entity, const char* payload, int len) {
    if (len < 4) {
        printf("[Channel] Invalid payload size: %d (need 4)\n", len);
        return;
    }

    int new_channel;
    std::memcpy(&new_channel, payload, 4);

    auto& session = world.GetComponent<SessionComponent>(entity);
    bool had_channel = world.HasComponent<ChannelComponent>(entity);
    int old_channel = 0;

    if (had_channel) {
        old_channel = world.GetComponent<ChannelComponent>(entity).channel_id;
        if (old_channel == new_channel) {
            // 이미 같은 채널 → 확인만 보냄
            char resp[4];
            std::memcpy(resp, &new_channel, 4);
            auto pkt = BuildPacket(MsgType::CHANNEL_INFO, resp, 4);
            g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
            return;
        }
    }

    bool has_grid = world.HasComponent<GridCellComponent>(entity);
    bool has_pos = world.HasComponent<PositionComponent>(entity);

    // Session 6: 존 정보 (채널 전환 시 같은 존의 Entity만 대상)
    bool has_zone = world.HasComponent<ZoneComponent>(entity);
    int my_zone = 0;
    if (has_zone) {
        my_zone = world.GetComponent<ZoneComponent>(entity).zone_id;
    }

    // ━━━ 1단계: 기존 채널에서 DISAPPEAR (채널 변경 시) ━━━
    if (had_channel && has_grid) {
        auto& grid = world.GetComponent<GridCellComponent>(entity);

        world.ForEach<ChannelComponent, GridCellComponent, SessionComponent>(
            [&](Entity other, ChannelComponent& other_ch, GridCellComponent& other_grid,
                SessionComponent& other_session) {

                if (other == entity) return;
                if (!other_session.connected) return;
                if (other_ch.channel_id != old_channel) return;
                if (!IsNearbyCell(grid.cell_x, grid.cell_y,
                                  other_grid.cell_x, other_grid.cell_y)) return;

                // Session 6: 존 필터
                if (has_zone) {
                    if (!world.HasComponent<ZoneComponent>(other)) return;
                    if (world.GetComponent<ZoneComponent>(other).zone_id != my_zone) return;
                } else if (world.HasComponent<ZoneComponent>(other)) {
                    return;
                }

                // 양방향 DISAPPEAR
                char p[8];
                std::memcpy(p, &entity, 8);
                auto pkt1 = BuildPacket(MsgType::DISAPPEAR, p, 8);
                g_network->SendTo(other_session.session_id,
                                  pkt1.data(), static_cast<int>(pkt1.size()));

                std::memcpy(p, &other, 8);
                auto pkt2 = BuildPacket(MsgType::DISAPPEAR, p, 8);
                g_network->SendTo(session.session_id,
                                  pkt2.data(), static_cast<int>(pkt2.size()));

                printf("[Channel] DISAPPEAR: Entity %llu <-> Entity %llu (ch %d)\n",
                       entity, other, old_channel);
            }
        );
    }

    // ━━━ 2단계: 채널 갱신 ━━━
    if (!had_channel) {
        world.AddComponent(entity, ChannelComponent{new_channel});
    } else {
        world.GetComponent<ChannelComponent>(entity).channel_id = new_channel;
    }

    // ━━━ 3단계: 새 채널에서 APPEAR ━━━
    if (has_grid && has_pos) {
        auto& grid = world.GetComponent<GridCellComponent>(entity);
        auto& pos = world.GetComponent<PositionComponent>(entity);

        world.ForEach<ChannelComponent, GridCellComponent, SessionComponent>(
            [&](Entity other, ChannelComponent& other_ch, GridCellComponent& other_grid,
                SessionComponent& other_session) {

                if (other == entity) return;
                if (!other_session.connected) return;
                if (other_ch.channel_id != new_channel) return;
                if (!IsNearbyCell(grid.cell_x, grid.cell_y,
                                  other_grid.cell_x, other_grid.cell_y)) return;
                if (!world.HasComponent<PositionComponent>(other)) return;

                // Session 6: 존 필터
                if (has_zone) {
                    if (!world.HasComponent<ZoneComponent>(other)) return;
                    if (world.GetComponent<ZoneComponent>(other).zone_id != my_zone) return;
                } else if (world.HasComponent<ZoneComponent>(other)) {
                    return;
                }

                auto& other_pos = world.GetComponent<PositionComponent>(other);

                // 양방향 APPEAR
                char p[20];
                std::memcpy(p, &entity, 8);
                std::memcpy(p + 8, &pos.x, 4);
                std::memcpy(p + 12, &pos.y, 4);
                std::memcpy(p + 16, &pos.z, 4);
                auto pkt1 = BuildPacket(MsgType::APPEAR, p, 20);
                g_network->SendTo(other_session.session_id,
                                  pkt1.data(), static_cast<int>(pkt1.size()));

                std::memcpy(p, &other, 8);
                std::memcpy(p + 8, &other_pos.x, 4);
                std::memcpy(p + 12, &other_pos.y, 4);
                std::memcpy(p + 16, &other_pos.z, 4);
                auto pkt2 = BuildPacket(MsgType::APPEAR, p, 20);
                g_network->SendTo(session.session_id,
                                  pkt2.data(), static_cast<int>(pkt2.size()));

                printf("[Channel] APPEAR: Entity %llu <-> Entity %llu (ch %d)\n",
                       entity, other, new_channel);
            }
        );
    }

    // ━━━ 4단계: 채널 배정 확인 ━━━
    char resp[4];
    std::memcpy(resp, &new_channel, 4);
    auto pkt = BuildPacket(MsgType::CHANNEL_INFO, resp, 4);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Channel] Entity %llu -> Channel %d%s\n",
           entity, new_channel, had_channel ? " (switched)" : " (joined)");
}

// ZONE_ENTER 핸들러 (Session 6): 맵 진입 또는 맵 전환
// 페이로드: [zone_id(4 int)]
//
// 동작:
//   첫 진입: ZoneComponent 부착 + 스폰 포인트 배치
//   맵 전환: 기존 맵 DISAPPEAR → 존 갱신 → 스폰 포인트 → GridCell 재설정
//   확인: ZONE_INFO 응답
//   다음 틱에서 InterestSystem이 새 맵 이웃에게 APPEAR 전송
void OnZoneEnter(World& world, Entity entity, const char* payload, int len) {
    if (len < 4) {
        printf("[Zone] Invalid payload size: %d (need 4)\n", len);
        return;
    }

    int new_zone;
    std::memcpy(&new_zone, payload, 4);

    auto& session = world.GetComponent<SessionComponent>(entity);
    bool had_zone = world.HasComponent<ZoneComponent>(entity);
    int old_zone = 0;

    if (had_zone) {
        old_zone = world.GetComponent<ZoneComponent>(entity).zone_id;
        if (old_zone == new_zone) {
            // 이미 같은 맵 → 확인만 보냄
            char resp[4];
            std::memcpy(resp, &new_zone, 4);
            auto pkt = BuildPacket(MsgType::ZONE_INFO, resp, 4);
            g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
            return;
        }
    }

    bool has_grid = world.HasComponent<GridCellComponent>(entity);
    bool has_channel = world.HasComponent<ChannelComponent>(entity);
    int ch_id = 0;
    if (has_channel) {
        ch_id = world.GetComponent<ChannelComponent>(entity).channel_id;
    }

    // ━━━ 1단계: 기존 맵에서 DISAPPEAR (맵 전환 시) ━━━
    if (had_zone && has_grid) {
        auto& grid = world.GetComponent<GridCellComponent>(entity);

        world.ForEach<ZoneComponent, GridCellComponent, SessionComponent>(
            [&](Entity other, ZoneComponent& other_zone, GridCellComponent& other_grid,
                SessionComponent& other_session) {

                if (other == entity) return;
                if (!other_session.connected) return;
                if (other_zone.zone_id != old_zone) return;
                if (!IsNearbyCell(grid.cell_x, grid.cell_y,
                                  other_grid.cell_x, other_grid.cell_y)) return;

                // 채널 필터: 채널이 있으면 같은 채널만
                if (has_channel) {
                    if (!world.HasComponent<ChannelComponent>(other)) return;
                    if (world.GetComponent<ChannelComponent>(other).channel_id != ch_id) return;
                } else if (world.HasComponent<ChannelComponent>(other)) {
                    return;
                }

                // 양방향 DISAPPEAR
                char p[8];
                std::memcpy(p, &entity, 8);
                auto pkt1 = BuildPacket(MsgType::DISAPPEAR, p, 8);
                g_network->SendTo(other_session.session_id,
                                  pkt1.data(), static_cast<int>(pkt1.size()));

                std::memcpy(p, &other, 8);
                auto pkt2 = BuildPacket(MsgType::DISAPPEAR, p, 8);
                g_network->SendTo(session.session_id,
                                  pkt2.data(), static_cast<int>(pkt2.size()));

                printf("[Zone] DISAPPEAR: Entity %llu <-> Entity %llu (zone %d)\n",
                       entity, other, old_zone);
            }
        );
    }

    // ━━━ 2단계: 존 갱신 ━━━
    if (!had_zone) {
        world.AddComponent(entity, ZoneComponent{new_zone});
    } else {
        world.GetComponent<ZoneComponent>(entity).zone_id = new_zone;
    }

    // ━━━ 3단계: 스폰 포인트로 위치 이동 ━━━
    SpawnPoint spawn = GetSpawnPoint(new_zone);

    if (!world.HasComponent<PositionComponent>(entity)) {
        world.AddComponent(entity, PositionComponent{});
    }
    auto& pos = world.GetComponent<PositionComponent>(entity);
    pos.x = spawn.x;
    pos.y = spawn.y;
    pos.z = spawn.z;
    pos.position_dirty = true;  // InterestSystem이 다음 틱에 처리

    // ━━━ 4단계: GridCellComponent 재설정 ━━━
    // 제거 후 InterestSystem이 first_time으로 재배치 → 새 맵 이웃에게 APPEAR
    if (world.HasComponent<GridCellComponent>(entity)) {
        world.RemoveComponent<GridCellComponent>(entity);
    }

    // ━━━ 5단계: 맵 배정 확인 ━━━
    char resp[4];
    std::memcpy(resp, &new_zone, 4);
    auto pkt = BuildPacket(MsgType::ZONE_INFO, resp, 4);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Zone] Entity %llu -> Zone %d (spawn: %.0f, %.0f)%s\n",
           entity, new_zone, spawn.x, spawn.y,
           had_zone ? " (transfer)" : " (enter)");
}

// ━━━ Session 16: Zone Transfer 핸들러 ━━━
// ZONE_TRANSFER_REQ: 존 전환 요청
// 페이로드: [target_zone_id(4 int)]
// 응답: ZONE_TRANSFER_RESULT [result(1) zone_id(4) x(4) y(4) z(4)]
//   result: 0=성공, 1=존재하지 않는 맵, 2=이미 같은 맵
void OnZoneTransfer(World& world, Entity entity, const char* payload, int len) {
    if (len < 4) {
        printf("[ZoneTransfer] Invalid payload size: %d (need 4)\n", len);
        return;
    }

    int target_zone;
    std::memcpy(&target_zone, payload, 4);

    auto& session = world.GetComponent<SessionComponent>(entity);

    // 유효한 맵인지 확인 (1~3)
    if (target_zone < 1 || target_zone > 3) {
        char resp[17];
        resp[0] = 1;  // 존재하지 않는 맵
        std::memcpy(resp + 1, &target_zone, 4);
        float zero = 0.0f;
        std::memcpy(resp + 5, &zero, 4);
        std::memcpy(resp + 9, &zero, 4);
        std::memcpy(resp + 13, &zero, 4);
        auto pkt = BuildPacket(MsgType::ZONE_TRANSFER_RESULT, resp, 17);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        printf("[ZoneTransfer] Entity %llu: invalid zone %d\n", entity, target_zone);
        return;
    }

    // 현재 존 확인
    bool had_zone = world.HasComponent<ZoneComponent>(entity);
    int old_zone = had_zone ? world.GetComponent<ZoneComponent>(entity).zone_id : 0;

    // 같은 맵 체크
    if (had_zone && old_zone == target_zone) {
        SpawnPoint sp = GetSpawnPoint(target_zone);
        char resp[17];
        resp[0] = 2;  // 이미 같은 맵
        std::memcpy(resp + 1, &target_zone, 4);
        std::memcpy(resp + 5, &sp.x, 4);
        std::memcpy(resp + 9, &sp.y, 4);
        std::memcpy(resp + 13, &sp.z, 4);
        auto pkt = BuildPacket(MsgType::ZONE_TRANSFER_RESULT, resp, 17);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        printf("[ZoneTransfer] Entity %llu: already in zone %d\n", entity, target_zone);
        return;
    }

    bool has_grid = world.HasComponent<GridCellComponent>(entity);
    bool has_channel = world.HasComponent<ChannelComponent>(entity);
    int ch_id = has_channel ? world.GetComponent<ChannelComponent>(entity).channel_id : 0;

    // 1단계: 기존 맵에서 DISAPPEAR
    if (had_zone && has_grid) {
        auto& grid = world.GetComponent<GridCellComponent>(entity);

        world.ForEach<ZoneComponent, GridCellComponent, SessionComponent>(
            [&](Entity other, ZoneComponent& other_zone, GridCellComponent& other_grid,
                SessionComponent& other_session) {

                if (other == entity) return;
                if (!other_session.connected) return;
                if (other_zone.zone_id != old_zone) return;
                if (!IsNearbyCell(grid.cell_x, grid.cell_y,
                                  other_grid.cell_x, other_grid.cell_y)) return;

                if (has_channel) {
                    if (!world.HasComponent<ChannelComponent>(other)) return;
                    if (world.GetComponent<ChannelComponent>(other).channel_id != ch_id) return;
                } else if (world.HasComponent<ChannelComponent>(other)) {
                    return;
                }

                // 양방향 DISAPPEAR
                char p[8];
                std::memcpy(p, &entity, 8);
                auto pkt1 = BuildPacket(MsgType::DISAPPEAR, p, 8);
                g_network->SendTo(other_session.session_id,
                                  pkt1.data(), static_cast<int>(pkt1.size()));

                std::memcpy(p, &other, 8);
                auto pkt2 = BuildPacket(MsgType::DISAPPEAR, p, 8);
                g_network->SendTo(session.session_id,
                                  pkt2.data(), static_cast<int>(pkt2.size()));
            }
        );
    }

    // 2단계: 존 갱신
    if (!had_zone) {
        world.AddComponent(entity, ZoneComponent{target_zone});
    } else {
        world.GetComponent<ZoneComponent>(entity).zone_id = target_zone;
    }

    // 3단계: 스폰 포인트로 위치 이동
    SpawnPoint spawn = GetSpawnPoint(target_zone);
    if (!world.HasComponent<PositionComponent>(entity)) {
        world.AddComponent(entity, PositionComponent{});
    }
    auto& pos = world.GetComponent<PositionComponent>(entity);
    pos.x = spawn.x;
    pos.y = spawn.y;
    pos.z = spawn.z;
    pos.position_dirty = true;

    // 4단계: GridCellComponent 재설정 (InterestSystem이 다음 틱에 재배치)
    if (world.HasComponent<GridCellComponent>(entity)) {
        world.RemoveComponent<GridCellComponent>(entity);
    }

    // 5단계: ZONE_TRANSFER_RESULT 전송 (성공)
    char resp[17];
    resp[0] = 0;  // 성공
    std::memcpy(resp + 1, &target_zone, 4);
    std::memcpy(resp + 5, &spawn.x, 4);
    std::memcpy(resp + 9, &spawn.y, 4);
    std::memcpy(resp + 13, &spawn.z, 4);
    auto pkt = BuildPacket(MsgType::ZONE_TRANSFER_RESULT, resp, 17);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    // 6단계: 새 존의 몬스터 정보 전송
    SendZoneMonsters(world, entity);

    printf("[ZoneTransfer] Entity %llu: zone %d -> %d (spawn: %.0f, %.0f)\n",
           entity, old_zone, target_zone, spawn.x, spawn.y);
}

// HANDOFF_REQUEST 핸들러 (Session 7): 핸드오프 요청
// 빈 페이로드 또는 무시
//
// 동작:
//   1. Entity 상태 직렬화 → HANDOFF_DATA 전송
//   2. 이웃에게 DISAPPEAR
//   3. 게임 Component 제거 (서버에서 "떠남" 처리)
void OnHandoffRequest(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    // 1단계: Entity 상태 직렬화
    auto serialized = SerializeEntity(world, entity);

    // 2단계: HANDOFF_DATA 전송
    auto data_pkt = BuildPacket(MsgType::HANDOFF_DATA, serialized);
    g_network->SendTo(session.session_id, data_pkt.data(), static_cast<int>(data_pkt.size()));

    // 3단계: 이웃에게 DISAPPEAR
    bool has_grid = world.HasComponent<GridCellComponent>(entity);
    bool has_zone = world.HasComponent<ZoneComponent>(entity);
    bool has_channel = world.HasComponent<ChannelComponent>(entity);
    int zone_id = has_zone ? world.GetComponent<ZoneComponent>(entity).zone_id : 0;
    int ch_id = has_channel ? world.GetComponent<ChannelComponent>(entity).channel_id : 0;

    if (has_grid) {
        auto& grid = world.GetComponent<GridCellComponent>(entity);

        world.ForEach<SessionComponent, GridCellComponent>(
            [&](Entity other, SessionComponent& other_session, GridCellComponent& other_grid) {
                if (other == entity) return;
                if (!other_session.connected) return;
                if (!IsNearbyCell(grid.cell_x, grid.cell_y,
                                  other_grid.cell_x, other_grid.cell_y)) return;

                // 존 필터
                if (has_zone || world.HasComponent<ZoneComponent>(other)) {
                    if (!has_zone || !world.HasComponent<ZoneComponent>(other)) return;
                    if (world.GetComponent<ZoneComponent>(other).zone_id != zone_id) return;
                }

                // 채널 필터
                if (has_channel || world.HasComponent<ChannelComponent>(other)) {
                    if (!has_channel || !world.HasComponent<ChannelComponent>(other)) return;
                    if (world.GetComponent<ChannelComponent>(other).channel_id != ch_id) return;
                }

                char p[8];
                std::memcpy(p, &entity, 8);
                auto pkt = BuildPacket(MsgType::DISAPPEAR, p, 8);
                g_network->SendTo(other_session.session_id,
                                  pkt.data(), static_cast<int>(pkt.size()));
            }
        );
    }

    // 4단계: 게임 상태 Component 제거
    if (world.HasComponent<PositionComponent>(entity))
        world.RemoveComponent<PositionComponent>(entity);
    if (world.HasComponent<ZoneComponent>(entity))
        world.RemoveComponent<ZoneComponent>(entity);
    if (world.HasComponent<ChannelComponent>(entity))
        world.RemoveComponent<ChannelComponent>(entity);
    if (world.HasComponent<GridCellComponent>(entity))
        world.RemoveComponent<GridCellComponent>(entity);

    printf("[Handoff] Entity %llu -> HANDOFF_DATA sent (%d bytes)\n",
           entity, static_cast<int>(serialized.size()));
}

// HANDOFF_RESTORE 핸들러 (Session 7): 직렬화 데이터로 Entity 복원
// 페이로드: [직렬화된 바이트 (SerializeEntity 출력)]
//
// 동작:
//   1. 역직렬화로 Component 복원 (position_dirty=true 포함)
//   2. HANDOFF_RESULT 응답 [zone(4) ch(4) x(4) y(4) z(4)]
//   3. 다음 틱에서 InterestSystem이 APPEAR 처리 (GridCellComponent 없음 → first_time)
void OnHandoffRestore(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    // 1단계: 역직렬화 (Component 복원)
    DeserializeEntity(world, entity, payload, len);

    // 2단계: HANDOFF_RESULT 응답
    char result[20];
    int zone_id = 0, channel_id = 0;
    float x = 0, y = 0, z = 0;

    if (world.HasComponent<ZoneComponent>(entity))
        zone_id = world.GetComponent<ZoneComponent>(entity).zone_id;
    if (world.HasComponent<ChannelComponent>(entity))
        channel_id = world.GetComponent<ChannelComponent>(entity).channel_id;
    if (world.HasComponent<PositionComponent>(entity)) {
        auto& pos = world.GetComponent<PositionComponent>(entity);
        x = pos.x; y = pos.y; z = pos.z;
    }

    std::memcpy(result, &zone_id, 4);
    std::memcpy(result + 4, &channel_id, 4);
    std::memcpy(result + 8, &x, 4);
    std::memcpy(result + 12, &y, 4);
    std::memcpy(result + 16, &z, 4);

    auto pkt = BuildPacket(MsgType::HANDOFF_RESULT, result, 20);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Handoff] Entity %llu -> restored (zone=%d, ch=%d, pos=%.1f,%.1f,%.1f)\n",
           entity, zone_id, channel_id, x, y, z);
}

// ━━━ Session 9: Login + Character Select 핸들러 ━━━

// LOGIN 핸들러: ID/PW 인증
// 페이로드: [username_len(1)] [username(N)] [pw_len(1)] [pw(N)]
// 응답: LOGIN_RESULT [result(1 byte: 0=성공, 1=계정없음, 2=비번틀림)] [account_id(4)]
void OnLogin(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    // 이미 로그인된 상태면 무시
    if (world.HasComponent<LoginComponent>(entity)) {
        auto& login = world.GetComponent<LoginComponent>(entity);
        if (login.state >= LoginState::AUTHENTICATED) {
            char resp[5] = {};
            resp[0] = 0;  // 이미 성공
            std::memcpy(resp + 1, &login.account_id, 4);
            auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
            g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
            return;
        }
    }

    // 페이로드 파싱
    if (len < 2) {
        char resp[5] = {};
        resp[0] = 3;  // 잘못된 패킷
        auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    int offset = 0;
    uint8_t uname_len = static_cast<uint8_t>(payload[offset++]);
    if (offset + uname_len > len) {
        char resp[5] = {};
        resp[0] = 3;
        auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }
    std::string username(payload + offset, uname_len);
    offset += uname_len;

    if (offset >= len) {
        char resp[5] = {};
        resp[0] = 3;
        auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    uint8_t pw_len = static_cast<uint8_t>(payload[offset++]);
    if (offset + pw_len > len) {
        char resp[5] = {};
        resp[0] = 3;
        auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }
    std::string password(payload + offset, pw_len);

    // 계정 DB 조회
    auto& db = GetAccountDB();
    auto it = db.find(username);

    if (it == db.end()) {
        // Session 15: Auto-registration (봇/테스트 계정 자동 생성)
        static uint32_t next_auto_id = 2000;
        AccountData newAcc;
        newAcc.account_id = next_auto_id++;
        newAcc.username = username;
        newAcc.password = password;
        CharacterInfo c;
        c.char_id = newAcc.account_id;
        std::snprintf(c.name, 31, "Bot_%s", username.c_str());
        c.level = 10;
        c.job_class = 0;  // Warrior
        c.zone_id = 1;
        c.x = 100.0f + static_cast<float>(rand() % 400);
        c.y = 100.0f + static_cast<float>(rand() % 400);
        c.z = 0.0f;
        newAcc.characters.push_back(c);
        db[username] = newAcc;
        it = db.find(username);
        printf("[Login] Auto-register: '%s' (id=%u, pos=%.0f,%.0f)\n",
               username.c_str(), newAcc.account_id, c.x, c.y);
    }

    if (it->second.password != password) {
        // 비밀번호 틀림
        char resp[5] = {};
        resp[0] = 2;  // 비번 틀림
        auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        printf("[Login] FAIL: wrong password for '%s'\n", username.c_str());
        return;
    }

    // 로그인 성공
    LoginComponent login;
    login.state = LoginState::AUTHENTICATED;
    login.account_id = it->second.account_id;
    std::strncpy(login.username, username.c_str(), 31);

    if (!world.HasComponent<LoginComponent>(entity)) {
        world.AddComponent(entity, login);
    } else {
        world.GetComponent<LoginComponent>(entity) = login;
    }

    char resp[5] = {};
    resp[0] = 0;  // 성공
    std::memcpy(resp + 1, &login.account_id, 4);
    auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Login] OK: '%s' (account_id=%u, entity=%llu)\n",
           username.c_str(), login.account_id, entity);
}

// CHAR_LIST_REQ 핸들러: 캐릭터 목록 조회
// 응답: CHAR_LIST_RESP [count(1)] {char_id(4) name(32) level(4) job(4)}...
void OnCharListReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    // 로그인 상태 확인
    if (!world.HasComponent<LoginComponent>(entity) ||
        world.GetComponent<LoginComponent>(entity).state < LoginState::AUTHENTICATED) {
        // 로그인 안 됨 → 빈 목록
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::CHAR_LIST_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& login = world.GetComponent<LoginComponent>(entity);
    std::string uname(login.username);

    auto& db = GetAccountDB();
    auto it = db.find(uname);
    if (it == db.end()) {
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::CHAR_LIST_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& chars = it->second.characters;
    uint8_t count = static_cast<uint8_t>(chars.size());

    // 페이로드: count(1) + count * (id(4) + name(32) + level(4) + job(4)) = 1 + count*44
    int payload_size = 1 + count * 44;
    std::vector<char> resp(payload_size, 0);
    resp[0] = static_cast<char>(count);

    int off = 1;
    for (auto& c : chars) {
        std::memcpy(resp.data() + off, &c.char_id, 4);    off += 4;
        std::memcpy(resp.data() + off, c.name, 32);        off += 32;
        std::memcpy(resp.data() + off, &c.level, 4);       off += 4;
        std::memcpy(resp.data() + off, &c.job_class, 4);   off += 4;
    }

    auto pkt = BuildPacket(MsgType::CHAR_LIST_RESP, resp.data(), payload_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[CharList] Entity %llu: %d characters\n", entity, count);
}

// CHAR_SELECT 핸들러: 캐릭터 선택 → 게임 진입
// 페이로드: [char_id(4)]
// 응답: ENTER_GAME [result(1: 0=성공, 1=로그인안됨, 2=캐릭터없음)] [entity(8)] [zone(4)] [x(4)] [y(4)] [z(4)]
void OnCharSelect(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    auto send_fail = [&](uint8_t code) {
        char resp[25] = {};
        resp[0] = code;
        auto pkt = BuildPacket(MsgType::ENTER_GAME, resp, 25);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
    };

    // 로그인 상태 확인
    if (!world.HasComponent<LoginComponent>(entity) ||
        world.GetComponent<LoginComponent>(entity).state < LoginState::AUTHENTICATED) {
        send_fail(1);  // 로그인 안 됨
        return;
    }

    if (len < 4) {
        send_fail(2);
        return;
    }

    uint32_t char_id;
    std::memcpy(&char_id, payload, 4);

    auto& login = world.GetComponent<LoginComponent>(entity);
    std::string uname(login.username);

    auto& db = GetAccountDB();
    auto it = db.find(uname);
    if (it == db.end()) {
        send_fail(2);
        return;
    }

    // 캐릭터 찾기
    CharacterInfo* found = nullptr;
    for (auto& c : it->second.characters) {
        if (c.char_id == char_id) {
            found = &c;
            break;
        }
    }

    if (!found) {
        send_fail(2);  // 캐릭터 없음
        printf("[CharSelect] Entity %llu: char_id=%u not found\n", entity, char_id);
        return;
    }

    // 게임 진입: Component 부착
    login.state = LoginState::IN_GAME;

    // Stats (Session 12)
    auto job = static_cast<JobClass>(found->job_class);
    auto stats = CreateStats(job, found->level);
    if (!world.HasComponent<StatsComponent>(entity)) {
        world.AddComponent(entity, stats);
    } else {
        world.GetComponent<StatsComponent>(entity) = stats;
    }

    // Combat (Session 13)
    if (!world.HasComponent<CombatComponent>(entity)) {
        world.AddComponent(entity, CombatComponent{});
    }

    // Position
    if (!world.HasComponent<PositionComponent>(entity)) {
        world.AddComponent(entity, PositionComponent{});
    }
    auto& pos = world.GetComponent<PositionComponent>(entity);
    pos.x = found->x;
    pos.y = found->y;
    pos.z = found->z;
    pos.position_dirty = true;

    // Zone
    if (!world.HasComponent<ZoneComponent>(entity)) {
        world.AddComponent(entity, ZoneComponent{found->zone_id});
    } else {
        world.GetComponent<ZoneComponent>(entity).zone_id = found->zone_id;
    }

    // GridCell 제거 → InterestSystem이 다음 틱에 first_time 처리
    if (world.HasComponent<GridCellComponent>(entity)) {
        world.RemoveComponent<GridCellComponent>(entity);
    }

    // ENTER_GAME 응답
    char resp[25] = {};
    resp[0] = 0;  // 성공
    std::memcpy(resp + 1, &entity, 8);
    int32_t zone = found->zone_id;
    std::memcpy(resp + 9, &zone, 4);
    std::memcpy(resp + 13, &found->x, 4);
    std::memcpy(resp + 17, &found->y, 4);
    std::memcpy(resp + 21, &found->z, 4);

    auto pkt = BuildPacket(MsgType::ENTER_GAME, resp, 25);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[CharSelect] Entity %llu: selected char '%s' (id=%u, zone=%d, pos=%.0f,%.0f)\n",
           entity, found->name, char_id, found->zone_id, found->x, found->y);

    // Session 14: 같은 존의 몬스터 정보 전송
    SendZoneMonsters(world, entity);
}

// GHOST_QUERY 핸들러 (Session 8): Ghost 수 조회
// 응답: [ghost_count(4 int)]
void OnGhostQuery(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    int32_t ghost_count = 0;
    world.ForEach<GhostComponent>([&](Entity g, GhostComponent& gc) {
        ghost_count++;
    });

    char resp[4];
    std::memcpy(resp, &ghost_count, 4);
    auto pkt = BuildPacket(MsgType::GHOST_INFO, resp, 4);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// ━━━ Session 12: Stats System 핸들러 ━━━

// 스탯 동기화 패킷 전송 헬퍼
void SendStatSync(World& world, Entity entity) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (!world.HasComponent<StatsComponent>(entity)) return;
    auto& stats = world.GetComponent<StatsComponent>(entity);

    // STAT_SYNC: level(4) hp(4) max_hp(4) mp(4) max_mp(4) atk(4) def(4) exp(4) exp_next(4) = 36바이트
    char buf[36];
    std::memcpy(buf,      &stats.level, 4);
    std::memcpy(buf + 4,  &stats.hp, 4);
    std::memcpy(buf + 8,  &stats.max_hp, 4);
    std::memcpy(buf + 12, &stats.mp, 4);
    std::memcpy(buf + 16, &stats.max_mp, 4);
    std::memcpy(buf + 20, &stats.attack, 4);
    std::memcpy(buf + 24, &stats.defense, 4);
    std::memcpy(buf + 28, &stats.exp, 4);
    std::memcpy(buf + 32, &stats.exp_to_next, 4);
    auto pkt = BuildPacket(MsgType::STAT_SYNC, buf, 36);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
    stats.stats_dirty = false;
}

// STAT_QUERY: 내 스탯 조회 (빈 페이로드)
void OnStatQuery(World& world, Entity entity, const char* payload, int len) {
    if (!world.HasComponent<StatsComponent>(entity)) {
        // StatsComponent가 없으면 → 로그인 상태에 따라 자동 부착
        if (world.HasComponent<LoginComponent>(entity)) {
            auto& login = world.GetComponent<LoginComponent>(entity);
            if (login.state >= LoginState::IN_GAME) {
                // 계정DB에서 직업/레벨 가져오기
                std::string uname(login.username);
                auto& db = GetAccountDB();
                auto it = db.find(uname);
                JobClass job = JobClass::WARRIOR;
                int32_t level = 1;
                if (it != db.end() && !it->second.characters.empty()) {
                    auto& c = it->second.characters[0];
                    job = static_cast<JobClass>(c.job_class);
                    level = c.level;
                }
                world.AddComponent(entity, CreateStats(job, level));
            }
        }
    }
    SendStatSync(world, entity);
}

// STAT_ADD_EXP: EXP 추가 (테스트용)
// 페이로드: [exp_amount(4 int)]
void OnStatAddExp(World& world, Entity entity, const char* payload, int len) {
    if (len < 4) return;
    if (!world.HasComponent<StatsComponent>(entity)) return;

    int32_t amount;
    std::memcpy(&amount, payload, 4);

    auto& stats = world.GetComponent<StatsComponent>(entity);
    int old_level = stats.level;
    bool leveled = stats.AddExp(amount);

    if (leveled) {
        printf("[Stats] Entity %llu: LEVEL UP %d -> %d\n", entity, old_level, stats.level);
        // EventBus에 이벤트 발행 (미래 시스템용)
        if (g_eventBus) {
            Event evt;
            evt.type = EventType::CUSTOM_1;  // LEVEL_UP 용도
            evt.source = entity;
            evt.param1 = old_level;
            evt.param2 = stats.level;
            g_eventBus->Publish(evt);
        }
    }

    SendStatSync(world, entity);
    printf("[Stats] Entity %llu: +%d EXP (total %d/%d, lv%d)\n",
           entity, amount, stats.exp, stats.exp_to_next, stats.level);
}

// STAT_TAKE_DMG: 데미지 받기 (테스트용)
// 페이로드: [raw_damage(4 int)]
void OnStatTakeDmg(World& world, Entity entity, const char* payload, int len) {
    if (len < 4) return;
    if (!world.HasComponent<StatsComponent>(entity)) return;

    int32_t raw_damage;
    std::memcpy(&raw_damage, payload, 4);

    auto& stats = world.GetComponent<StatsComponent>(entity);
    int actual = stats.TakeDamage(raw_damage);

    printf("[Stats] Entity %llu: took %d damage (raw %d), HP=%d/%d\n",
           entity, actual, raw_damage, stats.hp, stats.max_hp);

    if (!stats.IsAlive()) {
        printf("[Stats] Entity %llu: DIED!\n", entity);
        if (g_eventBus) {
            Event evt;
            evt.type = EventType::ENTITY_DIED;
            evt.source = entity;
            g_eventBus->Publish(evt);
        }
    }

    SendStatSync(world, entity);
}

// STAT_HEAL: 힐 (테스트용)
// 페이로드: [heal_amount(4 int)]
void OnStatHeal(World& world, Entity entity, const char* payload, int len) {
    if (len < 4) return;
    if (!world.HasComponent<StatsComponent>(entity)) return;

    int32_t heal_amount;
    std::memcpy(&heal_amount, payload, 4);

    auto& stats = world.GetComponent<StatsComponent>(entity);
    int actual = stats.Heal(heal_amount);

    printf("[Stats] Entity %llu: healed %d (requested %d), HP=%d/%d\n",
           entity, actual, heal_amount, stats.hp, stats.max_hp);

    SendStatSync(world, entity);
}

// ━━━ Session 14: Monster Spawning ━━━

void SpawnMonsters(World& world) {
    for (int i = 0; i < MONSTER_SPAWN_COUNT; i++) {
        auto& spawn = MONSTER_SPAWNS[i];
        Entity e = world.CreateEntity();

        MonsterComponent mc{};
        mc.monster_id = spawn.monster_id;
        std::strncpy(mc.name, spawn.name, 31);
        mc.state = MonsterState::IDLE;
        mc.spawn_x = spawn.x;
        mc.spawn_y = spawn.y;
        mc.spawn_z = spawn.z;
        mc.aggro_range = spawn.aggro_range;
        mc.respawn_time = spawn.respawn_time;
        mc.target_entity = 0;
        mc.loot_table_id = spawn.loot_table_id;
        world.AddComponent(e, mc);

        StatsComponent stats = CreateMonsterStats(spawn.level, spawn.hp, spawn.attack, spawn.defense);
        world.AddComponent(e, stats);

        CombatComponent combat;
        combat.attack_range = 200.0f;
        combat.attack_cooldown = 2.0f;
        world.AddComponent(e, combat);

        PositionComponent pos;
        pos.x = spawn.x;
        pos.y = spawn.y;
        pos.z = spawn.z;
        world.AddComponent(e, pos);

        world.AddComponent(e, ZoneComponent{spawn.zone_id});

        printf("[Spawn] Monster '%s' (id=%u, lv%d) at (%.0f, %.0f) zone %d -> Entity %llu\n",
               spawn.name, spawn.monster_id, spawn.level, spawn.x, spawn.y, spawn.zone_id, e);
    }
}

void SendZoneMonsters(World& world, Entity player_entity) {
    if (!world.HasComponent<SessionComponent>(player_entity)) return;
    if (!world.HasComponent<ZoneComponent>(player_entity)) return;

    auto& session = world.GetComponent<SessionComponent>(player_entity);
    int player_zone = world.GetComponent<ZoneComponent>(player_entity).zone_id;

    world.ForEach<MonsterComponent, StatsComponent, PositionComponent>(
        [&](Entity monster, MonsterComponent& mc, StatsComponent& ms,
            PositionComponent& mp) {
            if (!world.HasComponent<ZoneComponent>(monster)) return;
            if (world.GetComponent<ZoneComponent>(monster).zone_id != player_zone) return;
            if (mc.state == MonsterState::DEAD) return;

            // MONSTER_SPAWN: entity(8) monster_id(4) level(4) hp(4) max_hp(4) x(4) y(4) z(4)
            char buf[36];
            std::memcpy(buf, &monster, 8);
            std::memcpy(buf + 8, &mc.monster_id, 4);
            std::memcpy(buf + 12, &ms.level, 4);
            std::memcpy(buf + 16, &ms.hp, 4);
            std::memcpy(buf + 20, &ms.max_hp, 4);
            std::memcpy(buf + 24, &mp.x, 4);
            std::memcpy(buf + 28, &mp.y, 4);
            std::memcpy(buf + 32, &mp.z, 4);
            auto pkt = BuildPacket(MsgType::MONSTER_SPAWN, buf, 36);
            g_network->SendTo(session.session_id,
                              pkt.data(), static_cast<int>(pkt.size()));
        }
    );
}

// ━━━ Session 27: 루트 드롭 헬퍼 ━━━

// 몬스터 처치 시 루트 드롭 → LOOT_RESULT 패킷 전송
void ProcessMonsterLoot(World& world, Entity killer, Entity monster) {
    if (!world.HasComponent<MonsterComponent>(monster)) return;
    if (!world.HasComponent<SessionComponent>(killer)) return;

    auto& mc = world.GetComponent<MonsterComponent>(monster);
    if (mc.loot_table_id <= 0) return;

    const LootTable* table = FindLootTable(mc.loot_table_id);
    if (!table) return;

    auto loot = RollLoot(*table);
    if (loot.empty()) return;

    // LOOT_RESULT: count(1) + N * {item_id(4) + count(2)}
    uint8_t count = static_cast<uint8_t>(loot.size());
    int payload_size = 1 + count * 6;
    std::vector<char> buf(payload_size, 0);
    buf[0] = count;
    for (int i = 0; i < count; i++) {
        std::memcpy(buf.data() + 1 + i * 6, &loot[i].item_id, 4);
        std::memcpy(buf.data() + 1 + i * 6 + 4, &loot[i].count, 2);
    }

    auto pkt = BuildPacket(MsgType::LOOT_RESULT, buf.data(), payload_size);
    auto& session = world.GetComponent<SessionComponent>(killer);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Loot] Entity %llu killed monster '%s': %d items dropped\n",
           killer, mc.name, count);
}

// ━━━ Session 13: Combat System 핸들러 ━━━

// 공격 결과 전송 헬퍼
void SendAttackResult(World& world, Entity attacker, Entity target,
                      AttackResult result, int32_t damage,
                      int32_t target_hp, int32_t target_max_hp) {
    auto& session = world.GetComponent<SessionComponent>(attacker);
    char buf[29];
    buf[0] = static_cast<uint8_t>(result);
    std::memcpy(buf + 1, &attacker, 8);
    std::memcpy(buf + 9, &target, 8);
    std::memcpy(buf + 17, &damage, 4);
    std::memcpy(buf + 21, &target_hp, 4);
    std::memcpy(buf + 25, &target_max_hp, 4);
    auto pkt = BuildPacket(MsgType::ATTACK_RESULT, buf, 29);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// ATTACK_REQ 핸들러: 타겟 공격
// 페이로드: [target_entity(8)]
void OnAttackReq(World& world, Entity entity, const char* payload, int len) {
    if (len < 8) return;

    Entity target;
    std::memcpy(&target, payload, 8);

    // 자기 자신 공격 불가
    if (target == entity) {
        SendAttackResult(world, entity, target, AttackResult::SELF_ATTACK, 0, 0, 0);
        return;
    }

    // CombatComponent 자동 부착
    if (!world.HasComponent<CombatComponent>(entity)) {
        world.AddComponent(entity, CombatComponent{});
    }
    auto& combat = world.GetComponent<CombatComponent>(entity);

    // 공격자 상태 확인
    if (!world.HasComponent<StatsComponent>(entity)) {
        SendAttackResult(world, entity, target, AttackResult::ATTACKER_DEAD, 0, 0, 0);
        return;
    }
    auto& atk_stats = world.GetComponent<StatsComponent>(entity);
    if (!atk_stats.IsAlive()) {
        SendAttackResult(world, entity, target, AttackResult::ATTACKER_DEAD, 0, 0, 0);
        return;
    }

    // 타겟 존재 확인 (플레이어 또는 몬스터)
    bool target_is_player = world.HasComponent<SessionComponent>(target);
    bool target_is_monster = world.HasComponent<MonsterComponent>(target);
    if ((!target_is_player && !target_is_monster) ||
        !world.HasComponent<StatsComponent>(target)) {
        SendAttackResult(world, entity, target, AttackResult::TARGET_NOT_FOUND, 0, 0, 0);
        return;
    }
    auto& tgt_stats = world.GetComponent<StatsComponent>(target);

    // 타겟 사망 확인
    if (!tgt_stats.IsAlive()) {
        SendAttackResult(world, entity, target, AttackResult::TARGET_DEAD, 0, 0, 0);
        return;
    }

    // 사거리 확인
    if (world.HasComponent<PositionComponent>(entity) &&
        world.HasComponent<PositionComponent>(target)) {
        auto& atk_pos = world.GetComponent<PositionComponent>(entity);
        auto& tgt_pos = world.GetComponent<PositionComponent>(target);

        float dist = DistanceBetween(atk_pos, tgt_pos);
        if (dist > combat.attack_range) {
            SendAttackResult(world, entity, target, AttackResult::OUT_OF_RANGE,
                             0, tgt_stats.hp, tgt_stats.max_hp);
            return;
        }
    }

    // 존 확인 (같은 존에서만 공격 가능)
    if (world.HasComponent<ZoneComponent>(entity) &&
        world.HasComponent<ZoneComponent>(target)) {
        if (world.GetComponent<ZoneComponent>(entity).zone_id !=
            world.GetComponent<ZoneComponent>(target).zone_id) {
            SendAttackResult(world, entity, target, AttackResult::OUT_OF_RANGE,
                             0, tgt_stats.hp, tgt_stats.max_hp);
            return;
        }
    }

    // 쿨타임 확인
    if (combat.cooldown_remaining > 0) {
        SendAttackResult(world, entity, target, AttackResult::COOLDOWN_NOT_READY,
                         0, tgt_stats.hp, tgt_stats.max_hp);
        return;
    }

    // ━━━ 전투 실행 ━━━
    int32_t damage = tgt_stats.TakeDamage(atk_stats.attack);
    combat.cooldown_remaining = combat.attack_cooldown;

    printf("[Combat] Entity %llu attacked Entity %llu: %d damage (HP: %d/%d)\n",
           entity, target, damage, tgt_stats.hp, tgt_stats.max_hp);

    // 공격 결과 전송
    SendAttackResult(world, entity, target, AttackResult::SUCCESS,
                     damage, tgt_stats.hp, tgt_stats.max_hp);

    // 피격자가 플레이어면 스탯 동기화
    if (target_is_player) {
        SendStatSync(world, target);
    }

    // 사망 처리
    if (!tgt_stats.IsAlive()) {
        printf("[Combat] Entity %llu killed by Entity %llu!\n", target, entity);

        // COMBAT_DIED 전송
        char died_buf[16];
        std::memcpy(died_buf, &target, 8);
        std::memcpy(died_buf + 8, &entity, 8);
        auto died_pkt = BuildPacket(MsgType::COMBAT_DIED, died_buf, 16);

        // 공격자에게 전송
        auto& atk_session = world.GetComponent<SessionComponent>(entity);
        g_network->SendTo(atk_session.session_id,
                          died_pkt.data(), static_cast<int>(died_pkt.size()));

        // 피격자가 플레이어면 피격자에게도 전송
        if (target_is_player) {
            auto& tgt_session = world.GetComponent<SessionComponent>(target);
            g_network->SendTo(tgt_session.session_id,
                              died_pkt.data(), static_cast<int>(died_pkt.size()));
        }

        // 몬스터 사망: 상태 변경 + 리스폰 타이머
        if (target_is_monster) {
            auto& monster = world.GetComponent<MonsterComponent>(target);
            monster.state = MonsterState::DEAD;
            monster.death_timer = monster.respawn_time;
            monster.target_entity = 0;
        }

        // EXP 보상
        int32_t exp_reward = CalcKillExp(tgt_stats.level);
        int old_level = atk_stats.level;
        bool leveled = atk_stats.AddExp(exp_reward);

        printf("[Combat] Entity %llu: +%d EXP from kill\n", entity, exp_reward);

        if (leveled) {
            printf("[Combat] Entity %llu: LEVEL UP %d -> %d\n",
                   entity, old_level, atk_stats.level);
        }

        // 공격자 스탯 동기화 (EXP 변경)
        SendStatSync(world, entity);

        // 몬스터 루트 드롭 (Session 27)
        if (target_is_monster) {
            ProcessMonsterLoot(world, entity, target);
        }

        // ENTITY_DIED 이벤트
        if (g_eventBus) {
            Event evt;
            evt.type = EventType::ENTITY_DIED;
            evt.source = target;
            evt.target = entity;  // killer
            g_eventBus->Publish(evt);
        }
    }
}

// RESPAWN_REQ 핸들러: 부활 요청
// 빈 페이로드
void OnRespawnReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    if (!world.HasComponent<StatsComponent>(entity)) {
        char resp[21] = {};
        resp[0] = 1;  // 에러
        auto pkt = BuildPacket(MsgType::RESPAWN_RESULT, resp, 21);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& stats = world.GetComponent<StatsComponent>(entity);

    if (stats.IsAlive()) {
        char resp[21] = {};
        resp[0] = 1;  // 살아있음 → 부활 불필요
        auto pkt = BuildPacket(MsgType::RESPAWN_RESULT, resp, 21);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // HP/MP 전회복
    stats.hp = stats.max_hp;
    stats.mp = stats.max_mp;
    stats.stats_dirty = true;

    // 스폰 위치로 이동
    float spawn_x = 100.0f, spawn_y = 100.0f, spawn_z = 0.0f;
    if (world.HasComponent<PositionComponent>(entity)) {
        auto& pos = world.GetComponent<PositionComponent>(entity);
        pos.x = spawn_x;
        pos.y = spawn_y;
        pos.z = spawn_z;
        pos.position_dirty = true;
    }

    // 응답: [result(1) hp(4) mp(4) x(4) y(4) z(4)]
    char resp[21];
    resp[0] = 0;  // 성공
    std::memcpy(resp + 1, &stats.hp, 4);
    std::memcpy(resp + 5, &stats.mp, 4);
    std::memcpy(resp + 9, &spawn_x, 4);
    std::memcpy(resp + 13, &spawn_y, 4);
    std::memcpy(resp + 17, &spawn_z, 4);
    auto pkt = BuildPacket(MsgType::RESPAWN_RESULT, resp, 21);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    // 스탯 동기화
    SendStatSync(world, entity);

    printf("[Combat] Entity %llu: RESPAWNED at (%.0f, %.0f)\n",
           entity, spawn_x, spawn_y);
}

// ━━━ Session 19: Skill System 핸들러 ━━━

void OnSkillListReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    int job_num = 0;
    if (world.HasComponent<StatsComponent>(entity)) {
        job_num = static_cast<int>(world.GetComponent<StatsComponent>(entity).job) + 1;
    }

    // 사용 가능한 스킬 수집 (공용 + 자기 직업)
    std::vector<const SkillData*> available;
    for (int i = 0; i < SKILL_TABLE_SIZE; i++) {
        if (SKILL_TABLE[i].job_class == 0 || SKILL_TABLE[i].job_class == job_num) {
            available.push_back(&SKILL_TABLE[i]);
        }
    }

    uint8_t count = static_cast<uint8_t>(available.size());
    int payload_size = 1 + count * 37;  // id(4)+name(16)+cd(4)+dmg(4)+mp(4)+range(4)+type(1)
    std::vector<char> resp(payload_size, 0);
    resp[0] = static_cast<char>(count);

    int off = 1;
    for (auto* s : available) {
        std::memcpy(resp.data() + off, &s->skill_id, 4); off += 4;
        std::memcpy(resp.data() + off, s->name, 16); off += 16;
        std::memcpy(resp.data() + off, &s->cooldown_ms, 4); off += 4;
        std::memcpy(resp.data() + off, &s->damage_multiplier, 4); off += 4;
        std::memcpy(resp.data() + off, &s->mp_cost, 4); off += 4;
        int32_t range_i = static_cast<int32_t>(s->range);
        std::memcpy(resp.data() + off, &range_i, 4); off += 4;
        resp[off++] = s->job_class;
    }

    auto pkt = BuildPacket(MsgType::SKILL_LIST_RESP, resp.data(), payload_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

void SendSkillResult(World& world, Entity caster, SkillResult result,
                     int32_t skill_id, Entity target, int32_t damage, int32_t target_hp) {
    if (!world.HasComponent<SessionComponent>(caster)) return;
    auto& session = world.GetComponent<SessionComponent>(caster);
    char buf[29];
    buf[0] = static_cast<uint8_t>(result);
    std::memcpy(buf + 1, &skill_id, 4);
    std::memcpy(buf + 5, &caster, 8);
    std::memcpy(buf + 13, &target, 8);
    std::memcpy(buf + 21, &damage, 4);
    std::memcpy(buf + 25, &target_hp, 4);
    auto pkt = BuildPacket(MsgType::SKILL_RESULT, buf, 29);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

void OnSkillUse(World& world, Entity entity, const char* payload, int len) {
    if (len < 12) return;
    int32_t skill_id;
    Entity target;
    std::memcpy(&skill_id, payload, 4);
    std::memcpy(&target, payload + 4, 8);

    auto* skill = FindSkill(skill_id);
    if (!skill) { SendSkillResult(world, entity, SkillResult::SKILL_NOT_FOUND, skill_id, target, 0, 0); return; }
    if (!world.HasComponent<StatsComponent>(entity)) return;
    auto& stats = world.GetComponent<StatsComponent>(entity);
    if (!stats.IsAlive()) { SendSkillResult(world, entity, SkillResult::CASTER_DEAD, skill_id, target, 0, 0); return; }

    // SkillComponent 자동 부착
    if (!world.HasComponent<SkillComponent>(entity)) world.AddComponent(entity, SkillComponent{});
    auto& sc = world.GetComponent<SkillComponent>(entity);

    // 쿨다운 확인
    if (sc.GetCooldown(skill_id) > 0) {
        SendSkillResult(world, entity, SkillResult::COOLDOWN, skill_id, target, 0, 0); return;
    }
    // MP 확인
    if (stats.mp < skill->mp_cost) {
        SendSkillResult(world, entity, SkillResult::NO_MP, skill_id, target, 0, 0); return;
    }

    // 자힐 스킬 (Heal, id=2)
    if (skill_id == 2) {
        stats.UseMp(skill->mp_cost);
        int32_t heal = 50 + stats.level * 5;
        stats.Heal(heal);
        sc.SetCooldown(skill_id, skill->cooldown_ms / 1000.0f);
        SendSkillResult(world, entity, SkillResult::SUCCESS, skill_id, entity, heal, stats.hp);
        SendStatSync(world, entity);
        printf("[Skill] Entity %llu used Heal: +%d HP\n", entity, heal);
        return;
    }

    // 타겟 공격 스킬
    if (!world.HasComponent<StatsComponent>(target)) {
        SendSkillResult(world, entity, SkillResult::INVALID_TARGET, skill_id, target, 0, 0); return;
    }
    auto& tgt_stats = world.GetComponent<StatsComponent>(target);
    if (!tgt_stats.IsAlive()) {
        SendSkillResult(world, entity, SkillResult::TARGET_DEAD, skill_id, target, 0, tgt_stats.hp); return;
    }

    // 사거리 확인
    if (skill->range > 0 && world.HasComponent<PositionComponent>(entity) && world.HasComponent<PositionComponent>(target)) {
        float dist = DistanceBetween(world.GetComponent<PositionComponent>(entity), world.GetComponent<PositionComponent>(target));
        if (dist > skill->range) {
            SendSkillResult(world, entity, SkillResult::OUT_OF_RANGE, skill_id, target, 0, tgt_stats.hp); return;
        }
    }

    // 스킬 실행
    stats.UseMp(skill->mp_cost);
    int32_t base_dmg = stats.attack * skill->damage_multiplier / 100;
    int32_t damage = tgt_stats.TakeDamage(base_dmg);
    sc.SetCooldown(skill_id, skill->cooldown_ms / 1000.0f);

    SendSkillResult(world, entity, SkillResult::SUCCESS, skill_id, target, damage, tgt_stats.hp);
    SendStatSync(world, entity);

    // 타겟 스탯 동기화
    if (world.HasComponent<SessionComponent>(target)) SendStatSync(world, target);

    printf("[Skill] Entity %llu used skill %d on %llu: %d damage (HP: %d)\n",
           entity, skill_id, target, damage, tgt_stats.hp);

    // 사망 처리 (OnAttackReq와 동일 수준으로 보강)
    if (!tgt_stats.IsAlive()) {
        printf("[Skill] Entity %llu killed by Entity %llu (skill %d)!\n", target, entity, skill_id);

        bool target_is_player = world.HasComponent<SessionComponent>(target);
        bool target_is_monster = world.HasComponent<MonsterComponent>(target);

        // COMBAT_DIED 전송: [dead_entity(8) killer_entity(8)]
        char died_buf[16];
        std::memcpy(died_buf, &target, 8);
        std::memcpy(died_buf + 8, &entity, 8);
        auto died_pkt = BuildPacket(MsgType::COMBAT_DIED, died_buf, 16);

        // 공격자에게 전송
        auto& atk_session = world.GetComponent<SessionComponent>(entity);
        g_network->SendTo(atk_session.session_id,
                          died_pkt.data(), static_cast<int>(died_pkt.size()));

        // 피격자가 플레이어면 피격자에게도 전송
        if (target_is_player) {
            auto& tgt_session = world.GetComponent<SessionComponent>(target);
            g_network->SendTo(tgt_session.session_id,
                              died_pkt.data(), static_cast<int>(died_pkt.size()));
        }

        // 몬스터 사망: 상태 변경 + 리스폰 타이머
        if (target_is_monster) {
            auto& mc = world.GetComponent<MonsterComponent>(target);
            mc.state = MonsterState::DEAD;
            mc.death_timer = mc.respawn_time;
            mc.target_entity = 0;
        }

        // EXP 보상
        int32_t exp_reward = CalcKillExp(tgt_stats.level);
        int old_level = stats.level;
        bool leveled = stats.AddExp(exp_reward);

        printf("[Skill] Entity %llu: +%d EXP from skill kill\n", entity, exp_reward);

        if (leveled) {
            printf("[Skill] Entity %llu: LEVEL UP %d -> %d\n",
                   entity, old_level, stats.level);
        }

        // 공격자 스탯 동기화 (EXP 변경)
        SendStatSync(world, entity);

        // 몬스터 루트 드롭 (Session 27)
        if (target_is_monster) {
            ProcessMonsterLoot(world, entity, target);
        }

        // ENTITY_DIED 이벤트 (Session 11)
        if (g_eventBus) {
            Event evt;
            evt.type = EventType::ENTITY_DIED;
            evt.source = target;
            evt.target = entity;  // killer
            g_eventBus->Publish(evt);
        }
    }
}

// ━━━ Session 20: Party System 핸들러 ━━━

void SendPartyInfo(World& world, Entity target, PartyResult result, uint32_t party_id) {
    if (!world.HasComponent<SessionComponent>(target)) return;
    auto& session = world.GetComponent<SessionComponent>(target);

    auto* party = FindParty(party_id);
    if (!party || result != PartyResult::SUCCESS) {
        char resp[14] = {};
        resp[0] = static_cast<uint8_t>(result);
        std::memcpy(resp + 1, &party_id, 4);
        Entity zero = 0;
        std::memcpy(resp + 5, &zero, 8);
        resp[13] = 0;
        auto pkt = BuildPacket(MsgType::PARTY_INFO, resp, 14);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    uint8_t count = static_cast<uint8_t>(party->members.size());
    int payload_size = 14 + count * 12;  // result(1)+party_id(4)+leader(8)+count(1) + N*(entity(8)+level(4))
    std::vector<char> resp(payload_size, 0);
    resp[0] = 0;  // SUCCESS
    std::memcpy(resp.data() + 1, &party_id, 4);
    std::memcpy(resp.data() + 5, &party->leader, 8);
    resp[13] = static_cast<char>(count);

    int off = 14;
    for (auto m : party->members) {
        std::memcpy(resp.data() + off, &m, 8); off += 8;
        int32_t lv = 1;
        if (world.HasComponent<StatsComponent>(m)) lv = world.GetComponent<StatsComponent>(m).level;
        std::memcpy(resp.data() + off, &lv, 4); off += 4;
    }

    auto pkt = BuildPacket(MsgType::PARTY_INFO, resp.data(), payload_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

void BroadcastPartyInfo(World& world, uint32_t party_id) {
    auto* party = FindParty(party_id);
    if (!party) return;
    for (auto m : party->members) SendPartyInfo(world, m, PartyResult::SUCCESS, party_id);
}

void OnPartyCreate(World& world, Entity entity, const char* payload, int len) {
    if (FindEntityParty(entity) > 0) {
        SendPartyInfo(world, entity, PartyResult::ALREADY_IN_PARTY, 0); return;
    }

    uint32_t pid = g_next_party_id++;
    PartyData party;
    party.party_id = pid;
    party.leader = entity;
    party.members.push_back(entity);
    g_parties[pid] = party;

    if (!world.HasComponent<PartyComponent>(entity)) world.AddComponent(entity, PartyComponent{pid});
    else world.GetComponent<PartyComponent>(entity).party_id = pid;

    SendPartyInfo(world, entity, PartyResult::SUCCESS, pid);
    printf("[Party] Entity %llu created party %u\n", entity, pid);
}

void OnPartyInvite(World& world, Entity entity, const char* payload, int len) {
    if (len < 8) return;
    Entity target;
    std::memcpy(&target, payload, 8);

    uint32_t pid = FindEntityParty(entity);
    if (pid == 0) { SendPartyInfo(world, entity, PartyResult::NOT_IN_PARTY, 0); return; }
    auto* party = FindParty(pid);
    if (!party || !party->IsLeader(entity)) { SendPartyInfo(world, entity, PartyResult::NOT_LEADER, 0); return; }
    if (party->IsFull()) { SendPartyInfo(world, entity, PartyResult::PARTY_FULL, 0); return; }
    if (FindEntityParty(target) > 0) { SendPartyInfo(world, entity, PartyResult::TARGET_IN_PARTY, 0); return; }
    if (!world.HasComponent<SessionComponent>(target)) { SendPartyInfo(world, entity, PartyResult::INVALID_TARGET, 0); return; }

    // 초대 전송 (자동 수락 간소화: 바로 파티에 추가)
    party->members.push_back(target);
    if (!world.HasComponent<PartyComponent>(target)) world.AddComponent(target, PartyComponent{pid});
    else world.GetComponent<PartyComponent>(target).party_id = pid;

    BroadcastPartyInfo(world, pid);
    printf("[Party] Entity %llu invited %llu to party %u\n", entity, target, pid);
}

void OnPartyAccept(World& world, Entity entity, const char* payload, int len) {
    // 간소화 버전에서는 Invite에서 자동 추가되므로, 이미 파티 상태 확인만
    uint32_t pid = FindEntityParty(entity);
    if (pid > 0) SendPartyInfo(world, entity, PartyResult::SUCCESS, pid);
    else SendPartyInfo(world, entity, PartyResult::PARTY_NOT_FOUND, 0);
}

void OnPartyLeave(World& world, Entity entity, const char* payload, int len) {
    uint32_t pid = FindEntityParty(entity);
    if (pid == 0) { SendPartyInfo(world, entity, PartyResult::NOT_IN_PARTY, 0); return; }
    auto* party = FindParty(pid);
    if (!party) return;

    party->RemoveMember(entity);
    if (world.HasComponent<PartyComponent>(entity)) world.RemoveComponent<PartyComponent>(entity);

    printf("[Party] Entity %llu left party %u\n", entity, pid);

    if (party->members.empty()) {
        g_parties.erase(pid);
        printf("[Party] Party %u disbanded (empty)\n", pid);
    } else {
        if (party->leader == entity) {
            party->leader = party->members[0];
            printf("[Party] New leader: Entity %llu\n", party->leader);
        }
        BroadcastPartyInfo(world, pid);
    }
    SendPartyInfo(world, entity, PartyResult::NOT_IN_PARTY, 0);
}

void OnPartyKick(World& world, Entity entity, const char* payload, int len) {
    if (len < 8) return;
    Entity target;
    std::memcpy(&target, payload, 8);

    uint32_t pid = FindEntityParty(entity);
    if (pid == 0) { SendPartyInfo(world, entity, PartyResult::NOT_IN_PARTY, 0); return; }
    auto* party = FindParty(pid);
    if (!party || !party->IsLeader(entity)) { SendPartyInfo(world, entity, PartyResult::NOT_LEADER, 0); return; }
    if (!party->IsMember(target)) { SendPartyInfo(world, entity, PartyResult::INVALID_TARGET, 0); return; }

    party->RemoveMember(target);
    if (world.HasComponent<PartyComponent>(target)) world.RemoveComponent<PartyComponent>(target);

    BroadcastPartyInfo(world, pid);
    SendPartyInfo(world, target, PartyResult::NOT_IN_PARTY, 0);
    printf("[Party] Entity %llu kicked %llu from party %u\n", entity, target, pid);
}

// ━━━ Session 21: Instance Dungeon 핸들러 ━━━

void OnInstanceCreate(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;

    int32_t dungeon_type;
    std::memcpy(&dungeon_type, payload, 4);

    auto* tmpl = FindDungeonTemplate(dungeon_type);
    if (!tmpl) {
        char resp[9] = {};
        resp[0] = static_cast<uint8_t>(InstanceResult::DUNGEON_NOT_FOUND);
        auto pkt = BuildPacket(MsgType::INSTANCE_ENTER, resp, 9);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // 이미 인스턴스에 있는지 확인
    if (world.HasComponent<InstanceComponent>(entity)) {
        char resp[9] = {};
        resp[0] = static_cast<uint8_t>(InstanceResult::ALREADY_IN_INSTANCE);
        auto pkt = BuildPacket(MsgType::INSTANCE_ENTER, resp, 9);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // 레벨 확인
    int32_t level = 1;
    if (world.HasComponent<StatsComponent>(entity)) level = world.GetComponent<StatsComponent>(entity).level;
    if (level < tmpl->min_level) {
        char resp[9] = {};
        resp[0] = static_cast<uint8_t>(InstanceResult::LEVEL_TOO_LOW);
        auto pkt = BuildPacket(MsgType::INSTANCE_ENTER, resp, 9);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // 인스턴스 생성
    uint32_t iid = g_next_instance_id++;
    InstanceData inst;
    inst.instance_id = iid;
    inst.dungeon_type = dungeon_type;

    // 이전 위치 저장
    InstanceComponent ic;
    ic.instance_id = iid;
    if (world.HasComponent<ZoneComponent>(entity)) ic.previous_zone = world.GetComponent<ZoneComponent>(entity).zone_id;
    if (world.HasComponent<PositionComponent>(entity)) {
        auto& pos = world.GetComponent<PositionComponent>(entity);
        ic.previous_x = pos.x; ic.previous_y = pos.y; ic.previous_z = pos.z;
    }

    // 인스턴스 몬스터 생성
    // 던전 타입별 루트 테이블: GoblinCave(1)→Basic, WolfDen(2)→Elite, DragonLair(3)→Boss
    int32_t dungeon_loot_table = (dungeon_type <= 1) ? 1 : (dungeon_type == 2) ? 2 : 3;

    for (int i = 0; i < tmpl->monster_count; i++) {
        Entity me = world.CreateEntity();
        MonsterComponent mc{};
        mc.monster_id = 100 + dungeon_type * 10 + i;
        std::snprintf(mc.name, 31, "Inst_%s_%d", tmpl->name, i);
        mc.state = MonsterState::IDLE;
        mc.spawn_x = 100.0f + i * 100.0f;
        mc.spawn_y = 100.0f;
        mc.spawn_z = 0;
        mc.respawn_time = 0;  // 인스턴스 몬스터는 리스폰 없음
        mc.loot_table_id = dungeon_loot_table;
        world.AddComponent(me, mc);
        int32_t m_atk = tmpl->monster_level * 3;
        int32_t m_def = tmpl->monster_level;
        world.AddComponent(me, CreateMonsterStats(tmpl->monster_level, tmpl->monster_hp, m_atk, m_def));
        CombatComponent cc; cc.attack_range = 200.0f; cc.attack_cooldown = 2.0f;
        world.AddComponent(me, cc);
        PositionComponent pos; pos.x = mc.spawn_x; pos.y = mc.spawn_y;
        world.AddComponent(me, pos);
        InstanceMonsterComponent imc; imc.instance_id = iid;
        world.AddComponent(me, imc);
        inst.monsters.push_back(me);
    }

    inst.players.push_back(entity);
    g_instances[iid] = inst;

    world.AddComponent(entity, ic);

    // 응답
    char resp[9];
    resp[0] = static_cast<uint8_t>(InstanceResult::SUCCESS);
    std::memcpy(resp + 1, &iid, 4);
    std::memcpy(resp + 5, &dungeon_type, 4);
    auto pkt = BuildPacket(MsgType::INSTANCE_ENTER, resp, 9);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Instance] Entity %llu created instance %u (type=%d, monsters=%d)\n",
           entity, iid, dungeon_type, tmpl->monster_count);
}

void OnInstanceLeave(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    if (!world.HasComponent<InstanceComponent>(entity)) {
        char resp[17] = {};
        resp[0] = static_cast<uint8_t>(InstanceResult::NOT_IN_INSTANCE);
        auto pkt = BuildPacket(MsgType::INSTANCE_LEAVE_RESULT, resp, 17);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& ic = world.GetComponent<InstanceComponent>(entity);
    uint32_t iid = ic.instance_id;
    int32_t prev_zone = ic.previous_zone;
    float px = ic.previous_x, py = ic.previous_y, pz = ic.previous_z;

    // 인스턴스에서 제거
    auto* inst = FindInstance(iid);
    if (inst) {
        inst->RemovePlayer(entity);
        if (inst->players.empty()) {
            // 인스턴스 정리: 몬스터 Entity 삭제
            for (auto me : inst->monsters) {
                world.DestroyEntity(me);
            }
            g_instances.erase(iid);
            printf("[Instance] Instance %u destroyed (no players)\n", iid);
        }
    }

    world.RemoveComponent<InstanceComponent>(entity);

    // 이전 위치로 복원
    if (world.HasComponent<PositionComponent>(entity)) {
        auto& pos = world.GetComponent<PositionComponent>(entity);
        pos.x = px; pos.y = py; pos.z = pz;
        pos.position_dirty = true;
    }

    char resp[17];
    resp[0] = static_cast<uint8_t>(InstanceResult::SUCCESS);
    std::memcpy(resp + 1, &prev_zone, 4);
    std::memcpy(resp + 5, &px, 4);
    std::memcpy(resp + 9, &py, 4);
    std::memcpy(resp + 13, &pz, 4);
    auto pkt = BuildPacket(MsgType::INSTANCE_LEAVE_RESULT, resp, 17);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Instance] Entity %llu left instance %u, returned to zone %d\n", entity, iid, prev_zone);
}

void OnInstanceInfo(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (!world.HasComponent<InstanceComponent>(entity)) {
        char resp[10] = {};
        auto pkt = BuildPacket(MsgType::INSTANCE_INFO, resp, 10);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& ic = world.GetComponent<InstanceComponent>(entity);
    auto* inst = FindInstance(ic.instance_id);
    if (!inst) {
        char resp[10] = {};
        auto pkt = BuildPacket(MsgType::INSTANCE_INFO, resp, 10);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // 살아있는 몬스터 수
    uint8_t alive_monsters = 0;
    for (auto me : inst->monsters) {
        if (world.HasComponent<StatsComponent>(me) && world.GetComponent<StatsComponent>(me).IsAlive())
            alive_monsters++;
    }

    char resp[10];
    std::memcpy(resp, &inst->instance_id, 4);
    std::memcpy(resp + 4, &inst->dungeon_type, 4);
    resp[8] = static_cast<uint8_t>(inst->players.size());
    resp[9] = alive_monsters;
    auto pkt = BuildPacket(MsgType::INSTANCE_INFO, resp, 10);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// ━━━ Session 22: Matching Queue 핸들러 ━━━

void OnMatchEnqueue(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;

    int32_t dungeon_type;
    std::memcpy(&dungeon_type, payload, 4);

    // 이미 큐에 있는지 확인
    if (world.HasComponent<MatchComponent>(entity) && world.GetComponent<MatchComponent>(entity).in_queue) {
        char resp[5];
        resp[0] = static_cast<uint8_t>(MatchStatus::IN_QUEUE);
        int32_t pos = GetQueuePosition(entity);
        std::memcpy(resp + 1, &pos, 4);
        auto pkt = BuildPacket(MsgType::MATCH_STATUS, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // 인스턴스에 있으면 불가
    if (world.HasComponent<InstanceComponent>(entity)) {
        char resp[5] = {};
        resp[0] = static_cast<uint8_t>(MatchStatus::IDLE);
        auto pkt = BuildPacket(MsgType::MATCH_STATUS, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    int32_t level = 1;
    if (world.HasComponent<StatsComponent>(entity)) level = world.GetComponent<StatsComponent>(entity).level;

    MatchQueueEntry entry;
    entry.entity = entity;
    entry.dungeon_type = dungeon_type;
    entry.level = level;
    entry.wait_time = 0;
    g_match_queue.push_back(entry);

    if (!world.HasComponent<MatchComponent>(entity)) world.AddComponent(entity, MatchComponent{});
    auto& mc = world.GetComponent<MatchComponent>(entity);
    mc.in_queue = true;
    mc.dungeon_type = dungeon_type;

    char resp[5];
    resp[0] = static_cast<uint8_t>(MatchStatus::IN_QUEUE);
    int32_t pos = GetQueuePosition(entity);
    std::memcpy(resp + 1, &pos, 4);
    auto pkt = BuildPacket(MsgType::MATCH_STATUS, resp, 5);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Match] Entity %llu enqueued for dungeon %d (queue pos=%d)\n", entity, dungeon_type, pos);

    // 큐에서 죽은 엔티티 정리
    g_match_queue.erase(
        std::remove_if(g_match_queue.begin(), g_match_queue.end(),
            [&world](const MatchQueueEntry& e) { return !world.IsAlive(e.entity); }),
        g_match_queue.end());

    // 즉시 매칭 체크: 같은 던전 타입 2명 이상이면 매칭
    std::vector<Entity> matched;
    for (auto& e : g_match_queue) {
        if (e.dungeon_type == dungeon_type) matched.push_back(e.entity);
        if (static_cast<int>(matched.size()) >= 2) break;
    }

    if (static_cast<int>(matched.size()) >= 2) {
        uint32_t mid = g_next_match_id++;

        // 큐에서 제거
        for (auto m : matched) {
            RemoveFromMatchQueue(m);
            if (world.HasComponent<MatchComponent>(m)) {
                auto& mmc = world.GetComponent<MatchComponent>(m);
                mmc.in_queue = false;
                mmc.pending_match_id = mid;
            }
        }

        // MATCH_FOUND 전송
        for (auto m : matched) {
            if (!world.HasComponent<SessionComponent>(m)) continue;
            auto& ms = world.GetComponent<SessionComponent>(m);
            char fbuf[9];
            std::memcpy(fbuf, &mid, 4);
            std::memcpy(fbuf + 4, &dungeon_type, 4);
            fbuf[8] = static_cast<uint8_t>(matched.size());
            auto fpkt = BuildPacket(MsgType::MATCH_FOUND, fbuf, 9);
            g_network->SendTo(ms.session_id, fpkt.data(), static_cast<int>(fpkt.size()));
        }

        MatchResultData mrd;
        mrd.match_id = mid;
        mrd.dungeon_type = dungeon_type;
        mrd.players = matched;
        g_pending_matches[mid] = mrd;

        printf("[Match] Match %u found for dungeon %d (%d players)\n",
               mid, dungeon_type, static_cast<int>(matched.size()));
    }
}

void OnMatchDequeue(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    RemoveFromMatchQueue(entity);
    if (world.HasComponent<MatchComponent>(entity)) {
        world.GetComponent<MatchComponent>(entity).in_queue = false;
    }

    char resp[5] = {};
    resp[0] = static_cast<uint8_t>(MatchStatus::IDLE);
    auto pkt = BuildPacket(MsgType::MATCH_STATUS, resp, 5);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
    printf("[Match] Entity %llu dequeued\n", entity);
}

void OnMatchAccept(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;

    uint32_t match_id;
    std::memcpy(&match_id, payload, 4);

    auto it = g_pending_matches.find(match_id);
    if (it == g_pending_matches.end()) {
        char resp[5] = {};
        resp[0] = static_cast<uint8_t>(MatchStatus::IDLE);
        auto pkt = BuildPacket(MsgType::MATCH_STATUS, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& mrd = it->second;
    mrd.accept_count++;

    printf("[Match] Entity %llu accepted match %u (%d/%d)\n",
           entity, match_id, mrd.accept_count, static_cast<int>(mrd.players.size()));

    // 모든 플레이어 수락 시 인스턴스 자동 생성
    if (mrd.accept_count >= static_cast<int>(mrd.players.size())) {
        // 인스턴스 생성 (첫 플레이어 기준)
        int32_t dt = mrd.dungeon_type;
        char create_buf[4];
        std::memcpy(create_buf, &dt, 4);

        // 첫 플레이어로 인스턴스 생성
        Entity first = mrd.players[0];
        OnInstanceCreate(world, first, create_buf, 4);

        // 나머지 플레이어도 같은 인스턴스에 추가
        if (world.HasComponent<InstanceComponent>(first)) {
            uint32_t iid = world.GetComponent<InstanceComponent>(first).instance_id;
            auto* inst = FindInstance(iid);
            if (inst) {
                for (size_t i = 1; i < mrd.players.size(); i++) {
                    Entity p = mrd.players[i];
                    InstanceComponent pic;
                    pic.instance_id = iid;
                    if (world.HasComponent<ZoneComponent>(p)) pic.previous_zone = world.GetComponent<ZoneComponent>(p).zone_id;
                    if (world.HasComponent<PositionComponent>(p)) {
                        auto& pp = world.GetComponent<PositionComponent>(p);
                        pic.previous_x = pp.x; pic.previous_y = pp.y; pic.previous_z = pp.z;
                    }
                    if (!world.HasComponent<InstanceComponent>(p)) world.AddComponent(p, pic);
                    inst->players.push_back(p);

                    // INSTANCE_ENTER 전송
                    if (world.HasComponent<SessionComponent>(p)) {
                        auto& ps = world.GetComponent<SessionComponent>(p);
                        char ieresp[9];
                        ieresp[0] = 0;
                        std::memcpy(ieresp + 1, &iid, 4);
                        std::memcpy(ieresp + 5, &dt, 4);
                        auto iepkt = BuildPacket(MsgType::INSTANCE_ENTER, ieresp, 9);
                        g_network->SendTo(ps.session_id, iepkt.data(), static_cast<int>(iepkt.size()));
                    }
                }
            }
        }

        // MatchComponent 정리
        for (auto p : mrd.players) {
            if (world.HasComponent<MatchComponent>(p)) world.RemoveComponent<MatchComponent>(p);
        }
        g_pending_matches.erase(it);

        printf("[Match] Match %u completed - instance created\n", match_id);
    }
}

// ━━━ Session 23: Inventory/Item 핸들러 ━━━

void OnInventoryReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (!world.HasComponent<InventoryComponent>(entity)) world.AddComponent(entity, InventoryComponent{});
    auto& inv = world.GetComponent<InventoryComponent>(entity);

    // 비어있지 않은 슬롯 수 계산
    uint8_t count = 0;
    for (int i = 0; i < MAX_INVENTORY_SLOTS; i++) {
        if (inv.slots[i].item_id != 0) count++;
    }

    int payload_size = 1 + count * 8;  // count(1) + N*(slot(1)+item_id(4)+count(2)+equipped(1))
    std::vector<char> resp(payload_size, 0);
    resp[0] = count;
    int off = 1;
    for (int i = 0; i < MAX_INVENTORY_SLOTS; i++) {
        if (inv.slots[i].item_id == 0) continue;
        resp[off++] = static_cast<char>(i);
        std::memcpy(resp.data() + off, &inv.slots[i].item_id, 4); off += 4;
        std::memcpy(resp.data() + off, &inv.slots[i].count, 2); off += 2;
        resp[off++] = inv.slots[i].equipped ? 1 : 0;
    }
    auto pkt = BuildPacket(MsgType::INVENTORY_RESP, resp.data(), payload_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

void OnItemAdd(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 6) return;
    int32_t item_id;
    int16_t count;
    std::memcpy(&item_id, payload, 4);
    std::memcpy(&count, payload + 4, 2);

    if (!world.HasComponent<InventoryComponent>(entity)) world.AddComponent(entity, InventoryComponent{});
    auto& inv = world.GetComponent<InventoryComponent>(entity);

    int slot = inv.AddItem(item_id, count);
    char resp[8];
    resp[0] = (slot >= 0) ? 0 : static_cast<uint8_t>(ItemResult::INVENTORY_FULL);
    resp[1] = (slot >= 0) ? static_cast<char>(slot) : 0;
    std::memcpy(resp + 2, &item_id, 4);
    std::memcpy(resp + 6, &count, 2);
    auto pkt = BuildPacket(MsgType::ITEM_ADD_RESULT, resp, 8);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    if (slot >= 0) printf("[Item] Entity %llu: added item %d x%d to slot %d\n", entity, item_id, count, slot);
}

void OnItemUse(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 1) return;
    uint8_t slot = static_cast<uint8_t>(payload[0]);

    if (!world.HasComponent<InventoryComponent>(entity)) {
        char resp[6] = {}; resp[0] = static_cast<uint8_t>(ItemResult::EMPTY_SLOT);
        auto pkt = BuildPacket(MsgType::ITEM_USE_RESULT, resp, 6);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }
    auto& inv = world.GetComponent<InventoryComponent>(entity);
    if (slot >= MAX_INVENTORY_SLOTS || inv.slots[slot].item_id == 0) {
        char resp[6] = {}; resp[0] = static_cast<uint8_t>(ItemResult::EMPTY_SLOT);
        auto pkt = BuildPacket(MsgType::ITEM_USE_RESULT, resp, 6);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto* tmpl = FindItemTemplate(inv.slots[slot].item_id);
    if (!tmpl || tmpl->type != ItemType::CONSUMABLE) {
        char resp[6] = {}; resp[0] = static_cast<uint8_t>(ItemResult::NOT_CONSUMABLE);
        resp[1] = slot;
        auto pkt = BuildPacket(MsgType::ITEM_USE_RESULT, resp, 6);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // 포션 사용
    if (world.HasComponent<StatsComponent>(entity)) {
        auto& stats = world.GetComponent<StatsComponent>(entity);
        if (tmpl->param2 == 0) stats.Heal(tmpl->param1);        // HP 포션
        else { stats.mp = std::min(stats.max_mp, stats.mp + tmpl->param1); stats.stats_dirty = true; } // MP 포션
        SendStatSync(world, entity);
    }

    int32_t used_id = inv.slots[slot].item_id;
    inv.RemoveItem(slot, 1);

    char resp[6];
    resp[0] = 0;  // SUCCESS
    resp[1] = slot;
    std::memcpy(resp + 2, &used_id, 4);
    auto pkt = BuildPacket(MsgType::ITEM_USE_RESULT, resp, 6);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
    printf("[Item] Entity %llu used item %d from slot %d\n", entity, used_id, slot);
}

void OnItemEquip(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 1) return;
    uint8_t slot = static_cast<uint8_t>(payload[0]);

    if (!world.HasComponent<InventoryComponent>(entity)) { return; }
    auto& inv = world.GetComponent<InventoryComponent>(entity);
    if (slot >= MAX_INVENTORY_SLOTS || inv.slots[slot].item_id == 0) { return; }

    auto* tmpl = FindItemTemplate(inv.slots[slot].item_id);
    if (!tmpl || (tmpl->type != ItemType::WEAPON && tmpl->type != ItemType::ARMOR)) {
        char resp[7] = {}; resp[0] = static_cast<uint8_t>(ItemResult::NOT_EQUIPMENT);
        auto pkt = BuildPacket(MsgType::ITEM_EQUIP_RESULT, resp, 7);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    inv.slots[slot].equipped = true;

    char resp[7];
    resp[0] = 0;
    resp[1] = slot;
    std::memcpy(resp + 2, &inv.slots[slot].item_id, 4);
    resp[6] = 1;
    auto pkt = BuildPacket(MsgType::ITEM_EQUIP_RESULT, resp, 7);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
    printf("[Item] Entity %llu equipped item %d at slot %d\n", entity, inv.slots[slot].item_id, slot);
}

void OnItemUnequip(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 1) return;
    uint8_t slot = static_cast<uint8_t>(payload[0]);

    if (!world.HasComponent<InventoryComponent>(entity)) return;
    auto& inv = world.GetComponent<InventoryComponent>(entity);
    if (slot >= MAX_INVENTORY_SLOTS || inv.slots[slot].item_id == 0) return;

    inv.slots[slot].equipped = false;

    char resp[7];
    resp[0] = 0;
    resp[1] = slot;
    std::memcpy(resp + 2, &inv.slots[slot].item_id, 4);
    resp[6] = 0;
    auto pkt = BuildPacket(MsgType::ITEM_EQUIP_RESULT, resp, 7);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// ━━━ Session 24: Buff/Debuff 핸들러 ━━━

void OnBuffListReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (!world.HasComponent<BuffComponent>(entity)) world.AddComponent(entity, BuffComponent{});
    auto& bc = world.GetComponent<BuffComponent>(entity);

    uint8_t count = static_cast<uint8_t>(bc.ActiveCount());
    int payload_size = 1 + count * 9;  // count(1) + N*(buff_id(4)+remaining_ms(4)+stacks(1))
    std::vector<char> resp(payload_size, 0);
    resp[0] = count;
    int off = 1;
    for (int i = 0; i < MAX_ACTIVE_BUFFS; i++) {
        if (!bc.buffs[i].active) continue;
        std::memcpy(resp.data() + off, &bc.buffs[i].buff_id, 4); off += 4;
        int32_t rem_ms = static_cast<int32_t>(bc.buffs[i].remaining * 1000);
        std::memcpy(resp.data() + off, &rem_ms, 4); off += 4;
        resp[off++] = static_cast<uint8_t>(bc.buffs[i].stacks);
    }
    auto pkt = BuildPacket(MsgType::BUFF_LIST_RESP, resp.data(), payload_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

void OnBuffApply(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;
    int32_t buff_id;
    std::memcpy(&buff_id, payload, 4);

    auto* tmpl = FindBuffTemplate(buff_id);
    if (!tmpl) {
        char resp[10] = {}; resp[0] = static_cast<uint8_t>(BuffResult::BUFF_NOT_FOUND);
        auto pkt = BuildPacket(MsgType::BUFF_RESULT, resp, 10);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    if (!world.HasComponent<BuffComponent>(entity)) world.AddComponent(entity, BuffComponent{});
    auto& bc = world.GetComponent<BuffComponent>(entity);
    int idx = bc.ApplyBuff(buff_id);

    char resp[10];
    resp[0] = (idx >= 0) ? 0 : static_cast<uint8_t>(BuffResult::NO_SLOT);
    std::memcpy(resp + 1, &buff_id, 4);
    resp[5] = (idx >= 0) ? static_cast<uint8_t>(bc.buffs[idx].stacks) : 0;
    std::memcpy(resp + 6, &tmpl->duration_ms, 4);
    auto pkt = BuildPacket(MsgType::BUFF_RESULT, resp, 10);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Buff] Entity %llu applied buff %d '%s' (stacks=%d)\n",
           entity, buff_id, tmpl->name, (idx >= 0) ? bc.buffs[idx].stacks : 0);
}

void OnBuffRemove(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;
    int32_t buff_id;
    std::memcpy(&buff_id, payload, 4);

    if (!world.HasComponent<BuffComponent>(entity)) {
        char resp[5] = {}; resp[0] = static_cast<uint8_t>(BuffResult::NOT_ACTIVE);
        std::memcpy(resp + 1, &buff_id, 4);
        auto pkt = BuildPacket(MsgType::BUFF_REMOVE_RESP, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& bc = world.GetComponent<BuffComponent>(entity);
    bc.RemoveBuff(buff_id);

    char resp[5];
    resp[0] = 0;
    std::memcpy(resp + 1, &buff_id, 4);
    auto pkt = BuildPacket(MsgType::BUFF_REMOVE_RESP, resp, 5);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
    printf("[Buff] Entity %llu removed buff %d\n", entity, buff_id);
}

// ━━━ Session 25: Condition Engine 핸들러 ━━━

// CONDITION_EVAL: 조건 트리 평가
// 페이로드: [count(1) root(1) {type(1) p1(4) p2(4) left(2) right(2)}...]
// 응답: CONDITION_RESULT [result(1: 0=false, 1=true)]
void OnConditionEval(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    ConditionTree tree = ConditionTree::Deserialize(payload, len);
    bool result = EvaluateCondition(tree, world, entity);

    char resp[1];
    resp[0] = result ? 1 : 0;
    auto pkt = BuildPacket(MsgType::CONDITION_RESULT, resp, 1);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// ━━━ Session 26: Spatial Query 핸들러 ━━━

// SPATIAL_QUERY_REQ: 범위 내 엔티티 검색
// 페이로드: [x(4) y(4) z(4) radius(4) filter(1)]
// 응답: SPATIAL_QUERY_RESP [count(1) {entity(8) dist(4)}...] = 1 + N*12
void OnSpatialQuery(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 17) return;

    float qx, qy, qz, radius;
    uint8_t filter;
    std::memcpy(&qx, payload, 4);
    std::memcpy(&qy, payload + 4, 4);
    std::memcpy(&qz, payload + 8, 4);
    std::memcpy(&radius, payload + 12, 4);
    filter = static_cast<uint8_t>(payload[16]);

    struct HitEntry { Entity e; float dist; };
    std::vector<HitEntry> hits;

    world.ForEach<PositionComponent>([&](Entity e, PositionComponent& pos) {
        if (e == entity) return;  // 자기 자신 제외

        // 필터링
        if (filter == 1 && !world.HasComponent<SessionComponent>(e)) return;  // 플레이어만
        if (filter == 2 && !world.HasComponent<MonsterComponent>(e)) return;   // 몬스터만

        float dx = pos.x - qx, dy = pos.y - qy, dz = pos.z - qz;
        float dist = std::sqrt(dx*dx + dy*dy + dz*dz);
        if (dist <= radius) {
            hits.push_back({e, dist});
        }
    });

    // 거리 순 정렬
    std::sort(hits.begin(), hits.end(), [](const HitEntry& a, const HitEntry& b) {
        return a.dist < b.dist;
    });

    uint8_t count = static_cast<uint8_t>(std::min(hits.size(), static_cast<size_t>(255)));
    int resp_size = 1 + count * 12;
    std::vector<char> resp(resp_size, 0);
    resp[0] = count;
    int off = 1;
    for (int i = 0; i < count; i++) {
        std::memcpy(resp.data() + off, &hits[i].e, 8); off += 8;
        std::memcpy(resp.data() + off, &hits[i].dist, 4); off += 4;
    }

    auto pkt = BuildPacket(MsgType::SPATIAL_QUERY_RESP, resp.data(), resp_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Spatial] Entity %llu: query at (%.0f,%.0f,%.0f) r=%.0f filter=%d -> %d hits\n",
           entity, qx, qy, qz, radius, filter, count);
}

// ━━━ Session 27: Loot/Drop Table 핸들러 ━━━

// LOOT_ROLL_REQ: 드롭 테이블 롤
// 페이로드: [table_id(4)]
// 응답: LOOT_RESULT [count(1) {item_id(4) count(2)}...]
void OnLootRoll(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;

    int32_t table_id;
    std::memcpy(&table_id, payload, 4);

    auto* table = FindLootTable(table_id);
    if (!table) {
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::LOOT_RESULT, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto results = RollLoot(*table);
    uint8_t count = static_cast<uint8_t>(results.size());
    int resp_size = 1 + count * 6;  // count(1) + N*(item_id(4) + count(2))
    std::vector<char> resp(resp_size, 0);
    resp[0] = count;
    int off = 1;
    for (auto& r : results) {
        std::memcpy(resp.data() + off, &r.item_id, 4); off += 4;
        std::memcpy(resp.data() + off, &r.count, 2); off += 2;
    }

    auto pkt = BuildPacket(MsgType::LOOT_RESULT, resp.data(), resp_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Loot] Entity %llu: rolled table %d '%s' -> %d items\n",
           entity, table_id, table->name, count);
}

// ━━━ Session 28: Quest System 핸들러 ━━━

// QUEST_LIST_REQ: 활성 퀘스트 목록
// 응답: QUEST_LIST_RESP [count(1) {quest_id(4) state(1) progress(4) target(4)}...]
void OnQuestListReq(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    if (!world.HasComponent<QuestComponent>(entity)) {
        world.AddComponent(entity, QuestComponent{});
    }
    auto& qc = world.GetComponent<QuestComponent>(entity);

    uint8_t count = static_cast<uint8_t>(qc.ActiveCount());
    int resp_size = 1 + count * 13;
    std::vector<char> resp(resp_size, 0);
    resp[0] = count;
    int off = 1;
    for (int i = 0; i < MAX_ACTIVE_QUESTS; i++) {
        if (!qc.quests[i].IsActive()) continue;
        auto& q = qc.quests[i];
        std::memcpy(resp.data() + off, &q.quest_id, 4); off += 4;
        resp[off++] = static_cast<uint8_t>(q.state);
        std::memcpy(resp.data() + off, &q.progress, 4); off += 4;
        std::memcpy(resp.data() + off, &q.target, 4); off += 4;
    }

    auto pkt = BuildPacket(MsgType::QUEST_LIST_RESP, resp.data(), resp_size);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// QUEST_ACCEPT: 퀘스트 수락
// 페이로드: [quest_id(4)]
// 응답: QUEST_ACCEPT_RESULT [result(1) quest_id(4)]
void OnQuestAccept(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;

    int32_t quest_id;
    std::memcpy(&quest_id, payload, 4);

    auto* tmpl = FindQuestTemplate(quest_id);
    if (!tmpl) {
        char resp[5]; resp[0] = static_cast<uint8_t>(QuestResult::QUEST_NOT_FOUND);
        std::memcpy(resp + 1, &quest_id, 4);
        auto pkt = BuildPacket(MsgType::QUEST_ACCEPT_RESULT, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // 레벨 체크
    if (world.HasComponent<StatsComponent>(entity)) {
        auto& stats = world.GetComponent<StatsComponent>(entity);
        if (stats.level < tmpl->min_level) {
            char resp[5]; resp[0] = static_cast<uint8_t>(QuestResult::LEVEL_TOO_LOW);
            std::memcpy(resp + 1, &quest_id, 4);
            auto pkt = BuildPacket(MsgType::QUEST_ACCEPT_RESULT, resp, 5);
            g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
            return;
        }
    }

    // 선행 퀘스트 체크
    if (tmpl->prerequisite_quest_id > 0) {
        if (!world.HasComponent<QuestComponent>(entity)) {
            world.AddComponent(entity, QuestComponent{});
        }
        auto& qc = world.GetComponent<QuestComponent>(entity);
        QuestState pre_state = qc.GetQuestState(tmpl->prerequisite_quest_id);
        if (pre_state != QuestState::REWARDED && pre_state != QuestState::COMPLETE) {
            char resp[5]; resp[0] = static_cast<uint8_t>(QuestResult::PREREQUISITE_NOT_MET);
            std::memcpy(resp + 1, &quest_id, 4);
            auto pkt = BuildPacket(MsgType::QUEST_ACCEPT_RESULT, resp, 5);
            g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
            return;
        }
    }

    if (!world.HasComponent<QuestComponent>(entity)) {
        world.AddComponent(entity, QuestComponent{});
    }
    auto& qc = world.GetComponent<QuestComponent>(entity);
    int result = qc.AcceptQuest(quest_id);

    char resp[5];
    if (result >= 0) {
        resp[0] = static_cast<uint8_t>(QuestResult::SUCCESS);
    } else if (result == -2) {
        resp[0] = static_cast<uint8_t>(QuestResult::ALREADY_ACCEPTED);
    } else {
        resp[0] = static_cast<uint8_t>(QuestResult::QUEST_FULL);
    }
    std::memcpy(resp + 1, &quest_id, 4);
    auto pkt = BuildPacket(MsgType::QUEST_ACCEPT_RESULT, resp, 5);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    if (result >= 0) {
        printf("[Quest] Entity %llu accepted quest %d '%s'\n", entity, quest_id, tmpl->name);
    }
}

// QUEST_PROGRESS: 퀘스트 진행도 확인/갱신
// 페이로드: [quest_id(4)]
// 응답: QUEST_LIST_RESP with single entry
void OnQuestProgress(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;

    int32_t quest_id;
    std::memcpy(&quest_id, payload, 4);

    if (!world.HasComponent<QuestComponent>(entity)) {
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::QUEST_LIST_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& qc = world.GetComponent<QuestComponent>(entity);

    // Collect 목표 갱신 (인벤토리 체크)
    if (world.HasComponent<InventoryComponent>(entity)) {
        qc.CheckCollectObjectives(world.GetComponent<InventoryComponent>(entity));
    }
    // Zone 목표 갱신
    if (world.HasComponent<ZoneComponent>(entity)) {
        qc.CheckZoneObjectives(world.GetComponent<ZoneComponent>(entity).zone_id);
    }

    int idx = qc.FindQuest(quest_id);
    if (idx < 0) {
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::QUEST_LIST_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    auto& q = qc.quests[idx];
    char resp[14];
    resp[0] = 1;  // count = 1
    std::memcpy(resp + 1, &q.quest_id, 4);
    resp[5] = static_cast<uint8_t>(q.state);
    std::memcpy(resp + 6, &q.progress, 4);
    std::memcpy(resp + 10, &q.target, 4);
    auto pkt = BuildPacket(MsgType::QUEST_LIST_RESP, resp, 14);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// QUEST_COMPLETE: 퀘스트 완료 + 보상 수령
// 페이로드: [quest_id(4)]
// 응답: QUEST_COMPLETE_RESULT [result(1) quest_id(4) reward_exp(4) reward_item_id(4) reward_item_count(2)]
void OnQuestComplete(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);
    if (len < 4) return;

    int32_t quest_id;
    std::memcpy(&quest_id, payload, 4);

    auto send_result = [&](QuestResult result) {
        char resp[15] = {};
        resp[0] = static_cast<uint8_t>(result);
        std::memcpy(resp + 1, &quest_id, 4);
        auto pkt = BuildPacket(MsgType::QUEST_COMPLETE_RESULT, resp, 15);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
    };

    if (!world.HasComponent<QuestComponent>(entity)) {
        send_result(QuestResult::NOT_ACCEPTED);
        return;
    }

    auto& qc = world.GetComponent<QuestComponent>(entity);
    int idx = qc.FindQuest(quest_id);
    if (idx < 0) {
        send_result(QuestResult::NOT_ACCEPTED);
        return;
    }

    auto& q = qc.quests[idx];
    if (q.state == QuestState::REWARDED) {
        send_result(QuestResult::ALREADY_REWARDED);
        return;
    }
    if (q.state != QuestState::COMPLETE) {
        send_result(QuestResult::NOT_COMPLETE);
        return;
    }

    auto* tmpl = FindQuestTemplate(quest_id);
    if (!tmpl) {
        send_result(QuestResult::QUEST_NOT_FOUND);
        return;
    }

    // 보상 지급
    auto& reward = tmpl->reward;

    // EXP
    if (reward.exp > 0 && world.HasComponent<StatsComponent>(entity)) {
        world.GetComponent<StatsComponent>(entity).AddExp(reward.exp);
    }

    // 아이템
    if (reward.item_id > 0) {
        if (!world.HasComponent<InventoryComponent>(entity)) {
            world.AddComponent(entity, InventoryComponent{});
        }
        world.GetComponent<InventoryComponent>(entity).AddItem(
            reward.item_id, reward.item_count);
    }

    // 버프
    if (reward.buff_id > 0) {
        if (!world.HasComponent<BuffComponent>(entity)) {
            world.AddComponent(entity, BuffComponent{});
        }
        world.GetComponent<BuffComponent>(entity).ApplyBuff(reward.buff_id);
    }

    q.state = QuestState::REWARDED;

    // 응답
    char resp[15];
    resp[0] = static_cast<uint8_t>(QuestResult::SUCCESS);
    std::memcpy(resp + 1, &quest_id, 4);
    std::memcpy(resp + 5, &reward.exp, 4);
    std::memcpy(resp + 9, &reward.item_id, 4);
    std::memcpy(resp + 13, &reward.item_count, 2);
    auto pkt = BuildPacket(MsgType::QUEST_COMPLETE_RESULT, resp, 15);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));

    printf("[Quest] Entity %llu completed quest %d '%s' (+%d EXP)\n",
           entity, quest_id, tmpl->name, reward.exp);

    // EventBus: 퀘스트 완료 이벤트
    if (g_eventBus) {
        Event evt;
        evt.type = EventType::CUSTOM_1;  // QUEST_COMPLETED
        evt.source = entity;
        evt.param1 = quest_id;
        g_eventBus->Publish(evt);
    }
}

// ━━━ Session 11: Infrastructure 핸들러 ━━━

// TIMER_ADD: 타이머 추가
// 페이로드: [timer_id(4 int)] [duration_ms(4 int)] [interval_ms(4 int)]
void OnTimerAdd(World& world, Entity entity, const char* payload, int len) {
    if (len < 12) return;

    int32_t timer_id, dur_ms, int_ms;
    std::memcpy(&timer_id, payload, 4);
    std::memcpy(&dur_ms, payload + 4, 4);
    std::memcpy(&int_ms, payload + 8, 4);

    float duration = dur_ms / 1000.0f;
    float interval = int_ms / 1000.0f;

    if (!world.HasComponent<TimerComponent>(entity)) {
        world.AddComponent(entity, TimerComponent{});
    }

    auto& tc = world.GetComponent<TimerComponent>(entity);
    tc.AddTimer(timer_id, duration, interval);

    printf("[Timer] Entity %llu: added timer %d (%.1fs, interval=%.1fs)\n",
           entity, timer_id, duration, interval);
}

// TIMER_INFO: 타이머 정보 조회
// 응답: [active_timer_count(4)] [total_events_fired(4)]
void OnTimerInfo(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    int32_t active_count = 0;
    if (world.HasComponent<TimerComponent>(entity)) {
        active_count = static_cast<int32_t>(
            world.GetComponent<TimerComponent>(entity).timers.size());
    }

    char resp[8];
    std::memcpy(resp, &active_count, 4);
    std::memcpy(resp + 4, &g_total_events_fired, 4);
    auto pkt = BuildPacket(MsgType::TIMER_INFO, resp, 8);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// CONFIG_QUERY: 설정 조회
// 페이로드: [table_name_len(1)] [table_name(N)] [key_len(1)] [key(N)]
// 응답: CONFIG_RESP [found(1)] [data_len(2)] [data(N)]
void OnConfigQuery(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    if (len < 2 || !g_config) {
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::CONFIG_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    int off = 0;
    uint8_t tname_len = static_cast<uint8_t>(payload[off++]);
    if (off + tname_len > len) {
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::CONFIG_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }
    std::string table_name(payload + off, tname_len);
    off += tname_len;

    uint8_t key_len = (off < len) ? static_cast<uint8_t>(payload[off++]) : 0;
    std::string key_val;
    if (key_len > 0 && off + key_len <= len) {
        key_val = std::string(payload + off, key_len);
    }

    // 테이블 검색
    auto* table = g_config->GetTable(table_name);
    if (!table) {
        // JSON 설정 검색
        auto* settings = g_config->GetSettings(table_name);
        if (settings && !key_val.empty()) {
            std::string val = settings->GetString(key_val);
            if (!val.empty()) {
                std::string data = key_val + "=" + val;
                uint16_t dlen = static_cast<uint16_t>(data.size());
                std::vector<char> resp(3 + dlen);
                resp[0] = 1;  // found
                std::memcpy(resp.data() + 1, &dlen, 2);
                std::memcpy(resp.data() + 3, data.c_str(), dlen);
                auto pkt = BuildPacket(MsgType::CONFIG_RESP, resp.data(), static_cast<int>(resp.size()));
                g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
                return;
            }
        }
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::CONFIG_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // CSV에서 id로 검색
    const ConfigRow* row = nullptr;
    if (!key_val.empty()) {
        row = table->FindByKey("id", key_val);
        if (!row) row = table->FindByKey("name", key_val);
    }

    if (!row && table->GetRowCount() > 0) {
        // 키 없으면 첫 행
        row = &table->GetRow(0);
    }

    if (!row) {
        char resp[1] = {0};
        auto pkt = BuildPacket(MsgType::CONFIG_RESP, resp, 1);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        return;
    }

    // row를 "k=v|k=v" 포맷으로 직렬화
    std::string data;
    for (auto& [k, v] : row->GetAll()) {
        if (!data.empty()) data += "|";
        data += k + "=" + v;
    }

    uint16_t dlen = static_cast<uint16_t>(data.size());
    std::vector<char> resp(3 + dlen);
    resp[0] = 1;  // found
    std::memcpy(resp.data() + 1, &dlen, 2);
    std::memcpy(resp.data() + 3, data.c_str(), dlen);
    auto pkt = BuildPacket(MsgType::CONFIG_RESP, resp.data(), static_cast<int>(resp.size()));
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

// EVENT_SUB_COUNT: EventBus 상태 조회
// 응답: [subscriber_count_for_test(4)] [queue_size(4)]
void OnEventSubCount(World& world, Entity entity, const char* payload, int len) {
    auto& session = world.GetComponent<SessionComponent>(entity);

    int32_t sub_count = g_eventBus ? g_eventBus->GetSubscriberCount(EventType::TEST_EVENT) : 0;
    int32_t queue_size = g_eventBus ? g_eventBus->GetQueueSize() : 0;

    char resp[8];
    std::memcpy(resp, &sub_count, 4);
    std::memcpy(resp + 4, &queue_size, 4);
    auto pkt = BuildPacket(MsgType::EVENT_SUB_COUNT, resp, 8);
    g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
}

int main(int argc, char* argv[]) {
    // Session 10: 커맨드라인으로 포트 지정 가능 (기본 7777)
    // Session 17: FieldServer.exe <port> [gate_port] [max_ccu]
    uint16_t port = SERVER_PORT;
    if (argc > 1) {
        port = static_cast<uint16_t>(std::atoi(argv[1]));
    }
    uint16_t gate_port = 0;
    uint32_t max_ccu = 200;
    if (argc > 2) {
        gate_port = static_cast<uint16_t>(std::atoi(argv[2]));
    }
    if (argc > 3) {
        max_ccu = static_cast<uint32_t>(std::atoi(argv[3]));
    }

    printf("======================================\n");
    printf("  ECS Field Server - Session 29\n");
    printf("  +Condition/Spatial/Loot/Quest/Integration\n");
    printf("======================================\n\n");

    // ━━━ 1. 네트워크 엔진 (ECS 바깥) ━━━
    IOCPServer network;
    g_network = &network;

    if (!network.Start(port, WORKER_THREADS)) {
        printf("Failed to start network server!\n");
        return 1;
    }

    // ━━━ 2. ECS World + Infrastructure 생성 ━━━
    World world;
    EventBus eventBus;
    g_eventBus = &eventBus;

    ConfigLoader config;
    g_config = &config;

    // 기본 설정 로드 (테스트용 인메모리 데이터)
    config.LoadCSVFromString("monsters",
        "id,name,hp,attack,defense\n"
        "1,Goblin,100,15,5\n"
        "2,Wolf,200,25,10\n"
        "3,Dragon,5000,200,100\n");
    config.LoadJSONFromString("server",
        "{\"tick_rate\": 30, \"max_players\": 200, \"server_name\": \"Field-1\"}");

    // EventBus 구독: TIMER_EXPIRED 이벤트 카운트
    eventBus.Subscribe(EventType::TIMER_EXPIRED, [](const Event& e) {
        g_total_events_fired++;
        printf("[Event] TIMER_EXPIRED: entity=%llu, timer_id=%d\n", e.source, e.param1);
    });

    // 테스트 이벤트 구독 (테스트 검증용)
    eventBus.Subscribe(EventType::TEST_EVENT, [](const Event& e) {
        printf("[Event] TEST_EVENT: source=%llu, param1=%d\n", e.source, e.param1);
    });

    // ENTITY_DIED 구독: 퀘스트 진행 + 인스턴스 클리어 감지
    eventBus.Subscribe(EventType::ENTITY_DIED, [&world](const Event& e) {
        Entity dead = e.source;
        Entity killer = e.target;

        // 1) 킬러가 퀘스트 컴포넌트를 가지고 있으면 진행도 업데이트
        if (killer != 0 && world.IsAlive(killer) &&
            world.HasComponent<QuestComponent>(killer)) {
            int32_t monster_id = 0;
            if (world.HasComponent<MonsterComponent>(dead)) {
                monster_id = static_cast<int32_t>(
                    world.GetComponent<MonsterComponent>(dead).monster_id);
            }
            world.GetComponent<QuestComponent>(killer).OnMonsterKilled(monster_id);
            printf("[Quest] Entity %llu killed monster (id=%d), quest progress updated\n",
                   killer, monster_id);
        }

        // 2) 인스턴스 던전 클리어 감지
        if (world.HasComponent<InstanceMonsterComponent>(dead)) {
            uint32_t iid = world.GetComponent<InstanceMonsterComponent>(dead).instance_id;
            auto* inst = FindInstance(iid);
            if (inst) {
                // 살아있는 몬스터 수 확인
                int alive = 0;
                for (auto me : inst->monsters) {
                    if (world.IsAlive(me) && world.HasComponent<StatsComponent>(me) &&
                        world.GetComponent<StatsComponent>(me).IsAlive())
                        alive++;
                }
                if (alive == 0) {
                    printf("[Instance] Instance %u CLEARED! All monsters defeated.\n", iid);
                    // 클리어 보상: 인스턴스 내 모든 플레이어에게 보너스 EXP
                    auto* tmpl = FindDungeonTemplate(inst->dungeon_type);
                    int32_t clear_exp = tmpl ? tmpl->monster_level * 50 : 100;
                    for (auto pe : inst->players) {
                        if (world.IsAlive(pe) && world.HasComponent<StatsComponent>(pe)) {
                            world.GetComponent<StatsComponent>(pe).AddExp(clear_exp);
                            printf("[Instance] Entity %llu: +%d clear bonus EXP\n", pe, clear_exp);
                            if (world.HasComponent<SessionComponent>(pe)) {
                                // STAT_SYNC로 EXP 변경 알림
                                SendStatSync(world, pe);
                            }
                        }
                    }
                }
            }
        }
    });

    // ━━━ 3. System 등록 (실행 순서가 곧 게임 루프) ━━━
    //
    // [1] NetworkSystem      ← IOCP 이벤트 → RecvBuffer 적재
    // [2] MessageDispatch    ← RecvBuffer → 패킷 조립 → 핸들러 호출
    //                           (OnMove → dirty, OnChannelJoin → 채널 전환,
    //                            OnZoneEnter → 맵 전환 + DISAPPEAR,
    //                            OnHandoffRequest → 직렬화, OnHandoffRestore → 복원)
    // [3] InterestSystem     ← 셀 전환 감지 + APPEAR/DISAPPEAR (같은 존+채널만)
    // [4] BroadcastSystem    ← dirty Entity의 위치를 근처 셀 + 같은 존+채널에만 전파
    // [5] GhostSystem        ← 경계 근처 Entity의 Ghost 생성/동기화/파괴
    //
    world.AddSystem<NetworkSystem>(network);

    auto& dispatch = world.AddSystemAndGet<MessageDispatchSystem>(network);
    dispatch.RegisterHandler(MsgType::ECHO, OnEcho);
    dispatch.RegisterHandler(MsgType::PING, OnPing);
    dispatch.RegisterHandler(MsgType::STATS, OnStats);
    dispatch.RegisterHandler(MsgType::MOVE, OnMove);
    dispatch.RegisterHandler(MsgType::POS_QUERY, OnPosQuery);
    dispatch.RegisterHandler(MsgType::CHANNEL_JOIN, OnChannelJoin);      // Session 5
    dispatch.RegisterHandler(MsgType::ZONE_ENTER, OnZoneEnter);          // Session 6
    dispatch.RegisterHandler(MsgType::HANDOFF_REQUEST, OnHandoffRequest); // Session 7
    dispatch.RegisterHandler(MsgType::HANDOFF_RESTORE, OnHandoffRestore); // Session 7
    dispatch.RegisterHandler(MsgType::GHOST_QUERY, OnGhostQuery);         // Session 8
    dispatch.RegisterHandler(MsgType::LOGIN, OnLogin);                     // Session 9
    dispatch.RegisterHandler(MsgType::CHAR_LIST_REQ, OnCharListReq);       // Session 9
    dispatch.RegisterHandler(MsgType::CHAR_SELECT, OnCharSelect);          // Session 9
    dispatch.RegisterHandler(MsgType::TIMER_ADD, OnTimerAdd);              // Session 11
    dispatch.RegisterHandler(MsgType::TIMER_INFO, OnTimerInfo);            // Session 11
    dispatch.RegisterHandler(MsgType::CONFIG_QUERY, OnConfigQuery);        // Session 11
    dispatch.RegisterHandler(MsgType::EVENT_SUB_COUNT, OnEventSubCount);   // Session 11
    dispatch.RegisterHandler(MsgType::STAT_QUERY, OnStatQuery);            // Session 12
    dispatch.RegisterHandler(MsgType::STAT_ADD_EXP, OnStatAddExp);         // Session 12
    dispatch.RegisterHandler(MsgType::STAT_TAKE_DMG, OnStatTakeDmg);       // Session 12
    dispatch.RegisterHandler(MsgType::STAT_HEAL, OnStatHeal);              // Session 12
    dispatch.RegisterHandler(MsgType::ATTACK_REQ, OnAttackReq);            // Session 13
    dispatch.RegisterHandler(MsgType::RESPAWN_REQ, OnRespawnReq);          // Session 13
    dispatch.RegisterHandler(MsgType::ZONE_TRANSFER_REQ, OnZoneTransfer);  // Session 16
    dispatch.RegisterHandler(MsgType::SKILL_LIST_REQ, OnSkillListReq);     // Session 19
    dispatch.RegisterHandler(MsgType::SKILL_USE, OnSkillUse);               // Session 19
    dispatch.RegisterHandler(MsgType::PARTY_CREATE, OnPartyCreate);         // Session 20
    dispatch.RegisterHandler(MsgType::PARTY_INVITE, OnPartyInvite);         // Session 20
    dispatch.RegisterHandler(MsgType::PARTY_ACCEPT, OnPartyAccept);         // Session 20
    dispatch.RegisterHandler(MsgType::PARTY_LEAVE, OnPartyLeave);           // Session 20
    dispatch.RegisterHandler(MsgType::PARTY_KICK, OnPartyKick);             // Session 20
    dispatch.RegisterHandler(MsgType::INSTANCE_CREATE, OnInstanceCreate);   // Session 21
    dispatch.RegisterHandler(MsgType::INSTANCE_LEAVE, OnInstanceLeave);     // Session 21
    dispatch.RegisterHandler(MsgType::INSTANCE_INFO, OnInstanceInfo);       // Session 21
    dispatch.RegisterHandler(MsgType::MATCH_ENQUEUE, OnMatchEnqueue);       // Session 22
    dispatch.RegisterHandler(MsgType::MATCH_DEQUEUE, OnMatchDequeue);       // Session 22
    dispatch.RegisterHandler(MsgType::MATCH_ACCEPT, OnMatchAccept);         // Session 22
    dispatch.RegisterHandler(MsgType::INVENTORY_REQ, OnInventoryReq);       // Session 23
    dispatch.RegisterHandler(MsgType::ITEM_ADD, OnItemAdd);                 // Session 23
    dispatch.RegisterHandler(MsgType::ITEM_USE, OnItemUse);                 // Session 23
    dispatch.RegisterHandler(MsgType::ITEM_EQUIP, OnItemEquip);             // Session 23
    dispatch.RegisterHandler(MsgType::ITEM_UNEQUIP, OnItemUnequip);         // Session 23
    dispatch.RegisterHandler(MsgType::BUFF_LIST_REQ, OnBuffListReq);        // Session 24
    dispatch.RegisterHandler(MsgType::BUFF_APPLY_REQ, OnBuffApply);         // Session 24
    dispatch.RegisterHandler(MsgType::BUFF_REMOVE_REQ, OnBuffRemove);       // Session 24
    dispatch.RegisterHandler(MsgType::CONDITION_EVAL, OnConditionEval);     // Session 25
    dispatch.RegisterHandler(MsgType::SPATIAL_QUERY_REQ, OnSpatialQuery);   // Session 26
    dispatch.RegisterHandler(MsgType::LOOT_ROLL_REQ, OnLootRoll);           // Session 27
    dispatch.RegisterHandler(MsgType::QUEST_LIST_REQ, OnQuestListReq);     // Session 28
    dispatch.RegisterHandler(MsgType::QUEST_ACCEPT, OnQuestAccept);         // Session 28
    dispatch.RegisterHandler(MsgType::QUEST_PROGRESS, OnQuestProgress);     // Session 28
    dispatch.RegisterHandler(MsgType::QUEST_COMPLETE, OnQuestComplete);     // Session 28

    world.AddSystem<MonsterAISystem>(network);                   // Session 14
    world.AddSystem<InterestSystem>(network);
    world.AddSystem<BroadcastSystem>(network);
    world.AddSystem<GhostSystem>(network);          // Session 8
    world.AddSystem<TimerSystem>(eventBus);          // Session 11
    world.AddSystem<StatsSystem>(eventBus);          // Session 12
    world.AddSystem<CombatSystem>();                  // Session 13

    // Session 14: 몬스터 스폰
    SpawnMonsters(world);

    printf("\n[Main] Server running. Press Ctrl+C to stop.\n");
    printf("[Main] Listening on port %d, tick rate: %.0f/s\n", port, TICK_RATE);

    // ━━━ Session 17: Gate 연결 + 등록 ━━━
    TCPClient gate_client;
    if (gate_port > 0) {
        printf("[Main] Connecting to Gate at 127.0.0.1:%d...\n", gate_port);
        bool connected = false;
        for (int attempt = 0; attempt < 5; attempt++) {
            if (gate_client.Connect("127.0.0.1", gate_port)) {
                connected = true;
                break;
            }
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }

        if (connected) {
            // FIELD_REGISTER: [port(2) max_ccu(4) name_len(1) name(N)]
            char reg_buf[64];
            std::memcpy(reg_buf, &port, 2);
            std::memcpy(reg_buf + 2, &max_ccu, 4);
            const char* sname = "Field";
            uint8_t name_len = static_cast<uint8_t>(std::strlen(sname));
            reg_buf[6] = static_cast<char>(name_len);
            std::memcpy(reg_buf + 7, sname, name_len);

            auto pkt = BuildPacket(MsgType::FIELD_REGISTER, reg_buf, 7 + name_len);
            gate_client.Send(pkt.data(), static_cast<int>(pkt.size()));

            // FIELD_REGISTER_ACK 수신 대기
            char ack_buf[256];
            int ack_len = gate_client.RecvWithTimeout(ack_buf, 256, 2000);
            if (ack_len > 0) {
                printf("[Main] Registered with Gate (max_ccu=%d)\n", max_ccu);
            }
        } else {
            printf("[Main] WARNING: Could not connect to Gate\n");
        }
    }

    float heartbeat_timer = 0.0f;
    printf("\n");

    // ━━━ 4. 게임 루프 ━━━
    auto prev_time = std::chrono::high_resolution_clock::now();

    while (network.IsRunning()) {
        auto now = std::chrono::high_resolution_clock::now();
        float dt = std::chrono::duration<float>(now - prev_time).count();

        if (dt >= TICK_INTERVAL) {
            prev_time = now;

            // 모든 System을 등록된 순서대로 실행
            world.Update(dt);

            // Session 17: Gate 하트비트 전송
            if (gate_client.IsConnected()) {
                heartbeat_timer += dt;
                if (heartbeat_timer >= HEARTBEAT_INTERVAL) {
                    heartbeat_timer = 0.0f;

                    // CCU 계산: SessionComponent를 가진 Entity 수
                    uint32_t ccu = 0;
                    world.ForEach<SessionComponent>([&](Entity e, SessionComponent& s) {
                        if (s.connected) ccu++;
                    });

                    // FIELD_HEARTBEAT: [port(2) ccu(4) max_ccu(4)]
                    char hb[10];
                    std::memcpy(hb, &port, 2);
                    std::memcpy(hb + 2, &ccu, 4);
                    std::memcpy(hb + 6, &max_ccu, 4);

                    auto hb_pkt = BuildPacket(MsgType::FIELD_HEARTBEAT, hb, 10);
                    gate_client.Send(hb_pkt.data(), static_cast<int>(hb_pkt.size()));
                }
            }
        } else {
            // CPU를 쉬게 하기
            auto sleep_ms = static_cast<int>((TICK_INTERVAL - dt) * 1000.0f);
            if (sleep_ms > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
            }
        }
    }

    gate_client.Disconnect();
    printf("[Main] Server shutting down...\n");
    g_network = nullptr;
    g_eventBus = nullptr;
    g_config = nullptr;
    return 0;
}
