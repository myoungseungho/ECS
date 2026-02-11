#pragma once

// ━━━ TimerSystem: 타이머 처리 + EventBus 연동 ━━━
//
// 매 틱:
//   1. TimerComponent를 가진 모든 Entity 순회
//   2. 각 타이머의 remaining -= dt
//   3. remaining <= 0 → EventBus에 이벤트 발행
//   4. 반복 타이머면 remaining += interval, 1회성이면 제거

#include "../Core/System.h"
#include "../Core/World.h"
#include "../Core/EventBus.h"
#include "../Components/TimerComponents.h"

#include <cstdio>

class TimerSystem : public ISystem {
public:
    TimerSystem(EventBus& eventBus) : event_bus_(eventBus) {}

    void Update(World& world, float dt) override {
        world.ForEach<TimerComponent>(
            [&](Entity entity, TimerComponent& tc) {
                // 역순 순회 (제거 시 안전)
                for (int i = static_cast<int>(tc.timers.size()) - 1; i >= 0; i--) {
                    auto& t = tc.timers[i];
                    if (!t.active) continue;

                    t.remaining -= dt;
                    if (t.remaining <= 0.0f) {
                        // 이벤트 발행
                        Event evt;
                        evt.type = t.event_type;
                        evt.source = entity;
                        evt.param1 = t.timer_id;
                        evt.param2 = t.event_param;
                        event_bus_.Publish(evt);

                        if (t.interval > 0.0f) {
                            // 반복 타이머: 리셋
                            t.remaining += t.interval;
                        } else {
                            // 1회성: 제거
                            tc.timers.erase(tc.timers.begin() + i);
                        }
                    }
                }
            }
        );

        // 이벤트 큐 처리
        event_bus_.ProcessAll();
    }

    const char* GetName() const override { return "TimerSystem"; }

private:
    EventBus& event_bus_;
};
