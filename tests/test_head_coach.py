"""The head coaches' shared rules, without a camera: the cal tally and the tile-distance ruler."""
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import head_coach as H
import tiles_pose as T

BASES, TIPS = {40, 41, 46, 47}, {2, 3}


def centres(ids, shift=0.0):
    return {i: np.array([100.0 * n + shift, 200.0]) for n, i in enumerate(ids)}


class CalTallyTests(unittest.TestCase):
    def test_faces_link_only_through_still_covisible_frames(self):
        tally = H.CalTally(BASES, TIPS, still_px_s=300.0)
        for k in range(4):                                   # 25-26 still together: 3 counted frames
            tally.add(k / 60, centres([25, 26]))
        for k in range(4, 8):                                # 26-27 seen together but sweeping fast
            tally.add(k / 60, centres([26, 27], shift=50.0 * k))
        self.assertEqual(tally.linked(), {25, 26})
        self.assertEqual(tally.pair[(25, 26)], 3)            # the first frame has no velocity yet
        self.assertEqual(tally.pair[(26, 27)], 0)

    def test_back_sides_and_tool_frame_views(self):
        tally = H.CalTally(BASES, TIPS, still_px_s=300.0)
        for k in range(3):
            tally.add(k / 60, centres([25, 26, 40]), tips_seen={2, 3}, n_tiles=2)
        tally.add(3 / 60, centres([25, 26, 46]), tips_seen={2}, n_tiles=4)
        self.assertEqual(tally.sides, ({40, 41}, {46, 47}))
        self.assertEqual(tally.back, [2, 1])
        self.assertEqual((tally.tool, tally.tool_tiles), (3, 3))      # one tip alone never counts


class TileRulerTests(unittest.TestCase):
    def test_tile_distances_are_the_layout_distances_whatever_the_camera_pose(self):
        K = np.array([[1255.7, 0, 939.0], [0, 1256.7, 560.0], [0, 0, 1]])
        dist = np.array([-.33, .19, 0, 0, -.07])
        tags = {"ids": [2, 4, 5], "edge_mm": 60.08}
        layout = {2: [0, .508, 0], 4: [.608, 0, 0], 5: [0, 0, 0]}
        truth = {(a, b): 1000 * np.linalg.norm(np.subtract(layout[a], layout[b])) for a, b in ((2, 4), (2, 5), (4, 5))}
        for rv, tv in (([2.9, .1, .1], [-.3, .25, .9]), ([3.0, -.2, .3], [-.2, .3, 1.1])):
            corners = {i: cv2.projectPoints(T.tag_obj(.06008) + np.array(p), np.array(rv), np.array(tv), K, dist)[0]
                       for i, p in layout.items()}
            got = H.tile_distances(H.tile_centres(corners, K, dist, tags))
            self.assertEqual(set(got), set(truth))
            for p, d in truth.items():
                self.assertAlmostEqual(got[p], d, delta=0.05)


if __name__ == "__main__":
    unittest.main()
