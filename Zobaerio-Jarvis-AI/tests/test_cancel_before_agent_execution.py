from __future__ import annotations

import threading
import unittest
from unittest.mock import Mock

from app import JarvisDesktop


class _FakeRoot:
    def __init__(self) -> None:
        self.callbacks = []

    def after(self, delay, callback, *args) -> None:
        self.callbacks.append((delay, callback, args))


class CancelBeforeExecutionTests(unittest.TestCase):
    def test_cancelled_task_does_not_start_agent_or_tools(self) -> None:
        desktop = object.__new__(JarvisDesktop)
        desktop.root = _FakeRoot()
        desktop.agent = Mock()

        cancelled = threading.Event()
        cancelled.set()

        desktop._work("Create a report", None, cancelled)

        desktop.agent.respond.assert_not_called()
        self.assertEqual(len(desktop.root.callbacks), 1)
        _delay, callback, args = desktop.root.callbacks[0]
        self.assertEqual(args[0], "Task cancelled before execution began. No AI tool actions were started.")
        self.assertEqual(args[2], "cancelled")


if __name__ == "__main__":
    unittest.main()
