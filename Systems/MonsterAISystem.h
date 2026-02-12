#pragma once

#include "../Core/Entity.h"
#include "../Core/System.h"
#include "../Core/World.h"
#include "../NetworkEngine/IOCPServer.h"
#include "../Components/MonsterComponents.h"
#include "../Components/CombatComponents.h"
#include "../Components/NetworkComponents.h"
#include "../Components/SpatialComponents.h"
#include "../Components/ZoneComponents.h"
#include "../Components/PacketComponents.h"
#include "../Components/BossComponents.h"  // Session 34

#include <cstdio>
#include <cstring>

// ━━━ Session 14: MonsterAISystem ━━━
//
// 몬스터 AI 상태 머신:
//   IDLE   → 주변 플레이어 탐색 → 감지 시 ATTACK
//   ATTACK → 타겟 공격 (쿨타임 기반) → 타겟 사망/이탈 시 IDLE
//   DEAD   → 리스폰 타이머 → 리스폰 시 IDLE + 브로드캐스트
//
// 실행 순서:
//   NetworkSystem → MessageDispatch → [MonsterAISystem] → InterestSystem → BroadcastSystem
//
// 주의: 몬스터는 SessionComponent가 없으므로
//   InterestSystem/BroadcastSystem에서 자동 처리 안 됨
//   → 이 시스템에서 직접 패킷 전송
class MonsterAISystem : public ISystem {
public:
    explicit MonsterAISystem(IOCPServer& server) : server_(server) {}

    void Update(World& world, float dt) override {
        // ForEach<3개> + HasComponent로 4번째 체크 (World는 3-component ForEach까지 지원)
        world.ForEach<MonsterComponent, StatsComponent, PositionComponent>(
            [&](Entity entity, MonsterComponent& monster, StatsComponent& stats,
                PositionComponent& pos) {

                if (!world.HasComponent<ZoneComponent>(entity)) return;
                auto& zone = world.GetComponent<ZoneComponent>(entity);

                switch (monster.state) {
                    case MonsterState::DEAD:
                        UpdateDead(world, entity, monster, stats, pos, zone, dt);
                        break;
                    case MonsterState::IDLE:
                        UpdateIdle(world, entity, monster, stats, pos, zone, dt);
                        break;
                    case MonsterState::ATTACK:
                        UpdateAttack(world, entity, monster, stats, pos, zone, dt);
                        break;
                }
            }
        );
    }

    const char* GetName() const override { return "MonsterAISystem"; }

private:
    IOCPServer& server_;

    // ━━━ DEAD: 리스폰 카운트다운 ━━━
    void UpdateDead(World& world, Entity entity, MonsterComponent& monster,
                    StatsComponent& stats, PositionComponent& pos,
                    ZoneComponent& zone, float dt) {
        monster.death_timer -= dt;
        if (monster.death_timer <= 0) {
            // HP 복구 + 위치 초기화
            stats.hp = stats.max_hp;
            stats.mp = stats.max_mp;
            pos.x = monster.spawn_x;
            pos.y = monster.spawn_y;
            pos.z = monster.spawn_z;
            monster.state = MonsterState::IDLE;
            monster.target_entity = 0;

            // Session 34: 보스 리스폰 시 BossComponent 리셋
            if (world.HasComponent<BossComponent>(entity)) {
                auto& bc = world.GetComponent<BossComponent>(entity);
                auto* tmpl = FindBossTemplate(bc.boss_id);
                bc.current_phase = 0;
                bc.enrage_timer = 0;
                bc.is_enraged = false;
                bc.combat_started = false;
                bc.special_timer = tmpl ? tmpl->phases[0].special_cooldown : 10.0f;
                // ATK도 원래대로 복구
                if (tmpl) {
                    stats.attack = tmpl->attack;
                }
            }

            printf("[MonsterAI] Entity %llu '%s' RESPAWNED at (%.0f, %.0f)\n",
                   entity, monster.name, pos.x, pos.y);

            BroadcastMonsterRespawn(world, entity, stats, pos, zone);
        }
    }

    // ━━━ IDLE: 어그로 탐색 ━━━
    void UpdateIdle(World& world, Entity entity, MonsterComponent& monster,
                    StatsComponent& stats, PositionComponent& pos,
                    ZoneComponent& zone, float dt) {
        Entity nearest = 0;
        float nearest_dist = monster.aggro_range;

        world.ForEach<SessionComponent, PositionComponent, StatsComponent>(
            [&](Entity other, SessionComponent& other_session,
                PositionComponent& other_pos, StatsComponent& other_stats) {

                if (!other_session.connected) return;
                if (!other_stats.IsAlive()) return;
                if (!world.HasComponent<ZoneComponent>(other)) return;
                if (world.GetComponent<ZoneComponent>(other).zone_id != zone.zone_id) return;

                float dist = DistanceBetween(pos, other_pos);
                if (dist < nearest_dist) {
                    nearest_dist = dist;
                    nearest = other;
                }
            }
        );

        if (nearest != 0) {
            monster.target_entity = nearest;
            monster.state = MonsterState::ATTACK;
            printf("[MonsterAI] Entity %llu '%s' -> AGGRO on Entity %llu (dist=%.1f)\n",
                   entity, monster.name, nearest, nearest_dist);
        }
    }

