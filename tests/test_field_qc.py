"""field_qc: frame indexing on a real macOS-style MJPEG take, head-turn speed from
tiles, robust peak, width-hold grouping, and gap detection."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import field_qc as Q
from recording_io import MJPEGWriter


def rot_y(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])


class FrameReaderTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "requires ffmpeg")
    def test_wanted_frames_come_back_with_their_own_index(self):
        with tempfile.TemporaryDirectory() as d:
            w = MJPEGWriter(d, "t_b0587b", 160, 96, 25, 0.2)       # several segments
            w.prepare()
            for i in range(20):
                ok, jpeg = cv2.imencode(".jpg", np.full((96, 160, 3), 10 * i, np.uint8),
                                        [cv2.IMWRITE_JPEG_QUALITY, 95])
                w.write(jpeg, 1791600000 + i / 25)
            w.close()
            w.finalize()
            wanted = [0, 3, 4, 11, 19]
            for allow_raw in (True, False):
                for half in (True, False):
                    src = Q.Frames(Path(d) / "t_b0587b.mkv", half=half, allow_raw=allow_raw)
                    got = list(src.read(wanted))
                    self.assertEqual([k for k, _ in got], wanted)
                    for k, img in got:
                        self.assertEqual(img.shape, (48, 80) if half else (96, 160))
                        self.assertAlmostEqual(float(img.mean()), 10 * k, delta=3)
                    if allow_raw:
                        self.assertTrue(src.raw)       # complete JPEGs decode on their own


class TurnSpeedTests(unittest.TestCase):
    def test_tile_rotation_recovers_a_known_camera_turn(self):
        K = np.array([[900.0, 0, 640], [0, 900.0, 360], [0, 0, 1]])
        dist = np.zeros(5)
        h = 0.03
        obj = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]])
        Rs = []
        for deg in (0.0, 6.0):                          # the camera turns 6 deg about y
            R = rot_y(deg) @ cv2.Rodrigues(np.array([2.3, 0.0, 0.0]))[0]
            t = np.array([0.05, -0.02, 0.8])
            img, _ = cv2.projectPoints(obj, cv2.Rodrigues(R)[0], t, K, dist)
            Rs.append(Q.tile_rotations({1: img.reshape(4, 2)}, K, dist, 2 * h)[1])
        self.assertAlmostEqual(Q.rot_angle_deg(*Rs), 6.0, delta=0.2)
        speeds = Q.pair_speeds([(0.0, {1: Rs[0]}), (0.05, {1: Rs[1]})])
        self.assertAlmostEqual(speeds[0][1], 120.0, delta=4)

    def test_pairs_without_a_shared_tile_are_not_measured(self):
        self.assertEqual(Q.pair_speeds([(0.0, {1: np.eye(3)}), (0.1, {2: np.eye(3)})]), [])

    def test_one_spurious_pair_does_not_make_a_turn(self):
        speeds = [(0.1, 20.0), (0.2, 900.0), (0.3, 25.0), (0.4, 30.0)]
        peak, t = Q.robust_peak(speeds)
        self.assertEqual(peak, 30.0)
        self.assertEqual(t, 0.2)
        self.assertEqual(Q.robust_peak([(0.1, 200.0), (0.2, 210.0)])[0], 200.0)
        self.assertEqual(Q.robust_peak([]), (None, None))


class HoldsAndGapsTests(unittest.TestCase):
    def test_holds_split_on_width_change_and_pause(self):
        ev = [{"event": "e8_meas", "t_wall": t, "gap_mm": g, "gripper_pos": g}
              for t, g in [(0, 0.0), (0.5, 0.0), (1.0, 0.0), (5, 20.0), (5.5, 20.0), (9, 20.0)]]
        holds = Q.group_holds(ev + [{"event": "other", "t_wall": 2}])
        self.assertEqual([(h["gap_mm"], h["t0"], h["t1"]) for h in holds],
                         [(0.0, 0, 1.0), (20.0, 5, 5.5), (20.0, 9, 9)])

    def test_max_gap_sees_holes_and_missing_edges(self):
        w = np.arange(0, 10, 0.04)
        self.assertLess(Q.max_gap(w, 2.0, 4.0), 0.05)
        w2 = np.concatenate([w[w < 3.0], w[w > 3.5]])
        self.assertGreater(Q.max_gap(w2, 2.0, 4.0), 0.45)
        self.assertGreater(Q.max_gap(w, -1.0, 1.0), 0.9)    # window starts before the recording


if __name__ == "__main__":
    unittest.main()
