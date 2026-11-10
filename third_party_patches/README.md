# Local patches of third-party code

The text of each uncommitted change in a third-party checkout that a pipeline step runs. A
change's sha256 is recorded in the cache key and in run.json, under
`code_fingerprints.<impl>.git:<checkout>`; the matching file here has that hash's first 12 hex
digits in its name. To rebuild a checkout: clone it at the recorded commit, then
`git apply <file>` in the checkout (or in the submodule for `<submodule path>_*.diff`).
`slam.run` warns when a patch it runs with is missing here.

DROID-SLAM (princeton-vl/DROID-SLAM @ 2dfd39f):
- `root_*.diff`: droid_slam/modules/corr.py splits the correlation lookup for the int32 limit at
  960x536 (output identical).
- `thirdparty__lietorch_*.diff`: lietorch setup.py builds for sm_86 only (RTX 3090).

Metric3D (YvanYin/Metric3D @ eb5b6fa), used by depth `metric3d_v2` (exp008):
- `root_*.diff`: mono/utils/comm.py falls back to mmengine's `collect_env` when mmcv 1.x is not
  installed (mmcv 1.x does not build against torch 2.7; the function is only used for logging).

UniDepth (@ 8d8cfe4), MoGe (@ 74fbce0), Depth-Anything-3 (@ 3d835ec): unpatched; installed with
`pip install --no-deps -e` into the conda env `mdepth` (see experiments/exp008_depth_models/README.md).
