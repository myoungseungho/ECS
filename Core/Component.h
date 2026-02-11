#pragma once

#include "Entity.h"
#include <unordered_map>
#include <typeindex>
#include <memory>
#include <functional>
#include <cassert>

// Component 저장소의 인터페이스 (타입 소거용)
class IComponentArray {
public:
    virtual ~IComponentArray() = default;
    virtual void Remove(Entity entity) = 0;
    virtual bool Has(Entity entity) const = 0;
};

// 타입별 Component 저장소
// "Entity 1번의 PositionComponent는?" → components_[1]
template <typename T>
class ComponentArray : public IComponentArray {
public:
    void Add(Entity entity, T component) {
        components_[entity] = std::move(component);
    }

    void Remove(Entity entity) override {
        components_.erase(entity);
    }

    bool Has(Entity entity) const override {
        return components_.count(entity) > 0;
    }

    T& Get(Entity entity) {
        auto it = components_.find(entity);
        assert(it != components_.end() && "Entity does not have this component");
        return it->second;
    }

    const T& Get(Entity entity) const {
        auto it = components_.find(entity);
        assert(it != components_.end() && "Entity does not have this component");
        return it->second;
    }

    // 모든 Entity-Component 쌍을 순회
    std::unordered_map<Entity, T>& GetAll() { return components_; }
    const std::unordered_map<Entity, T>& GetAll() const { return components_; }

private:
    std::unordered_map<Entity, T> components_;
};
