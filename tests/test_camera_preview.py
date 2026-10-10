"""Single-worker lifecycle, failure recovery, and bounded teardown tests."""
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from camera_config import CaptureSource
from camera_preview import PreviewSession


def synthetic_worker(source, stop, frames, events):
    import numpy as np
    if source.device_id == "failed":
        events.send("Simulated camera failure")
        return
    if source.device_id == "stuck":
        time.sleep(30)  # Parent must be able to terminate native startup stalls.
        return
    frames.cancel_join_thread()
    frames.put((time.monotonic(), np.zeros((2, 3, 3), np.uint8)))
    stop.wait(20)


class PreviewSessionTests(unittest.TestCase):
    def make_session(self, **kwargs):
        session = PreviewSession(worker_target=synthetic_worker, **kwargs)
        self.addCleanup(session.close)
        return session

    def wait_for_frame_or_error(self, session):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            state = session.poll()
            if state.live or state.error:
                return state
            time.sleep(0.02)
        self.fail("Preview worker did not produce a frame or error")

    def test_switch_stops_old_worker_before_starting_new_one(self):
        session = self.make_session()
        session.start(CaptureSource("first", "test", 640, 480, 30))
        first = self.wait_for_frame_or_error(session)
        self.assertTrue(first.live)
        session.start(CaptureSource("second", "test", 640, 480, 30))
        self.assertFalse(first.process.is_alive())
        self.assertTrue(first.released)
        second = self.wait_for_frame_or_error(session)
        self.assertTrue(second.live)
        self.assertEqual(second.source.device_id, "second")
        session.close()
        self.assertFalse(second.process.is_alive())
        self.assertIsNone(session.state)

    def test_failed_camera_is_released_and_next_camera_can_open(self):
        session = self.make_session()
        session.start(CaptureSource("failed", "test", 640, 480, 30))
        failed = self.wait_for_frame_or_error(session)
        self.assertIn("Simulated camera failure", failed.error)
        self.assertFalse(failed.process.is_alive())
        session.start(CaptureSource("live", "test", 640, 480, 30))
        self.assertTrue(self.wait_for_frame_or_error(session).live)

    def test_switch_releases_stalled_startup(self):
        session = self.make_session()
        session.start(CaptureSource("stuck", "test", 640, 480, 30))
        previous = session.state
        start = time.monotonic()
        session.start(CaptureSource("live", "test", 640, 480, 30))
        self.assertLess(time.monotonic() - start, 2)
        self.assertFalse(previous.process.is_alive())
        self.assertTrue(self.wait_for_frame_or_error(session).live)

    def test_blocked_startup_times_out_without_blocking_the_caller(self):
        session = self.make_session(startup_timeout=0.2)
        start = time.monotonic()
        session.start(CaptureSource("stuck", "test", 640, 480, 30))
        self.assertLess(time.monotonic() - start, 1)
        state = session.state
        state.started -= 1
        session.poll()
        self.assertIn("No preview", state.error)
        self.assertFalse(state.process.is_alive())
        session.close()
        session.close()  # Closing after a released error is idempotent.


if __name__ == "__main__":
    unittest.main()
