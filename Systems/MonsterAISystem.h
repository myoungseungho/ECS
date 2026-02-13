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
#include "../Components/BossComponents.h"

#include <cstdio>
#include <cstring>
#include <cmath>
#include <algorithm>

// ━━━ Session 36: Enhanced MonsterAISystem ━━━
//
// 6상태 FSM:
//   IDLE   → 주변 플레이어 감지 / 순찰 전환
//   PATROL → 스폰 주변 랜덤 이동, 감지 시 CHASE
//   CHASE  → 타겟 추적 이동, 사거리 도달 시 ATTACK, 리쉬 초과 시 RETURN
//   ATTACK → 타겟 공격, 사거리 이탈 시 CHASE, 타겟 사망 시 다음 어그로/IDLE
//   RETURN → 스폰 복귀 + HP 회복, 도착 시 IDLE
//   DEAD   → 리스폰 타이머 → IDLE
//
// 어그로 테이블: 데미지 기반 위협도, 탑 어그로 타겟팅
// 이동: 직선 이동 (패스파인딩 없음), MONSTER_MOVE 브로드캐스트
//
class MonsterAISystem : public ISystem {
public:
    explicit MonsterAISystem(IOCPServer& server) : server_(server) {}

    void Update(World& world, float dt) override {
        world.ForEach<MonsterComponent, StatsComponent, PositionComponent>(
            [&](Entity entity, MonsterComponent& monster, StatsComponent& stats,
                PositionComponent& pos) {

                if (!world.HasComponent<ZoneComponent>(entity)) return;
                auto& zone = world.GetComponent<ZoneComponent>(entity);

                switch (monster.state) {
                    case MonsterState::IDLE:
                        UpdateIdle(world, entity, monster, stats, pos, zone, dt);
                        break;
                    case MonsterState::PATROL:
                        UpdatePatrol(world, entity, monster, stats, pos, zone, dt);
                        break;
                    case MonsterState::CHASE:
                        UpdateChase(world, entity, monster, stats, pos, zone, dt);
                        break;
                    case MonsterState::ATTACK:
                        UpdateAttack(world, entity, monster, stats, pos, zone, dt);
                        break;
                    case MonsterState::RETURN:
                        UpdateReturn(world, entity, monster, stats, pos, zone, dt);
                        break;
                    case MonsterState::DEAD:
                        UpdateDead(world, entity, monster, stats, pos, zone, dt);
                        break;
                }
            }
        );
    }

    const char* GetName() const override { return "MonsterAISystem"; }

private:
    IOCPServer& server_;

    // ━━━ 유틸리티 ━━━

    static float Dist2D(float x1, float y1, float x2, float y2) {
        float dx = x2 - x1, dy = y2 - y1;
        return std::sqrt(dx * dx + dy * dy);
    }

    static float PseudoRandom(float min_val, float max_val) {
        static uint32_t seed = 7919;
        seed = seed * 1103515245u + 12345u;
        float t = static_cast<float>((seed >> 16) & 0x7FFF) / 32767.0f;
        return min_val + t * (max_val - min_val);
    }

    bool MoveToward(PositionComponent& pos, float tx, float ty, float speed, float dt) {
        float dx = tx - pos.x;
        float dy = ty - pos.y;
        float dist = std::sqrt(dx * dx + dy * dy);
        if (dist < MonsterAI::ARRIVAL_THRESHOLD) {
            pos.x = tx; pos.y = ty;
            pos.position_dirty = true;
            return true;
        }
        float step = speed * dt;
        if (step >= dist) {
            pos.x = tx; pos.y = ty;
            pos.position_dirty = true;
            return true;
        }
        pos.x += (dx / dist) * step;
        pos.y += (dy / dist) * step;
        pos.position_dirty = true;
        return false;
    }

