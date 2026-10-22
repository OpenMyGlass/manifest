# SPDX-License-Identifier: Apache-2.0
"""tools/ci-blob-stubs.sh, tools/check-build.sh, tools/check-build-6.0.sh and
tools/build-kitkat.sh's argument checks."""
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

    def test_marshmallow_stubs(self):
        egl = self.tree / "hardware/ti/omap4/libEGL_POWERVR"
        egl.mkdir(parents=True)
        (egl / "egl.c").write_text(
            "EGLint eglGetError(void) { return IMGeglGetError(); }\n"
            "EGLBoolean eglTerminate(EGLDisplay d) { return IMGeglTerminate(d); }\n")
        r = run(TOOLS / "ci-blob-stubs.sh", self.tree, "6.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = self.tree / "vendor/glass/glass-1"
        self.assertIn("PRODUCT_PACKAGES += libsrv_init libsrv_um libIMGegl",
                      (d / "device-vendor.mk").read_text())
        android_mk = (d / "Android.mk").read_text()
        self.assertEqual(android_mk.count("include $(BUILD_SHARED_LIBRARY)"), 3)
        for m in ("libsrv_init", "libsrv_um", "libIMGegl"):
            self.assertIn(f"LOCAL_MODULE := {m}\n", android_mk)
        self.assertIn("LINKED/libEGL_POWERVR_SGX54X.so:", android_mk)
        stub = (d / "egl_stub.c").read_text()
        self.assertIn("void IMGeglGetError(void) {}", stub)
        self.assertIn("void IMGeglTerminate(void) {}", stub)

    def test_marshmallow_stubs_need_the_egl_wrapper_source(self):
        r = run(TOOLS / "ci-blob-stubs.sh", self.tree, "6.0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("egl.c", r.stderr)

    def test_unknown_version(self):
        r = run(TOOLS / "ci-blob-stubs.sh", self.tree, "5.1")
        self.assertNotEqual(r.returncode, 0)


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

    def test_known_art_mention_is_allowed(self):
        (self.tree / "art").mkdir()
        (self.tree / "art/Android.mk").write_text("use-dalvik:\n\tadb shell setprop x libdvm.so\n")
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("./art/Android.mk names libdvm (known", r.stdout)

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


@unittest.skipUnless(shutil.which("unzip"), "needs unzip")
class CheckBuildMarshmallowTest(unittest.TestCase):
    """check-build-6.0.sh on a fake product directory."""

    FILES = ("lib/libart.so", "lib/libart-compiler.so", "bin/dex2oat", "bin/dalvikvm",
             "framework/arm/boot.art", "framework/arm/boot.oat", "framework/core-libart.jar",
             "lib/modules/pvrsrvkm_sgx540_120.ko", "vendor/lib/hw/hwcomposer.omap4.so",
             "vendor/lib/egl/libEGL_POWERVR_SGX54X.so", "bin/pvrsrvinit",
             "lib/hw/camera.omap4.so", "vendor/firmware/fw_bcmdhd.bin", "app/Settings.apk")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tree = self.tmp / "tree"
        dt = self.tree / "device/glass/glass-1"
        dt.mkdir(parents=True)
        (dt / "proprietary-files.txt").write_text(
            "# comment\n\nvendor/firmware/fw_bcmdhd.bin\nvendor/lib/libIMGegl_SGX540_120.so\n")
        self.out = self.tmp / "product"
        self.sys = self.out / "system"
        for f in self.FILES:
            (self.sys / f).parent.mkdir(parents=True, exist_ok=True)
            (self.sys / f).write_bytes(b"x")
        for img in ("system.img", "boot.img", "recovery.img"):
            (self.out / img).write_bytes(b"img")
        (self.sys / "build.prop").write_text(
            "ro.build.version.release=6.0.1\nro.build.version.sdk=23\n"
            "ro.build.version.security_patch=2017-10-01\nro.board.platform=omap4\n"
            "persist.sys.dalvik.vm.lib.2=libart\ndalvik.vm.isa.arm.variant=cortex-a9\n"
            "ro.glass.blob_stubs=true\n")

    def check(self, *extra):
        return run(TOOLS / "check-build-6.0.sh", self.tree, self.out, *extra)

    def test_clean_product_passes(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("fw_bcmdhd.bin present (known", r.stdout)

    def test_missing_image_fails(self):
        (self.out / "boot.img").unlink()
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("boot.img missing", r.stdout)

    def test_missing_art_fails(self):
        (self.sys / "framework/arm/boot.oat").unlink()
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("boot.oat missing", r.stdout)

    def test_listed_blob_fails(self):
        (self.sys / "vendor/lib/libIMGegl_SGX540_120.so").write_bytes(b"blob")
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("libIMGegl_SGX540_120.so", r.stdout)
        self.assertEqual(self.check(str(self.tmp)).returncode, 0, "owner builds skip the list")

    def test_google_named_apk_fails(self):
        (self.sys / "priv-app/GmsCore").mkdir(parents=True)
        (self.sys / "priv-app/GmsCore/GmsCore.apk").write_bytes(b"x")
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("GmsCore.apk", r.stdout)

    def test_wrong_property_fails(self):
        (self.sys / "build.prop").write_text("ro.build.version.release=4.4.4\n")
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ro.build.version.release", r.stdout)

    def test_runtime_library_with_so_suffix_fails(self):
        # libart.so is the KitKat form; 6.0.1_r81 core/main.mk writes libart.
        bp = self.sys / "build.prop"
        bp.write_text(bp.read_text().replace("vm.lib.2=libart\n", "vm.lib.2=libart.so\n"))
        r = self.check()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("persist.sys.dalvik.vm.lib.2='libart.so', want 'libart'", r.stdout)


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

    def test_unknown_android_version(self):
        r = run(TOOLS / "build-kitkat.sh", "--tree", "x", "--stubs", "--android", "7.0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--android", r.stderr)


if __name__ == "__main__":
    unittest.main()
