import json
import os
import subprocess
import sys
import textwrap
import unittest


class SecurityConfigTest(unittest.TestCase):
    def _run_app_import(self, **env_overrides):
        env = os.environ.copy()
        env.update(env_overrides)
        code = textwrap.dedent(
            """
            import json
            from fastapi.middleware.cors import CORSMiddleware
            from app.main import app

            for middleware in app.user_middleware:
                if middleware.cls is CORSMiddleware:
                    print(json.dumps(middleware.kwargs, ensure_ascii=False, sort_keys=True))
                    break
            else:
                raise RuntimeError("CORSMiddleware is not configured")
            """
        )
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=os.getcwd(),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_production_cors_requires_explicit_origins(self):
        result = self._run_app_import(
            DEBUG="false",
            CORS_ORIGINS="",
            DATABASE_URL="postgresql://nailmind:secret@db.example.test:5432/nailmind",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CORS_ORIGINS", result.stderr + result.stdout)

    def test_production_cors_rejects_wildcard_origin(self):
        result = self._run_app_import(
            DEBUG="false",
            CORS_ORIGINS="*",
            DATABASE_URL="postgresql://nailmind:secret@db.example.test:5432/nailmind",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CORS_ORIGINS", result.stderr + result.stdout)

    def test_production_cors_uses_configured_allowlist(self):
        result = self._run_app_import(
            DEBUG="false",
            CORS_ORIGINS="https://app.example.test, https://admin.example.test",
            DATABASE_URL="postgresql://nailmind:secret@db.example.test:5432/nailmind",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        middleware_kwargs = json.loads(result.stdout)
        self.assertEqual(
            middleware_kwargs["allow_origins"],
            ["https://app.example.test", "https://admin.example.test"],
        )

    def test_production_rejects_default_sqlite_database_url(self):
        result = self._run_app_import(
            DEBUG="false",
            CORS_ORIGINS="https://app.example.test",
            DATABASE_URL="sqlite:///./nailmind.db",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL", result.stderr + result.stdout)

    def test_production_accepts_external_database_url(self):
        result = self._run_app_import(
            DEBUG="false",
            CORS_ORIGINS="https://app.example.test",
            DATABASE_URL="postgresql://nailmind:secret@db.example.test:5432/nailmind",
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
