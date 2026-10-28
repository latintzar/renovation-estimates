import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/runtime-env.py"
spec = importlib.util.spec_from_file_location("runtime_env", MODULE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class PrivateRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.parent = Path(self.temporary.name)
        self.parent.chmod(0o700)
        self.path = self.parent / "runtime.env"

    def tearDown(self):
        self.temporary.cleanup()

    def test_selected_file_owns_provider_access(self):
        actual = runtime.child_env({"GEMINI_API_KEY": "synthetic-selected"}, {
            "GEMINI_API_KEY": "synthetic-inherited", "UNRELATED_PROVIDER_TOKEN": "synthetic-other",
            "AWS_PROFILE": "other-owner", "GOOGLE_APPLICATION_CREDENTIALS": "/other-owner.json", "PATH": "/bin",
        })
        self.assertEqual(actual["GEMINI_API_KEY"], "synthetic-selected")
        self.assertNotIn("UNRELATED_PROVIDER_TOKEN", actual)
        self.assertNotIn("AWS_PROFILE", actual)
        self.assertEqual(actual["AWS_CONFIG_FILE"], os.devnull)
        self.assertEqual(actual["GOOGLE_APPLICATION_CREDENTIALS"], "/recipient-google-credentials-not-configured")
        self.assertEqual(actual["PATH"], "/bin")

    def test_vertex_project_is_selected_from_owned_file(self):
        env = runtime.child_env({"GOOGLE_CLOUD_PROJECT_ID": "synthetic-owned-project"}, {"GOOGLE_CLOUD_PROJECT": "other-owner"})
        self.assertEqual(env["GOOGLE_CLOUD_PROJECT"], "synthetic-owned-project")

    def test_empty_credentials_keep_cloud_profile_guard(self):
        env = runtime.child_env({"GOOGLE_APPLICATION_CREDENTIALS": "", "GEMINI_API_KEY": ""}, {"GEMINI_API_KEY": "synthetic-other-owner"})
        self.assertEqual(env["GOOGLE_APPLICATION_CREDENTIALS"], "/recipient-google-credentials-not-configured")
        self.assertNotIn("GEMINI_API_KEY", env)

    def test_private_permissions_and_round_trip(self):
        runtime.write_config(self.path, {"GEMINI_API_KEY": "synthetic-private-value"})
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        runtime.private_path(str(self.path))
        self.assertEqual(runtime.read_config(self.path)["GEMINI_API_KEY"], "synthetic-private-value")
        self.path.chmod(0o644)
        with self.assertRaises(runtime.ConfigError):
            runtime.private_path(str(self.path))

    def test_checkout_and_links_rejected(self):
        with self.assertRaises(runtime.ConfigError):
            runtime.private_path(str(runtime.ROOT / "provider.env"))
        target = self.parent / "target"; target.write_text(""); target.chmod(0o600)
        self.path.symlink_to(target)
        with self.assertRaises(runtime.ConfigError):
            runtime.private_path(str(self.path))

    def test_unknown_duplicate_and_shell_syntax(self):
        for content in ("UNRELATED_TOKEN=synthetic\n", "GEMINI_API_KEY=a\nGEMINI_API_KEY=b\n", "export GEMINI_API_KEY=synthetic\n"):
            self.path.write_text(content)
            with self.assertRaises(runtime.ConfigError):
                runtime.read_config(self.path)
        self.path.write_text("GEMINI_API_KEY=$(echo synthetic)\n")
        self.assertEqual(runtime.read_config(self.path)["GEMINI_API_KEY"], "$(echo synthetic)")

    def test_doctor_masks_values_and_cannot_configure_from_pipe(self):
        runtime.write_config(self.path, {"GEMINI_API_KEY": "synthetic-doctor-canary"})
        run = subprocess.run([sys.executable, str(MODULE), "doctor", "--file", str(self.path)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertNotIn("synthetic-doctor-canary", run.stdout + run.stderr)
        self.assertTrue(json.loads(run.stdout)["fields"]["GEMINI_API_KEY"])
        run = subprocess.run([sys.executable, str(MODULE), "configure", "--file", str(self.path), "--capability", "gemini"], input="synthetic\n", capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertNotIn("synthetic-doctor-canary", run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
