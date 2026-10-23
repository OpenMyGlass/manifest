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
        self.edit("default.xml", 'revision="a99c69f02e20af59e760763a284a984e6af45ad9"',
                  'revision="aosp-4.4"')
        self.assertTrue(any("40-hex" in p for p in self.problems()))

    def test_unknown_organisation(self):
        self.edit("default.xml", 'name="omap4-aosp/android_hardware_ti_omap4"',
                  'name="someone/android_hardware_ti_omap4"')
        self.assertTrue(any("organisation someone" in p for p in self.problems()))

    def test_android_security_no_longer_allowed(self):
        self.edit("default.xml", 'name="OpenMyGlass/android_art"', 'name="android-security/android_art"')
        self.assertTrue(any("organisation android-security" in p for p in self.problems()))

    def test_mirror_name_and_branch(self):
        self.edit("default.xml", 'name="OpenMyGlass/android_system_vold"',
                  'name="OpenMyGlass/android_vold"')
        self.edit("default.xml", 'name="OpenMyGlass/android_bionic" remote="github" groups="pdk" '
                  'revision="b351ec422dd055a372052a8b152a300ad06b3b34" upstream="aosp-4.4"',
                  'name="OpenMyGlass/android_bionic" remote="github" groups="pdk" '
                  'revision="b351ec422dd055a372052a8b152a300ad06b3b34" upstream="glass-4.4"')
        found = self.problems()
        self.assertTrue(any("must be OpenMyGlass/android_system_vold" in p for p in found))
        self.assertTrue(any("project bionic: OpenMyGlass mirror must have upstream" in p for p in found))

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



class CheckMarshmallowManifestTest(unittest.TestCase):
    """Track B: android-6.0.xml over aosp-6.0.xml."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for f in ("aosp-6.0.xml", "android-6.0.xml"):
            shutil.copy(ROOT / f, self.tmp / f)

    def edit(self, name, old, new):
        path = self.tmp / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def problems(self, **kw):
        return check_manifest.check(self.tmp, android="6.0", **kw)

    def test_repository_manifest_is_clean(self):
        self.assertEqual(check_manifest.check(android="6.0"), [])

    def test_upstream_comparison(self):
        upstream = (ROOT / "aosp-6.0.xml").read_text().replace(
            f'fetch="{check_manifest.AOSP_FETCH}"', 'fetch=".."', 1)
        self.assertEqual(self.problems(upstream_text=upstream), [])
        self.assertTrue(self.problems(upstream_text=upstream.replace("platform/art", "x/art")))

    def test_aosp_tag(self):
        self.edit("aosp-6.0.xml", "refs/tags/android-6.0.1_r81", "refs/tags/android-6.0.1_r31")
        self.assertTrue(any("default revision is not refs/tags/android-6.0.1_r81" in p
                            for p in self.problems()))

    def test_includes_its_own_aosp_file(self):
        self.edit("android-6.0.xml", '<include name="aosp-6.0.xml" />', '<include name="aosp.xml" />')
        self.assertTrue(any("must include aosp-6.0.xml" in p for p in self.problems()))

    def test_fork_branch(self):
        self.edit("android-6.0.xml", 'upstream="glass-6.0" />', 'upstream="aosp-6.0-omap" />')
        self.assertTrue(any("fork must have upstream glass-6.0" in p for p in self.problems()))

    def test_fork_is_required(self):
        self.edit("android-6.0.xml", 'name="OpenMyGlass/android_frameworks_av"',
                  'name="omap4-aosp/android_frameworks_av"')
        self.assertTrue(any("frameworks/av: must be OpenMyGlass/android_frameworks_av" in p
                            for p in self.problems()))

    def test_device_tree_branch(self):
        self.edit("android-6.0.xml", 'upstream="android-6.0.1_r31"', 'upstream="android-4.4.4"')
        self.assertTrue(any("device tree must have upstream android-6.0.1_r31" in p
                            for p in self.problems()))

    def test_unlegacy_is_not_an_allowed_organisation(self):
        self.edit("android-6.0.xml", 'name="omap4-aosp/android_hardware_ti_omap4"',
                  'name="Unlegacy-Android/android_hardware_ti_omap4"')
        self.assertTrue(any("organisation Unlegacy-Android" in p for p in self.problems()))


if __name__ == "__main__":
    unittest.main()
