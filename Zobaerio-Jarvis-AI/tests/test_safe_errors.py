from __future__ import annotations

import unittest

from jarvis.safe_errors import safe_exception_type, safe_tool_error, safe_worker_error


class SafeExceptionFormattingTests(unittest.TestCase):
    def test_tool_error_excludes_raw_exception_message(self) -> None:
        secret = "PRIVATE_SENTINEL C:/Users/example/private-key.txt"
        exc = RuntimeError(secret)
        message = safe_tool_error(exc)
        self.assertIn("RuntimeError", message)
        self.assertIn("Sensitive exception details were withheld", message)
        self.assertNotIn(secret, message)
        self.assertNotIn("private-key.txt", message)

    def test_worker_error_excludes_raw_exception_message(self) -> None:
        secret = "PRIVATE_SENTINEL bearer=super-secret-value"
        message = safe_worker_error(ValueError(secret))
        self.assertIn("ValueError", message)
        self.assertIn("বিস্তারিত error লুকানো হয়েছে", message)
        self.assertNotIn(secret, message)
        self.assertNotIn("super-secret-value", message)

    def test_exception_type_is_bounded_and_has_no_punctuation(self) -> None:
        class Strange_Error_Name__:
            __name__ = "Bad Type / Secret"
        # An actual exception subclass is used so the helper sees a genuine exception instance.
        StrangeError = type("Bad Type / Secret", (Exception,), {})
        self.assertEqual(safe_exception_type(StrangeError("private text")), "BadTypeSecret")

    def test_empty_exception_type_falls_back_to_error(self) -> None:
        StrangeError = type("", (Exception,), {})
        self.assertEqual(safe_exception_type(StrangeError("secret")), "Error")


if __name__ == "__main__":
    unittest.main()
