"""
Session 15: Bot Manager

Orchestrates multiple AI bots: spawn, tick, shutdown.

    manager = BotManager(count=20, port=7777)
    manager.start()         # connect all bots + start BT loop
    time.sleep(30)          # bots act for 30 seconds
    manager.stop()          # disconnect all
"""

import time
import threading
from .bot_client import BotClient
from .bot_behaviors import create_default_bt


class BotManager:
    def __init__(self, count=10, host='127.0.0.1', port=7777, tick_rate=10.0):
        self.count = count
        self.host = host
        self.port = port
        self.tick_interval = 1.0 / tick_rate

        self.bots = []
        self.trees = []
        self.running = False
        self._thread = None

    @property
    def active_count(self):
        return sum(1 for b in self.bots if b.in_game)

    @property
    def alive_count(self):
        return sum(1 for b in self.bots if b.in_game and b.alive)

    def start(self, bt_factory=None):
        """Connect all bots + start BT loop thread."""
        if bt_factory is None:
            bt_factory = create_default_bt

        for i in range(self.count):
            bot = BotClient(i + 1, self.host, self.port)
            tree = bt_factory()
            try:
                bot.connect()
                bot.login()
                self.bots.append(bot)
                self.trees.append(tree)
                time.sleep(0.05)  # Stagger connections
            except Exception as e:
                print(f"[BotManager] Bot {i+1} connect failed: {e}")

        # Wait for all bots to enter game
        deadline = time.time() + 5.0
        while time.time() < deadline:
            all_ready = True
            for bot in self.bots:
                bot.update(0)
                if not bot.in_game:
                    all_ready = False
            if all_ready:
                break
            time.sleep(0.05)

        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop loop + disconnect all bots."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        for bot in self.bots:
            bot.disconnect()
        self.bots.clear()
        self.trees.clear()

    def tick_once(self):
        """Manual single tick (for testing)."""
        for bot, tree in zip(self.bots, self.trees):
            if bot.connected:
                bot.update(self.tick_interval)
                if bot.in_game:
                    tree.tick(bot)

    def _loop(self):
        """BT execution loop (runs in separate thread)."""
        while self.running:
            tick_start = time.time()

            for bot, tree in zip(self.bots, self.trees):
                if not bot.connected:
                    continue
                bot.update(self.tick_interval)
                if bot.in_game:
                    tree.tick(bot)

            elapsed = time.time() - tick_start
            sleep_time = max(0, self.tick_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
