from contextlib import redirect_stdout
import io
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nb_edit import get_cell_source, load_notebook


class NotebookSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cells = load_notebook()["cells"]
        source = next(
            get_cell_source(cell)
            for cell in cells
            if get_cell_source(cell).startswith("# Environment Setup:")
        )
        cls.setup_code = compile(source, "<notebook setup>", "exec")

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        previous_directory = Path.cwd()
        os.chdir(directory.name)
        self.addCleanup(os.chdir, previous_directory)
        self.directory = Path.cwd()
        (self.directory / "requirements.txt").write_text(
            "python-dotenv>=1.0.0\n", encoding="utf-8"
        )
        (self.directory / ".env.example").write_text(
            "EXAMPLE=value\n", encoding="utf-8"
        )
        self.output = io.StringIO()
        popen_patch = patch("subprocess.Popen")
        self.popen = popen_patch.start()
        self.addCleanup(popen_patch.stop)
        self.process = self.popen.return_value.__enter__.return_value
        self.process.stdout = io.StringIO("pip progress\n")
        self.process.wait.return_value = 0

    def execute_setup(self):
        with redirect_stdout(self.output):
            exec(self.setup_code, {})

    def test_installs_with_kernel_python_and_visible_output(self):
        self.execute_setup()
        self.popen.assert_called_once_with(
            [
                sys.executable, "-m", "pip", "install",
                "--no-cache-dir", "--no-input",
                "-r", str(self.directory / "requirements.txt"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.process.wait.assert_called_once_with()
        output = self.output.getvalue()
        self.assertIn("pip progress", output)
        self.assertIn("Requirements installed successfully.", output)
        self.assertIn("Restart the kernel", output)
        self.assertEqual(
            (self.directory / ".env").read_text(encoding="utf-8"), "EXAMPLE=value\n"
        )

    def test_pip_failure_is_an_error_without_success_or_restart_banner(self):
        self.process.stdout = io.StringIO("ERROR: HASH MISMATCH\n")
        self.process.wait.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "pip exit code 1"):
            self.execute_setup()
        output = self.output.getvalue()
        self.assertIn("ERROR: HASH MISMATCH", output)
        self.assertNotIn("Requirements installed successfully.", output)
        self.assertNotIn("Restart the kernel", output)

    def test_missing_requirements_stops_before_installing_or_copying_env(self):
        (self.directory / "requirements.txt").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "Requirements file not found"):
            self.execute_setup()
        self.popen.assert_not_called()
        self.assertFalse((self.directory / ".env").exists())

    def test_existing_env_is_preserved(self):
        (self.directory / ".env").write_text("EXAMPLE=existing\n", encoding="utf-8")
        self.execute_setup()
        self.assertEqual(
            (self.directory / ".env").read_text(encoding="utf-8"), "EXAMPLE=existing\n"
        )

    def test_missing_env_template_keeps_explicit_warning(self):
        (self.directory / ".env.example").unlink()
        self.execute_setup()
        self.assertIn("No .env.example found", self.output.getvalue())
        self.assertFalse((self.directory / ".env").exists())
        self.popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
