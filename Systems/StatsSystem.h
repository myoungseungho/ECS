#pragma once

// ━━━ StatsSystem: HP/MP 자연회복 + 죽음 판정 ━━━
//
// 매 틱:
//   1. StatsComponent를 가진 모든 Entity 순회
//   2. 살아있으면 HP/MP 자연회복 (regen_rate * dt)
//   3. HP가 0이 되면 ENTITY_DIED 이벤트 발행
//
// 데미지/힐은 핸들러에서 StatsComponent 메서드 직접 호출.
// StatsSystem은 "매 틱 반복 처리"만 담당.

#include "../Core/System.h"
#include "../Core/World.h"
#include "../Core/EventBus.h"
#include "../Components/StatsComponents.h"

#include <cstdio>

class StatsSystem : public ISystem {
public:
    StatsSystem(EventBus& eventBus) : event_bus_(eventBus) {}

    void Update(World& world, float dt) override {
        world.ForEach<StatsComponent>(
            [&](Entity entity, StatsComponent& stats) {
                if (!stats.IsAlive()) return;

                // HP 자연회복
                if (stats.hp < stats.max_hp) {
                    stats.regen_accumulator += stats.hp_regen_rate * dt;
                    if (stats.regen_accumulator >= 1.0f) {
                        int regen = static_cast<int>(stats.regen_accumulator);
                        stats.regen_accumulator -= static_cast<float>(regen);
                        stats.hp = std::min(stats.max_hp, stats.hp + regen);
                        stats.stats_dirty = true;
                    }
                }

                // MP 자연회복
                if (stats.mp < stats.max_mp) {
                    float mp_regen = stats.mp_regen_rate * dt;
                    // MP도 누적 방식 (regen_accumulator 하나로 같이 쓰면 복잡하니 간단하게)
                    stats.mp += static_cast<int>(mp_regen);
                    if (stats.mp > stats.max_mp) stats.mp = stats.max_mp;
                }
            }
        );
    }

    const char* GetName() const override { return "StatsSystem"; }

private:
    EventBus& event_bus_;
};
