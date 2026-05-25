from __future__ import annotations

import asyncio
import unittest

from fastapi.responses import Response

from backend.main import (
    add_security_headers,
    configured_allowed_hosts,
    configured_cors_origins,
    drive_upload_mode,
    parse_csv_env,
    public_base_origin,
    validate_runtime_config,
)


class RuntimeConfigTests(unittest.TestCase):
    def test_parse_csv_env_trims_and_skips_empty_values(self) -> None:
        self.assertEqual(parse_csv_env(" https://a.example, ,https://b.example "), ["https://a.example", "https://b.example"])

    def test_public_base_origin_strips_paths(self) -> None:
        self.assertEqual(public_base_origin("https://corsair.example.com/app"), "https://corsair.example.com")

    def test_public_base_origin_rejects_invalid_values(self) -> None:
        self.assertIsNone(public_base_origin(""))
        self.assertIsNone(public_base_origin("corsair.example.com"))

    def test_configured_cors_origins_includes_dev_configured_and_public_origins(self) -> None:
        origins = configured_cors_origins(
            cors_allowed_origins="https://frontend.example.com, https://admin.example.com",
            public_base_url="https://api.example.com/app",
        )
        self.assertIn("http://localhost:5173", origins)
        self.assertIn("https://frontend.example.com", origins)
        self.assertIn("https://admin.example.com", origins)
        self.assertIn("https://api.example.com", origins)
        self.assertEqual(len(origins), len(set(origins)))

    def test_configured_allowed_hosts_uses_csv(self) -> None:
        self.assertEqual(
            configured_allowed_hosts("corsair.example.com, localhost"),
            ["corsair.example.com", "localhost"],
        )

    def test_runtime_config_allows_incomplete_development_config(self) -> None:
        validate_runtime_config(app_env="development", public_base_url="", admin_cleanup_token="", allowed_hosts="")

    def test_runtime_config_rejects_incomplete_production_config(self) -> None:
        with self.assertRaises(RuntimeError) as raised:
            validate_runtime_config(app_env="production", public_base_url="", admin_cleanup_token="", allowed_hosts="")
        message = str(raised.exception)
        self.assertIn("PUBLIC_BASE_URL", message)
        self.assertIn("ADMIN_CLEANUP_TOKEN", message)
        self.assertIn("ALLOWED_HOSTS", message)

    def test_runtime_config_requires_https_public_base_url_in_production(self) -> None:
        with self.assertRaises(RuntimeError) as raised:
            validate_runtime_config(
                app_env="production",
                public_base_url="http://corsair.example.com",
                admin_cleanup_token="secret",
                allowed_hosts="corsair.example.com",
            )
        self.assertIn("https://", str(raised.exception))

    def test_runtime_config_accepts_complete_production_config(self) -> None:
        validate_runtime_config(
            app_env="production",
            public_base_url="https://corsair.example.com",
            admin_cleanup_token="secret",
            allowed_hosts="corsair.example.com",
        )

    def test_drive_upload_mode_accepts_known_modes(self) -> None:
        self.assertEqual(drive_upload_mode("sync"), "sync")
        self.assertEqual(drive_upload_mode("background"), "background")
        self.assertEqual(drive_upload_mode("disabled"), "disabled")

    def test_drive_upload_mode_defaults_unknown_values_to_background(self) -> None:
        self.assertEqual(drive_upload_mode("surprise"), "background")

    def test_health_response_includes_security_headers(self) -> None:
        async def call_next(_: object) -> Response:
            return Response("ok")

        response = asyncio.run(add_security_headers(None, call_next))
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["referrer-policy"], "strict-origin-when-cross-origin")
        self.assertEqual(response.headers["x-frame-options"], "SAMEORIGIN")
        self.assertEqual(response.headers["permissions-policy"], "camera=(), microphone=(), geolocation=()")


if __name__ == "__main__":
    unittest.main()
