"""Identify cameras by native ID and preview their canonical image direction.

This setup stage does not enable the legacy Linux recorder on macOS.
"""
import argparse
from pathlib import Path
import sys
import time

import cv2

from camera_config import (CameraBinding, CameraSpec, CaptureMode, ROLES,
                           load_config, save_config, supported_frame_rate)
from camera_setup_options import (GUIDE_MODES, ROLE_LABELS, ROLE_HINTS,
                                  identity_preview_mode, preferred_fps)

ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_CONFIG = ROOT / "calib/cameras.macos.local.json"


def preview(spec, seconds):
    from camera_macos import PreviewCapture
    title = f"{ROLE_LABELS[spec.role]} | {spec.device_id} | rotate {spec.rotation_degrees} | q to close"
    count = 0
    try:
        with PreviewCapture(spec) as capture:
            print(f"Requested {spec.fps:g} fps; native mode {capture.negotiated_fps:.8g} fps")
            start = time.monotonic()
            while time.monotonic() - start < seconds:
                frame = capture.read()
                if count == 0:
                    print(f"Verified source and frame: {frame.image.shape[1]}x{frame.image.shape[0]}")
                scale = min(1, 1100 / frame.image.shape[1])
                display = cv2.resize(frame.image, None, fx=scale, fy=scale)
                cv2.imshow(title, display)
                count += 1
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
                if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                    break
    finally:
        cv2.destroyAllWindows()
    if count == 0:
        raise RuntimeError("preview received no frames")
    print(f"{spec.role}: preview received {count} frames; "
          "exposure, recording FPS and multi-camera synchronization NOT validated")


def choose_binding(role, inventory, used_ids, args):
    label = ROLE_LABELS[role]
    print(f"\nIdentify: {label}")
    print(ROLE_HINTS[role])
    optional = role == "b0587b" and not args.require_head
    while True:
        answer = input(f"{label}: choose device number from the list above"
                       + (" (blank to skip head)" if optional else "") + ": ").strip()
        if not answer and optional:
            return None
        try:
            index = int(answer)
            if index < 0 or index >= len(inventory):
                raise ValueError("device number out of range")
            info = inventory[index]
            if info["device_id"] in used_ids:
                raise ValueError("that device already has a role")
            rotation = int(input("Image rotation before processing [0 / 180, default 0]: ").strip() or "0")
            binding = CameraBinding(role, info["device_id"], info["name"], rotation)
            mode = identity_preview_mode(info["modes"])
            print(f"Opening device [{index}] {binding.device_id} for {label}.")
            print(f"Identity preview only: {mode.width}x{mode.height} @ {mode.fps:g} fps. "
                  "Capture settings will be chosen in stage 2.")
            print(f"Briefly cover the lens of the intended {label} to verify that this preview changes.")
            preview(CameraSpec.from_binding(binding, mode), args.seconds)
            if input(f"Is this your {label}, with an upright view? [y/N]: ").strip().lower() == "y":
                return binding
        except (ValueError, RuntimeError) as exc:
            print(f"  {exc}")


def choose_capture_spec(binding, modes, seconds):
    label = ROLE_LABELS[binding.role]
    suggested = GUIDE_MODES[binding.role]
    ranges = sorted(set(modes), reverse=True)
    if not ranges:
        raise ValueError(f"{label}: device advertises no video modes")
    print(f"\nCapture settings: {label} -> {binding.name} | {binding.device_id}")
    print("Choose from this device's supported modes. These settings will be used for calibration and capture.")
    recommendation = None
    for i, (width, height, low, high) in enumerate(ranges):
        is_suggested = ((width, height) == (suggested.width, suggested.height)
                        and supported_frame_rate(suggested.fps, low, high) is not None)
        if is_suggested and recommendation is None:
            recommendation = i
        hint = f" (guide suggestion: {suggested.fps:g} fps)" if is_suggested else ""
        print(f"  [{i}] {width}x{height}, {low:.8g}–{high:.8g} fps{hint}")
    if recommendation is None:
        print(f"The guide's {suggested.width}x{suggested.height} @ {suggested.fps:g} fps "
              "is unavailable on this device. Choose a supported mode explicitly.")
    while True:
        try:
            default = f" [Enter = {recommendation}, guide suggestion]" if recommendation is not None else ""
            answer = input(f"{label}: choose capture mode number{default}: ").strip()
            index = recommendation if not answer and recommendation is not None else int(answer)
            if index < 0 or index >= len(ranges):
                raise ValueError("capture mode number out of range")
            width, height, low, high = ranges[index]
            default_fps = preferred_fps(low, high, suggested.fps) if index == recommendation else preferred_fps(low, high)
            fps = float(input(f"Capture FPS [{low:.8g}–{high:.8g}, default {default_fps:g}]: ").strip() or default_fps)
            if supported_frame_rate(fps, low, high) is None:
                raise ValueError("FPS is outside the selected mode's supported range")
            spec = CameraSpec.from_binding(binding, CaptureMode(width, height, fps))
            print(f"Validating capture mode: {width}x{height} @ {fps:g} fps, rotation {binding.rotation_degrees}.")
            preview(spec, seconds)
            if input(f"Use this capture mode for {label}? [y/N]: ").strip().lower() == "y":
                return spec
        except (ValueError, RuntimeError) as exc:
            print(f"  {exc}")


