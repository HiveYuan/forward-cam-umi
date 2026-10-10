"""Exercise setup decisions without importing AVFoundation or opening cameras."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from camera_config import CameraBinding, CaptureMode, load_config
import cameras_setup_macos as setup


class CameraSetupTests(unittest.TestCase):
    def setUp(self):
        self.inventory = [
            {"device_id": "test-1080", "name": "1080p camera",
             "modes": [(1920, 1080, 30.00003, 30.00003)]},
            {"device_id": "test-head", "name": "Identical 4K camera",
             "modes": [(3840, 2160, 25, 25), (1280, 720, 15, 30)]},
            {"device_id": "test-wrist", "name": "Identical 4K camera",
             "modes": [(3840, 2160, 25, 25), (1280, 720, 15, 30)]},
        ]

    def test_identity_preview_uses_device_capabilities_only(self):
        self.assertEqual(setup.identity_preview_mode(self.inventory[0]["modes"]),
                         CaptureMode(1920, 1080, 30))
        self.assertEqual(setup.identity_preview_mode(self.inventory[1]["modes"]),
                         CaptureMode(1280, 720, 30))
        self.assertEqual(setup.identity_preview_mode([(3840, 2160, 25, 25)]),
                         CaptureMode(3840, 2160, 25))
        self.assertEqual(setup.identity_preview_mode([(640, 480, 5, 20)]),
                         CaptureMode(640, 480, 20))
        with self.assertRaisesRegex(ValueError, "no video modes"):
            setup.identity_preview_mode([])

    def test_all_identities_precede_capture_modes_and_saved_modes_are_explicit(self):
        # Deliberately assign a 1080p device to Forward and a 4K one to Wrist:
        # role recommendations must neither reject identity nor set final mode.
        answers = iter([
            "0", "0", "y",       # Forward identity at 1080p
            "1", "180", "y",     # Head identity at 720p, rotated
            "2", "0", "y",       # Wrist identity at 720p
            "0", "", "y",        # Forward: explicitly choose available 1080p30
            "", "", "y",         # Head: accept suggested 4K25
            "1", "15", "y",      # Wrist: explicitly choose 720p15
        ])
        output = io.StringIO()
        seen = []
        def answer(prompt):
            seen.append(prompt)
            return next(answers)
        with tempfile.TemporaryDirectory() as d:
            args = SimpleNamespace(config=Path(d) / "cameras.local.json", require_head=True, seconds=1)
            with patch.object(setup.sys.stdin, "isatty", return_value=True), \
                    patch("builtins.input", side_effect=answer), \
                    patch.object(setup, "preview") as preview, redirect_stdout(output):
                setup.wizard(self.inventory, args)
            saved = load_config(args.config)
        previews = [call.args[0] for call in preview.call_args_list]
        self.assertEqual([s.role for s in previews], ["b0587", "b0587b", "fish"] * 2)
        self.assertEqual([s.width for s in previews[:3]], [1920, 1280, 1280])
        self.assertEqual(saved, previews[3:])
        self.assertEqual([s.device_id for s in saved], [i["device_id"] for i in self.inventory])
        self.assertEqual([(s.width, s.height, s.fps) for s in saved],
                         [(1920, 1080, 30), (3840, 2160, 25), (1280, 720, 15)])
        self.assertEqual(saved[1].rotation_degrees, 180)
        self.assertEqual(previews[1].rotation_degrees, 180)
        self.assertIn("Stage 1/2", output.getvalue())
        self.assertIn("Stage 2/2", output.getvalue())
        # No default is offered for a guide mode unsupported by the bound device.
        forward_mode_prompt = next(p for p in seen if "Forward" in p and "capture mode number" in p)
        self.assertNotIn("Enter =", forward_mode_prompt)

    def test_capture_failure_keeps_binding_and_does_not_fall_back_silently(self):
        binding = CameraBinding("b0587b", "test-head", "Identical 4K camera", 180)
        # First reject an out-of-range FPS without capture; then reproduce a
        # native 4K failure. Only the operator's next choice changes the mode.
        answers = ["0", "30", "0", "25", "1", "20", "y"]
        with patch("builtins.input", side_effect=answers), redirect_stdout(io.StringIO()), \
                patch.object(setup, "preview", side_effect=[RuntimeError("native mode failed"), None]) as preview:
            spec = setup.choose_capture_spec(binding, self.inventory[1]["modes"], 1)
        attempted = [call.args[0] for call in preview.call_args_list]
        self.assertEqual([s.width for s in attempted], [3840, 1280])
        self.assertTrue(all(s.device_id == binding.device_id and s.rotation_degrees == 180 for s in attempted))
        self.assertEqual((spec.width, spec.height, spec.fps), (1280, 720, 20))

    def test_identity_retry_and_duplicate_device_do_not_bind_wrong_camera(self):
        args = SimpleNamespace(require_head=True, seconds=1)
        # Reject an already-bound device, reject a preview, then confirm another.
        with patch("builtins.input", side_effect=["0", "1", "0", "n", "2", "180", "y"]), \
                patch.object(setup, "preview") as preview, redirect_stdout(io.StringIO()):
            binding = setup.choose_binding("b0587b", self.inventory, {"test-1080"}, args)
        self.assertEqual(binding.device_id, "test-wrist")
        self.assertEqual(binding.rotation_degrees, 180)
        self.assertEqual(preview.call_count, 2)

    def test_optional_head_can_be_skipped_without_opening_device(self):
        args = SimpleNamespace(require_head=False, seconds=1)
        with patch("builtins.input", return_value=""), \
                patch.object(setup, "preview") as preview, redirect_stdout(io.StringIO()):
            self.assertIsNone(setup.choose_binding("b0587b", self.inventory, set(), args))
        preview.assert_not_called()

    def test_cancel_during_mode_selection_does_not_save_preview_settings(self):
        answers = ["0", "0", "y", "1", "180", "y", "2", "0", "y"]
        with tempfile.TemporaryDirectory() as d:
            args = SimpleNamespace(config=Path(d) / "cameras.local.json", require_head=True, seconds=1)
            with patch.object(setup.sys.stdin, "isatty", return_value=True), \
                    patch("builtins.input", side_effect=answers + [KeyboardInterrupt()]), \
                    patch.object(setup, "preview"), redirect_stdout(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    setup.wizard(self.inventory, args)
            self.assertFalse(args.config.exists())


if __name__ == "__main__":
    unittest.main()
