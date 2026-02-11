#include "InterestSystem.h"
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
#include <climits>

InterestSystem::InterestSystem(IOCPServer& server)
    : server_(server) {}

void InterestSystem::SendAppear(Entity entity, float x, float y, float z, uint64_t to_session) {
    // APPEAR 페이로드: [entity_id(8)] [x(4)] [y(4)] [z(4)] = 20바이트
    char payload[20];
    std::memcpy(payload, &entity, 8);
    std::memcpy(payload + 8, &x, 4);
    std::memcpy(payload + 12, &y, 4);
    std::memcpy(payload + 16, &z, 4);
    auto pkt = BuildPacket(MsgType::APPEAR, payload, 20);
    server_.SendTo(to_session, pkt.data(), static_cast<int>(pkt.size()));
}

void InterestSystem::SendDisappear(Entity entity, uint64_t to_session) {
    // DISAPPEAR 페이로드: [entity_id(8)] = 8바이트
    char payload[8];
    std::memcpy(payload, &entity, 8);
    auto pkt = BuildPacket(MsgType::DISAPPEAR, payload, 8);
    server_.SendTo(to_session, pkt.data(), static_cast<int>(pkt.size()));
}

void InterestSystem::Update(World& world, float dt) {
    // 이동한(dirty) Entity 중 셀 갱신이 필요한 것들을 수집
    struct MoverInfo {
        Entity entity;
        uint64_t session_id;
        float x, y, z;
        int new_cx, new_cy;
        int old_cx, old_cy;
        bool first_time;  // GridCellComponent가 없었음 (첫 진입)
        int channel_id;   // Session 5
        bool has_channel;  // Session 5
        int zone_id;       // Session 6
        bool has_zone;     // Session 6
    };
    std::vector<MoverInfo> movers;

    world.ForEach<PositionComponent, SessionComponent>(
        [&](Entity entity, PositionComponent& pos, SessionComponent& session) {
            if (!pos.position_dirty) return;
            if (!session.connected) return;

            int new_cx = ToCell(pos.x);
            int new_cy = ToCell(pos.y);

            bool first_time = !world.HasComponent<GridCellComponent>(entity);
            int old_cx = INT_MIN;
            int old_cy = INT_MIN;

            if (!first_time) {
                auto& grid = world.GetComponent<GridCellComponent>(entity);
                old_cx = grid.cell_x;
                old_cy = grid.cell_y;

                // 셀이 안 바뀌었으면 전환 처리 불필요
                if (old_cx == new_cx && old_cy == new_cy) {
                    grid.cell_changed = false;
                    return;
                }
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

            movers.push_back({entity, session.session_id,
                              pos.x, pos.y, pos.z,
                              new_cx, new_cy, old_cx, old_cy, first_time,
                              ch_id, has_ch,
                              zone_id, has_zone});
        }
    );

    if (movers.empty()) return;

    // 각 셀 전환 Entity에 대해 APPEAR/DISAPPEAR 처리
    for (auto& mover : movers) {
        // 다른 모든 Entity(GridCell이 있는)를 순회하며 전환 판정
        world.ForEach<GridCellComponent, SessionComponent, PositionComponent>(
            [&](Entity other, GridCellComponent& other_grid,
                SessionComponent& other_session, PositionComponent& other_pos) {

                if (other == mover.entity) return;
                if (!other_session.connected) return;

                // Session 6: 존 필터 (최상위 — 맵이 다르면 무조건 무시)
                // 둘 다 존 없음 → 필터 안 함 (Session 1-5 호환)
                // 하나라도 존 있음 → 같은 존이어야 함
                bool other_has_zone = world.HasComponent<ZoneComponent>(other);
                if (mover.has_zone || other_has_zone) {
                    if (!mover.has_zone || !other_has_zone) return;
                    if (world.GetComponent<ZoneComponent>(other).zone_id != mover.zone_id) return;
                }

                // Session 5: 채널 필터
                // 둘 다 채널 없음 → 필터 안 함 (Session 1-4 호환)
                // 하나라도 채널 있음 → 같은 채널이어야 함
                bool other_has_ch = world.HasComponent<ChannelComponent>(other);
                if (mover.has_channel || other_has_ch) {
                    if (!mover.has_channel || !other_has_ch) return;
                    if (world.GetComponent<ChannelComponent>(other).channel_id != mover.channel_id) return;
                }

                bool was_nearby = false;
                if (!mover.first_time) {
                    was_nearby = IsNearbyCell(mover.old_cx, mover.old_cy,
                                              other_grid.cell_x, other_grid.cell_y);
                }

                bool is_nearby = IsNearbyCell(mover.new_cx, mover.new_cy,
                                              other_grid.cell_x, other_grid.cell_y);

                if (!was_nearby && is_nearby) {
                    // 새로 시야에 들어옴 → 양방향 APPEAR
                    SendAppear(mover.entity, mover.x, mover.y, mover.z,
                               other_session.session_id);
                    SendAppear(other, other_pos.x, other_pos.y, other_pos.z,
                               mover.session_id);

                    printf("[Interest] APPEAR: Entity %llu <-> Entity %llu\n",
                           mover.entity, other);
                }
                else if (was_nearby && !is_nearby) {
                    // 시야에서 벗어남 → 양방향 DISAPPEAR
                    SendDisappear(mover.entity, other_session.session_id);
                    SendDisappear(other, mover.session_id);

                    printf("[Interest] DISAPPEAR: Entity %llu <-> Entity %llu\n",
                           mover.entity, other);
                }
            }
        );

        // GridCellComponent 갱신 (또는 첫 부착)
        if (mover.first_time) {
            GridCellComponent grid;
            grid.cell_x = mover.new_cx;
            grid.cell_y = mover.new_cy;
            grid.prev_cell_x = INT_MIN;
            grid.prev_cell_y = INT_MIN;
            grid.cell_changed = true;
            world.AddComponent(mover.entity, grid);
        } else {
            auto& grid = world.GetComponent<GridCellComponent>(mover.entity);
            grid.prev_cell_x = grid.cell_x;
            grid.prev_cell_y = grid.cell_y;
            grid.cell_x = mover.new_cx;
            grid.cell_y = mover.new_cy;
            grid.cell_changed = true;
        }
    }
}