    // ━━━ ATTACK: 타겟 공격 ━━━
    void UpdateAttack(World& world, Entity entity, MonsterComponent& monster,
                      StatsComponent& stats, PositionComponent& pos,
                      ZoneComponent& zone, float dt) {
        // 타겟 유효성 검증
        if (monster.target_entity == 0 ||
            !world.IsAlive(monster.target_entity) ||
            !world.HasComponent<StatsComponent>(monster.target_entity) ||
            !world.HasComponent<PositionComponent>(monster.target_entity) ||
            !world.HasComponent<SessionComponent>(monster.target_entity)) {
            monster.state = MonsterState::IDLE;
            monster.target_entity = 0;
            return;
        }

        auto& target_stats = world.GetComponent<StatsComponent>(monster.target_entity);
        auto& target_pos = world.GetComponent<PositionComponent>(monster.target_entity);
        auto& target_session = world.GetComponent<SessionComponent>(monster.target_entity);

        if (!target_stats.IsAlive() || !target_session.connected) {
            monster.state = MonsterState::IDLE;
            monster.target_entity = 0;
            return;
        }

        // 어그로 범위 x2 벗어나면 포기
        float dist = DistanceBetween(pos, target_pos);
        if (dist > monster.aggro_range * 2.0f) {
            monster.state = MonsterState::IDLE;
            monster.target_entity = 0;
            printf("[MonsterAI] Entity %llu '%s' -> target out of range, IDLE\n",
                   entity, monster.name);
            return;
        }

        // 쿨타임 확인 (CombatSystem이 매 틱 감소)
        if (!world.HasComponent<CombatComponent>(entity)) return;
        auto& combat = world.GetComponent<CombatComponent>(entity);
        if (combat.cooldown_remaining > 0) return;

        // 공격 범위 확인
        if (dist > combat.attack_range) return;

        // ━━━ 공격 실행 ━━━
        int32_t damage = target_stats.TakeDamage(stats.attack);
        combat.cooldown_remaining = combat.attack_cooldown;

        printf("[MonsterAI] Entity %llu '%s' attacked Entity %llu: %d dmg (HP: %d/%d)\n",
               entity, monster.name, monster.target_entity, damage,
               target_stats.hp, target_stats.max_hp);

        // ATTACK_RESULT를 타겟 플레이어에게 전송
        {
            char buf[29];
            buf[0] = static_cast<uint8_t>(AttackResult::SUCCESS);
            std::memcpy(buf + 1, &entity, 8);
            std::memcpy(buf + 9, &monster.target_entity, 8);
            std::memcpy(buf + 17, &damage, 4);
            std::memcpy(buf + 21, &target_stats.hp, 4);
            std::memcpy(buf + 25, &target_stats.max_hp, 4);
            auto pkt = BuildPacket(MsgType::ATTACK_RESULT, buf, 29);
            server_.SendTo(target_session.session_id,
                           pkt.data(), static_cast<int>(pkt.size()));
        }

        // STAT_SYNC를 타겟 플레이어에게 전송
        {
            char buf[36];
            std::memcpy(buf,      &target_stats.level, 4);
            std::memcpy(buf + 4,  &target_stats.hp, 4);
            std::memcpy(buf + 8,  &target_stats.max_hp, 4);
            std::memcpy(buf + 12, &target_stats.mp, 4);
            std::memcpy(buf + 16, &target_stats.max_mp, 4);
            std::memcpy(buf + 20, &target_stats.attack, 4);
            std::memcpy(buf + 24, &target_stats.defense, 4);
            std::memcpy(buf + 28, &target_stats.exp, 4);
            std::memcpy(buf + 32, &target_stats.exp_to_next, 4);
            auto pkt = BuildPacket(MsgType::STAT_SYNC, buf, 36);
            server_.SendTo(target_session.session_id,
                           pkt.data(), static_cast<int>(pkt.size()));
            target_stats.stats_dirty = false;
        }

        // 플레이어 사망 처리
        if (!target_stats.IsAlive()) {
            printf("[MonsterAI] Entity %llu '%s' killed Entity %llu!\n",
                   entity, monster.name, monster.target_entity);

            char died_buf[16];
            std::memcpy(died_buf, &monster.target_entity, 8);
            std::memcpy(died_buf + 8, &entity, 8);
            auto died_pkt = BuildPacket(MsgType::COMBAT_DIED, died_buf, 16);
            server_.SendTo(target_session.session_id,
                           died_pkt.data(), static_cast<int>(died_pkt.size()));

            monster.state = MonsterState::IDLE;
            monster.target_entity = 0;
        }
    }

    // ━━━ 몬스터 리스폰 브로드캐스트 ━━━
    void BroadcastMonsterRespawn(World& world, Entity monster_entity,
                                 StatsComponent& stats, PositionComponent& pos,
                                 ZoneComponent& zone) {
        // MONSTER_RESPAWN: entity(8) hp(4) max_hp(4) x(4) y(4) z(4) = 28 bytes
        char buf[28];
        std::memcpy(buf, &monster_entity, 8);
        std::memcpy(buf + 8, &stats.hp, 4);
        std::memcpy(buf + 12, &stats.max_hp, 4);
        std::memcpy(buf + 16, &pos.x, 4);
        std::memcpy(buf + 20, &pos.y, 4);
        std::memcpy(buf + 24, &pos.z, 4);
        auto pkt = BuildPacket(MsgType::MONSTER_RESPAWN, buf, 28);

        world.ForEach<SessionComponent, ZoneComponent>(
            [&](Entity player, SessionComponent& session, ZoneComponent& player_zone) {
                if (!session.connected) return;
                if (player_zone.zone_id != zone.zone_id) return;
                server_.SendTo(session.session_id,
                               pkt.data(), static_cast<int>(pkt.size()));
            }
        );
    }
};