def wizard(inventory, args):
    if args.config.exists():
        raise ValueError(f"{args.config} already exists; archive it or use --config with a new path")
    if not sys.stdin.isatty():
        raise ValueError("interactive setup requires a terminal; use --list to inspect devices")
    print("\nStage 1/2: identify the physical cameras. Capture settings come later.")
    bindings = []
    used_ids = set()
    for role in ROLES:
        binding = choose_binding(role, inventory, used_ids, args)
        if binding is not None:
            bindings.append(binding)
            used_ids.add(binding.device_id)
    print("\nStage 2/2: choose and validate capture settings for the confirmed cameras.")
    modes_by_id = {info["device_id"]: info["modes"] for info in inventory}
    selected = [choose_capture_spec(b, modes_by_id[b.device_id], args.seconds) for b in bindings]
    save_config(args.config, selected)
    print(f"Saved local bindings: {args.config}")
    for spec in selected:
        print(f"  {ROLE_LABELS[spec.role]} -> {spec.device_id} | "
              f"{spec.width}x{spec.height} @ {spec.fps:g} fps | rotate {spec.rotation_degrees}")
    print("Next: --preview ROLE to recheck. macOS session recording is not implemented yet.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list", action="store_true", help="enumerate IDs without opening cameras")
    action.add_argument("--preview", choices=ROLES, help="preview a role from the local config")
    action.add_argument("--check-config", action="store_true", help="validate bindings and modes without capture")
    parser.add_argument("--formats", action="store_true", help="also list advertised capture modes")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--require-head", action="store_true", help="require all three roles during setup")
    parser.add_argument("--seconds", type=float, default=8, help="preview duration")
    parser.add_argument("--text", action="store_true", help="use the terminal wizard instead of the graphical camera list")
    args = parser.parse_args(argv)
    if not 0 < args.seconds <= 300:
        parser.error("--seconds must be between 0 and 300")
    try:
        from camera_macos import device_info, devices, resolve_device
        if args.preview or args.check_config:
            specs = load_config(args.config)
            if args.require_head and "b0587b" not in {s.role for s in specs}:
                raise ValueError("head camera is required but not configured")
            for spec in specs:
                device = resolve_device(spec.device_id)
                info = device_info(device)
                if info["name"] != spec.name:
                    raise ValueError(f"{spec.role}: name changed for saved device ID; rerun setup")
                if not any(w == spec.width and h == spec.height
                           and supported_frame_rate(spec.fps, low, high) is not None
                           for w, h, low, high in info["modes"]):
                    raise ValueError(f"{spec.role}: configured mode is not supported")
            if args.preview:
                selected = next((s for s in specs if s.role == args.preview), None)
                if selected is None:
                    raise ValueError(f"role {args.preview} is not configured")
                preview(selected, args.seconds)
            else:
                print("Device IDs, names and requested modes match (no camera opened).")
            return
        inventory = [device_info(d) for d in devices()]
        if not inventory:
            raise RuntimeError("no video devices found")
        for i, info in enumerate(inventory):
            print(f"[{i}] {info['name']}\n    ID: {info['device_id']}")
            if args.formats:
                for width, height, low, high in info["modes"]:
                    print(f"    {width}x{height}: {low:g}–{high:g} fps")
        print("IDs may depend on USB connection. Recheck after moving ports; never use menu order as identity.")
        if not args.list:
            if args.text:
                wizard(inventory, args)
            else:
                from camera_setup_gui import run_wizard
                run_wizard(inventory, args)
    except ImportError as exc:
        parser.exit(1, f"Missing macOS dependency: {exc}. Install scripts/requirements-macos.txt\n")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Camera setup: {exc}\n")
    except (KeyboardInterrupt, EOFError):
        parser.exit(1, "\nCamera setup cancelled; no new bindings saved.\n")


if __name__ == "__main__":
    main()
