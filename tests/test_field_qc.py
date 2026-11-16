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


def head_turn(deg_s, tiles=(1, 2), n=20, dt=1 / 30, noise_deg=0.0):
    """[(t, {tile: camera-from-tile R})] while the head turns at deg_s about y, with an
    optional random pose error per tile and frame."""
    rng = np.random.default_rng(0)
    tile = {i: cv2.Rodrigues(np.array([2.3, 0.3 * i, 0.1 * i]))[0] for i in tiles}
    err = lambda: cv2.Rodrigues(rng.normal(0.0, np.radians(noise_deg) / np.sqrt(3), 3))[0]
    return [(k * dt, {i: err() @ rot_y(deg_s * k * dt) @ R for i, R in tile.items()}) for k in range(n)]


def flip(samples, frames, tile):
    """The tile's pose at `frames` replaced by one 120 deg away, the size of the IPPE
    mirror-pose flips seen on yuan_pilot_01b."""
    F = cv2.Rodrigues(np.array([np.radians(120.0), 0.0, 0.0]))[0]
    for k in frames:
        samples[k][1][tile] = F @ samples[k][1][tile]
    return samples


def tiles_turning(deg_s_by_tile, n=20):
    """Like head_turn, but each tile reads its own speed (per-tile pose noise or error)."""
    per_tile = [head_turn(v, tiles=(i,), n=n) for i, v in deg_s_by_tile.items()]
    return [(frames[0][0], {i: R for _, rots in frames for i, R in rots.items()}) for frames in zip(*per_tile)]


def turn_peak(samples):
    """The preroll gate's reading: field_qc.main's chain."""
    return Q.robust_peak(Q.pair_speeds(Q.drop_pose_flips(samples, Q.TURN_DEG_S), Q.TURN_DEG_S))[0]


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

    @unittest.skipUnless(shutil.which("ffmpeg"), "requires ffmpeg")
    def test_head_is_searched_at_about_1080p_for_4k_and_1080p_takes(self):
        with tempfile.TemporaryDirectory() as d:
            for (w, h), scale in (((3840, 2160), 2), ((1920, 1080), 1)):
                stem = f"t{w}_b0587b"
                rec = MJPEGWriter(d, stem, w, h, 25, 1.0)
                rec.prepare()
                ok, jpeg = cv2.imencode(".jpg", np.zeros((h, w, 3), np.uint8))
                rec.write(jpeg, 1791600000.0)
                rec.close()
                rec.finalize()
                self.assertEqual(Q.head_detect_scale(Path(d) / f"{stem}.mkv"), scale)


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
        speeds = Q.pair_speeds([(0.0, {1: Rs[0]}), (0.05, {1: Rs[1]})], Q.TURN_DEG_S)
        self.assertAlmostEqual(speeds[0][1], 120.0, delta=4)

    def test_pairs_without_a_shared_tile_are_not_measured(self):
        self.assertEqual(Q.pair_speeds([(0.0, {1: np.eye(3)}), (0.1, {2: np.eye(3)})], Q.TURN_DEG_S), [])

    def test_one_spurious_pair_does_not_make_a_turn(self):
        speeds = [(0.1, 20.0), (0.2, 900.0), (0.3, 25.0), (0.4, 30.0)]
        peak, t = Q.robust_peak(speeds)
        self.assertEqual(peak, 30.0)
        self.assertEqual(t, 0.2)
        self.assertEqual(Q.robust_peak([(0.1, 200.0), (0.2, 210.0)])[0], 200.0)
        self.assertEqual(Q.robust_peak([]), (None, None))

    def test_a_one_frame_pose_flip_is_not_a_turn(self):
        # yuan_pilot_01b ep5: tile 2 flipped for one frame next to a calm tile 5 -> 1753 deg/s FAIL
        for tiles in ((2,), (2, 5), (2, 3, 5)):
            self.assertAlmostEqual(turn_peak(flip(head_turn(20.0, tiles), [8], 2)), 20.0, delta=0.5, msg=tiles)

    def test_a_lasting_mirror_pose_on_one_of_two_tiles_is_not_a_turn(self):
        # yuan_pilot_01c ep3: tile 5 switched next to a calm tile 2 -> 1204 deg/s FAIL
        for frames in ([8, 9, 10], range(8, 20)):       # out and back after 3 frames; switched for good
            self.assertAlmostEqual(turn_peak(flip(head_turn(20.0), frames, 2)), 20.0, delta=0.5)

    def test_tiles_that_agree_on_a_turn_count_together(self):
        # yuan_pilot_01c ep1: a real turn read 306/128, 238/95 deg/s by tiles 2/5 must still FAIL
        self.assertAlmostEqual(turn_peak(tiles_turning({2: 180.0, 5: 100.0})), 140.0, delta=1.0)
        # one tile reading far too low does not hide a turn the other two agree on
        self.assertAlmostEqual(turn_peak(tiles_turning({1: 10.0, 2: 150.0, 3: 150.0})), 150.0, delta=1.0)

    def test_a_flip_after_the_tile_was_out_of_view_is_not_a_turn(self):
        s = flip(head_turn(20.0, tiles=(2,)), [12], 2)
        del s[5:12]                                     # tile 2 unseen, then seen flipped for one frame
        self.assertAlmostEqual(turn_peak(s), 20.0, delta=0.5)

    def test_a_real_turn_above_the_gate_is_kept(self):
        # yuan_rehearsal_01 ep0: a real 129 deg/s turn on one tile must still FAIL
        for tiles in ((1,), (1, 2), (1, 2, 3)):
            s = head_turn(150.0, tiles, noise_deg=0.5)
            self.assertEqual(len(Q.drop_pose_flips(s, Q.TURN_DEG_S)), len(s))
            self.assertGreater(turn_peak(s), Q.TURN_DEG_S, msg=tiles)
            self.assertGreater(turn_peak(flip(s, [3], tiles[-1])), Q.TURN_DEG_S, msg=tiles)


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
