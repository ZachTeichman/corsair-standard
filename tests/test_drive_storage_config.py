from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.drive_storage import DriveStorageUnavailable, _credentials


class DriveStorageConfigTests(unittest.TestCase):
    def test_invalid_google_drive_token_json_raises_clear_error(self) -> None:
        with patch.dict("os.environ", {"GOOGLE_DRIVE_TOKEN_JSON": "not-json"}, clear=True):
            with self.assertRaises(DriveStorageUnavailable) as raised:
                _credentials()
        self.assertIn("GOOGLE_DRIVE_TOKEN_JSON is not valid JSON", str(raised.exception))

    def test_invalid_google_service_account_json_raises_clear_error(self) -> None:
        with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": "not-json"}, clear=True):
            with self.assertRaises(DriveStorageUnavailable) as raised:
                _credentials()
        self.assertIn("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
