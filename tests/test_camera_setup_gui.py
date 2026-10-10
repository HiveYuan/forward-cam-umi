"""Keyboard and lifecycle tests using synthetic previews, never cameras."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
HAS_QT = importlib.util.find_spec("PySide6") is not None
if HAS_QT:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from camera_setup_gui import CameraWizard
    from camera_config import load_config, normalize_image


class FakeSession:
    def __init__(self):
        self.state = None
        self.starts = []
        self.fail_start = False

    def start(self, source):
        assert self.state is None, "UI must release the previous preview before switching"
        self.starts.append(source)
        if self.fail_start:
            raise RuntimeError("Simulated startup failure")
        pixels = np.zeros((180, 320, 3), np.uint8)
        pixels[:] = (70, 45, 20)
        pixels[:90, :160] = (30, 150, 230)
        pixels[90:, 160:] = (150, 100, 40)
        self.state = SimpleNamespace(
            source=source, live=True, error="", last_frame=time.monotonic(),
            first_frame=time.monotonic() - 20,
            image=normalize_image(pixels, source.rotation_degrees))

    def poll(self):
        return self.state

    def close(self):
        self.state = None


@unittest.skipUnless(HAS_QT, "install macOS UI dependencies to test Qt")
class CameraGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.inventory = [
            {"device_id": f"demo-device-{i}",
             "name": "Identical 4K camera" if i < 2 else f"Demo camera {i}",
             "modes": [(640, 480, 15, 30), (1920, 1080, 30.00003, 30.00003),
                       (3840, 2160, 25, 25)]} for i in range(6)
        ]
        self.session = FakeSession()
        self.args = SimpleNamespace(config=Path(self.directory.name) / "cameras.local.json",
                                    seconds=0.01, require_head=True)
        self.window = CameraWizard(self.inventory, self.args, self.session)
        self.window.show()
        self.settle()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.directory.cleanup()

    def settle(self, window=None):
        window = window or self.window
        if window.switch_timer.isActive():
            QTest.qWait(window.SWITCH_DELAY_MS + 60)
        self.app.processEvents()
        window.tick()

    def enter(self):
        target = self.window.choices if self.window.choices.isVisible() else self.window.next_button
        QTest.keyClick(target, Qt.Key.Key_Return)
        self.settle()

    def bind_all(self):
        for role in range(3):
            self.enter()  # First unassigned camera -> rotation
            if role == 1:
                QTest.keyClick(self.window.choices, Qt.Key.Key_Down)
            self.enter()  # Confirm physical identity and direction

    def test_keyboard_can_complete_all_stages_and_save_explicit_modes(self):
        self.assertEqual(self.window.choices.count(), 6)
        self.assertEqual(len(self.session.starts), 1)
        self.assertEqual(self.window.stage, "identity")
        self.assertIn("Forward", self.window.title.text())
        self.bind_all()
        self.assertEqual(self.window.stage, "mode")
        self.assertEqual(self.window.bindings["b0587b"].rotation_degrees, 180)
        self.assertFalse(self.args.config.exists())
        for _ in range(3):
            self.enter()  # Test suggested mode
            self.assertEqual(self.window.stage, "validate")
            self.assertTrue(self.window.next_button.isEnabled())
            self.enter()  # Accept validated mode
        self.assertEqual(self.window.stage, "review")
        self.assertIsNone(self.session.state)
        self.assertFalse(self.args.config.exists())
        self.enter()
        self.assertEqual(self.window.stage, "done")
        specs = load_config(self.args.config)
        self.assertEqual([s.device_id for s in specs], [f"demo-device-{i}" for i in range(3)])
        self.assertEqual([(s.width, s.height) for s in specs], [(3840, 2160)] * 2 + [(1920, 1080)])
        self.assertEqual(specs[1].rotation_degrees, 180)
        full_head = [s for s in self.session.starts if s.device_id == "demo-device-1" and s.width == 3840]
        self.assertEqual(full_head[0].rotation_degrees, 180)

    def test_arrow_selection_uses_exact_id_for_identically_named_devices(self):
        QTest.keyClick(self.window.choices, Qt.Key.Key_Down)
        self.assertEqual(self.window.pending_id, "demo-device-1")
        self.settle()
        self.assertEqual(self.session.state.source.device_id, "demo-device-1")
        self.enter()
        self.enter()
        self.assertEqual(self.window.bindings["b0587"].device_id, "demo-device-1")
        assigned = self.window.choices.item(1)
        self.assertFalse(assigned.flags() & Qt.ItemFlag.ItemIsEnabled)

    def test_rapid_selection_closes_old_preview_and_only_opens_last_device(self):
        self.assertFalse(self.window.preview.image.pixmap().isNull())
        for _ in range(3):
            QTest.keyClick(self.window.choices, Qt.Key.Key_Down)
        self.assertIsNone(self.session.state)
        self.assertTrue(self.window.preview.image.pixmap().isNull())
        self.assertEqual(self.window.preview.identity.text(), "demo-device-3")
        self.assertFalse(self.window.next_button.isEnabled())
        # Enter before a frame arrives must not bind the previous image.
        QTest.keyClick(self.window.choices, Qt.Key.Key_Return)
        self.assertEqual(self.window.stage, "identity")
        self.settle()
        self.assertEqual([s.device_id for s in self.session.starts], ["demo-device-0", "demo-device-3"])
        self.assertTrue(self.window.next_button.isEnabled())

    def test_failed_camera_can_be_retried_or_switched_without_losing_bindings(self):
        self.enter()
        self.enter()  # Forward confirmed; now preview Head candidate.
        confirmed = dict(self.window.bindings)
        source = self.session.state.source
        self.session.state.live, self.session.state.error = False, "No frame"
        self.window.tick()
        self.assertFalse(self.window.next_button.isEnabled())
        self.enter()
        self.assertEqual(self.window.stage, "identity")
        self.window.retry_button.click()
        self.settle()
        self.assertEqual(self.session.state.source, source)
        self.assertTrue(self.window.next_button.isEnabled())
        self.assertEqual(self.window.bindings, confirmed)
        self.session.state.live, self.session.state.error = False, "No frame"
        QTest.keyClick(self.window.choices, Qt.Key.Key_Down)
        self.settle()
        self.assertEqual(self.session.state.source.device_id, "demo-device-2")
        self.assertEqual(self.window.bindings, confirmed)

    def test_failed_formal_validation_cannot_save_and_back_retains_bindings(self):
        self.bind_all()
        self.enter()
        self.session.state.live = False
        self.session.state.error = "Wrong source dimensions"
        self.window.tick()
        self.enter()
        self.assertEqual(self.window.stage, "validate")
        self.assertFalse(self.args.config.exists())
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.settle()
        self.assertEqual(self.window.stage, "mode")
        self.assertEqual(len(self.window.bindings), 3)
        self.assertIsNone(self.session.state)

    def test_startup_exception_is_visible_and_retry_uses_same_capture_mode(self):
        self.bind_all()
        self.session.fail_start = True
        self.enter()
        self.assertIn("Simulated startup failure", self.window.notice.text())
        self.assertFalse(self.window.next_button.isEnabled())
        source = self.session.starts[-1]
        self.session.fail_start = False
        self.window.retry_button.click()
        self.settle()
        self.assertEqual(self.session.state.source, source)
        self.assertTrue(self.window.next_button.isEnabled())

    def test_rotation_preview_does_not_rotate_normalized_capture_twice(self):
        self.bind_all()
        self.enter()
        self.enter()  # Head mode
        self.enter()  # Head validation, normalized in the worker
        shown = self.window.preview.image.pixmap().toImage()
        # Original top-left is orange; normalized top-left is blue.
        color = shown.pixelColor(shown.width() // 4, shown.height() // 4)
        self.assertGreater(color.blue(), color.red())

    def test_back_to_identity_releases_binding_for_editing(self):
        self.bind_all()
        self.window.go_back()
        self.settle()
        self.assertIn("Wrist", self.window.title.text())
        self.assertNotIn("fish", self.window.bindings)
        self.assertEqual(len(self.window.bindings), 2)
        self.enter()
        self.window.go_back()  # Rotation -> same selected identity.
        self.assertEqual(self.window.pending_id, "demo-device-2")
        self.window.go_back()  # Wrist -> edit Head.
        self.settle()
        self.assertEqual(list(self.window.bindings), ["b0587"])
        self.assertEqual(self.window.pending_id, "demo-device-1")

    def test_optional_skip_stops_camera_without_opening_another_until_next_role(self):
        self.args.require_head = False
        self.enter()
        self.enter()
        self.window.choices.setCurrentRow(self.window.choices.count() - 1)
        self.assertIsNone(self.session.state)
        self.assertIsNone(self.window.pending_id)
        self.assertTrue(self.window.next_button.isEnabled())
        self.enter()
        self.assertIn("Wrist", self.window.title.text())
        self.assertNotIn("b0587b", self.window.bindings)

    def test_closing_cancels_pending_switch_without_partial_config(self):
        QTest.keyClick(self.window.choices, Qt.Key.Key_Down)
        self.window.close()
        starts = len(self.session.starts)
        QTest.qWait(self.window.SWITCH_DELAY_MS + 60)
        self.assertEqual(len(self.session.starts), starts)
        self.assertIsNone(self.session.state)
        self.assertFalse(self.args.config.exists())
        self.assertIsNone(self.window.result)

    def test_large_inventory_uses_list_and_only_one_preview(self):
        more = self.inventory + [dict(self.inventory[0], device_id=f"extra-{i}") for i in range(10)]
        other = CameraWizard(more, self.args, FakeSession())
        self.addCleanup(other.close)
        other.show()
        self.settle(other)
        self.assertEqual(other.choices.count(), 16)
        self.assertEqual(len(other.session.starts), 1)
        destination = os.environ.get("UMI_UI_PREVIEW_DIR")
        if destination:
            path = Path(destination)
            path.mkdir(parents=True, exist_ok=True)
            self.window.grab().save(str(path / "camera-list-preview.png"))
            other.grab().save(str(path / "camera-long-list-preview.png"))


if __name__ == "__main__":
    unittest.main()
