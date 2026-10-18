import json
import tarfile
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from garmin_recovery import backup

NOW = datetime(2026, 11, 1, 3, 20)


class Backup(unittest.TestCase):
    def make(self):
        d = Path(tempfile.mkdtemp())
        (d / "history").mkdir()
        (d / "history" / "daily.csv").write_text("date\n2026-10-18\n", encoding="utf-8")
        (d / "training_feedback.json").write_text(json.dumps({"i1": {"rpe": 9}}), encoding="utf-8")
        (d / "secreto.txt").write_text("no debe entrar", encoding="utf-8")
        return d

    def test_build_and_verify(self):
        root = self.make()
        res = backup.build(root, root / "dist", NOW)
        self.assertEqual((res["tag"], res["files"]), ("backup-2026-11", 2))
        self.assertIn("crossfit_insights.json", res["missing"])
        self.assertEqual(backup.verify(res["archive"]), [])
        with tarfile.open(res["archive"]) as tar:
            names = tar.getnames()
        self.assertIn("MANIFEST.json", names)
        self.assertNotIn("secreto.txt", names)

    def test_verify_detects_tampering_and_missing_manifest(self):
        root = self.make()
        res = backup.build(root, root / "dist", NOW)
        bad = root / "dist" / "bad.tar.gz"
        with tarfile.open(res["archive"]) as src, tarfile.open(bad, "w:gz") as dst:
            import io
            for m in src.getmembers():
                data = src.extractfile(m).read()
                if m.name == "training_feedback.json":
                    data = b"{}"
                    m.size = len(data)
                dst.addfile(m, io.BytesIO(data))
        self.assertEqual(backup.verify(bad), ["hash distinto en training_feedback.json"])
        empty = root / "dist" / "empty.tar.gz"
        with tarfile.open(empty, "w:gz"):
            pass
        self.assertEqual(backup.verify(empty), ["falta MANIFEST.json"])

    def test_allowlist_has_no_code_or_secrets(self):
        for rel in backup.INCLUDE:
            self.assertFalse(rel.endswith((".py", ".yml", ".gs", ".sh")))
            self.assertNotIn("token", rel.lower())

    def test_prune(self):
        tags = [f"backup-2025-{m:02d}" for m in range(1, 13)] + ["backup-2026-01", "backup-2026-02", "v1.0", "backup-x"]
        self.assertEqual(backup.tags_to_prune(tags), ["backup-2025-01", "backup-2025-02"])
        self.assertEqual(backup.tags_to_prune(tags[:5]), [])


if __name__ == "__main__":
    unittest.main()
