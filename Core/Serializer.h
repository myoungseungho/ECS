#pragma once

// ━━━ Entity Serializer (Session 7) ━━━
//
// Entity의 게임 상태(Component들)를 바이트 배열로 직렬화/역직렬화.
// 서버 간 핸드오프 시 캐릭터 상태를 전달하는 데 사용.
//
// 직렬화 대상 Component:
//   - PositionComponent (x, y, z)  — position_dirty는 제외 (일시적 플래그)
//   - ZoneComponent (zone_id)
//   - ChannelComponent (channel_id)
//
// 직렬화 제외:
//   - SessionComponent       — 서버 로컬 (네트워크 세션은 서버마다 다름)
//   - RecvBufferComponent    — 서버 로컬 (수신 버퍼)
//   - GridCellComponent      — 파생 데이터 (PositionComponent에서 계산)
//
// 바이너리 형식 (little-endian):
//   [component_count (2 uint16)]
//   [block] [block] ...
//
//   각 block:
//     [type_id (2 uint16)] [data_size (2 uint16)] [data (N bytes)]
//
// 예: Position(100,200,0) + Zone(2) + Channel(3)
//   count=3 | type=1 size=12 [100.0f][200.0f][0.0f] | type=2 size=4 [2] | type=3 size=4 [3]
//   = 2 + (4+12) + (4+4) + (4+4) = 34 바이트

#include "World.h"
#include "../Components/GameComponents.h"
#include "../Components/ZoneComponents.h"
#include "../Components/ChannelComponents.h"

#include <vector>
#include <cstring>
#include <cstdint>

// Component 타입 ID (직렬화 식별자)
enum class ComponentTypeId : uint16_t {
    POSITION = 1,
    ZONE     = 2,
    CHANNEL  = 3,
};

// ━━━ 직렬화: Entity → 바이트 배열 ━━━
inline std::vector<char> SerializeEntity(World& world, Entity entity) {
    std::vector<char> buffer;
    uint16_t count = 0;

    // count 자리 확보 (나중에 덮어씀)
    buffer.resize(2);

    // Position (12 bytes: x, y, z)
    if (world.HasComponent<PositionComponent>(entity)) {
        auto& pos = world.GetComponent<PositionComponent>(entity);
        uint16_t type = static_cast<uint16_t>(ComponentTypeId::POSITION);
        uint16_t size = 12;

        buffer.insert(buffer.end(), reinterpret_cast<char*>(&type),
                      reinterpret_cast<char*>(&type) + 2);
        buffer.insert(buffer.end(), reinterpret_cast<char*>(&size),
                      reinterpret_cast<char*>(&size) + 2);
        buffer.insert(buffer.end(), reinterpret_cast<const char*>(&pos.x),
                      reinterpret_cast<const char*>(&pos.x) + 4);
        buffer.insert(buffer.end(), reinterpret_cast<const char*>(&pos.y),
                      reinterpret_cast<const char*>(&pos.y) + 4);
        buffer.insert(buffer.end(), reinterpret_cast<const char*>(&pos.z),
                      reinterpret_cast<const char*>(&pos.z) + 4);
        count++;
    }

    // Zone (4 bytes: zone_id)
    if (world.HasComponent<ZoneComponent>(entity)) {
        auto& zone = world.GetComponent<ZoneComponent>(entity);
        uint16_t type = static_cast<uint16_t>(ComponentTypeId::ZONE);
        uint16_t size = 4;

        buffer.insert(buffer.end(), reinterpret_cast<char*>(&type),
                      reinterpret_cast<char*>(&type) + 2);
        buffer.insert(buffer.end(), reinterpret_cast<char*>(&size),
                      reinterpret_cast<char*>(&size) + 2);
        buffer.insert(buffer.end(), reinterpret_cast<const char*>(&zone.zone_id),
                      reinterpret_cast<const char*>(&zone.zone_id) + 4);
        count++;
    }

    // Channel (4 bytes: channel_id)
    if (world.HasComponent<ChannelComponent>(entity)) {
        auto& ch = world.GetComponent<ChannelComponent>(entity);
        uint16_t type = static_cast<uint16_t>(ComponentTypeId::CHANNEL);
        uint16_t size = 4;

        buffer.insert(buffer.end(), reinterpret_cast<char*>(&type),
                      reinterpret_cast<char*>(&type) + 2);
        buffer.insert(buffer.end(), reinterpret_cast<char*>(&size),
                      reinterpret_cast<char*>(&size) + 2);
        buffer.insert(buffer.end(), reinterpret_cast<const char*>(&ch.channel_id),
                      reinterpret_cast<const char*>(&ch.channel_id) + 4);
        count++;
    }

    // count 기록
    std::memcpy(buffer.data(), &count, 2);

    return buffer;
}

// ━━━ 역직렬화: 바이트 배열 → Entity에 Component 복원 ━━━
inline void DeserializeEntity(World& world, Entity entity,
                              const char* data, int len) {
    if (len < 2) return;

    uint16_t count;
    std::memcpy(&count, data, 2);
    int offset = 2;

    for (uint16_t i = 0; i < count && offset + 4 <= len; i++) {
        uint16_t type_id;
        uint16_t data_size;
        std::memcpy(&type_id, data + offset, 2);
        std::memcpy(&data_size, data + offset + 2, 2);
        offset += 4;

        if (offset + data_size > len) break;

        switch (static_cast<ComponentTypeId>(type_id)) {
            case ComponentTypeId::POSITION: {
                if (data_size >= 12) {
                    PositionComponent pos{};
                    std::memcpy(&pos.x, data + offset, 4);
                    std::memcpy(&pos.y, data + offset + 4, 4);
                    std::memcpy(&pos.z, data + offset + 8, 4);
                    pos.position_dirty = true;  // InterestSystem이 처리하도록

                    if (!world.HasComponent<PositionComponent>(entity))
                        world.AddComponent(entity, pos);
                    else
                        world.GetComponent<PositionComponent>(entity) = pos;
                }
                break;
            }
            case ComponentTypeId::ZONE: {
                if (data_size >= 4) {
                    ZoneComponent zone{};
                    std::memcpy(&zone.zone_id, data + offset, 4);

                    if (!world.HasComponent<ZoneComponent>(entity))
                        world.AddComponent(entity, zone);
                    else
                        world.GetComponent<ZoneComponent>(entity) = zone;
                }
                break;
            }
            case ComponentTypeId::CHANNEL: {
                if (data_size >= 4) {
                    ChannelComponent ch{};
                    std::memcpy(&ch.channel_id, data + offset, 4);

                    if (!world.HasComponent<ChannelComponent>(entity))
                        world.AddComponent(entity, ch);
                    else
                        world.GetComponent<ChannelComponent>(entity) = ch;
                }
                break;
            }
        }

        offset += data_size;
    }
}
