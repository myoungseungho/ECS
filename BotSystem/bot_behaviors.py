"""
Session 15: Bot Behavior Nodes

BT framework + concrete game behaviors.

Bot behavior pattern:
  DEAD  -> Wait -> Respawn
  ALIVE -> Hunt (find monster -> approach -> attack loop)
        or Wander (random destination -> pause)
"""

import random
import time
from .behavior_tree import BTNode, Status, Selector, Sequence, Condition, Action


# ━━━ Condition Functions ━━━

def is_dead(bot) -> bool:
    return not bot.alive


def has_alive_monster(bot) -> bool:
    return any(m.get('alive', True) for m in bot.monsters.values())


# ━━━ Stateful Behavior Nodes ━━━

class HuntSequence(BTNode):
    """Full hunt cycle: find -> approach -> attack until kill."""

    def __init__(self):
        self._state = 'find'

    def tick(self, ctx) -> Status:
        if self._state == 'find':
            eid = ctx.get_nearest_alive_monster()
            if eid == 0:
                return Status.FAILURE
            ctx.target_entity = eid
            self._state = 'move'

        if self._state == 'move':
            m = ctx.monsters.get(ctx.target_entity)
            if not m or not m.get('alive', True):
                self._state = 'find'
                return Status.FAILURE
            dist = ctx.distance_to(m['x'], m['y'])
            if dist < 150.0:
                self._state = 'attack'
            else:
                ctx.move_toward(m['x'], m['y'], speed=40.0)
                return Status.RUNNING

        if self._state == 'attack':
            m = ctx.monsters.get(ctx.target_entity)
            if not m or not m.get('alive', True):
                ctx.target_entity = 0
                self._state = 'find'
                return Status.SUCCESS  # Kill complete
            if ctx.attack_cooldown <= 0:
                ctx.send_attack(ctx.target_entity)
            return Status.RUNNING

        return Status.FAILURE

    def reset(self):
        self._state = 'find'


class WanderAction(BTNode):
    """Wander to random positions with idle pauses."""

    def __init__(self):
        self._target = None
        self._idle_until = 0

    def tick(self, ctx) -> Status:
        now = time.time()
        if self._idle_until > now:
            return Status.RUNNING

        if self._target is None:
            self._target = (random.uniform(80, 480), random.uniform(80, 480))

        arrived = ctx.move_toward(self._target[0], self._target[1], speed=25.0)
        if arrived:
            self._target = None
            self._idle_until = now + random.uniform(1.0, 4.0)

        return Status.RUNNING

    def reset(self):
        self._target = None
        self._idle_until = 0


class WaitAction(BTNode):
    """Wait for a random duration."""

    def __init__(self, min_sec=1.0, max_sec=3.0):
        self.min_sec = min_sec
        self.max_sec = max_sec
        self._until = 0

    def tick(self, ctx) -> Status:
        now = time.time()
        if self._until == 0:
            self._until = now + random.uniform(self.min_sec, self.max_sec)
        if now >= self._until:
            self._until = 0
            return Status.SUCCESS
        return Status.RUNNING

    def reset(self):
        self._until = 0


# ━━━ BT Constructors ━━━

def create_default_bt():
    """Default bot BT: dead->respawn, hunt monsters, or wander."""
    return Selector([
        # Dead -> Wait -> Respawn
        Sequence([
            Condition(is_dead),
            WaitAction(1.0, 2.0),
            Action(lambda ctx: (ctx.send_respawn(), Status.SUCCESS)[1]),
        ]),
        # Hunt monsters
        HuntSequence(),
        # Wander (fallback)
        WanderAction(),
    ])


def create_hunt_only_bt():
    """Hunt-only BT for testing."""
    return Selector([
        Sequence([
            Condition(is_dead),
            WaitAction(0.5, 1.0),
            Action(lambda ctx: (ctx.send_respawn(), Status.SUCCESS)[1]),
        ]),
        HuntSequence(),
    ])


def create_wander_only_bt():
    """Wander-only BT for testing."""
    return Selector([
        Sequence([
            Condition(is_dead),
            WaitAction(0.5, 1.0),
            Action(lambda ctx: (ctx.send_respawn(), Status.SUCCESS)[1]),
        ]),
        WanderAction(),
    ])
