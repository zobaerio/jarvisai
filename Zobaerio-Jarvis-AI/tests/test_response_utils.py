from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from jarvis.response_utils import ResponseTooLargeError, read_bounded_json


class BoundedResponseTests(unittest.TestCase):
    def test_reads_json_incrementally_and_closes_response(self) -> None:
        response = Mock()
        response.iter_content.return_value = [b'{"ok":', b'true}']
        self.assertEqual(read_bounded_json(response, 100), {"ok": True})
        response.iter_content.assert_called_once_with(chunk_size=64 * 1024)
        response.close.assert_called_once_with()

    def test_rejects_oversized_body_and_closes_response(self) -> None:
        response = Mock()
        response.iter_content.return_value = [b"x" * 6, b"y"]
        with self.assertRaises(ResponseTooLargeError):
            read_bounded_json(response, 6)
        response.close.assert_called_once_with()

    def test_rejects_non_byte_chunk_and_closes_response(self) -> None:
        response = Mock()
        response.iter_content.return_value = ["not bytes"]
        with self.assertRaisesRegex(ValueError, "non-byte chunk"):
            read_bounded_json(response, 100)
        response.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
