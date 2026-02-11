#include "World.h"
#include <cstdio>

World::World() = default;
World::~World() = default;

Entity World::CreateEntity() {
    Entity e = next_entity_id_++;
    alive_entities_.insert(e);
    return e;
}

void World::DestroyEntity(Entity entity) {
    // 모든 Component 배열에서 제거
    for (auto& [type, arr] : component_arrays_) {
        arr->Remove(entity);
    }
    alive_entities_.erase(entity);
}

bool World::IsAlive(Entity entity) const {
    return alive_entities_.count(entity) > 0;
}

void World::Update(float dt) {
    for (auto& system : systems_) {
        system->Update(*this, dt);
    }
}
