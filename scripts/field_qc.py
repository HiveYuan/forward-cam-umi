#!/usr/bin/env python3
"""Field QC for a glove session, run on the recording machine right after
`record_session.py --glove` finishes, so bad episodes are re-recorded on the
spot instead of being found days later on the server.

  python scripts/field_qc.py <dataset> [--unit yuan] [--head-intr calib/<file>.json]

Defaults for --unit / --head-intr / --tags come from data/raw/<dataset>_session.json
(scripts/session_meta.py) when present. Reads data/raw/<dataset>_{b0587b,fish}.*,
<dataset>_glove_episodes.json and, for a width-holds session, <dataset>_glove_log.json.
Detection is on decoded frames in the episode windows only (half resolution for the
4K head camera), so a 15-episode session takes a few minutes. Writes
data/raw/<dataset>_field_qc.json; exit code 1 if any episode FAILs.

Per episode (FAIL = re-record it, WARN = note it):
  preroll    the head video covers the 5 s before ENTER without frame gaps (FAIL)
  turn       head rotation speed in those 5 s, from the tiles: the second-highest
             frame-pair speed above 120 deg/s (droid_adaptive's threshold) FAILs.
             Fast turns before an episode broke DROID's initialisation on glove5.
  short      under 2 s: a false start (FAIL)
  ball       the glove ball (4x4 25-35) seen in the first 0.5 s (FAIL) and in
             >= 70 % of the episode frames (the build's pose gate, FAIL)
  tiles      >= 1 tile in >= 70 % of frames (the tile GT, FAIL); >= 2 tiles in
             >= 50 % (WARN)
  width      a tail AND a back marker in view (the head-camera width needs the
             pair) in >= 70 % of frames (WARN)
  wrist      both fingertip tags decoded (cross-check only: INFO, never fails)
Per width hold (holds sessions): frames near the hold with a tail/back pair in
the head camera (WARN under 40) and the wrist tip decode rate.

Not checked here: optical sync, exposure, focus, the closed/open glove hold at
the start of the session (see docs/SLAM_COLLECTION.md).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(Path(__file__).resolve().parent))

PREROLL_S = 5.0          # SLAM segments start 5 s before ENTER
TURN_DEG_S = 120.0       # droid_adaptive: a faster pre-episode turn shortens the preroll
MIN_EP_S = 2.0
MAX_GAP_S = 0.25         # a larger hole in the timestamps = dropped/missing frames
START_S = 0.5            # "ball visible at the start" window
BALL_IDS = frozenset(range(25, 36))
GATE_BALL, GATE_TILE1, GATE_TILE2, GATE_PAIR = 0.70, 0.70, 0.50, 0.70
HOLD_PAD_S, HOLD_MIN_PAIR = 0.3, 40


# ---------------------------------------------------------------- video input

class Frames:
    """Sequential reader yielding (index, grayscale image) for wanted frame indices.

    Frame k of the mkv is entry k of <stem>_ts.json, so frames are counted by
    sequential grab, never seeked. When the container's JPEG packets decode on
    their own (macOS recordings: complete JPEGs), packets are read raw and only
    wanted frames are decoded, at reduced size by the JPEG decoder itself
    (IMREAD_REDUCED_GRAYSCALE_2). Otherwise (camera MJPEG without Huffman tables)
    frames are decoded normally and downscaled."""

    def __init__(self, path, half, allow_raw=True):
        self.path, self.half = str(path), half
        self.cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open {path}")
        self.raw = allow_raw and bool(self.cap.set(cv2.CAP_PROP_FORMAT, -1))
        self.flag = cv2.IMREAD_REDUCED_GRAYSCALE_2 if half else cv2.IMREAD_GRAYSCALE
        self.pending = None
        if self.raw:
            ok = self.cap.grab()
            okr, buf = self.cap.retrieve() if ok else (False, None)
            img = self._imdecode(buf) if okr else None
            if img is None:                       # not standalone JPEGs: decode mode
                self.cap.release()
                self.cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
                self.raw = False
            else:
                self.pending = img                # frame 0, already decoded
        self.idx = -1

    def _imdecode(self, buf):
        if buf is None or buf.size == 0:
            return None
        return cv2.imdecode(np.asarray(buf).reshape(-1), self.flag)

    def _decoded(self):
        ok, img = self.cap.retrieve()
        if not ok:
            return None
        if self.raw:
            return self._imdecode(img)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        return cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA) if self.half else g

    def read(self, wanted):
        wanted = sorted(set(int(k) for k in wanted))
        j = 0
        while j < len(wanted):
            if self.idx == -1 and self.pending is not None:
                self.idx, img = 0, self.pending
                self.pending = None
            else:
                if not self.cap.grab():
                    ok, _ = self.cap.read()       # a corrupt packet: count it, resync
                    if not ok:
                        return
                    self.idx += 1
                    continue
                self.idx += 1
                img = None
            while j < len(wanted) and wanted[j] < self.idx:
                j += 1
            if j < len(wanted) and wanted[j] == self.idx:
                if img is None:
                    img = self._decoded()
                if img is not None:
                    yield self.idx, img
                j += 1


# ---------------------------------------------------------------- detection

def _detector(dictionary, ecr=None):
    p = cv2.aruco.DetectorParameters()
    if ecr is not None:
        p.errorCorrectionRate = ecr
    return cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(dictionary), p)


class Detect:
    def __init__(self):
        self.d36 = _detector(cv2.aruco.DICT_APRILTAG_36h11)
        self.d4 = _detector(cv2.aruco.DICT_4X4_50, ecr=1.0)   # the pipeline's glove setting
        self.d16 = _detector(cv2.aruco.DICT_APRILTAG_16h5)

    @staticmethod
    def _run(det, gray):
        corners, ids, _ = det.detectMarkers(gray)
        if ids is None:
            return {}
        return {int(i): c.reshape(4, 2) for i, c in zip(ids.flatten(), corners)}

    def head(self, gray, scale):
        """Tiles (36h11) and glove markers (4x4) on a head frame; corners in full-res px."""
        tiles = {i: (c + 0.5) * scale - 0.5 for i, c in self._run(self.d36, gray).items()}
        return tiles, set(self._run(self.d4, gray))

    def wrist(self, gray):
        return set(self._run(self.d16, gray)), set(self._run(self.d4, gray))


# ---------------------------------------------------------------- head rotation from tiles

def tile_rotations(tiles, K, dist, edge_m):
    """Camera-from-tile rotation of every decoded tile (IPPE, one tag at a time)."""
    h = edge_m / 2
    obj = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], np.float64)
    out = {}
    for i, c in tiles.items():
        ok, rvec, _ = cv2.solvePnP(obj, c.astype(np.float64), K, dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if ok:
            out[i] = cv2.Rodrigues(rvec)[0]
    return out


def rot_angle_deg(Ra, Rb):
    c = (np.trace(Rb @ Ra.T) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def pair_speeds(samples):
    """samples: [(t, {tile: R})] in time order -> [(t_mid, deg/s)] over consecutive
    samples sharing a tile (median over the shared tiles)."""
    out = []
    for (ta, Ra), (tb, Rb) in zip(samples, samples[1:]):
        common = sorted(set(Ra) & set(Rb))
        if not common or tb <= ta:
            continue
        ang = np.median([rot_angle_deg(Ra[i], Rb[i]) for i in common])
        out.append(((ta + tb) / 2, float(ang / (tb - ta))))
    return out


def robust_peak(speeds):
    """Second-highest pair speed (a single IPPE pose flip makes one spurious pair),
    and the time of the highest; (None, None) without pairs."""
    if not speeds:
        return None, None
    v = sorted(s for _, s in speeds)
    peak = v[-2] if len(v) >= 2 else v[-1]
    t_max = max(speeds, key=lambda x: x[1])[0]
    return peak, t_max


# ---------------------------------------------------------------- helpers

def load_json(p):
    return json.load(open(p))


def walls_of(raw, stem):
    p = raw / f"{stem}_ts.json"
    return np.array([r["wall"] for r in load_json(p)], float) if p.exists() else None


def frames_in(walls, t0, t1):
    return np.arange(np.searchsorted(walls, t0, "left"), np.searchsorted(walls, t1, "right"))


def max_gap(walls, t0, t1):
    idx = frames_in(walls, t0, t1)
    if len(idx) < 2:
        return float("inf")
    w = walls[idx]
    edges = np.concatenate([[w[0] - t0], np.diff(w), [t1 - w[-1]]])
    return float(edges.max())


def group_holds(events, max_dt=1.0):
    """record_session's e8_meas events (every 0.5 s during a hold) -> holds."""
    holds = []
    for e in sorted((e for e in events if e.get("event") == "e8_meas"), key=lambda e: e["t_wall"]):
        h = holds[-1] if holds else None
        if h and e["gap_mm"] == h["gap_mm"] and e["t_wall"] - h["t1"] <= max_dt:
            h["t1"] = e["t_wall"]
        else:
            holds.append({"gap_mm": e["gap_mm"], "t0": e["t_wall"], "t1": e["t_wall"]})
    return holds


