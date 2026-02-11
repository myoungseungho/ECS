#pragma once

// ━━━ EventBus: System 간 이벤트 전달 ━━━
//
// 목적: CombatSystem이 "ENTITY_DIED" 발행 → QuestSystem, PartySystem 등이 구독
// ECS에서 System끼리 직접 호출하면 스파게티. EventBus가 중간 다리 역할.
//
// 사용법:
//   eventBus.Subscribe(EventType::ENTITY_DIED, [](const Event& e) { ... });
//   eventBus.Publish({EventType::ENTITY_DIED, entity, 0, 50.0f});
//   eventBus.ProcessAll();  // 매 틱에 호출 → 구독자에게 전달

#include "Entity.h"
#include <cstdint>
#include <vector>
#include <unordered_map>
#include <functional>
#include <mutex>

// 이벤트 타입 (새 시스템 추가 시 여기에 추가)
enum class EventType : uint32_t {
    // 타이머
    TIMER_EXPIRED       = 100,  // param1 = timer_id

    // 전투 (미래)
    ENTITY_DAMAGED      = 200,
    ENTITY_DIED         = 201,
    ENTITY_HEALED       = 202,

    // 아이템 (미래)
    ITEM_ACQUIRED       = 300,
    ITEM_USED           = 301,
    ITEM_DROPPED        = 302,

    // 존/채널
    ZONE_CHANGED        = 400,
    CHANNEL_CHANGED     = 401,

    // 커스텀 (자유 사용)
    CUSTOM_1            = 900,
    CUSTOM_2            = 901,
    CUSTOM_3            = 902,

    // 테스트
    TEST_EVENT          = 999,
};

// 이벤트 데이터 (가볍게, 복사 가능하게)
struct Event {
    EventType type;
    Entity source = 0;      // 이벤트 발생 주체
    Entity target = 0;      // 이벤트 대상 (옵션)
    int32_t param1 = 0;     // 범용 정수 파라미터
    int32_t param2 = 0;
    float fparam1 = 0.0f;   // 범용 실수 파라미터
    float fparam2 = 0.0f;
};

// 이벤트 핸들러 타입
using EventHandler = std::function<void(const Event&)>;

class EventBus {
public:
    // 이벤트 구독: 특정 타입의 이벤트가 발생하면 핸들러 호출
    void Subscribe(EventType type, EventHandler handler) {
        subscribers_[type].push_back(std::move(handler));
    }

    // 이벤트 발행: 큐에 넣고, ProcessAll() 때 전달
    void Publish(const Event& event) {
        queue_.push_back(event);
    }

    // 즉시 전달 (큐를 거치지 않고 바로 핸들러 호출)
    void PublishImmediate(const Event& event) {
        auto it = subscribers_.find(event.type);
        if (it == subscribers_.end()) return;
        for (auto& handler : it->second) {
            handler(event);
        }
    }

    // 큐에 쌓인 이벤트를 모두 처리 (매 틱 호출)
    int ProcessAll() {
        // swap으로 현재 큐를 꺼내고, 처리 중 새로 발행된 이벤트는 다음 틱에
        std::vector<Event> current;
        std::swap(current, queue_);

        int processed = 0;
        for (auto& event : current) {
            auto it = subscribers_.find(event.type);
            if (it == subscribers_.end()) continue;
            for (auto& handler : it->second) {
                handler(event);
            }
            processed++;
        }
        return processed;
    }

    // 큐에 쌓인 이벤트 수
    int GetQueueSize() const { return static_cast<int>(queue_.size()); }

    // 특정 타입의 구독자 수
    int GetSubscriberCount(EventType type) const {
        auto it = subscribers_.find(type);
        return it != subscribers_.end() ? static_cast<int>(it->second.size()) : 0;
    }

    // 전체 구독 해제 (테스트용)
    void Clear() {
        subscribers_.clear();
        queue_.clear();
    }

private:
    std::unordered_map<EventType, std::vector<EventHandler>> subscribers_;
    std::vector<Event> queue_;
};
