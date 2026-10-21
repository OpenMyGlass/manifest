# SPDX-License-Identifier: Apache-2.0
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_manifest  # noqa: E402


class CheckManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for f in ("aosp.xml", "default.xml"):
            shutil.copy(ROOT / f, self.tmp / f)

    def edit(self, name, old, new):
        path = self.tmp / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def problems(self, **kw):
        return check_manifest.check(self.tmp, **kw)

    def test_repository_manifest_is_clean(self):
        self.assertEqual(check_manifest.check(), [])

    def test_upstream_comparison(self):
        upstream = (ROOT / "aosp.xml").read_text().replace(
            f'fetch="{check_manifest.AOSP_FETCH}"', 'fetch=".."', 1)
        self.assertEqual(self.problems(upstream_text=upstream), [])
        self.assertTrue(self.problems(upstream_text=upstream.replace("platform/art", "x/art")))

    def test_branch_instead_of_commit(self):
        self.edit("default.xml", 'revision="ba4198604bcda7ec42e3d8870c9a8ff1fb1f4a89"',
                  'revision="aosp-4.4"')
        self.assertTrue(any("40-hex" in p for p in self.problems()))

    def test_unknown_organisation(self):
        self.edit("default.xml", 'name="omap4-aosp/android_hardware_ti_omap4"',
                  'name="someone/android_hardware_ti_omap4"')
        self.assertTrue(any("organisation someone" in p for p in self.problems()))

    def test_path_clash_without_remove(self):
        self.edit("default.xml", '<remove-project name="platform/libnativehelper" />', "")
        self.assertTrue(any("already used" in p for p in self.problems()))

    def test_remove_of_unknown_project(self):
        self.edit("default.xml", '<remove-project name="platform/cts" />',
                  '<remove-project name="platform/cts" /><remove-project name="platform/nope" />')
        self.assertTrue(any("platform/nope" in p for p in self.problems()))

    def test_aosp_tag_and_remote(self):
        self.edit("aosp.xml", "refs/tags/android-4.4.4_r2.0.1", "refs/tags/android-4.4.4_r2")
        self.edit("aosp.xml", 'fetch="https://android.googlesource.com/"', 'fetch=".."')
        found = self.problems()
        self.assertTrue(any("default revision" in p for p in found))
        self.assertTrue(any("remotes" in p for p in found))

    def test_device_tree_must_be_pinned(self):
        self.edit("default.xml", 'name="OpenMyGlass/android_device_glass_glass-1"',
                  'name="OpenMyGlass/other"')
        self.assertTrue(any("device/glass/glass-1" in p for p in self.problems()))


if __name__ == "__main__":
    unittest.main()