def frac(n, d):
    return None if d == 0 else n / d


def pct(x):
    return "  -" if x is None else f"{100 * x:3.0f}"


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--unit", help="glove unit (calib/marker_map_glove_<unit>.json); default from _session.json")
    ap.add_argument("--head-intr", help="head-camera intrinsics json; default from _session.json")
    ap.add_argument("--tags", help="workspace tags json (default from _session.json, else calib/tags36h11_<unit>.json)")
    ap.add_argument("--raw-dir", default=str(ROOT / "data/raw"))
    ap.add_argument("--head", default="b0587b", help="head camera role (stem suffix)")
    ap.add_argument("--wrist", default="fish", help="wrist camera role; '' to skip")
    ap.add_argument("--stem-suffix", default="", help="e.g. .take1 for a renamed first take")
    ap.add_argument("--stride", type=int, default=2, help="process every Nth head frame (default 2)")
    ap.add_argument("--wrist-stride", type=int, default=3)
    ap.add_argument("--episodes", help="only these episode indices, e.g. 0-9,12")
    ap.add_argument("--no-transport", action="store_true", help="skip recording_check's transport checks")
    ap.add_argument("--out", help="report path (default data/raw/<dataset>_field_qc.json)")
    a = ap.parse_args()

    raw = Path(a.raw_dir)
    meta_p = raw / f"{a.dataset}_session.json"
    meta = load_json(meta_p) if meta_p.exists() else {}
    unit = a.unit or meta.get("unit")
    if not unit:
        ap.error("--unit is required (no data/raw/<dataset>_session.json)")
    head_intr = a.head_intr or (meta.get("cameras", {}).get(a.head, {}) or {}).get("intrinsics")
    tags_p = a.tags or (meta.get("tiles", {}) or {}).get("tags") or f"calib/tags36h11_{unit}.json"
    resolve = lambda p: Path(p) if Path(p).is_absolute() else ROOT / p
    mm = load_json(resolve(f"calib/marker_map_glove_{unit}.json"))
    tags = load_json(resolve(tags_p))
    tile_ids = set(int(i) for i in tags["ids"])
    edge_m = float(tags["edge_mm"]) / 1000
    tails, bases = set(map(int, mm["tails"])), set(map(int, mm["bases"]))
    tips = sorted(map(int, mm.get("tips", {})))
    tips_dict = mm.get("tips_dict", "16h5")
    K = dist = None
    if head_intr:
        d = load_json(resolve(head_intr))
        K, dist = np.array(d["camera_matrix"], float), np.array(d["dist_coeffs"], float).reshape(-1)
    problems, warnings = [], []
    if K is None:
        warnings.append("no head intrinsics (--head-intr or _session.json): head-turn check skipped")
    if not meta:
        warnings.append(f"no {meta_p.name}: run scripts/session_meta.py {a.dataset}")

    sfx = a.stem_suffix
    head_stem, wrist_stem = f"{a.dataset}_{a.head}{sfx}", (f"{a.dataset}_{a.wrist}{sfx}" if a.wrist else None)
    hw = walls_of(raw, head_stem)
    if hw is None:
        sys.exit(f"missing {raw / (head_stem + '_ts.json')}")
    ww = walls_of(raw, wrist_stem) if wrist_stem else None
    if wrist_stem and ww is None:
        warnings.append(f"no wrist stream {wrist_stem}: wrist cross-check skipped")

    # transport (frame counts, cadence, drops) via recording_check
    transport = []
    if not a.no_transport:
        try:
            from recording_check import check_stream
            for stem in [head_stem] + ([wrist_stem] if ww is not None else []):
                try:
                    r = check_stream(raw, stem)
                    transport.append({"stem": stem, "problems": r["problems"], "timing": r["timing"]})
                    problems += [f"{stem}: {p}" for p in r["problems"]]
                except Exception as exc:          # older recorders lack the capture contract
                    warnings.append(f"{stem}: transport check unavailable ({type(exc).__name__}: {exc})")
        except ImportError as exc:
            warnings.append(f"transport check unavailable ({exc})")

    # episodes and holds, restricted to this take's wall-clock span
    ep_p = raw / f"{a.dataset}_glove_episodes.json"
    eps = load_json(ep_p)["episodes"] if ep_p.exists() else []
    eps = [e for e in eps if hw[0] - PREROLL_S - 60 <= e["t_start"] <= hw[-1]]
    if a.episodes:
        keep = set()
        for part in a.episodes.split(","):
            lo, _, hi = part.partition("-")
            keep |= set(range(int(lo), int(hi or lo) + 1))
        eps = [e for e in eps if e["episode_index"] in keep]
    log_p = raw / f"{a.dataset}_glove_log.json"
    holds = group_holds(load_json(log_p).get("events", [])) if log_p.exists() else []
    holds = [h for h in holds if hw[0] <= h["t1"] and h["t0"] <= hw[-1]]
    if not eps and not holds:
        sys.exit(f"no episodes ({ep_p.name}) and no width holds ({log_p.name}) in this take")

    # which head frames to decode: preroll + episode (+ holds), every `stride`
    want, pre_want = set(), set()
    for e in eps:
        pre = frames_in(hw, e["t_start"] - PREROLL_S, e["t_start"])
        body = frames_in(hw, e["t_start"], e["t_end"])
        pre_want |= set(pre[::a.stride].tolist())
        want |= set(pre[::a.stride].tolist()) | set(body[::a.stride].tolist())
        want |= set(frames_in(hw, e["t_start"], e["t_start"] + START_S).tolist())   # every start frame
    for h in holds:
        want |= set(frames_in(hw, h["t0"] - HOLD_PAD_S, h["t1"] + HOLD_PAD_S)[::a.stride].tolist())

    det = Detect()
    t0 = time.time()
    print(f"[head] {head_stem}: decoding {len(want)} of {len(hw)} frames ...", flush=True)
    src = Frames(raw / f"{head_stem}.mkv", half=True)
    H = {}                                   # frame -> (tile ids, glove marker ids, {tile: R})
    for k, g in src.read(want):
        tiles, glove = det.head(g, 2.0)
        tiles = {i: c for i, c in tiles.items() if i in tile_ids}
        rots = tile_rotations(tiles, K, dist, edge_m) if (K is not None and k in pre_want) else {}
        H[k] = (set(tiles), glove, rots)
    print(f"[head] {len(H)} frames in {time.time() - t0:.0f}s ({'raw JPEG' if src.raw else 'decode'} mode)", flush=True)

    W = {}
    if ww is not None:
        wwant = set()
        for e in eps:
            wwant |= set(frames_in(ww, e["t_start"], e["t_end"])[::a.wrist_stride].tolist())
        for h in holds:
            wwant |= set(frames_in(ww, h["t0"] - HOLD_PAD_S, h["t1"] + HOLD_PAD_S)[::a.wrist_stride].tolist())
        t1 = time.time()
        for k, g in Frames(raw / f"{wrist_stem}.mkv", half=False).read(wwant):
            W[k] = det.wrist(g)
        print(f"[wrist] {len(W)} frames in {time.time() - t1:.0f}s", flush=True)

    def tips_ok(ids16, ids4):
        seen = ids16 if tips_dict == "16h5" else ids4
        return bool(tips) and all(t in seen for t in tips)

    wrist_hist16, wrist_hist4 = {}, {}
    for ids16, ids4 in W.values():
        for i in ids16:
            wrist_hist16[i] = wrist_hist16.get(i, 0) + 1
        for i in ids4:
            if i not in BALL_IDS:
                wrist_hist4[i] = wrist_hist4.get(i, 0) + 1

    rows = []
    for e in eps:
        i, ts, te = e["episode_index"], e["t_start"], e["t_end"]
        fail, warn = [], []
        dur = te - ts
        if dur < MIN_EP_S:
            fail.append(f"short {dur:.1f}s (false start?)")
        have_pre = ts - hw[0]
        gap = max_gap(hw, ts - PREROLL_S, te)
        if have_pre < PREROLL_S:
            fail.append(f"preroll only {max(have_pre, 0):.1f}s recorded")
        elif gap > MAX_GAP_S:
            fail.append(f"frame gap {gap:.2f}s")
        body = [k for k in frames_in(hw, ts, te) if k in H]
        start = [k for k in frames_in(hw, ts, ts + START_S) if k in H]
        n = len(body)
        ball = frac(sum(bool(H[k][1] & BALL_IDS) for k in body), n)
        ball_start = any(H[k][1] & BALL_IDS for k in start)
        pair = frac(sum(bool(H[k][1] & tails) and bool(H[k][1] & bases) for k in body), n)
        t1c = frac(sum(len(H[k][0]) >= 1 for k in body), n)
        t2c = frac(sum(len(H[k][0]) >= 2 for k in body), n)
        pre = [k for k in frames_in(hw, ts - PREROLL_S, ts) if k in H]
        speeds = pair_speeds([(hw[k], H[k][2]) for k in pre if H[k][2]])
        peak, t_peak = robust_peak(speeds)
        n_pre_pairs = max(len(pre) - 1, 0)
        if not ball_start:
            fail.append("ball not seen in the first 0.5 s")
        if ball is not None and ball < GATE_BALL:
            fail.append(f"ball {100 * ball:.0f}% < {100 * GATE_BALL:.0f}%")
        if t1c is not None and t1c < GATE_TILE1:
            fail.append(f">=1 tile {100 * t1c:.0f}% < {100 * GATE_TILE1:.0f}%")
        elif t2c is not None and t2c < GATE_TILE2:
            warn.append(f">=2 tiles {100 * t2c:.0f}%")
        if pair is not None and pair < GATE_PAIR:
            warn.append(f"tail+back pair {100 * pair:.0f}%")
        if peak is not None and peak > TURN_DEG_S:
            fail.append(f"head turn {peak:.0f} deg/s at {t_peak - ts:+.1f}s before ENTER")
        elif K is not None and n_pre_pairs and len(speeds) < 0.5 * n_pre_pairs:
            warn.append(f"turn speed measurable on {len(speeds)}/{n_pre_pairs} preroll pairs (tiles out of view)")
        wr = None
        if W:
            wk = [k for k in frames_in(ww, ts, te) if k in W]
            wr = frac(sum(tips_ok(*W[k]) for k in wk), len(wk))
        rows.append({"episode_index": i, "duration_s": round(dur, 2), "verdict": "FAIL" if fail else ("WARN" if warn else "OK"),
                     "fail": fail, "warn": warn, "frames_checked": n, "ball": ball, "ball_at_start": ball_start,
                     "tail_back_pair": pair, "tiles_ge1": t1c, "tiles_ge2": t2c,
                     "preroll_turn_deg_s": peak, "preroll_turn_t_rel_s": None if t_peak is None else t_peak - ts,
                     "preroll_pairs_measured": len(speeds), "wrist_both_tips": wr})

    hold_rows = []
    for h in holds:
        hk = [k for k in frames_in(hw, h["t0"] - HOLD_PAD_S, h["t1"] + HOLD_PAD_S) if k in H]
        npair = sum(bool(H[k][1] & tails) and bool(H[k][1] & bases) for k in hk)
        ntail = sorted(set().union(*[H[k][1] & tails for k in hk])) if hk else []
        wr = None
        if W:
            wk = [k for k in frames_in(ww, h["t0"] - HOLD_PAD_S, h["t1"] + HOLD_PAD_S) if k in W]
            wr = frac(sum(tips_ok(*W[k]) for k in wk), len(wk))
        warn = [] if npair * a.stride >= HOLD_MIN_PAIR else [f"~{npair * a.stride} head frames with a tail+back pair < {HOLD_MIN_PAIR}"]
        hold_rows.append({"gap_mm": h["gap_mm"], "duration_s": round(h["t1"] - h["t0"], 1), "pair_frames_checked": npair,
                          "tails_seen": ntail, "wrist_both_tips": wr, "warn": warn})

    # ---- print
    if rows:
        print(f"\n{'ep':>3} {'dur':>5} {'turn':>9} {'ball':>4} {'b@0':>3} {'pair':>4} {'t>=1':>4} {'t>=2':>4} {'wrst':>4}  verdict")
        for r in rows:
            turn = "  -" if r["preroll_turn_deg_s"] is None else f"{r['preroll_turn_deg_s']:4.0f}@{r['preroll_turn_t_rel_s']:+.1f}"
            print(f"{r['episode_index']:3d} {r['duration_s']:5.1f} {turn:>9} {pct(r['ball'])} {'y' if r['ball_at_start'] else 'N':>3} "
                  f"{pct(r['tail_back_pair'])} {pct(r['tiles_ge1'])} {pct(r['tiles_ge2'])} {pct(r['wrist_both_tips'])}  "
                  f"{r['verdict']} {'; '.join(r['fail'] + r['warn'])}")
    if hold_rows:
        print(f"\nwidth holds ({len(hold_rows)}):")
        for h in hold_rows:
            print(f"  {h['gap_mm']:6.1f} mm  {h['duration_s']:4.1f}s  head tail+back frames {h['pair_frames_checked']:3d} "
                  f"(tails {h['tails_seen']})  wrist tips {pct(h['wrist_both_tips'])}%  {'; '.join(h['warn'])}")
    if W:
        top = lambda d: ", ".join(f"{k}:{v}" for k, v in sorted(d.items(), key=lambda x: -x[1])[:6]) or "-"
        print(f"\nwrist ids seen (frames): 16h5 [{top(wrist_hist16)}]  4x4 non-ball [{top(wrist_hist4)}]  "
              f"(marker map tips: {tips_dict} {tips})")
    bad = [r["episode_index"] for r in rows if r["verdict"] == "FAIL"]
    for w in warnings:
        print(f"WARN: {w}")
    for p in problems:
        print(f"PROBLEM: {p}")
    print(f"\n{len(rows)} episodes: {sum(r['verdict'] == 'OK' for r in rows)} OK, "
          f"{sum(r['verdict'] == 'WARN' for r in rows)} WARN, {len(bad)} FAIL"
          + (f" -> re-record {len(bad)} (episodes {bad}) in a new dataset name" if bad else ""))

    report = {"dataset": a.dataset, "unit": unit, "head_stem": head_stem, "wrist_stem": wrist_stem if W else None,
              "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stride": a.stride,
              "gates": {"preroll_s": PREROLL_S, "turn_deg_s": TURN_DEG_S, "min_episode_s": MIN_EP_S, "max_gap_s": MAX_GAP_S,
                        "ball": GATE_BALL, "tiles_ge1": GATE_TILE1, "tiles_ge2_warn": GATE_TILE2, "pair_warn": GATE_PAIR},
              "episodes": rows, "holds": hold_rows, "fail_episodes": bad,
              "wrist_ids_16h5": wrist_hist16, "wrist_ids_4x4": wrist_hist4,
              "transport": transport, "problems": problems, "warnings": warnings}
    out = Path(a.out) if a.out else raw / f"{a.dataset}{sfx}_field_qc.json"
    out.write_text(json.dumps(report, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    print(f"report: {out}")
    return 1 if (bad or problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())
