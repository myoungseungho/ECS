#pragma once

// ━━━ Timer/Scheduler Components ━━━
//
// 목적: 시간 기반 로직 (버프 만료, 리젠, 주기 저장 등)
// ECS 패턴: TimerComponent(데이터) + TimerSystem(로직)
//
// 사용법:
//   TimerEntry t;
//   t.timer_id = 1;
//   t.remaining = 5.0f;    // 5초 후 만료
//   t.interval = 0.0f;     // 1회성 (>0이면 반복)
//   t.event_type = EventType::TIMER_EXPIRED;
//
//   world.GetComponent<TimerComponent>(entity).timers.push_back(t);
//   → 5초 후 EventBus에 TIMER_EXPIRED 이벤트 발행

#include "../Core/EventBus.h"
#include <vector>
#include <cstdint>

struct TimerEntry {
    int32_t timer_id = 0;           // 타이머 식별자 (Entity 내에서 유일)
    float remaining = 0.0f;         // 남은 시간 (초)
    float interval = 0.0f;          // 0 = 1회성, >0 = 반복 주기
    bool active = true;             // false면 무시
    EventType event_type = EventType::TIMER_EXPIRED;  // 만료 시 발행할 이벤트
    int32_t event_param = 0;        // 이벤트에 전달할 파라미터
};

// TimerComponent: "이 Entity는 타이머가 있다"
struct TimerComponent {
    std::vector<TimerEntry> timers;

    // 타이머 추가 헬퍼
    void AddTimer(int32_t id, float duration, float interval = 0.0f,
                  EventType evt = EventType::TIMER_EXPIRED, int32_t param = 0) {
        TimerEntry t;
        t.timer_id = id;
        t.remaining = duration;
        t.interval = interval;
        t.event_type = evt;
        t.event_param = param;
        timers.push_back(t);
    }

    // 특정 타이머 제거
    void RemoveTimer(int32_t id) {
        timers.erase(
            std::remove_if(timers.begin(), timers.end(),
                [id](const TimerEntry& t) { return t.timer_id == id; }),
            timers.end()
        );
    }

    // 특정 타이머 존재 여부
    bool HasTimer(int32_t id) const {
        for (auto& t : timers) {
            if (t.timer_id == id && t.active) return true;
        }
        return false;
    }
};
