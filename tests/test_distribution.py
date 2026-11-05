"""Exercise installation isolation and release archive contents."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("etf-comment-drafts-v2",)


class DistributionTests(unittest.TestCase):
    def test_install_is_self_contained_and_preserves_existing_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "skills"
            command = [sys.executable, str(ROOT / "scripts" / "install.py"), "--dest", str(dest)]
            subprocess.run(command, check=True, capture_output=True)
            for name in NAMES:
                self.assertTrue((dest / name / "SKILL.md").is_file())
                self.assertTrue((dest / name / "agents" / "openai.yaml").is_file())
                self.assertFalse(list((dest / name).rglob("__pycache__")))
            entry = dest / NAMES[0] / "SKILL.md"
            entry.write_text("local customization", encoding="utf-8")
            again = subprocess.run(command, capture_output=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(entry.read_text(), "local customization")

    def test_zip_contains_only_tracked_files_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "a", Path(directory) / "b"
            for dest in (first, second):
                subprocess.run([sys.executable, str(ROOT / "scripts" / "package.py"), "--dest", str(dest)],
                               check=True, capture_output=True)
            for name in NAMES:
                a, b = first / (name + ".zip"), second / (name + ".zip")
                self.assertEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())
                expected = subprocess.check_output(["git", "ls-files", "-z", "--", "skills/" + name], cwd=ROOT)
                expected = {p.removeprefix("skills/") for p in expected.decode().split("\0") if p}
                expected.add(name + "/LICENSE")
                with zipfile.ZipFile(a) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(set(archive.namelist()), expected)
                    self.assertIn(name + "/SKILL.md", archive.namelist())


if __name__ == "__main__":
    unittest.main()
