import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import release


class ReleaseSafetyTests(unittest.TestCase):
    def test_version_bump_is_explicit_and_only_changes_version_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "paperlight").mkdir()
            path = root / "paperlight/__init__.py"
            path.write_text(f'__version__ = "{release.__version__}"\nDISPLAY_NAME = "Folio"\n', encoding="utf-8")
            with patch.object(release, "ROOT", root):
                release.bump_version("1.0.0")
                self.assertEqual(path.read_text(encoding="utf-8"), '__version__ = "1.0.0"\nDISPLAY_NAME = "Folio"\n')
                for version in ("0.10.0", release.__version__, "1.0.0;command", "1.0"):
                    with self.assertRaises(SystemExit):
                        release.bump_version(version)

    def test_dirty_tree_cannot_publish(self):
        with patch.object(release.subprocess, "check_output", return_value=" M README.md"), \
             patch.object(release.subprocess, "run") as run:
            with self.assertRaises(SystemExit):
                release.publish(Path("unused"), "commit")
            run.assert_not_called()

    def test_tampered_artifact_cannot_upload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "test.nupkg").write_bytes(b"tampered")
            (root / "release-info.json").write_text(json.dumps(dict(commit="commit", version=release.__version__,
                sha256={"test.nupkg": "0" * 64})), encoding="utf-8")
            with patch.object(release.subprocess, "check_output", return_value=""), \
                 patch.object(release.subprocess, "run") as run:
                with self.assertRaises(SystemExit):
                    release.publish(root, "commit")
                run.assert_not_called()

    def test_wrong_source_commit_cannot_upload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "release-info.json").write_text(json.dumps(dict(commit="other", version=release.__version__)), encoding="utf-8")
            with patch.object(release.subprocess, "check_output", return_value=""), \
                 patch.object(release.subprocess, "run") as run:
                with self.assertRaises(SystemExit):
                    release.publish(root, "commit")
                run.assert_not_called()
