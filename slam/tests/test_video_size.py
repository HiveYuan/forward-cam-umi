"""Raw frames are decoded at the recorded size, not an assumed 4K (python -m slam.tests.test_video_size; CPU,
needs ffmpeg)."""
import subprocess
import tempfile
from pathlib import Path

from slam.preprocess import video_size


def make_video(path, w, h):
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=30",
                    "-frames:v", "3", "-c:v", "mjpeg", str(path)], check=True)


def test_video_size_reads_each_recording_mode():
    with tempfile.TemporaryDirectory() as d:
        for w, h in ((64, 36), (48, 27)):           # 16:9 like 4K and 1080p, small enough for CI
            p = Path(d) / f"take_{w}x{h}_b0587b.mkv"
            make_video(p, w, h)
            assert video_size(str(p)) == (w, h)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
