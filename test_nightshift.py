import tempfile
import unittest
from pathlib import Path

import glm_quota
import nightshift


class NightshiftLifecycleTests(unittest.TestCase):
    def test_prune_state_runs_drops_stale_entries(self):
        state = {
            "runs": [
                {"timestamp": "2026-02-01T00:00:00+00:00", "repo": "old/repo", "task": "old"},
                {"timestamp": "2026-04-01T00:00:00+00:00", "repo": "new/repo", "task": "new"},
                {"timestamp": "not-a-date", "repo": "bad/repo", "task": "bad"},
            ]
        }

        removed = nightshift.prune_state_runs(state, retention_days=30)

        self.assertEqual(removed, 2)
        self.assertEqual(state["runs"], [{"timestamp": "2026-04-01T00:00:00+00:00", "repo": "new/repo", "task": "new"}])

    def test_cleanup_workspace_only_removes_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_workspace = nightshift.WORKSPACE
            workspace = Path(tmpdir)
            nightshift.WORKSPACE = workspace
            try:
                (workspace / "keep.txt").write_text("keep")
                (workspace / "stale-clone").mkdir()
                (workspace / "preserved-clone").mkdir()

                removed = nightshift.cleanup_workspace({"preserved-clone"})

                self.assertEqual(removed, ["stale-clone"])
                self.assertTrue((workspace / "keep.txt").exists())
                self.assertTrue((workspace / "preserved-clone").exists())
                self.assertFalse((workspace / "stale-clone").exists())
            finally:
                nightshift.WORKSPACE = original_workspace

    def test_validate_config_rejects_unknown_keys(self):
        with self.assertRaises(ValueError):
            nightshift.validate_config({"nope": True})


class GlmQuotaTests(unittest.TestCase):
    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cache_dir = glm_quota.CACHE_DIR
            original_cache_file = glm_quota.CACHE_FILE
            cache_dir = Path(tmpdir)
            glm_quota.CACHE_DIR = cache_dir
            glm_quota.CACHE_FILE = cache_dir / "glm-quota-cache.json"
            try:
                payload = {"success": True, "data": {"hello": "world"}}
                glm_quota._write_cached_response("/test", {"a": 1}, payload)

                self.assertEqual(glm_quota._read_cached_response("/test", {"a": 1}), payload)
                self.assertIsNone(glm_quota._read_cached_response("/test", {"a": 2}))
            finally:
                glm_quota.CACHE_DIR = original_cache_dir
                glm_quota.CACHE_FILE = original_cache_file

    def test_should_run_reports_missing_key(self):
        original_key = glm_quota.GLM_KEY
        glm_quota.GLM_KEY = ""
        try:
            self.assertEqual(
                glm_quota.should_run_nightshift(),
                (False, "GLM_API_KEY is not set", None),
            )
        finally:
            glm_quota.GLM_KEY = original_key


if __name__ == "__main__":
    unittest.main()
