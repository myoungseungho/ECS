#include "BroadcastSystem.h"
#include "../Core/World.h"
#include "../Components/NetworkComponents.h"
#include "../Components/GameComponents.h"
#include "../Components/SpatialComponents.h"
#include "../Components/ChannelComponents.h"    // Session 5
#include "../Components/ZoneComponents.h"       // Session 6
#include "../Components/PacketComponents.h"
#include <cstdio>
#include <cstring>
#include <vector>

BroadcastSystem::BroadcastSystem(IOCPServer& server)
    : server_(server) {}

void BroadcastSystem::Update(World& world, float dt) {
    // 1단계: dirty인 Entity를 수집
    struct DirtyInfo {
        Entity entity;
        uint64_t session_id;
        float x, y, z;
        int cell_x, cell_y;
        bool has_grid;
        int channel_id;     // Session 5
        bool has_channel;   // Session 5
        int zone_id;        // Session 6
        bool has_zone;      // Session 6
    };
    std::vector<DirtyInfo> dirty_list;

    world.ForEach<PositionComponent, SessionComponent>(
        [&](Entity entity, PositionComponent& pos, SessionComponent& session) {
            if (!pos.position_dirty) return;
            if (!session.connected) return;

            int cx = 0, cy = 0;
            bool has_grid = world.HasComponent<GridCellComponent>(entity);
            if (has_grid) {
                auto& grid = world.GetComponent<GridCellComponent>(entity);
                cx = grid.cell_x;
                cy = grid.cell_y;
            }

            // Session 5: 채널 정보 수집
            bool has_ch = world.HasComponent<ChannelComponent>(entity);
            int ch_id = 0;
            if (has_ch) {
                ch_id = world.GetComponent<ChannelComponent>(entity).channel_id;
            }

            // Session 6: 존 정보 수집
            bool has_zone = world.HasComponent<ZoneComponent>(entity);
            int zone_id = 0;
            if (has_zone) {
                zone_id = world.GetComponent<ZoneComponent>(entity).zone_id;
            }

            dirty_list.push_back({entity, session.session_id,
                                  pos.x, pos.y, pos.z, cx, cy, has_grid,
                                  ch_id, has_ch,
                                  zone_id, has_zone});
        }
    );

    if (dirty_list.empty()) return;

    // 2단계: 근처 셀의 같은 존 + 같은 채널 Entity에게만 MOVE_BROADCAST
    for (auto& dirty : dirty_list) {
        char payload[20];
        std::memcpy(payload, &dirty.entity, 8);
        std::memcpy(payload + 8, &dirty.x, 4);
        std::memcpy(payload + 12, &dirty.y, 4);
        std::memcpy(payload + 16, &dirty.z, 4);

        auto packet = BuildPacket(MsgType::MOVE_BROADCAST, payload, 20);

        world.ForEach<SessionComponent>(
            [&](Entity other_entity, SessionComponent& other_session) {
                if (other_entity == dirty.entity) return;
                if (!other_session.connected) return;

                // AOI 필터 (Session 4)
                if (!dirty.has_grid) return;
                if (!world.HasComponent<GridCellComponent>(other_entity)) return;

                auto& other_grid = world.GetComponent<GridCellComponent>(other_entity);
                if (!IsNearbyCell(dirty.cell_x, dirty.cell_y,
                                  other_grid.cell_x, other_grid.cell_y)) {
                    return;  // 멀리 있음 → 전송 안 함
                }

                // 존 필터 (Session 6 — 채널 필터보다 먼저!)
                // 둘 다 존 없음 → 필터 안 함 (Session 1-5 호환)
                // 하나라도 존 있음 → 같은 존이어야 함
                bool other_has_zone = world.HasComponent<ZoneComponent>(other_entity);
                if (dirty.has_zone || other_has_zone) {
                    if (!dirty.has_zone || !other_has_zone) return;
                    if (world.GetComponent<ZoneComponent>(other_entity).zone_id != dirty.zone_id) return;
                }

                // 채널 필터 (Session 5)
                // 둘 다 채널 없음 → 필터 안 함 (Session 1-4 호환)
                // 하나라도 채널 있음 → 같은 채널이어야 함
                bool other_has_ch = world.HasComponent<ChannelComponent>(other_entity);
                if (dirty.has_channel || other_has_ch) {
                    if (!dirty.has_channel || !other_has_ch) return;
                    if (world.GetComponent<ChannelComponent>(other_entity).channel_id != dirty.channel_id) return;
                }

                server_.SendTo(other_session.session_id,
                              packet.data(),
                              static_cast<int>(packet.size()));
            }
        );
    }

    // 3단계: dirty 플래그 해제
    for (auto& dirty : dirty_list) {
        if (world.IsAlive(dirty.entity) &&
            world.HasComponent<PositionComponent>(dirty.entity)) {
            world.GetComponent<PositionComponent>(dirty.entity).position_dirty = false;
        }
    }
}
