#pragma once

// ━━━ CombatSystem: 매 틱 쿨타임 감소 ━━━
//
// 공격 후 cooldown_remaining이 설정됨.
// 이 System이 매 틱 dt만큼 감소시킴.
// cooldown_remaining <= 0이면 다시 공격 가능.

#include "../Core/System.h"
#include "../Core/World.h"
#include "../Components/CombatComponents.h"

class CombatSystem : public ISystem {
public:
    void Update(World& world, float dt) override {
        world.ForEach<CombatComponent>(
            [&](Entity entity, CombatComponent& combat) {
                if (combat.cooldown_remaining > 0) {
                    combat.cooldown_remaining -= dt;
                    if (combat.cooldown_remaining < 0) {
                        combat.cooldown_remaining = 0;
                    }
                }
            }
        );
    }

    const char* GetName() const override { return "CombatSystem"; }
};
