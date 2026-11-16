"""upload_gcs decides what to send without touching the network."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import upload_gcs as U

DEST = "gs://bucket/collect/yuan"


class UploadPlanTests(unittest.TestCase):
    def test_listing_keeps_paths_relative_to_dest(self):
        text = ("1814793734  2026-10-31T16:30:00Z  gs://bucket/collect/yuan/data/raw/x_b0587b.mkv\n"
                "        92  2026-10-31T16:09:14Z  gs://bucket/collect/yuan/calib/h_intrinsics.json\n"
                "        11  2026-10-31T16:09:14Z  gs://bucket/collect/other/data/raw/y.mkv\n"
                "TOTAL: 3 objects, 1814793837 bytes (1.69GiB)\n")
        self.assertEqual(U.parse_listing(text, DEST + "/"),
                         {"data/raw/x_b0587b.mkv": 1814793734, "calib/h_intrinsics.json": 92})

    def test_resume_refresh_metadata_and_refuse_a_reused_recording_name(self):
        local = {"data/raw/a.mkv": 100, "data/raw/b.mkv": 200, "data/raw/a_session.json": 50,
                 "data/raw/c.mkv": 300, "calib/h_charuco_views.npz": 40}
        remote = {"data/raw/a.mkv": 100, "data/raw/a_session.json": 45, "data/raw/c.mkv": 299,
                  "calib/h_charuco_views.npz": 41}
        upload, skip, conflicts = U.plan(local, remote)
        self.assertEqual(sorted(upload), ["data/raw/a_session.json", "data/raw/b.mkv"])
        self.assertEqual(skip, ["data/raw/a.mkv"])
        self.assertEqual(sorted(conflicts), ["calib/h_charuco_views.npz", "data/raw/c.mkv"])

    def test_each_file_lands_under_its_own_directory(self):
        calls = []

        def run(cmd, **kw):
            calls.append((cmd, kw["input"]))
            return U.subprocess.CompletedProcess(cmd, 0)
        with patch.object(U.subprocess, "run", side_effect=run):
            U.send(["data/raw/a.mkv", "calib/h_intrinsics.json", "data/raw/a_ts.json"], DEST)
        self.assertEqual(calls, [
            (["gcloud", "storage", "cp", "-I", DEST + "/calib/"], "calib/h_intrinsics.json\n"),
            (["gcloud", "storage", "cp", "-I", DEST + "/data/raw/"], "data/raw/a.mkv\ndata/raw/a_ts.json\n")])

    def test_a_refused_copy_stops_with_a_resume_hint(self):
        with patch.object(U.subprocess, "run", return_value=U.subprocess.CompletedProcess([], 1)), \
                patch("builtins.print"):
            with self.assertRaisesRegex(SystemExit, "re-run sends only what is missing"):
                U.send(["calib/h_intrinsics.json"], DEST)

    def test_conflict_stops_before_anything_is_sent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data/raw").mkdir(parents=True)
            (root / "data/raw/x_b0587b.mkv").write_bytes(b"12345")
            (root / "data/raw/handoff_yuan.txt").write_text("data/raw/x_b0587b.mkv\n")
            with patch.object(U, "ROOT", root), \
                    patch.object(U, "remote_sizes", return_value={"data/raw/x_b0587b.mkv": 4}), \
                    patch.object(U, "send") as send, patch("builtins.print"):
                with self.assertRaisesRegex(SystemExit, "reused name"):
                    U.main(["data/raw/handoff_yuan.txt", DEST])
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
