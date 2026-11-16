"""Video stream facts shared by the export tools. Kept out of slam/preprocess.py on purpose: that file is in the
preprocess and tiles steps' code hashes (slam/pipeline/registry.py), so a helper added there would recompute
every cached experiment."""
import functools
import subprocess


@functools.lru_cache(maxsize=None)
def video_size(video):
    """(width, height) of the video's first stream. Raw frames are decoded at the size the camera was
    recorded at (4K@25 for the paper's head camera, 1080p@60 for the yuan head camera under 60 Hz mains light)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
                         capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)
