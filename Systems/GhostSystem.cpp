#include "GhostSystem.h"
#include "../Core/World.h"
#include "../Components/GhostComponents.h"
#include "../Components/GameComponents.h"
#include "../Components/ZoneComponents.h"
#include "../Components/ChannelComponents.h"
#include "../Components/SpatialComponents.h"
#include "../Components/NetworkComponents.h"
#include "../Components/PacketComponents.h"
#include <cstring>
#include <cstdio>
#include <vector>

GhostSystem::GhostSystem(IOCPServer& server) : server_(server) {}

void GhostSystem::Update(World& world, float dt) {
    // ═══ Phase 1: 기존 Ghost 정리 ═══
    // 원본이 죽었거나 경계 이탈 → Ghost 파괴 대상 수집
    std::vector<Entity> to_destroy;

    world.ForEach<GhostComponent>([&](Entity ghost, GhostComponent& gc) {
        // 원본 Entity가 죽었거나 필수 Component가 없으면 파괴
        if (!world.IsAlive(gc.origin_entity) ||
            !world.HasComponent<PositionComponent>(gc.origin_entity) ||
            !world.HasComponent<ZoneComponent>(gc.origin_entity)) {
            to_destroy.push_back(ghost);
            return;
        }

        // 원본이 경계에서 벗어남 → 파괴
        auto& orig_pos = world.GetComponent<PositionComponent>(gc.origin_entity);
        auto& orig_zone = world.GetComponent<ZoneComponent>(gc.origin_entity);
        if (!IsNearBoundary(orig_pos.x, orig_pos.y, orig_zone.zone_id)) {
            to_destroy.push_back(ghost);
        }
    });

    // Phase 1b: Ghost 파괴 실행 (DISAPPEAR 전송 후 Entity 삭제)
    for (Entity ghost : to_destroy) {
        SendGhostDisappear(world, ghost);
        printf("[Ghost] Destroyed ghost %llu\n", ghost);
        world.DestroyEntity(ghost);
    }

    // ═══ Phase 2: 새 Ghost 생성 ═══
    struct NeedGhost {
        Entity origin;
        float x, y, z;
        int origin_zone;
        int target_zone;
        int channel_id;
        bool has_channel;
    };
    std::vector<NeedGhost> needs;

    world.ForEach<PositionComponent, ZoneComponent, SessionComponent>(
        [&](Entity entity, PositionComponent& pos, ZoneComponent& zone,
            SessionComponent& sess) {
            if (!sess.connected) return;
            // Ghost 자신은 제외 (SessionComponent 없어서 여기 안 옴, 안전장치)
            if (world.HasComponent<GhostComponent>(entity)) return;

            // 경계 근처인지 확인
            if (!IsNearBoundary(pos.x, pos.y, zone.zone_id)) return;

            int adj = GetAdjacentZone(zone.zone_id);
            if (adj == 0) return;

            // 이미 이 Entity에 대한 Ghost가 있는지 확인
            bool ghost_exists = false;
            world.ForEach<GhostComponent>([&](Entity g, GhostComponent& gc) {
                if (gc.origin_entity == entity) ghost_exists = true;
            });
            if (ghost_exists) return;

            bool has_ch = world.HasComponent<ChannelComponent>(entity);
            int ch = has_ch ? world.GetComponent<ChannelComponent>(entity).channel_id : 0;

            needs.push_back({entity, pos.x, pos.y, pos.z,
                            zone.zone_id, adj, ch, has_ch});
        }
    );

    // Phase 2b: Ghost Entity 생성 + APPEAR 전송
    for (auto& ng : needs) {
        Entity ghost = world.CreateEntity();
        world.AddComponent(ghost, GhostComponent{ng.origin, ng.origin_zone});
        world.AddComponent(ghost, PositionComponent{ng.x, ng.y, ng.z, false});
        world.AddComponent(ghost, ZoneComponent{ng.target_zone});
        if (ng.has_channel) {
            world.AddComponent(ghost, ChannelComponent{ng.channel_id});
        }

        SendGhostAppear(world, ghost, ng.x, ng.y, ng.z);

        printf("[Ghost] Created ghost %llu for entity %llu (zone %d -> %d)\n",
               ghost, ng.origin, ng.origin_zone, ng.target_zone);
    }

    // ═══ Phase 3: 기존 Ghost 위치 동기화 ═══
    world.ForEach<GhostComponent, PositionComponent>(
        [&](Entity ghost, GhostComponent& gc, PositionComponent& gpos) {
            if (!world.IsAlive(gc.origin_entity)) return;
            if (!world.HasComponent<PositionComponent>(gc.origin_entity)) return;

            auto& orig_pos = world.GetComponent<PositionComponent>(gc.origin_entity);

            // 위치 변화 감지
            float dx = orig_pos.x - gpos.x;
            float dy = orig_pos.y - gpos.y;
            float dz = orig_pos.z - gpos.z;
            if (dx*dx + dy*dy + dz*dz < 0.001f) return;

            // 동기화
            gpos.x = orig_pos.x;
            gpos.y = orig_pos.y;
            gpos.z = orig_pos.z;

            // 근처 실제 플레이어에게 MOVE_BROADCAST
            SendGhostMoveBroadcast(world, ghost, gpos.x, gpos.y, gpos.z);
        }
    );
}

