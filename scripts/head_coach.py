#!/usr/bin/env python3
"""Live coaches for the worn head camera: each one measures, while you move, what a downstream stage of
the SLAM pipeline needs from the head camera (macOS capture of the bound head role).

  coverage   tile placement while worn: share of frames with >= 2 tiles (field_qc WARNs under 50 %, and
             slam.evaluate uses only those frames) and each tile's share.
  focus      session focus meter. A tile-to-tile distance is a physical invariant: measured the way the
             layout solve measures it (tiles_pose: its detector, single-tile IPPE, per-ID edge) it reads
             long once the far tiles blur. Shown live against a reference take, next to the glove markers a
             session needs (>= 2 ball faces for the ball pose; a tail + back-marker pair for the width).
  cal        glove-calibration practice with scripts/bundle_dodeca.py's rules (still frames with >= 2 ball
             faces; a face counts once linked to the most-seen face through pairs co-visible in >= 3 still
             frames), back markers on both sides, and frames with BOTH fingertip tags and the ball (the tool
             frame, scripts/glove_tool_frame.py).
  audit-cal  the cal tally over a recorded take's marked episodes, offline.

  python scripts/head_coach.py coverage [--seconds 90] [--shots DIR]
  python scripts/head_coach.py focus --intr calib/<head>_intrinsics.json \\
         --ref-take <layout dataset> --ref-intr calib/<its head>_intrinsics.json
  python scripts/head_coach.py cal [--seconds 150] [--shots DIR]
  python scripts/head_coach.py audit-cal <cal dataset>

Yuan, 2026-11-15: coverage found a USB hub's cables lying on tile 4 (2 % of frames -> 53 % once moved);
the focus meter showed a nearer focus reading the far tiles 2-4.5 % long and set the session focus at
+-0.3 % with >= 2 ball faces in 98-100 % of frames; cal practice showed the 1080p head reads the 6 mm
fingertips only at a nearer focus, hence a cal take with its own intrinsics (SLAM_COLLECTION.md).
"""
import argparse
import collections
import itertools
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labels_lib as L  # noqa: E402
import tiles_pose as T  # noqa: E402
from field_qc import Detect  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BALL = tuple(range(25, 36))
# bundle_dodeca's MAX_VEL (150 px/s) is computed on frame-index steps of 1/29.97 s: on 60 fps 1080p frames
# that is ~300 real px/s, the stillness used here (scaled with the frame width).
STILL_PX_S_1080 = 300.0
LINK_FRAMES = 3
GREEN, RED, AMBER, CYAN = (0, 200, 0), (0, 0, 255), (0, 140, 255), (255, 255, 0)
DICTS = {"16h5": cv2.aruco.DICT_APRILTAG_16h5, "4x4": cv2.aruco.DICT_4X4_50, "36h11": cv2.aruco.DICT_APRILTAG_36h11}


def glove(unit):
    """(tails, bases, tips, tip dictionary) of a glove unit's marker map."""
    mm = json.load(open(ROOT / f"calib/marker_map_glove_{unit}.json"))
    ids = lambda key: {int(i) for i in mm[key]}  # noqa: E731
    return ids("tails"), ids("bases"), ids("tips"), mm.get("tips_dict", "4x4")


def tip_detector(family):
    p = cv2.aruco.DetectorParameters()
    p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
    return cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICTS[family]), p)


def decoded(detector, gray, keep=None):
    """{id: (4, 2) corners} of the decoded markers, optionally only those in `keep`."""
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None:
        return {}
    return {int(i): c.reshape(4, 2) for i, c in zip(ids.ravel(), corners) if keep is None or int(i) in keep}


# ---------------------------------------------------------------- the cal tally (live and offline)

