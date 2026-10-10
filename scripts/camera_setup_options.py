"""Presentation labels and device-mode choices shared by both setup UIs."""
from camera_config import CaptureMode, supported_frame_rate

# Pilot suggestions, never identity constraints or silent capture fallbacks.
GUIDE_MODES = {"b0587": CaptureMode(3840, 2160, 25),
              "b0587b": CaptureMode(3840, 2160, 25),
              "fish": CaptureMode(1920, 1080, 30)}
ROLE_LABELS = {
    "b0587": "Forward camera (b0587)",
    "b0587b": "Head camera (b0587b)",
    "fish": "Wrist camera (fish)",
}
ROLE_HINTS = {
    "b0587": "Select the external camera viewing the workspace and tracking the glove's marker ball.",
    "b0587b": "Select the camera worn on your head. If mounted upside down, choose 180 degrees.",
    "fish": "Select the fisheye camera mounted on the glove/gripper.",
}


def preferred_fps(low, high, preferred=30):
    if supported_frame_rate(preferred, low, high) is not None:
        return preferred
    return min(max(preferred, low), high)


def identity_preview_mode(modes, max_width=1280, max_height=720, fps=30):
    """Choose an advertised identity-preview mode, independently of the role.

Prefer the largest mode below the size limits; otherwise choose the smallest
available. Temporary preview settings must never become capture defaults.
    """
    if not modes:
        raise ValueError("device advertises no video modes")
    small = [m for m in modes if m[0] <= max_width and m[1] <= max_height]
    candidates = small or modes
    target_area = (max if small else min)(w * h for w, h, _, _ in candidates)
    candidates = [m for m in candidates if m[0] * m[1] == target_area]
    width, height, low, high = min(
        candidates, key=lambda m: (abs(preferred_fps(m[2], m[3], fps) - fps), m))
    return CaptureMode(width, height, preferred_fps(low, high, fps))
