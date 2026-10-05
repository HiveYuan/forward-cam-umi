"""Per-camera control rituals, selected automatically by V4L2 device name.

Controls latch only while streaming (see PROBLEMS_AND_FIXES.md) — call
apply(dev) AFTER frames are flowing. Each control is applied separately so a
camera lacking one (e.g. no AF control) skips it without losing the rest.
UVC_RITUAL env still overrides everything when set.
"""
import os
import subprocess

RITUALS = {
    # Arducam B0587 4K low-light (STARVIS 2). Focus is BARREL-ONLY: the UVC
    # focus_absolute control is accepted but INERT (user-verified 2026-09-07)
    # — focus lives in the physical barrel + witness mark, never here. This
    # also means both B0587 twins can share this one ritual.
    # B0587's F1.65/STARVIS2 gathers ~7x the B0591's light: sub-ms exposure
    # suffices in the lit workspace (e=2 -> ~0.2ms; huge blur headroom)
    # DIM SCENE (ceiling light at night) CERTIFIED 2026-09-03 via e8 rollout
    # ladder: e=10/gain=20 (1ms) -> mean 118, 99% detection, rigid pairs
    # 1.8mm, 14 GOOD aperture estimators / 88.0% coverage / 6.0%-of-stroke
    # fused RMS — at parity with the bright-lab e=2 numbers. e=5/gain=40 was
    # darker (67) and lost the sub-mm pairs (10 GOOD, 78.8%). ~5px blur at
    # 1 m/s; speeds beyond 0.25 m/s untested in dim. Override for dim sessions:
    #   UVC_RITUAL="auto_exposure=1,exposure_time_absolute=10,gain=20,sharpness=0,backlight_compensation=0"
    "B0587": ("auto_exposure=1,exposure_time_absolute=2,gain=0,sharpness=0,"
              "backlight_compensation=0"),
    # Arducam B0591 1080p HDR (the certified tracker):
    "1080P-HDR": ("auto_exposure=1,exposure_time_absolute=20,gain=50,"
                  "sharpness=0,backlight_compensation=0,"
                  "focus_automatic_continuous=0,focus_absolute=250"),
    # wrist fisheye ("Arducam 1080P Low Light"): fixed focus; keep exposure
    # discipline. LAB-LIGHT swept 2026-09-03: e=2/gain=0 -> mean 115, tips
    # 13/14 detect at ~110px; the old B0591-inherited e=20/gain=50 saturated
    # (mean 238, ZERO detections). NOTE the name check must not match the
    # B0587 ("4K-Low-Light") — order matters: B0587 is checked first.
    "1080P Low Light": ("auto_exposure=1,exposure_time_absolute=2,gain=0,"
                        "sharpness=0,backlight_compensation=0"),
}
DEFAULT = "auto_exposure=1,exposure_time_absolute=20,gain=50,sharpness=0"


def _name(dev):
    try:
        node = os.path.basename(os.path.realpath(dev))
        return open(f"/sys/class/video4linux/{node}/name").read().strip()
    except OSError:
        return ""


def apply(dev):
    name = _name(dev)
    ritual = os.environ.get("UVC_RITUAL")
    src = "env"
    if not ritual:
        ritual = next((r for key, r in RITUALS.items() if key in name), DEFAULT)
        src = f"auto ({name or 'unknown camera'})"
    keys = []
    for kv in ritual.split(","):
        kv = kv.strip()
        if not kv:
            continue
        r = subprocess.run(["v4l2-ctl", "-d", dev, "-c", kv],
                           capture_output=True, text=True)
        if r.returncode == 0:
            keys.append(kv.split("=")[0])
        else:
            print(f"  (skip {kv}: {r.stderr.strip()})")
    out = subprocess.run(["v4l2-ctl", "-d", dev, "-C", ",".join(keys)],
                         capture_output=True, text=True).stdout
    print(f"[ritual applied mid-stream — {src}]")
    print(out.strip())