class CalTally:
    """What the glove-calibration solvers will find in a take, frame by frame.

    Bundle: only STILL frames (mean marker motion under `still_px_s`) with >= 2 ball faces count, and a face
    joins the bundle once it reaches the most-seen face through pairs co-visible in >= LINK_FRAMES of them.
    Back markers: still frames with >= 2 faces and a back marker, per gripper side. Tool frame: frames with
    both fingertip tags and >= 1 ball face; `tool_tiles` additionally needs >= 2 workspace tiles."""

    def __init__(self, bases, tips, still_px_s):
        b = sorted(bases)
        self.sides = (set(b[: len(b) // 2]), set(b[len(b) // 2:]))   # each side carries a consecutive pair
        self.tips, self.still_px_s = set(tips), still_px_s
        self.pair, self.seen = collections.Counter(), collections.Counter()
        self.back, self.tool, self.tool_tiles = [0, 0], 0, 0
        self._prev = None

    def add(self, t, centres, tips_seen=(), n_tiles=0):
        """One frame at time t (s): centres {4x4 id: (x, y)}. Returns (ball faces, still)."""
        faces = sorted(set(centres) & set(BALL))
        still = False
        if self._prev is not None and faces and t > self._prev[0]:
            common = set(centres) & set(self._prev[1])
            if common:
                v = np.mean([np.linalg.norm(np.subtract(centres[i], self._prev[1][i])) for i in common])
                still = v / (t - self._prev[0]) < self.still_px_s
        self._prev = (t, centres)
        if still and len(faces) >= 2:
            self.seen.update(faces)
            self.pair.update(itertools.combinations(faces, 2))
            for k, side in enumerate(self.sides):
                self.back[k] += bool(set(centres) & side)
        both = bool(self.tips) and self.tips <= set(tips_seen)
        self.tool += both and bool(faces)
        self.tool_tiles += both and n_tiles >= 2
        return faces, still

    def linked(self):
        if not self.seen:
            return set()
        adj = collections.defaultdict(set)
        for (a, b), n in self.pair.items():
            if n >= LINK_FRAMES:
                adj[a].add(b)
                adj[b].add(a)
        ref = max(self.seen, key=self.seen.get)
        reach, stack = {ref}, [ref]
        while stack:
            for m in adj[stack.pop()] - reach:
                reach.add(m)
                stack.append(m)
        return reach

    def summary(self):
        ok = self.linked()
        return (f"faces linked {sorted(ok)}, NOT linked {[f for f in BALL if f not in ok]}\n"
                f"still co-visible frames per face {{{', '.join(f'{f}: {self.seen[f]}' for f in BALL)}}}\n"
                f"back markers {sorted(self.sides[0])}: {self.back[0]}  {sorted(self.sides[1])}: {self.back[1]}"
                f"   both tips + ball: {self.tool}   both tips + >= 2 tiles: {self.tool_tiles}")


# ---------------------------------------------------------------- tile distances (the focus meter's ruler)

def tile_centres(corners_by_id, K, dist, tags):
    """{tile id: centre (mm) in the camera frame}, by tiles_pose's single-tile IPPE with per-ID edges."""
    out = {}
    for i, c in corners_by_id.items():
        ok, _, tv = cv2.solvePnP(T.tag_obj(T.tag_edge_mm(tags, i) / 1000.0), np.asarray(c, float).reshape(4, 2),
                                 K, dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if ok:
            out[i] = tv.ravel() * 1000.0
    return out


def tile_distances(centres):
    """{(a, b): mm} for every pair of tiles in one frame (a < b): independent of the camera pose."""
    return {(a, b): float(np.linalg.norm(centres[a] - centres[b])) for a, b in itertools.combinations(sorted(centres), 2)}


def reference_distances(dataset, intr, raw_dir, tags, stride=10, min_frames=10):
    """Median tile-to-tile distances over a recorded layout take whose tiles you trust (sharp focus)."""
    K, dist = L.load_intrinsics(str(intr))
    det, ids_ok = T.detector(), {int(i) for i in tags["ids"]}
    cap, k, samples = cv2.VideoCapture(str(Path(raw_dir) / f"{dataset}_b0587b.mkv")), 0, collections.defaultdict(list)
    while cap.grab():
        if k % stride == 0:
            gray = cv2.cvtColor(cap.retrieve()[1], cv2.COLOR_BGR2GRAY)
            for p, d in tile_distances(tile_centres(decoded(det, gray, ids_ok), K, dist, tags)).items():
                samples[p].append(d)
        k += 1
    cap.release()
    ref = {p: float(np.median(v)) for p, v in samples.items() if len(v) >= min_frames}
    if not ref:
        raise SystemExit(f"{dataset}: no tile pair seen in >= {min_frames} sampled frames")
    return ref


# ---------------------------------------------------------------- coaches (one frame in, overlay lines out)

class Coverage:
    def __init__(self, tile_ids, width):
        self.det, self.ids, self.scale = Detect(), set(tile_ids), 2 if width > 2000 else 1   # field_qc's size
        self.counts, self.per_tile, self.now = [], collections.Counter(), []

    def frame(self, img, t):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if self.scale == 2:
            gray = cv2.resize(gray, (gray.shape[1] // 2, gray.shape[0] // 2), interpolation=cv2.INTER_AREA)
        self.now = sorted(set(self.det.head(gray, float(self.scale))[0]) & self.ids)
        self.counts.append(len(self.now))
        self.per_tile.update(self.now)
        return [(f"tiles {self.now}", GREEN if len(self.now) >= 2 else RED)]

    def tag(self):
        return f"tiles{len(self.now)}"

    def report(self):
        return f"tiles now {self.now}   >= 2 tiles so far {100 * np.mean(np.array(self.counts) >= 2):.0f}%"

    def final(self):
        c, n = np.array(self.counts), max(len(self.counts), 1)
        return (f"{len(c)} frames: >= 2 tiles {100 * np.mean(c >= 2):.0f}% (field_qc WARN under 50%)   "
                f">= 1 tile {100 * np.mean(c >= 1):.0f}% (FAIL under 70%)\neach tile in view: "
                + "   ".join(f"{i}: {100 * self.per_tile[i] / n:.0f}%" for i in sorted(self.ids)))


class FocusMeter:
    TOL = 0.006

    def __init__(self, K, dist, tags, ref, tails, bases):
        self.K, self.dist, self.tags, self.ref = K, dist, tags, ref
        self.det, self.ids = T.detector(), {int(i) for i in tags["ids"]}
        self.d4, self.tails, self.bases = Detect().d4, tails, bases
        self.hist = {p: collections.deque(maxlen=45) for p in ref}
        self.glove = collections.deque(maxlen=60)

    def frame(self, img, t):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        for p, d in tile_distances(tile_centres(decoded(self.det, gray, self.ids), self.K, self.dist, self.tags)).items():
            if p in self.hist:
                self.hist[p].append(d)
        four = set(decoded(self.d4, gray))
        self.glove.append((len(four & set(BALL)) >= 2, bool(four & self.tails) and bool(four & self.bases)))
        lines = []
        for (a, b), ref in self.ref.items():
            h = self.hist[(a, b)]
            if h:
                err = np.median(h) / ref - 1
                lines.append((f"{a}-{b}: {np.median(h):6.1f} mm (ref {ref:.1f}, {100 * err:+.1f}%)",
                              GREEN if abs(err) <= self.TOL else RED))
        g = np.array(self.glove)
        lines.append((f"glove, last 1 s: >= 2 ball faces {100 * g[:, 0].mean():.0f}%   tail + back {100 * g[:, 1].mean():.0f}%",
                      CYAN))
        return lines

    def report(self):
        g = np.array(self.glove) if self.glove else np.zeros((1, 2))
        return ("  ".join(f"{a}-{b} {np.median(h):6.1f} ({100 * (np.median(h) / self.ref[(a, b)] - 1):+.1f}%)"
                          for (a, b), h in self.hist.items() if h)
                + f"   ball>=2 {100 * g[:, 0].mean():.0f}%  tail+back {100 * g[:, 1].mean():.0f}%")

    def final(self):
        return self.report()

    def tag(self):
        return "focus"


class CalCoach:
    def __init__(self, tails, bases, tips, tip_family, tile_ids, width):
        self.tally = CalTally(bases, tips, STILL_PX_S_1080 * width / 1920)
        self.det, self.d16, self.tile_ids = Detect(), tip_detector(tip_family), set(tile_ids)
        self.now = ([], set(), [], False)

    def frame(self, img, t):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        centres = {i: c.mean(0) for i, c in decoded(self.det.d4, gray).items()}
        tips = set(decoded(self.d16, gray, self.tally.tips))
        tiles = sorted(set(decoded(self.det.d36, gray, self.tile_ids)))
        faces, still = self.tally.add(t, centres, tips, len(tiles))
        self.now = (faces, tips, tiles, still)
        ok, tl = self.tally.linked(), self.tally
        both = tl.tips <= tips
        return [("faces " + " ".join(f"{f}:{tl.seen[f]}" for f in BALL), GREEN if len(ok) == len(BALL) else RED),
                (f"back {sorted(tl.sides[0])}: {tl.back[0]}   {sorted(tl.sides[1])}: {tl.back[1]}",
                 GREEN if min(tl.back) >= 15 else RED),
                (f"tips + ball: {tl.tool}/30   tips + >= 2 tiles: {tl.tool_tiles}", GREEN if tl.tool >= 30 else RED),
                (f"now: tips {sorted(tips)}  faces {faces}  tiles {tiles}  {'STILL' if still else 'moving'}",
                 GREEN if both else AMBER)]

    def tag(self):
        faces, tips, tiles, _ = self.now
        return f"tips{len(tips)}_faces{len(faces)}_tiles{len(tiles)}"

    def report(self):
        tl = self.tally
        return (f"faces not linked yet {[f for f in BALL if f not in tl.linked()] or 'none'}   back {tl.back}"
                f"   tips+ball {tl.tool}   tips+tiles {tl.tool_tiles}")

    def final(self):
        return self.tally.summary()


def run_live(coach_factory, args, title):
    """Shared loop: the bound head camera, an ffplay/mpv preview with the coach's overlay, a terminal report
    every 2 s, optional full-frame snapshots every 2 s (named by the coach's tag), the summary at the end."""
    from camera_config import resolve_spec
    from camera_macos import PreviewCapture
    from preview_sink import close_sink, open_sink
    spec = resolve_spec("head", Path(args.config))
    coach = coach_factory(spec)
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    W, H = 960, 540
    sink = open_sink(title, W, H)
    try:
        with PreviewCapture(spec) as cap:
            t0 = last_print = last_shot = time.monotonic()
            while time.monotonic() - t0 < args.seconds:
                img = cap.read().image
                now = time.monotonic()
                lines = coach.frame(img, now)
                if shots and now - last_shot >= 2.0:
                    last_shot = now
                    cv2.imwrite(str(shots / f"t{now - t0:05.1f}_{coach.tag()}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                view = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
                for k, (text, colour) in enumerate(lines):
                    cv2.putText(view, text, (12, 30 + 28 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.65, colour, 2)
                if sink is not None:
                    try:
                        if sink.poll() is not None:
                            break
                        sink.stdin.write(view.tobytes())
                        sink.stdin.flush()
                    except BrokenPipeError:
                        break
                if now - last_print >= 2.0:
                    last_print = now
                    print(f"{now - t0:5.0f}s  {coach.report()}", flush=True)
    finally:
        try:
            close_sink(sink)
        except BrokenPipeError:
            pass
    print("\n" + coach.final())


def audit_cal(dataset, unit, raw_dir, tile_ids):
    """The cal tally over the head video inside the take's marked episodes (every 2nd frame, wall times)."""
    raw = Path(raw_dir)
    eps = json.load(open(raw / f"{dataset}_glove_episodes.json"))["episodes"]
    wall = np.array([f["wall"] for f in json.load(open(raw / f"{dataset}_b0587b_ts.json"))])
    inside = np.zeros(len(wall), bool)
    for e in eps:
        inside |= (wall >= e["t_start"]) & (wall <= e["t_end"])
    _, bases, tips, family = glove(unit)
    width = int(cv2.VideoCapture(str(raw / f"{dataset}_b0587b.mkv")).get(cv2.CAP_PROP_FRAME_WIDTH))
    tally, det, d16 = CalTally(bases, tips, STILL_PX_S_1080 * width / 1920), Detect(), tip_detector(family)
    cap, k = cv2.VideoCapture(str(raw / f"{dataset}_b0587b.mkv")), 0
    while cap.grab():
        if k < len(wall) and inside[k] and k % 2 == 0:
            gray = cv2.cvtColor(cap.retrieve()[1], cv2.COLOR_BGR2GRAY)
            tally.add(wall[k], {i: c.mean(0) for i, c in decoded(det.d4, gray).items()},
                      set(decoded(d16, gray, tally.tips)), len(decoded(det.d36, gray, tile_ids)))
        k += 1
    gaps = np.diff(wall[inside])
    print(f"{dataset}: {len(eps)} episode(s), {sum(e['t_end'] - e['t_start'] for e in eps):.1f} s, "
          f"{int(inside.sum())} head frames (every 2nd tallied), gaps > 0.1 s: {int((gaps > 0.1).sum())}")
    print(tally.summary())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--unit", default="yuan")
    ap.add_argument("--config", default=str(ROOT / "calib/cameras.macos.local.json"))
    ap.add_argument("--raw-dir", default=str(ROOT / "data/raw"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("coverage", "focus", "cal"):
        p = sub.add_parser(name)
        p.add_argument("--seconds", type=float, default={"coverage": 90, "focus": 300, "cal": 150}[name])
        p.add_argument("--shots", help="save a full frame every 2 s into this directory")
        if name == "focus":
            p.add_argument("--intr", required=True, help="head intrinsics nearest the focus being set")
            p.add_argument("--ref-take", required=True, help="layout take whose tile distances you trust")
            p.add_argument("--ref-intr", required=True, help="the reference take's own head intrinsics")
    p = sub.add_parser("audit-cal")
    p.add_argument("dataset")
    a = ap.parse_args(argv)

    tags = json.load(open(ROOT / f"calib/tags36h11_{a.unit}.json"))
    tile_ids = {int(i) for i in tags["ids"]}
    tails, bases, tips, family = glove(a.unit)
    if a.cmd == "audit-cal":
        return audit_cal(a.dataset, a.unit, a.raw_dir, tile_ids)
    if a.cmd == "coverage":
        return run_live(lambda spec: Coverage(tile_ids, spec.width), a, "head coach: tile coverage")
    if a.cmd == "cal":
        return run_live(lambda spec: CalCoach(tails, bases, tips, family, tile_ids, spec.width), a, "head coach: cal")
    ref = reference_distances(a.ref_take, ROOT / a.ref_intr, a.raw_dir, tags)
    print("reference tile distances (mm): " + "  ".join(f"{p[0]}-{p[1]} {d:.1f}" for p, d in ref.items()))
    K, dist = L.load_intrinsics(str(ROOT / a.intr))
    return run_live(lambda spec: FocusMeter(K, dist, tags, ref, tails, bases), a, "head coach: focus")


if __name__ == "__main__":
    main()
