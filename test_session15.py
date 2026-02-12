"""
Session 15: AI Bot System Tests
- BehaviorTree framework: Selector, Sequence, Condition, Action, stateful RUNNING
- BotClient: auto-register, login, enter game, receive monsters
- Bot Behaviors: Hunt (find->move->attack), Wander, Auto-respawn
- BotManager: multi-bot orchestration

Bot specs (auto-registered Lv10 Warrior):
  HP=300, ATK=28, DEF=23
  Bot vs Goblin: damage = max(1, 28-5) = 23. 5 hits to kill (100 HP). EXP = 50
"""

import sys
import os
import time
import subprocess

# Add project root to path for BotSystem imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from BotSystem.behavior_tree import Status, BTNode, Selector, Sequence, Condition, Action, Inverter
from BotSystem.bot_client import BotClient
from BotSystem.bot_behaviors import (
    create_default_bt, create_hunt_only_bt, create_wander_only_bt,
    HuntSequence, WanderAction, WaitAction
)
from BotSystem.bot_manager import BotManager

# ━━━ Test Framework ━━━
passed = 0
failed = 0
total = 0

def run_test(name, func):
    global passed, failed, total
    total += 1
    time.sleep(0.5)
    try:
        func()
        passed += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name}: {e}")

# ━━━ Server Process ━━━
server_procs = []

