# SPDX-License-Identifier: Apache-2.0
"""tools/ci-blob-stubs.sh, tools/check-build.sh and tools/build-kitkat.sh's argument checks."""
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def run(*args, **kw):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, **kw)


class StubsTest(unittest.TestCase):
    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree)

    def test_writes_stub_vendor(self):
        r = run(TOOLS / "ci-blob-stubs.sh", self.tree)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = self.tree / "vendor/glass/glass-1"
        mk = (d / "device-vendor.mk").read_text()
        self.assertIn("libsrv_init_SGX540_120 libsrv_um_SGX540_120", mk)
        self.assertIn("ro.glass.blob_stubs=true", mk)
        self.assertIn("SrvInit", (d / "stub.c").read_text())
        android_mk = (d / "Android.mk").read_text()
        self.assertEqual(android_mk.count("include $(BUILD_SHARED_LIBRARY)"), 2)
        self.assertIn("LOCAL_MODULE_PATH := $(TARGET_OUT_VENDOR)/lib", android_mk)

    def test_refuses_to_cover_extracted_files(self):
        (self.tree / "vendor/glass/glass-1/proprietary").mkdir(parents=True)
        r = run(TOOLS / "ci-blob-stubs.sh", self.tree)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.tree / "vendor/glass/glass-1/device-vendor.mk").exists())


@unittest.skipUnless(shutil.which("readelf") and shutil.which("unzip"), "needs readelf, unzip")
class CheckBuildTest(unittest.TestCase):
    """check-build.sh on a fake product directory."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tree = self.tmp / "tree"
        (self.tree / "dalvik/vm").mkdir(parents=True)
        (self.tree / "dalvik/vm/Android.mk").write_text("LOCAL_MODULE := libdvm\n")
        self.out = self.tmp / "product"
        sys = self.out / "system"
        for f in ("lib/libart.so", "lib/libart-compiler.so", "bin/dex2oat"):
            (sys / f).parent.mkdir(parents=True, exist_ok=True)
            (sys / f).write_bytes(b"not elf")
        (sys / "framework").mkdir()
        with zipfile.ZipFile(sys / "framework/core-libart.jar", "w") as z:
            z.writestr("classes.dex", "dex")
        (sys / "app").mkdir()
        with zipfile.ZipFile(sys / "app/Res.apk", "w") as z:
            z.writestr("resources.arsc", "")
        (sys / "build.prop").write_text(
            "persist.sys.dalvik.vm.lib=libart.so\npersist.glass.d2o.sys=speed\n"
            "persist.glass.d2o.usr=space\n")
        self.sys = sys

    def check(self):
        return run(TOOLS / "check-build.sh", self.tree, self.out)

    def test_clean_product_passes(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no classes.dex in app/Res.apk", r.stdout)

    def test_dalvik_leftovers_fail(self):
        for f in ("lib/libdvm.so", "bin/dexopt", "app/Foo.odex"):
            with self.subTest(f=f):
                (self.sys / f).write_bytes(b"x")
                r = self.check()
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("FAIL", r.stdout)
                (self.sys / f).unlink()

    def test_wrong_runtime_property_fails(self):
        (self.sys / "build.prop").write_text("persist.sys.dalvik.vm.lib=libdvm.so\n")
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("persist.sys.dalvik.vm.lib", r.stdout)

    def test_makefile_naming_libdvm_outside_dalvik_fails(self):
        (self.tree / "frameworks").mkdir()
        (self.tree / "frameworks/Android.mk").write_text("LOCAL_SHARED_LIBRARIES := libdvm\n")
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("frameworks/Android.mk", r.stdout)

    @unittest.skipUnless(shutil.which("cc"), "needs cc")
    def test_elf_needing_libdvm_fails(self):
        lib = self.tmp / "libdvm.so"
        run("cc", "-shared", "-o", lib, "-x", "c", "/dev/null")
        exe = self.sys / "bin/uses-dvm"
        src = self.tmp / "m.c"
        src.write_text("int main(void){return 0;}\n")
        r = run("cc", "-o", exe, src, f"-L{self.tmp}", "-Wl,--no-as-needed", "-ldvm")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("uses-dvm", r.stdout)


class BuildScriptArgsTest(unittest.TestCase):
    def test_requires_tree(self):
        r = run(TOOLS / "build-kitkat.sh", "--stubs")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--tree", r.stderr)

    def test_requires_image_or_stubs(self):
        r = run(TOOLS / "build-kitkat.sh", "--tree", "/nonexistent-tree")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--system-raw", r.stderr)

    def test_image_and_stubs_exclude_each_other(self):
        r = run(TOOLS / "build-kitkat.sh", "--tree", "x", "--stubs", "--system-raw", "y")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("exclude", r.stderr)


if __name__ == "__main__":
    unittest.main()
