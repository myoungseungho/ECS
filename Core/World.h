#pragma once

#include "Entity.h"
#include "Component.h"
#include "System.h"

#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <typeindex>
#include <memory>
#include <algorithm>
#include <functional>

class World {
public:
    World();
    ~World();

    // ━━━ Entity 관리 ━━━
    Entity CreateEntity();
    void DestroyEntity(Entity entity);
    bool IsAlive(Entity entity) const;

    // ━━━ Component 관리 ━━━

    // Entity에 Component 추가
    template <typename T>
    void AddComponent(Entity entity, T component) {
        auto& arr = GetOrCreateComponentArray<T>();
        arr.Add(entity, std::move(component));
    }

    // Entity에서 Component 제거
    template <typename T>
    void RemoveComponent(Entity entity) {
        auto arr = GetComponentArray<T>();
        if (arr) arr->Remove(entity);
    }

    // Entity의 Component 가져오기
    template <typename T>
    T& GetComponent(Entity entity) {
        auto arr = GetComponentArray<T>();
        assert(arr && "Component type not registered");
        return arr->Get(entity);
    }

    // Entity가 특정 Component를 가지고 있는지
    template <typename T>
    bool HasComponent(Entity entity) const {
        auto arr = GetComponentArray<T>();
        return arr && arr->Has(entity);
    }

    // ━━━ 쿼리 (ECS의 핵심!) ━━━

    // Component 1개를 가진 모든 Entity 순회
    template <typename T, typename Func>
    void ForEach(Func&& func) {
        auto arr = GetComponentArray<T>();
        if (!arr) return;
        for (auto& [entity, comp] : arr->GetAll()) {
            func(entity, comp);
        }
    }

    // Component 2개를 모두 가진 Entity만 순회
    template <typename T1, typename T2, typename Func>
    void ForEach(Func&& func) {
        auto arr1 = GetComponentArray<T1>();
        auto arr2 = GetComponentArray<T2>();
        if (!arr1 || !arr2) return;
        for (auto& [entity, comp1] : arr1->GetAll()) {
            if (arr2->Has(entity)) {
                func(entity, comp1, arr2->Get(entity));
            }
        }
    }

    // Component 3개를 모두 가진 Entity만 순회
    template <typename T1, typename T2, typename T3, typename Func>
    void ForEach(Func&& func) {
        auto arr1 = GetComponentArray<T1>();
        auto arr2 = GetComponentArray<T2>();
        auto arr3 = GetComponentArray<T3>();
        if (!arr1 || !arr2 || !arr3) return;
        for (auto& [entity, comp1] : arr1->GetAll()) {
            if (arr2->Has(entity) && arr3->Has(entity)) {
                func(entity, comp1, arr2->Get(entity), arr3->Get(entity));
            }
        }
    }

    // ━━━ System 관리 ━━━

    template <typename T, typename... Args>
    void AddSystem(Args&&... args) {
        systems_.push_back(std::make_unique<T>(std::forward<Args>(args)...));
    }

    // System 등록 + 참조 반환 (핸들러 등록 등 설정이 필요할 때)
    template <typename T, typename... Args>
    T& AddSystemAndGet(Args&&... args) {
        auto ptr = std::make_unique<T>(std::forward<Args>(args)...);
        T& ref = *ptr;
        systems_.push_back(std::move(ptr));
        return ref;
    }

    // 모든 System을 등록된 순서대로 실행
    void Update(float dt);

    // ━━━ 유틸리티 ━━━
    size_t GetEntityCount() const { return alive_entities_.size(); }

private:
    template <typename T>
    ComponentArray<T>& GetOrCreateComponentArray() {
        auto type = std::type_index(typeid(T));
        auto it = component_arrays_.find(type);
        if (it == component_arrays_.end()) {
            auto arr = std::make_shared<ComponentArray<T>>();
            component_arrays_[type] = arr;
            return *arr;
        }
        return *std::static_pointer_cast<ComponentArray<T>>(it->second);
    }

    template <typename T>
    ComponentArray<T>* GetComponentArray() {
        auto type = std::type_index(typeid(T));
        auto it = component_arrays_.find(type);
        if (it == component_arrays_.end()) return nullptr;
        return static_cast<ComponentArray<T>*>(it->second.get());
    }

    template <typename T>
    const ComponentArray<T>* GetComponentArray() const {
        auto type = std::type_index(typeid(T));
        auto it = component_arrays_.find(type);
        if (it == component_arrays_.end()) return nullptr;
        return static_cast<const ComponentArray<T>*>(it->second.get());
    }

    uint64_t next_entity_id_ = 1;
    std::unordered_set<Entity> alive_entities_;
    std::unordered_map<std::type_index, std::shared_ptr<IComponentArray>> component_arrays_;
    std::vector<std::unique_ptr<ISystem>> systems_;
};
