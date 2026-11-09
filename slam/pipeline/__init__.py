"""Experiment framework: stable step implementations selected by a config, cached by hash.

  python -m slam.run experiments/<exp>/config.yaml

Steps (registry.IMPLS, one or more implementations each):
  producers (big per-segment outputs, cached in <work>/cache/<step>/<key>/epNN/):
    preprocess  undistorted, cropped SLAM input frames + per-segment GT slices
    tiles       tile detections on the raw frames (evaluation GT, tile masks)
    masks       named mask sets (sam2_points, tile_geometry, ...)
    slam        named SLAM runs (droid, ...), slam.backends interface
    depth       metric depth on a SLAM run's keyframes (input of scale method B)
  analysis (small, recomputed per experiment in <work>/runs/<exp>/<variant>/):
    scale       per SLAM run: primary method + cross-checks (slam.scale methods)
    labels      tool poses on the 15 fps training grid, end-to-end check vs tiles
    evaluate    head-motion metrics vs the tile GT, label chunk metrics
    report      experiments/<exp>/results/{metrics.json, report.md}, comparisons

A producer's cache key hashes its implementation (name + version), its full parameter
set, the fingerprints of the data files it reads and the keys of the producers it
depends on, so experiments with the same upstream configuration share cache entries.
Each implementation runs as a subprocess in its own Python environment (envs.py).
"""
