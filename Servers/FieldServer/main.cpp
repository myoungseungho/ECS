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

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <chrono>
#include <thread>

// 서버 설정
constexpr uint16_t SERVER_PORT = 7777;
constexpr int WORKER_THREADS = 2;
constexpr float TICK_RATE = 30.0f;  // 초당 30틱
constexpr float TICK_INTERVAL = 1.0f / TICK_RATE;

// 전역 네트워크 포인터 (핸들러에서 접근용)
IOCPServer* g_network = nullptr;

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
        // 계정 없음
        char resp[5] = {};
        resp[0] = 1;  // 계정 없음
        auto pkt = BuildPacket(MsgType::LOGIN_RESULT, resp, 5);
        g_network->SendTo(session.session_id, pkt.data(), static_cast<int>(pkt.size()));
        printf("[Login] FAIL: account not found '%s'\n", username.c_str());
        return;
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

int main(int argc, char* argv[]) {
    // Session 10: 커맨드라인으로 포트 지정 가능 (기본 7777)
    uint16_t port = SERVER_PORT;
    if (argc > 1) {
        port = static_cast<uint16_t>(std::atoi(argv[1]));
    }

    printf("======================================\n");
    printf("  ECS Field Server - Session 10\n");
    printf("  Full Pipeline (Gate+Login+Game)\n");
    printf("======================================\n\n");

    // ━━━ 1. 네트워크 엔진 (ECS 바깥) ━━━
    IOCPServer network;
    g_network = &network;

    if (!network.Start(port, WORKER_THREADS)) {
        printf("Failed to start network server!\n");
        return 1;
    }

    // ━━━ 2. ECS World 생성 ━━━
    World world;

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

    world.AddSystem<InterestSystem>(network);
    world.AddSystem<BroadcastSystem>(network);
    world.AddSystem<GhostSystem>(network);          // Session 8

    printf("\n[Main] Server running. Press Ctrl+C to stop.\n");
    printf("[Main] Listening on port %d, tick rate: %.0f/s\n\n", port, TICK_RATE);

    // ━━━ 4. 게임 루프 ━━━
    auto prev_time = std::chrono::high_resolution_clock::now();

    while (network.IsRunning()) {
        auto now = std::chrono::high_resolution_clock::now();
        float dt = std::chrono::duration<float>(now - prev_time).count();

        if (dt >= TICK_INTERVAL) {
            prev_time = now;

            // 모든 System을 등록된 순서대로 실행
            world.Update(dt);
        } else {
            // CPU를 쉬게 하기
            auto sleep_ms = static_cast<int>((TICK_INTERVAL - dt) * 1000.0f);
            if (sleep_ms > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
            }
        }
    }

    printf("[Main] Server shutting down...\n");
    g_network = nullptr;
    return 0;
}
