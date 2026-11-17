"""Check credential handling without opening a camera or contacting Pushbullet."""

import contextlib
import io
import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


class StartupTests(unittest.TestCase):
    def load_app(self, key=None):
        modules = {name: MagicMock() for name in ("cv2", "mediapipe", "numpy", "pushbullet")}
        environment = {} if key is None else {"PUSHBULLET_API_KEY": key}
        with patch.dict(os.environ, environment, clear=True), patch.dict(sys.modules, modules):
            with contextlib.redirect_stdout(io.StringIO()):
                return runpy.run_path(str(ROOT / "main.py"))

    def test_no_key_runs_without_notifications_or_prompt(self):
        app = self.load_app()
        detector = MagicMock()
        with patch.dict(app["main"].__globals__, {"DoomscrollDetector": detector}):
            with patch("builtins.input", side_effect=AssertionError("Startup must not prompt")):
                with contextlib.redirect_stdout(io.StringIO()):
                    app["main"]()
        detector.assert_called_once_with()
        detector.return_value.run.assert_called_once_with()

    def test_key_is_read_from_environment(self):
        app = self.load_app("  test-token  ")
        self.assertEqual(app["PUSHBULLET_API_KEY"], "test-token")
        detector = MagicMock()
        with patch.dict(app["main"].__globals__, {"DoomscrollDetector": detector}):
            with contextlib.redirect_stdout(io.StringIO()):
                app["main"]()
        detector.assert_called_once_with("test-token")

    def test_empty_key_disables_pushbullet(self):
        app = self.load_app("   ")
        with contextlib.redirect_stdout(io.StringIO()):
            detector = app["DoomscrollDetector"](app["PUSHBULLET_API_KEY"])
        self.assertFalse(detector.use_pushbullet)


if __name__ == "__main__":
    unittest.main()