    Entity FindValidTopThreat(World& world, MonsterComponent& monster, ZoneComponent& zone) {
        for (int attempt = 0; attempt < monster.aggro_count + 1; attempt++) {
            Entity top = monster.GetTopThreat();
            if (top == 0) break;
            if (!world.IsAlive(top) ||
                !world.HasComponent<SessionComponent>(top) ||
                !world.HasComponent<StatsComponent>(top) ||
                !world.HasComponent<PositionComponent>(top)) {
                monster.RemoveThreat(top);
                continue;
            }
            auto& s = world.GetComponent<SessionComponent>(top);
            auto& st = world.GetComponent<StatsComponent>(top);
            if (!s.connected || !st.IsAlive()) {
                monster.RemoveThreat(top);
                continue;
            }
            if (world.HasComponent<ZoneComponent>(top) &&
                world.GetComponent<ZoneComponent>(top).zone_id != zone.zone_id) {
                monster.RemoveThreat(top);
                continue;
            }
            return top;
        }
        return 0;
    }

    void GeneratePatrolTarget(MonsterComponent& monster) {
        float angle = PseudoRandom(0.0f, 6.2831853f);
        float radius = PseudoRandom(MonsterAI::ARRIVAL_THRESHOLD, MonsterAI::PATROL_RADIUS);
        monster.patrol_target_x = monster.spawn_x + radius * std::cos(angle);
        monster.patrol_target_y = monster.spawn_y + radius * std::sin(angle);
    }

    // ━━━ IDLE: 대기 + 감지 + 순찰 전환 ━━━
    void UpdateIdle(World& world, Entity entity, MonsterComponent& monster,
                    StatsComponent& stats, PositionComponent& pos,
                    ZoneComponent& zone, float dt) {
        // 어그로 테이블에 유효 타겟이 있으면 추적
        Entity top = FindValidTopThreat(world, monster, zone);
        if (top != 0) {
            monster.target_entity = top;
            monster.state = MonsterState::CHASE;
            printf("[MonsterAI] %llu '%s' -> CHASE (aggro table, target %llu)\n",
                   entity, monster.name, top);
            BroadcastAggroChange(world, entity, top, zone);
            return;
        }

        // 근접 플레이어 탐색 (어그로 레인지 내)
        Entity nearest = 0;
        float nearest_dist = monster.aggro_range;

        world.ForEach<SessionComponent, PositionComponent, StatsComponent>(
            [&](Entity other, SessionComponent& sess, PositionComponent& opos,
                StatsComponent& ost) {
                if (!sess.connected || !ost.IsAlive()) return;
                if (!world.HasComponent<ZoneComponent>(other)) return;
                if (world.GetComponent<ZoneComponent>(other).zone_id != zone.zone_id) return;
                float dist = DistanceBetween(pos, opos);
                if (dist < nearest_dist) {
                    nearest_dist = dist;
                    nearest = other;
                }
            }
        );

        if (nearest != 0) {
            monster.AddThreat(nearest, 1.0f);
            monster.target_entity = nearest;
            monster.state = MonsterState::CHASE;
            printf("[MonsterAI] %llu '%s' -> CHASE (detect, target %llu, dist=%.1f)\n",
                   entity, monster.name, nearest, nearest_dist);
            BroadcastAggroChange(world, entity, nearest, zone);
            return;
        }

        // 순찰 타이머
        monster.patrol_timer -= dt;
        if (monster.patrol_timer <= 0) {
            GeneratePatrolTarget(monster);
            monster.state = MonsterState::PATROL;
            monster.patrol_timer = PseudoRandom(MonsterAI::PATROL_MIN_WAIT, MonsterAI::PATROL_MAX_WAIT);
        }
    }

