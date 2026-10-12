"""Metric scale, perspective/depth, missing-frame and hold-leak regressions."""
import json
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import forward_width as W
import forward_width_check as C
from labels_lib import marker_obj

K = np.array([[1900., 0, 1920], [0, 1900, 1080], [0, 0, 1]])
DIST = np.array([-.12, .04, .002, -.001, .005])


def model():
    return W.PairModel(44, 46, 12.18, 12.14, 10., 64.6,
                       np.array([.023, .006, -.003]),
                       np.array([.030, .001, .0005]), np.array([.05, .04, .01]))


def observation(gap, rng=None, n=0):
    m = model()
    rv = np.array([.25 + .18*np.sin(n), -.2 + .15*np.cos(n*.7), .06])
    tv = np.array([.02*np.sin(n*.2), .01*np.cos(n), .35 + .04*np.sin(n*.3)])
    points = np.r_[marker_obj(m.base_edge_mm),
                   marker_obj(m.tail_edge_mm) @ Rotation.from_rotvec(m.rotation).as_matrix().T
                   + m.origin_m + m.travel_m * ((gap - m.minimum_gap_mm) / m.span_mm)]
    projected = cv2.projectPoints(points, rv, tv, K, DIST)[0].reshape(8, 2)
    if rng is not None:
        projected += rng.normal(0, .08, projected.shape)
    return W.Observation(rv, tv, projected[:4], projected[4:])


class ForwardWidthTests(unittest.TestCase):
    def test_joint_image_constraint_preserves_mm_across_perspectives_without_clipping(self):
        # Known widths only construct synthetic images, never enter inference.
        for gap in (-5., 10., 42.3, 67.9, 90.):
            for n in (0, 3, 8):
                prediction = W.predict_pair(observation(gap, n=n), model(), K, DIST)
                self.assertIsNotNone(prediction)
                self.assertAlmostEqual(prediction.gap_mm, gap, places=4)
                self.assertGreater(prediction.std_mm_per_pixel, 0)

    def test_training_reconstructs_motion_and_generalizes_to_unused_aperture(self):
        rng = np.random.default_rng(8)
        labels, observations = [], []
        for gap in (10., 42.3, 74.6):
            for n in range(18):
                observations.append(observation(gap, rng, n))
                labels.append(gap)
        m = W.fit_pair(observations, labels, K, DIST, tail=44, base=46,
                       tail_edge_mm=12.18, base_edge_mm=12.14,
                       minimum_gap_mm=10, span_mm=64.6)
        for n in (1, 5, 10):
            p = W.predict_pair(observation(67.9, n=n), m, K, DIST)
            self.assertIsNotNone(p)
            self.assertLess(abs(p.gap_mm - 67.9), .35)
        restored = W.PairModel.from_dict(json.loads(json.dumps(m.to_dict())))
        np.testing.assert_array_equal(restored.parameters, m.parameters)

    def test_single_hold_cannot_produce_a_spurious_width_model(self):
        with self.assertRaisesRegex(ValueError, "One hold"):
            W.fit_pair([observation(42.3)] * 5, [42.3] * 5, K, DIST,
                       tail=44, base=46, tail_edge_mm=12.18, base_edge_mm=12.14,
                       minimum_gap_mm=10, span_mm=64.6)

    def test_ambiguous_markers_and_missing_pairs_never_generate_width(self):
        o = observation(67.9)
        corners = W.unique_corners([44, 44, 46],
                                  [o.tail_corners, o.tail_corners, o.base_corners])
        self.assertEqual(set(corners), {46})
        f = W.Frame(0, 10, o.rvec, o.tvec, corners)
        width, available = W.predict_width(f, [model()], {46: np.eye(4)}, K, DIST)
        self.assertIsNone(width)
        self.assertEqual(available, {})

    def test_base_frame_conversion_does_not_modify_calibrated_geometry(self):
        o = observation(67.9)
        T = np.eye(4)
        T[:3, :3] = Rotation.from_rotvec([.2, -.1, .3]).as_matrix()
        T[:3, 3] = [.05, -.03, .1]
        original = T.copy()
        local_R = cv2.Rodrigues(o.rvec)[0]
        body_R = local_R @ T[:3, :3].T
        body_t = o.tvec - body_R @ T[:3, 3]
        f = W.Frame(0, 10, cv2.Rodrigues(body_R)[0].ravel(), body_t,
                    {44: o.tail_corners, 46: o.base_corners})
        local = W.local_observation(f, 44, 46, T)
        prediction = W.predict_pair(local, model(), K, DIST)
        self.assertAlmostEqual(prediction.gap_mm, 67.9, places=4)
        np.testing.assert_array_equal(T, original)

    def test_repeated_hold_does_not_label_the_transit_between_holds(self):
        log = {"units": "mm", "events": [
            {"event": "e8_meas", "gap_mm": g, "t_wall": t}
            for g, t in [(0, 0), (0, .5), (32.3, 3), (32.3, 3.5), (0, 6), (0, 6.5)]]}
        holds = C.measurement_holds(log)
        self.assertEqual(holds, [(0, 0, .5), (32.3, 3, 3.5), (0, 6, 6.5)])
        self.assertIsNone(C.gap_at(1, holds))
        self.assertIsNone(C.gap_at(5, holds))

    def test_empty_verification_cannot_pass_vacuously(self):
        with self.assertRaisesRegex(ValueError, "No complete measured hold"):
            C.measurement_holds({"units": "mm", "events": []})

    def test_rejected_frames_stay_in_coverage_denominator(self):
        values = np.r_[np.full(5, 57.9), np.full(5, np.nan)]
        report = C.summarize_holds(np.arange(10), values, [(57.9, 0, 9)])[0]
        self.assertEqual(report["recorded_frames"], 10)
        self.assertEqual(report["width_coverage"], .5)
        self.assertFalse(report["passed"])
        self.assertTrue(report["checks"]["p95_absolute_error_at_most_2mm"])
        # Paired NaNs also preserve the right reference labels in CV statistics.
        summary = W.error_summary([0, np.nan, 64.6], [0, 32.3, 64.6])
        self.assertEqual(summary["absolute_error_p95_mm"], 0)

    def test_projective_center_removes_perspective_mean_bias(self):
        corners = cv2.projectPoints(marker_obj(30), np.array([.5, .7, .1]),
                                     np.array([.08, .02, .2]), K, DIST)[0].reshape(4, 2)
        # Distortion must be removed before applying a projective construction
        # when checking exact geometry; production works in image pixels.
        undistorted = cv2.undistortPoints(corners.reshape(-1, 1, 2), K, DIST, P=K).reshape(4, 2)
        expected = cv2.projectPoints(np.zeros((1, 3)), np.array([.5, .7, .1]),
                                     np.array([.08, .02, .2]), K, np.zeros(5))[0].ravel()
        np.testing.assert_allclose(W.image_center(undistorted), expected, atol=1e-6)
        self.assertGreater(np.linalg.norm(undistorted.mean(axis=0)-expected), .1)


if __name__ == "__main__":
    unittest.main()