// Ghost의 APPEAR를 인접 존의 실제 플레이어에게 전송
void GhostSystem::SendGhostAppear(World& world, Entity ghost, float x, float y, float z) {
    if (!world.HasComponent<ZoneComponent>(ghost)) return;
    int ghost_zone = world.GetComponent<ZoneComponent>(ghost).zone_id;
    bool has_ch = world.HasComponent<ChannelComponent>(ghost);
    int ghost_ch = has_ch ? world.GetComponent<ChannelComponent>(ghost).channel_id : 0;

    int gcx = ToCell(x);
    int gcy = ToCell(y);

    char p[20];
    std::memcpy(p, &ghost, 8);
    std::memcpy(p + 8, &x, 4);
    std::memcpy(p + 12, &y, 4);
    std::memcpy(p + 16, &z, 4);
    auto pkt = BuildPacket(MsgType::APPEAR, p, 20);

    world.ForEach<SessionComponent, ZoneComponent, GridCellComponent>(
        [&](Entity player, SessionComponent& sess, ZoneComponent& pz,
            GridCellComponent& pgrid) {
            if (!sess.connected) return;
            if (pz.zone_id != ghost_zone) return;
            if (!IsNearbyCell(gcx, gcy, pgrid.cell_x, pgrid.cell_y)) return;

            if (has_ch) {
                if (!world.HasComponent<ChannelComponent>(player)) return;
                if (world.GetComponent<ChannelComponent>(player).channel_id != ghost_ch) return;
            }

            server_.SendTo(sess.session_id, pkt.data(), static_cast<int>(pkt.size()));
        }
    );
}

// Ghost의 DISAPPEAR를 인접 존의 실제 플레이어에게 전송
void GhostSystem::SendGhostDisappear(World& world, Entity ghost) {
    if (!world.HasComponent<ZoneComponent>(ghost)) return;
    if (!world.HasComponent<PositionComponent>(ghost)) return;

    int ghost_zone = world.GetComponent<ZoneComponent>(ghost).zone_id;
    auto& gpos = world.GetComponent<PositionComponent>(ghost);
    bool has_ch = world.HasComponent<ChannelComponent>(ghost);
    int ghost_ch = has_ch ? world.GetComponent<ChannelComponent>(ghost).channel_id : 0;

    int gcx = ToCell(gpos.x);
    int gcy = ToCell(gpos.y);

    char p[8];
    std::memcpy(p, &ghost, 8);
    auto pkt = BuildPacket(MsgType::DISAPPEAR, p, 8);

    world.ForEach<SessionComponent, ZoneComponent, GridCellComponent>(
        [&](Entity player, SessionComponent& sess, ZoneComponent& pz,
            GridCellComponent& pgrid) {
            if (!sess.connected) return;
            if (pz.zone_id != ghost_zone) return;
            if (!IsNearbyCell(gcx, gcy, pgrid.cell_x, pgrid.cell_y)) return;

            if (has_ch) {
                if (!world.HasComponent<ChannelComponent>(player)) return;
                if (world.GetComponent<ChannelComponent>(player).channel_id != ghost_ch) return;
            }

            server_.SendTo(sess.session_id, pkt.data(), static_cast<int>(pkt.size()));
        }
    );
}

// Ghost의 위치 변경을 인접 존의 실제 플레이어에게 전송
void GhostSystem::SendGhostMoveBroadcast(World& world, Entity ghost, float x, float y, float z) {
    if (!world.HasComponent<ZoneComponent>(ghost)) return;
    int ghost_zone = world.GetComponent<ZoneComponent>(ghost).zone_id;
    bool has_ch = world.HasComponent<ChannelComponent>(ghost);
    int ghost_ch = has_ch ? world.GetComponent<ChannelComponent>(ghost).channel_id : 0;

    int gcx = ToCell(x);
    int gcy = ToCell(y);

    char payload[20];
    std::memcpy(payload, &ghost, 8);
    std::memcpy(payload + 8, &x, 4);
    std::memcpy(payload + 12, &y, 4);
    std::memcpy(payload + 16, &z, 4);
    auto pkt = BuildPacket(MsgType::MOVE_BROADCAST, payload, 20);

    world.ForEach<SessionComponent, ZoneComponent, GridCellComponent>(
        [&](Entity player, SessionComponent& sess, ZoneComponent& pz,
            GridCellComponent& pgrid) {
            if (!sess.connected) return;
            if (pz.zone_id != ghost_zone) return;
            if (!IsNearbyCell(gcx, gcy, pgrid.cell_x, pgrid.cell_y)) return;

            if (has_ch) {
                if (!world.HasComponent<ChannelComponent>(player)) return;
                if (world.GetComponent<ChannelComponent>(player).channel_id != ghost_ch) return;
            }

            server_.SendTo(sess.session_id, pkt.data(), static_cast<int>(pkt.size()));
        }
    );
}