    // ━━━ PATROL: 순찰 이동 ━━━
    void UpdatePatrol(World& world, Entity entity, MonsterComponent& monster,
                      StatsComponent& stats, PositionComponent& pos,
                      ZoneComponent& zone, float dt) {
        // 어그로 테이블 또는 근접 감지
        Entity top = FindValidTopThreat(world, monster, zone);
        if (top != 0) {
            monster.target_entity = top;
            monster.state = MonsterState::CHASE;
            BroadcastAggroChange(world, entity, top, zone);
            return;
        }

        Entity nearest = 0;
        float nearest_dist = monster.aggro_range;
        world.ForEach<SessionComponent, PositionComponent, StatsComponent>(
            [&](Entity other, SessionComponent& sess, PositionComponent& opos,
                StatsComponent& ost) {
                if (!sess.connected || !ost.IsAlive()) return;
                if (!world.HasComponent<ZoneComponent>(other)) return;
                if (world.GetComponent<ZoneComponent>(other).zone_id != zone.zone_id) return;
                float dist = DistanceBetween(pos, opos);
                if (dist < nearest_dist) { nearest_dist = dist; nearest = other; }
            }
        );
        if (nearest != 0) {
            monster.AddThreat(nearest, 1.0f);
            monster.target_entity = nearest;
            monster.state = MonsterState::CHASE;
            BroadcastAggroChange(world, entity, nearest, zone);
            return;
        }

        // 순찰 목표를 향해 이동
        bool arrived = MoveToward(pos, monster.patrol_target_x, monster.patrol_target_y,
                                  monster.move_speed, dt);

        // 이동 브로드캐스트
        monster.move_broadcast_timer -= dt;
        if (monster.move_broadcast_timer <= 0) {
            monster.move_broadcast_timer = MonsterAI::MOVE_BROADCAST_INTERVAL;
            BroadcastMonsterMove(world, entity, pos, zone);
        }

        if (arrived) {
            monster.state = MonsterState::IDLE;
            monster.patrol_timer = PseudoRandom(MonsterAI::PATROL_MIN_WAIT, MonsterAI::PATROL_MAX_WAIT);
        }
    }

    // ━━━ CHASE: 타겟 추적 ━━━
    void UpdateChase(World& world, Entity entity, MonsterComponent& monster,
                     StatsComponent& stats, PositionComponent& pos,
                     ZoneComponent& zone, float dt) {
        // 타겟 유효성
        if (monster.target_entity == 0) {
            Entity next = FindValidTopThreat(world, monster, zone);
            if (next != 0) {
                monster.target_entity = next;
                BroadcastAggroChange(world, entity, next, zone);
            } else {
                monster.state = MonsterState::RETURN;
                return;
            }
        }

        Entity target = monster.target_entity;
        if (!world.IsAlive(target) ||
            !world.HasComponent<PositionComponent>(target) ||
            !world.HasComponent<StatsComponent>(target) ||
            !world.HasComponent<SessionComponent>(target)) {
            monster.RemoveThreat(target);
            monster.target_entity = 0;
            Entity next = FindValidTopThreat(world, monster, zone);
            if (next != 0) {
                monster.target_entity = next;
                BroadcastAggroChange(world, entity, next, zone);
            } else {
                monster.state = MonsterState::RETURN;
            }
            return;
        }

        auto& tgt_sess = world.GetComponent<SessionComponent>(target);
        auto& tgt_stats = world.GetComponent<StatsComponent>(target);
        if (!tgt_sess.connected || !tgt_stats.IsAlive()) {
            monster.RemoveThreat(target);
            monster.target_entity = 0;
            Entity next = FindValidTopThreat(world, monster, zone);
            if (next != 0) {
                monster.target_entity = next;
                BroadcastAggroChange(world, entity, next, zone);
            } else {
                monster.state = MonsterState::RETURN;
            }
            return;
        }

        // 리쉬 체크
        float dist_from_spawn = Dist2D(pos.x, pos.y, monster.spawn_x, monster.spawn_y);
        if (dist_from_spawn > MonsterAI::LEASH_RANGE) {
            printf("[MonsterAI] %llu '%s' -> RETURN (leash, dist=%.1f)\n",
                   entity, monster.name, dist_from_spawn);
            monster.state = MonsterState::RETURN;
            monster.target_entity = 0;
            monster.ClearAggro();
            BroadcastAggroChange(world, entity, 0, zone);
            return;
        }

        // 타겟을 향해 이동
        auto& tgt_pos = world.GetComponent<PositionComponent>(target);
        float chase_speed = monster.move_speed * MonsterAI::CHASE_SPEED_MULT;
        MoveToward(pos, tgt_pos.x, tgt_pos.y, chase_speed, dt);

        // 이동 브로드캐스트
        monster.move_broadcast_timer -= dt;
        if (monster.move_broadcast_timer <= 0) {
            monster.move_broadcast_timer = MonsterAI::MOVE_BROADCAST_INTERVAL;
            BroadcastMonsterMove(world, entity, pos, zone);
        }

        // 사거리 내 도달 → ATTACK
        float dist_to_target = Dist2D(pos.x, pos.y, tgt_pos.x, tgt_pos.y);
        if (world.HasComponent<CombatComponent>(entity)) {
            float atk_range = world.GetComponent<CombatComponent>(entity).attack_range;
            if (dist_to_target <= atk_range) {
                monster.state = MonsterState::ATTACK;
            }
        }
    }

