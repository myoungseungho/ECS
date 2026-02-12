"""
Session 15: Behavior Tree Framework

Reusable BT skeleton for game AI.

    tree = Selector([
        Sequence([Condition(is_dead), Action(respawn)]),
        Sequence([Condition(has_target), Action(attack)]),
        Action(wander),
    ])
    status = tree.tick(context)

Nodes:
    Selector  - OR:  try children until SUCCESS/RUNNING
    Sequence  - AND: run all, stop on FAILURE
    Condition - pure check, no side effects
    Action    - execute, may have side effects
    Inverter  - flip SUCCESS/FAILURE

RUNNING state is preserved across ticks (stateful Selector/Sequence).
"""

from enum import Enum


class Status(Enum):
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3


class BTNode:
    def tick(self, ctx) -> Status:
        raise NotImplementedError

    def reset(self):
        pass


class Selector(BTNode):
    """OR: try children until one returns SUCCESS or RUNNING.
    Resumes from RUNNING child on next tick."""

    def __init__(self, children):
        self.children = children
        self._idx = 0

    def tick(self, ctx) -> Status:
        while self._idx < len(self.children):
            status = self.children[self._idx].tick(ctx)
            if status == Status.RUNNING:
                return Status.RUNNING
            if status == Status.SUCCESS:
                self._idx = 0
                return Status.SUCCESS
            self._idx += 1
        self._idx = 0
        return Status.FAILURE

    def reset(self):
        self._idx = 0
        for c in self.children:
            c.reset()


class Sequence(BTNode):
    """AND: run children in order. Stop on FAILURE.
    Resumes from RUNNING child on next tick."""

    def __init__(self, children):
        self.children = children
        self._idx = 0

    def tick(self, ctx) -> Status:
        while self._idx < len(self.children):
            status = self.children[self._idx].tick(ctx)
            if status == Status.RUNNING:
                return Status.RUNNING
            if status == Status.FAILURE:
                self._idx = 0
                return Status.FAILURE
            self._idx += 1
        self._idx = 0
        return Status.SUCCESS

    def reset(self):
        self._idx = 0
        for c in self.children:
            c.reset()


class Condition(BTNode):
    """Pure check. Returns SUCCESS if true, FAILURE if false."""

    def __init__(self, check_fn):
        self.check_fn = check_fn

    def tick(self, ctx) -> Status:
        return Status.SUCCESS if self.check_fn(ctx) else Status.FAILURE


class Action(BTNode):
    """Execute action_fn(ctx) -> Status."""

    def __init__(self, action_fn):
        self.action_fn = action_fn

    def tick(self, ctx) -> Status:
        return self.action_fn(ctx)


class Inverter(BTNode):
    """Flip SUCCESS <-> FAILURE. RUNNING passes through."""

    def __init__(self, child):
        self.child = child

    def tick(self, ctx) -> Status:
        status = self.child.tick(ctx)
        if status == Status.SUCCESS:
            return Status.FAILURE
        if status == Status.FAILURE:
            return Status.SUCCESS
        return Status.RUNNING

    def reset(self):
        self.child.reset()