def start_servers():
    global server_procs
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')
    field_exe = os.path.join(build_dir, 'FieldServer.exe')
    if not os.path.exists(field_exe):
        print(f"ERROR: {field_exe} not found. Build first!")
        sys.exit(1)
    p1 = subprocess.Popen([field_exe, '7777'], cwd=build_dir,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server_procs = [p1]
    time.sleep(1.5)

def stop_servers():
    for p in server_procs:
        try:
            p.terminate()
            p.wait(timeout=3)
        except:
            p.kill()

# ━━━ Helper: wait for bot to enter game ━━━
def wait_for_game(bot, timeout=5.0):
    """Poll bot.update() until in_game is True."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        bot.update(0)
        if bot.in_game:
            return True
        time.sleep(0.05)
    return False

def wait_for_monsters(bot, count=5, timeout=3.0):
    """Poll bot.update() until monsters dict has >= count entries."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        bot.update(0)
        if len(bot.monsters) >= count:
            return True
        time.sleep(0.05)
    return False

# ━━━ Test 1: BT Framework ━━━

def test_bt_framework():
    """Selector/Sequence/Condition/Action execution order"""
    log = []

    def action_a(ctx):
        log.append('A')
        return Status.FAILURE

    def action_b(ctx):
        log.append('B')
        return Status.SUCCESS

    def action_c(ctx):
        log.append('C')
        return Status.SUCCESS

    # Selector: tries children until SUCCESS
    tree = Selector([
        Action(action_a),  # FAILURE -> try next
        Action(action_b),  # SUCCESS -> stop
        Action(action_c),  # should NOT execute
    ])

    result = tree.tick(None)
    assert result == Status.SUCCESS, f"Selector should return SUCCESS, got {result}"
    assert log == ['A', 'B'], f"Expected ['A', 'B'], got {log}"

    # Sequence: runs all until FAILURE
    log.clear()
    tree2 = Sequence([
        Action(action_b),  # SUCCESS -> continue
        Action(action_a),  # FAILURE -> stop
        Action(action_c),  # should NOT execute
    ])

    result = tree2.tick(None)
    assert result == Status.FAILURE, f"Sequence should return FAILURE, got {result}"
    assert log == ['B', 'A'], f"Expected ['B', 'A'], got {log}"

    # Inverter
    inv = Inverter(Action(action_a))
    log.clear()
    result = inv.tick(None)
    assert result == Status.SUCCESS, f"Inverter(FAILURE) should be SUCCESS, got {result}"


def test_bt_running_state():
    """Stateful RUNNING resume: Sequence resumes from RUNNING child"""
    call_count = [0]

    class CountNode(BTNode):
        """Returns RUNNING first 2 times, then SUCCESS"""
        def __init__(self):
            self.ticks = 0
        def tick(self, ctx):
            self.ticks += 1
            call_count[0] += 1
            if self.ticks < 3:
                return Status.RUNNING
            return Status.SUCCESS
        def reset(self):
            self.ticks = 0

    pre_log = []
    def pre_action(ctx):
        pre_log.append('pre')
        return Status.SUCCESS

    # Sequence: pre_action -> CountNode
    # Tick 1: pre runs, CountNode returns RUNNING (tick=1)
    # Tick 2: Sequence resumes from CountNode (pre NOT called again), returns RUNNING (tick=2)
    # Tick 3: Sequence resumes from CountNode, returns SUCCESS (tick=3)
    tree = Sequence([Action(pre_action), CountNode()])

    r1 = tree.tick(None)
    assert r1 == Status.RUNNING, f"Tick 1 should be RUNNING, got {r1}"
    assert len(pre_log) == 1, "pre_action should run once"

    r2 = tree.tick(None)
    assert r2 == Status.RUNNING, f"Tick 2 should be RUNNING, got {r2}"
    assert len(pre_log) == 1, "pre_action should NOT run again (resume from CountNode)"

    r3 = tree.tick(None)
    assert r3 == Status.SUCCESS, f"Tick 3 should be SUCCESS, got {r3}"
    assert call_count[0] == 3, f"CountNode should tick 3 times, got {call_count[0]}"


# ━━━ Test 3: Bot Login ━━━

def test_bot_login():
    """Bot auto-registers and enters game"""
    bot = BotClient(101, '127.0.0.1', 7777)
    try:
        bot.connect()
        assert bot.connected, "Bot should be connected"

        bot.login()
        assert wait_for_game(bot), "Bot should enter game within 5s"

        assert bot.entity_id != 0, f"Bot should have entity ID, got {bot.entity_id}"
        assert bot.account_id != 0, f"Bot should have account ID, got {bot.account_id}"
        assert bot.alive, "Bot should be alive"
    finally:
        bot.disconnect()


# ━━━ Test 4: Bot Receives Monsters ━━━

def test_bot_receives_monsters():
    """Bot receives MONSTER_SPAWN packets and populates monsters dict"""
    bot = BotClient(102, '127.0.0.1', 7777)
    try:
        bot.connect()
        bot.login()
        assert wait_for_game(bot), "Bot should enter game"
        assert wait_for_monsters(bot, 5), f"Expected 5 monsters, got {len(bot.monsters)}"

        # Verify monster data
        alive = [m for m in bot.monsters.values() if m.get('alive', True)]
        assert len(alive) >= 5, f"All 5 should be alive, got {len(alive)}"

        # Check goblins exist (monster_id=1)
        goblins = [m for m in bot.monsters.values() if m.get('monster_id') == 1]
        assert len(goblins) >= 1, f"Should have goblins, got {len(goblins)}"
    finally:
        bot.disconnect()


# ━━━ Test 5: Bot Hunt Monster ━━━

def test_bot_hunt_monster():
    """Bot hunts and kills a goblin using HuntSequence BT"""
    bot = BotClient(103, '127.0.0.1', 7777)
    try:
        bot.connect()
        bot.login()
        assert wait_for_game(bot), "Bot should enter game"
        assert wait_for_monsters(bot, 5), "Need monsters to hunt"

        # Find closest goblin
        goblins = [m for m in bot.monsters.values() if m.get('monster_id') == 1]
        assert len(goblins) > 0, "No goblins found"
        target = min(goblins, key=lambda g: bot.distance_to(g['x'], g['y']))

        # Position bot near the goblin (within attack range 200)
        bot.send_move(target['x'] + 30, target['y'], 0.0)
        bot.position = [target['x'] + 30, target['y'], 0.0]
        time.sleep(0.3)
        bot.update(0)  # Process server responses

        # Create hunt BT and run loop
        # Sleep slightly longer than tick_interval so server cooldown always
        # expires before the bot's local cooldown does (avoids edge-case COOLDOWN rejections)
        tree = create_hunt_only_bt()
        tick_interval = 0.1
        sleep_time = 0.12  # 20ms buffer ensures server cooldown expired

        killed = False
        for i in range(80):  # ~9.6s real time (kill expected at ~7s)
            bot.update(tick_interval)
            if bot.in_game and bot.alive:
                tree.tick(bot)
            time.sleep(sleep_time)

            # Check if target was killed
            m = bot.monsters.get(target['entity'])
            if m and not m.get('alive', True):
                killed = True
                break

        assert killed, "Bot should have killed the goblin"

        # Verify EXP gained (STAT_SYNC should have arrived after kill)
        assert bot.stats['exp'] > 0, f"Bot should have gained EXP, got {bot.stats['exp']}"
    finally:
        bot.disconnect()


# ━━━ Test 6: Bot Auto-Respawn ━━━

def test_bot_auto_respawn():
    """Bot dies from damage, BT auto-detects death and respawns"""
    bot = BotClient(104, '127.0.0.1', 7777)
    try:
        bot.connect()
        bot.login()
        assert wait_for_game(bot), "Bot should enter game"
        assert bot.alive, "Bot should be alive initially"

        # Kill the bot with massive self-damage
        bot.send_take_damage(999999)

        # Wait for death (STAT_SYNC with HP=0)
        deadline = time.time() + 3.0
        while time.time() < deadline:
            bot.update(0)
            if not bot.alive:
                break
            time.sleep(0.05)

        assert not bot.alive, "Bot should be dead after massive damage"

        # Create default BT (has dead->wait->respawn branch)
        tree = create_default_bt()
        tick_interval = 0.1

        # Run BT loop: should detect death and auto-respawn
        # WaitAction takes 1-2s, then send_respawn
        for i in range(80):  # 8s game time, ~4s real time
            bot.update(tick_interval)
            if bot.in_game:
                tree.tick(bot)
            time.sleep(0.05)

            if bot.alive:
                break  # Respawn successful

        assert bot.alive, "Bot should have auto-respawned via BT"
    finally:
        bot.disconnect()


# ━━━ Test 7: Multi-Bot Connect ━━━

def test_multi_bot_connect():
    """Multiple bots connect and enter game via BotManager"""
    manager = BotManager(count=5, host='127.0.0.1', port=7777, tick_rate=10.0)
    try:
        manager.start()

        # Check bots connected and entered game
        assert len(manager.bots) >= 3, f"Expected >= 3 connected bots, got {len(manager.bots)}"
        assert manager.active_count >= 3, f"Expected >= 3 in-game, got {manager.active_count}"

        # Let bots act briefly
        time.sleep(1.0)

        # All should still be alive (goblins deal 1 dmg, won't kill 300 HP bot)
        alive = manager.alive_count
        assert alive >= 3, f"Expected >= 3 alive bots, got {alive}"
    finally:
        manager.stop()


# ━━━ Run ━━━
if __name__ == '__main__':
    print("=" * 50)
    print("  Session 15: AI Bot System Tests")
    print("=" * 50)
    print()

    # Pure Python tests (no server needed)
    print("[1] BT Framework (pure Python)")
    run_test("BT Selector/Sequence execution", test_bt_framework)
    run_test("BT RUNNING state resume", test_bt_running_state)

    # Server tests
    start_servers()

    try:
        print()
        print("[2] Bot Client")
        run_test("Bot auto-register + login", test_bot_login)
        run_test("Bot receives monsters", test_bot_receives_monsters)

        print()
        print("[3] Bot Behaviors")
        run_test("Bot hunts monster (kill verified)", test_bot_hunt_monster)
        run_test("Bot auto-respawn after death", test_bot_auto_respawn)

        print()
        print("[4] Multi-Bot")
        run_test("5 bots connect and act", test_multi_bot_connect)

    finally:
        stop_servers()

    print()
    print("=" * 50)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