    // ━━━ ATTACK: 타겟 공격 ━━━
    void UpdateAttack(World& world, Entity entity, MonsterComponent& monster,
                      StatsComponent& stats, PositionComponent& pos,
                      ZoneComponent& zone, float dt) {
        // 타겟 유효성
        if (monster.target_entity == 0 ||
            !world.IsAlive(monster.target_entity) ||
            !world.HasComponent<StatsComponent>(monster.target_entity) ||
            !world.HasComponent<PositionComponent>(monster.target_entity) ||
            !world.HasComponent<SessionComponent>(monster.target_entity)) {
            monster.RemoveThreat(monster.target_entity);
            monster.target_entity = 0;
            Entity next = FindValidTopThreat(world, monster, zone);
            if (next != 0) {
                monster.target_entity = next;
                monster.state = MonsterState::CHASE;
                BroadcastAggroChange(world, entity, next, zone);
            } else {
                monster.state = MonsterState::RETURN;
            }
            return;
        }

        auto& target_stats = world.GetComponent<StatsComponent>(monster.target_entity);
        auto& target_pos = world.GetComponent<PositionComponent>(monster.target_entity);
        auto& target_session = world.GetComponent<SessionComponent>(monster.target_entity);

        if (!target_stats.IsAlive() || !target_session.connected) {
            monster.RemoveThreat(monster.target_entity);
            monster.target_entity = 0;
            Entity next = FindValidTopThreat(world, monster, zone);
            if (next != 0) {
                monster.target_entity = next;
                monster.state = MonsterState::CHASE;
                BroadcastAggroChange(world, entity, next, zone);
            } else {
                monster.state = MonsterState::RETURN;
            }
            return;
        }

        // 리쉬 체크
        float dist_from_spawn = Dist2D(pos.x, pos.y, monster.spawn_x, monster.spawn_y);
        if (dist_from_spawn > MonsterAI::LEASH_RANGE) {
            monster.state = MonsterState::RETURN;
            monster.target_entity = 0;
            monster.ClearAggro();
            BroadcastAggroChange(world, entity, 0, zone);
            return;
        }

        // 사거리 벗어남 → 추적
        float dist = DistanceBetween(pos, target_pos);
        if (!world.HasComponent<CombatComponent>(entity)) return;
        auto& combat = world.GetComponent<CombatComponent>(entity);
        if (dist > combat.attack_range) {
            monster.state = MonsterState::CHASE;
            return;
        }

        // 탑 어그로 갱신 (다른 플레이어가 더 많은 데미지 → 타겟 변경)
        Entity current_top = monster.GetTopThreat();
        if (current_top != 0 && current_top != monster.target_entity) {
            monster.target_entity = current_top;
            monster.state = MonsterState::CHASE;
            BroadcastAggroChange(world, entity, current_top, zone);
            return;
        }

        // 쿨타임
        if (combat.cooldown_remaining > 0) return;

        // ━━━ 공격 실행 ━━━
        int32_t damage = target_stats.TakeDamage(stats.attack);
        combat.cooldown_remaining = combat.attack_cooldown;

        printf("[MonsterAI] %llu '%s' attacked %llu: %d dmg (HP: %d/%d)\n",
               entity, monster.name, monster.target_entity, damage,
               target_stats.hp, target_stats.max_hp);

        // ATTACK_RESULT
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

        // STAT_SYNC
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
            printf("[MonsterAI] %llu '%s' killed %llu!\n",
                   entity, monster.name, monster.target_entity);

            char died_buf[16];
            std::memcpy(died_buf, &monster.target_entity, 8);
            std::memcpy(died_buf + 8, &entity, 8);
            auto died_pkt = BuildPacket(MsgType::COMBAT_DIED, died_buf, 16);
            server_.SendTo(target_session.session_id,
                           died_pkt.data(), static_cast<int>(died_pkt.size()));

            monster.RemoveThreat(monster.target_entity);
            monster.target_entity = 0;
            Entity next = FindValidTopThreat(world, monster, zone);
            if (next != 0) {
                monster.target_entity = next;
                monster.state = MonsterState::CHASE;
                BroadcastAggroChange(world, entity, next, zone);
            } else {
                monster.state = MonsterState::IDLE;
                monster.patrol_timer = PseudoRandom(MonsterAI::PATROL_MIN_WAIT,
                                                    MonsterAI::PATROL_MAX_WAIT);
            }
        }
    }

    // ━━━ RETURN: 스폰 복귀 + HP 회복 ━━━
    void UpdateReturn(World& world, Entity entity, MonsterComponent& monster,
                      StatsComponent& stats, PositionComponent& pos,
                      ZoneComponent& zone, float dt) {
        // HP 회복
        if (stats.hp < stats.max_hp) {
            int32_t heal = static_cast<int32_t>(stats.max_hp * MonsterAI::RETURN_HEAL_RATE * dt);
            if (heal < 1) heal = 1;
            stats.hp = std::min(stats.hp + heal, stats.max_hp);
        }

        // 어그로 무시 (귀환 중)
        monster.ClearAggro();
        monster.target_entity = 0;

        // 스폰으로 이동
        bool arrived = MoveToward(pos, monster.spawn_x, monster.spawn_y,
                                  monster.move_speed, dt);

        // 이동 브로드캐스트
        monster.move_broadcast_timer -= dt;
        if (monster.move_broadcast_timer <= 0) {
            monster.move_broadcast_timer = MonsterAI::MOVE_BROADCAST_INTERVAL;
            BroadcastMonsterMove(world, entity, pos, zone);
        }

        if (arrived) {
            stats.hp = stats.max_hp;
            monster.state = MonsterState::IDLE;
            monster.patrol_timer = PseudoRandom(MonsterAI::PATROL_MIN_WAIT,
                                                MonsterAI::PATROL_MAX_WAIT);
            printf("[MonsterAI] %llu '%s' RETURNED to spawn (%.0f, %.0f)\n",
                   entity, monster.name, pos.x, pos.y);
        }
    }

    // ━━━ DEAD: 리스폰 카운트다운 ━━━
    void UpdateDead(World& world, Entity entity, MonsterComponent& monster,
                    StatsComponent& stats, PositionComponent& pos,
                    ZoneComponent& zone, float dt) {
        monster.death_timer -= dt;
        if (monster.death_timer <= 0) {
            stats.hp = stats.max_hp;
            stats.mp = stats.max_mp;
            pos.x = monster.spawn_x;
            pos.y = monster.spawn_y;
            pos.z = monster.spawn_z;
            monster.state = MonsterState::IDLE;
            monster.target_entity = 0;
            monster.ClearAggro();
            monster.patrol_timer = PseudoRandom(MonsterAI::PATROL_MIN_WAIT,
                                                MonsterAI::PATROL_MAX_WAIT);

            // Session 34: 보스 리스폰 시 BossComponent 리셋
            if (world.HasComponent<BossComponent>(entity)) {
                auto& bc = world.GetComponent<BossComponent>(entity);
                auto* tmpl = FindBossTemplate(bc.boss_id);
                bc.current_phase = 0;
                bc.enrage_timer = 0;
                bc.is_enraged = false;
                bc.combat_started = false;
                bc.special_timer = tmpl ? tmpl->phases[0].special_cooldown : 10.0f;
                if (tmpl) {
                    stats.attack = tmpl->attack;
                }
            }

            printf("[MonsterAI] %llu '%s' RESPAWNED at (%.0f, %.0f)\n",
                   entity, monster.name, pos.x, pos.y);

            BroadcastMonsterRespawn(world, entity, stats, pos, zone);
        }
    }

    // ━━━ 브로드캐스트 ━━━

    void BroadcastMonsterMove(World& world, Entity monster_entity,
                              PositionComponent& pos, ZoneComponent& zone) {
        char buf[20];
        std::memcpy(buf, &monster_entity, 8);
        std::memcpy(buf + 8, &pos.x, 4);
        std::memcpy(buf + 12, &pos.y, 4);
        std::memcpy(buf + 16, &pos.z, 4);
        auto pkt = BuildPacket(MsgType::MONSTER_MOVE, buf, 20);

        world.ForEach<SessionComponent, ZoneComponent>(
            [&](Entity player, SessionComponent& session, ZoneComponent& pz) {
                if (!session.connected) return;
                if (pz.zone_id != zone.zone_id) return;
                server_.SendTo(session.session_id,
                               pkt.data(), static_cast<int>(pkt.size()));
            }
        );
    }

    void BroadcastAggroChange(World& world, Entity monster_entity,
                              Entity target, ZoneComponent& zone) {
        char buf[16];
        std::memcpy(buf, &monster_entity, 8);
        std::memcpy(buf + 8, &target, 8);
        auto pkt = BuildPacket(MsgType::MONSTER_AGGRO, buf, 16);

        world.ForEach<SessionComponent, ZoneComponent>(
            [&](Entity player, SessionComponent& session, ZoneComponent& pz) {
                if (!session.connected) return;
                if (pz.zone_id != zone.zone_id) return;
                server_.SendTo(session.session_id,
                               pkt.data(), static_cast<int>(pkt.size()));
            }
        );
    }

    void BroadcastMonsterRespawn(World& world, Entity monster_entity,
                                 StatsComponent& stats, PositionComponent& pos,
                                 ZoneComponent& zone) {
        char buf[28];
        std::memcpy(buf, &monster_entity, 8);
        std::memcpy(buf + 8, &stats.hp, 4);
        std::memcpy(buf + 12, &stats.max_hp, 4);
        std::memcpy(buf + 16, &pos.x, 4);
        std::memcpy(buf + 20, &pos.y, 4);
        std::memcpy(buf + 24, &pos.z, 4);
        auto pkt = BuildPacket(MsgType::MONSTER_RESPAWN, buf, 28);

        world.ForEach<SessionComponent, ZoneComponent>(
            [&](Entity player, SessionComponent& session, ZoneComponent& pz) {
                if (!session.connected) return;
                if (pz.zone_id != zone.zone_id) return;
                server_.SendTo(session.session_id,
                               pkt.data(), static_cast<int>(pkt.size()));
            }
        );
    }
};
