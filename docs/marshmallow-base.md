<!-- SPDX-License-Identifier: Apache-2.0 -->
# Marshmallow base

Track B of the glass-rom roadmap: Android 6.0.1 for Glass Explorer Edition, rendering on the
SGX540 with Glass's own PowerVR binaries. Plan:
[`2026-10-21-android-lean-6.md`](https://github.com/OpenMyGlass/glass-rom/blob/main/docs/plans/2026-10-21-android-lean-6.md),
Task 1 and the first milestone (a CI build). This page records the base, the OMAP4 projects and
our forks, and why.

## Where the manifest lives

Track B is `android-6.0.xml` (over `aosp-6.0.xml`) on `main`, next to Track A's `default.xml`
(over `aosp.xml`):

    repo init -u https://github.com/OpenMyGlass/manifest -m android-6.0.xml

Ruling: a file on `main`, not a branch `android-6.0`. A branch would need a direct push to
create it and its own protection rule, and every shared fix to the scripts would have to be
merged across. With a file, both tracks share `tools/`, the `check` CI checks both manifests,
and the `build` workflow takes one input, `android` (`4.4` or `6.0`). The Track A files
(`default.xml`, `aosp.xml`, `docs/kitkat-base.md`) are not touched by Track B.

## The choice

| Project | From | Pinned |
|---|---|---|
| AOSP | `android-6.0.1_r81` (`aosp-6.0.xml`, unchanged except the remote URL) | tag |
| `hardware/ti/omap4` | [omap4-aosp/android_hardware_ti_omap4](https://github.com/omap4-aosp/android_hardware_ti_omap4) `stable` | `57eec4a` |
| `external/jhead` | AOSP `platform/external/jhead` at the `android-6.0.1_r81` tag, which r81's `default.xml` does not list | commit |
| `build` | our fork [OpenMyGlass/android_build](https://github.com/OpenMyGlass/android_build) `glass-6.0`: AOSP r81 plus one cherry-pick | commit |
| `frameworks/native` | our fork [OpenMyGlass/android_frameworks_native](https://github.com/OpenMyGlass/android_frameworks_native) `glass-6.0`: AOSP r81 plus four OMAP4 graphics cherry-picks | commit |
| `frameworks/av` | our fork [OpenMyGlass/android_frameworks_av](https://github.com/OpenMyGlass/android_frameworks_av) `glass-6.0`: AOSP r81 plus two OMAP4 media cherry-picks | commit |
| `device/glass/glass-1` | [OpenMyGlass/android_device_glass_glass-1](https://github.com/OpenMyGlass/android_device_glass_glass-1) `android-6.0.1_r31` | commit |
| kernel, SGX module | glass-kernel `tuned-stable` (`tools/kernel.env`, the same build as Track A), installed from `vendor/glass/kernel` by `device.mk` | commit |

### AOSP release: r81

`android-6.0.1_r81` (build `MOI10E`) is the last 6.0.1 release. Its
`PLATFORM_SECURITY_PATCH` is `2017-10-01` (`build/core/version_defaults.mk`): it carries Google's
monthly Android security fixes up to the October 2017 bulletin. The plan's other candidate, `r31`,
is only the name of the device tree's branch; nothing in the tree depends on that release, so
the later tag wins (two years more of fixes). Decision for the owner if they prefer otherwise.

### OMAP4 hardware: omap4-aosp `stable` at `57eec4a`

Neither omap4-aosp nor Unlegacy-Android has an `aosp-6.0` branch of `android_hardware_ti_omap4`.
Their 6.0 manifests (omap4-aosp `android` `aosp-6.0`, last change 2016-09-17, on
`android-6.0.1_r66`; Unlegacy-Android `android` `aosp-6.0`, 2019, on `r81`) both take its
`stable` branch, which supported 4.4 to 7.x through `android-api.mk`. `57eec4a` (2016-09-25) is
the head of omap4-aosp's `stable`, the branch its 6.0 manifest tracks, and the commit the device
tree's `docs/hals.md` already documents for the hardware composer. Unlegacy-Android's later
`stable` moved to DDK `1.12`/`1.14` kernel sources, a proprietary composer and 7.x+ changes,
so it is not used. LineageOS `cm-13.0` needs CyanogenMod's build system.

It is used unmodified. Its `pvr-source/` (DDK `1.9@2291151` kernel module) is never built: plain
AOSP has no inline kernel task, and the module comes from glass-kernel (DDK `1.9@2166536`, the
build of XE24's libraries). Its `omap4.mk` (with the `common.mk` it inherits) installs, built
from source:
- `hwcomposer.omap4` (HWC 1.0, `hwc/`);
- `libEGL_POWERVR_SGX54X`, the open `libEGL_POWERVR` wrapper (Kyle Repinski, 2016) that forwards
  each `eglX` to the blob's `IMGeglX` (the GPU path the owner chose);
- `pvrsrvinit`, `libion_ti`, `libdomx`, the Ducati OMX proxies, `libtiutils`.

The device tree adds the rest from the same project: `camera.omap4` (its `device.mk`), and
bltsville (`gc2d` from source, TI's `libbltsville_ticpu`, the same SHA-256 as XE24's), which
`bltsville/Android.mk` installs when the tree's `BoardConfig.mk` sets `TI_OMAP_USE_BLTSVILLE`.

#### AOSP projects outside the release manifest

hardware/ti/omap4's `camera/Android.mk` links `libjhead` for the EXIF data on Lollipop and later
(`ANDROID_API_LP_OR_LATER`), and includes `external/jhead`. AOSP dropped `external/jhead` from
its 6.0 `default.xml`, but the project still carries an `android-6.0.1_r81` tag, at
`a97d4609`, which includes Google's 6.0 security fixes for it ("Fix possible out of bounds
accesses"). `android-6.0.xml` takes it from AOSP at that commit. The first CI build without it
failed on `camera.omap4` (run 39796851902). `tools/check_manifest.py` allows only the listed
AOSP projects there, with the tag as `upstream`, and `tools/check_pins.py` checks that the
pinned commit is the one the tag names.

#### Kernel ABI against the Glass kernel

Compared with kernel-omap `glass-omap-xrx13b-stable-3.4.113` (`b6ea856`, the tuned-stable
source), as Track A did for `aosp-4.4` (`docs/kitkat-base.md`):

| Interface | Header in `57eec4a` | Result |
|---|---|---|
| dsscomp, hwc data (`video/dsscomp.h`, `video/omap_hwc.h`) | same files as `aosp-4.4` `a99c69f` | every struct size and ioctl number the HAL uses equal to Glass's; Glass's two extra `dss2_ovl_cfg` bytes fall into padding, and the HAL clears the struct (device tree `docs/hals.md`, "Kernel ABI", measured on `57eec4a`) |
| ION (`linux/omap_ion.h`) | `a99c69f`'s content, now inside `#ifdef USE_TI_LIBION`, which `libion_ti` and the HAL define (`BOARD_USE_TI_LIBION ?= true`) | `omap_ion_tiler_alloc_data` field for field equal to Glass's (with `out_align` and `token`); heap ids 0-4 and the TILER heap type equal; id 5 differs (`SECURE_OUTPUT_WFDHDCP` here, `MULTIMEDIA` in the kernel) and is not used |
| rpmsg-omx (`linux/rpmsg_omx.h`) | same file as `a99c69f` | `OMX_IOCCONNECT`, `IOCIONREGISTER`, `IOCIONUNREGISTER`, `IOCPVRREGISTER` and `omx_pvr_data`, `omx_conn_req`, `omx_packet` equal; Glass adds `OMX_GET_TIMER` (5), which domx does not use |
| bltsville, omapfb | unchanged since `a99c69f` apart from warning fixes in `gcbv` | equal (`docs/hals.md`) |

So the hardware projects fit the Glass kernel as Track A's do. Not verified: whether
`IMG_native_handle_t` in `hwc/hal_public.h` is the layout of XE24's `gralloc.omap4430.so`
(DDK `1.9@2166536`); a device check (below).

### Our forks

Each fork has a branch `glass-6.0` that starts at the project's AOSP `android-6.0.1_r81`
commit, unchanged. Changes are pull requests. The cherry-picks keep their authorship and their
`(cherry picked from commit …)` line, and each fork's `check` CI runs
`tests/check_cherry_picks.sh`: every commit is either ours and touches only `.github/` and
`tests/`, or is an unchanged cherry-pick: its named source is an ancestor of the upstream branch
it came from (which CI fetches from the upstream repository), it keeps the source's author name,
email and date, and it has the same patch id. `tests/test_check_cherry_picks.sh` covers each
failure.

- `build` (base `5806573`), from omap4-aosp `android_build` `aosp-6.0`:
  - `4f20d76c` "Allow a device to generically define its own headers" (CyanogenMod):
    `TARGET_SPECIFIC_HEADER_PATH`, which hardware/ti/omap4's `BoardConfigCommon.mk` sets to TI's
    OpenMAX headers (`domx/omx_core/inc`). AOSP ignores the variable.
  - Not taken: the inline kernel task (the kernel is prebuilt), the "any JDK" change (we use
    OpenJDK 7, as 6.0 expects), recovery and OTA changes.
- `frameworks/native` (base `89b2934e`), from android-security `aosp-6.0-omap` (Unlegacy-Android's
  branch; omap4-aosp's `aosp-6.0`, on a pre-r81 base, has the four taken commits under other
  SHAs, `a01d47df`, `5ac1ac30`, `ed377653` and `28d48ca5`, but none of the HWC 1.1,
  `OMAP_ENHANCEMENT` or hwrotation patches listed below):
  - `a4428bf3` egl: Add back b/10194508 workaround (`BOARD_EGL_WORKAROUND_BUG_10194508`);
  - `61d46931` Add back support for glReadPixels screenshot path;
  - `9e22a66c` its board flag, `TARGET_FORCE_SCREENSHOT_CPU_PATH`;
  - `c95b8a7d` Remove "using EGL_IMG_context_priority" warning: r81's SurfaceFlinger defines
    `HAS_CONTEXT_PRIORITY` on omap4 and builds with `-Werror`, so the `#warning` stops the build
    (CI run 39796851902).
  `BoardConfigCommon.mk` sets both board flags. Not taken: the HWC 1.1 framebuffer patches (the
  pinned composer is HWC 1.0), hwrotation (Glass does not rotate), a GLES 1.1 thumbnail fix
  (SurfaceFlinger uses GLES 2 on the SGX540), and `befbb7ff` "SF: HWC1: Propagate the
  OMAP_ENHANCEMENT flag", which passes `-DOMAP_ENHANCEMENT` to SurfaceFlinger; only
  the HWC 1.1 patches (`c276a6db`, `bdfa0de7`, not taken) test it.
- `frameworks/av` (base `b7955755`), from the same branch (omap4-aosp's `aosp-6.0` has the same
  changes under other SHAs):
  - `d745b07d` skip the OMX output buffer reallocation when enough buffers exist, on omap4
    (KitKat behaviour, for TI's Ducati codecs);
  - `336ba469` `OMX_TI_COLOR_FormatYUV420PackedSemiPlanar` in `ACodec` (the TI colour format
    the plan names). Not taken: the Wi-Fi Display intra-refresh change.

The plan's other graphics item, `libEGL_POWERVR`, is not a fork: it is built from
`hardware/ti/omap4` as it stands.

### Security patch level

r81 includes the fixes of the Android security bulletins up to 2017-10-01. Missing: every later
bulletin: AOSP has no 6.0.1 tag after r81. Third-party backports exist and are **not** in this
manifest:

- [android-security](https://github.com/android-security), branch `aosp-6.0`: 51 repositories
  with backports dated from late 2017 to 2019 (its `build` bumps
  `PLATFORM_SECURITY_PATCH` to `2019-03-01`), maintained for Unlegacy-Android. The projects:
  `bootable/recovery`, `build`, `device/common`, `external/` `aac`, `chromium-libpac`,
  `chromium-webview`, `doclava`, `e2fsprogs`, `guava`, `libavc`, `libhevc`, `libmpeg2`,
  `libnfc-nci`, `libvorbis`, `libvpx`, `libxml2`, `neven`, `sfntly`, `sonivox`, `sqlite`,
  `tremolo`, `v8`, `wpa_supplicant_8`, `frameworks/` `av`, `base`, `ex`, `minikin`, `native`,
  `opt/net/wifi`, `opt/telephony`, `support`, `hardware/qcom/audio`, `libcore`,
  `packages/apps/` `Bluetooth`, `CertInstaller`, `Contacts`, `Email`, `ManagedProvisioning`,
  `Messaging`, `Nfc`, `PackageInstaller`, `Settings`, `UnifiedEmail`, `packages/providers/`
  `DownloadProvider`, `MediaProvider`, `UserDictionaryProvider`, `packages/services/Telephony`,
  `system/` `bt`, `core`, `media`, `vold`. Not covered at all: `bionic`, `art`, `external/skia`,
  `openssl`/`boringssl` and the rest.
- Of the 51, our OpenMyGlass mirrors of android-security (Track A) already carry `aosp-6.0` for
  32, at the same commits as android-security; `build` is the 51st: OpenMyGlass/android_build is
  also our `glass-6.0` fork, and its `aosp-6.0` is not android-security's. 18 would need new
  mirrors
  (`chromium-libpac`, `chromium-webview`, `doclava`, `guava`, `libavc`, `libhevc`, `libmpeg2`,
  `v8`, `frameworks/ex`, `minikin`, `opt/net/wifi`, `support`, `hardware/qcom/audio`,
  `ManagedProvisioning`, `Messaging`, `MediaProvider`, `UserDictionaryProvider`, `system/bt`).

Taking them is a decision for the owner (third-party sources). As Track A learned, they must be
taken as a set: later fixes in one project need definitions from others. Our `frameworks/native`
and `frameworks/av` would then be rebased onto android-security's `aosp-6.0` (its
`aosp-6.0-omap` branches already have the same OMAP4 commits on top).

## Trimming

`repo init -g default,-device,-darwin,-mips,-x86`, as Track A. `android-6.0.xml` also removes
the other devices (asus, google accessory and atv, htc, huawei, lge, moto),
`hardware/intel/*`, `marvell/bt`, `mediatek`, `nvidia/audio`, `qcom/*`, `ti/omap3`,
`ti/omap4-aah`, AOSP's `ti/omap4xxx` (replaced), `cts`, `developers/*` and the two eclipse
projects. `hardware/broadcom/wlan` and `libbt` stay (bcm4330 Wi-Fi and Bluetooth).

## CI blob stubs

CI builds without the owner's image (`tools/ci-blob-stubs.sh <tree> 6.0`). On 6.0,
hardware/ti/omap4 links two open parts against vendor libraries under their generic names:
`pvrsrvinit` against `libsrv_init` and `libsrv_um`, and `libEGL_POWERVR_SGX54X` against
`libIMGegl`. The stubs are libraries of those names that do nothing; `libIMGegl` exports every
`IMGegl*` function `egl.c` calls, read from the source at stub time. The image gets
`ro.glass.blob_stubs=true` and must never be booted.

## Checks

- CI `check`: `tools/check_manifest.py --android 6.0` compares `aosp-6.0.xml` with AOSP's
  manifest at r81, and checks that every removed project exists, every GitHub project is pinned
  to a commit from an expected organisation, the forks are on `glass-6.0` and the device tree on
  `android-6.0.1_r31`.
- CI `check`: `tools/check_pins.py` asks GitHub, for both tracks, that every pinned commit is the
  head of its `upstream` branch or an ancestor of it. A pin on an open pull request's branch
  fails, so the manifest can be merged only after the fork and device tree pull requests are
  merged and their merge commits pinned.
- CI `build` with `android=6.0` builds the whole tree without blobs and runs
  `tools/check-build-6.0.sh`: `system.img`, `boot.img`, `recovery.img` built; the glass-kernel
  SGX module installed; ART (`libart`, `dex2oat`, `dalvikvm`, `core-libart.jar`, the `arm` boot
  image) present, no `libdvm`/`dexopt`; `build.prop` says 6.0.1, SDK 23,
  `persist.sys.dalvik.vm.lib.2=libart` (6.0 writes the name without `.so`) and `cortex-a9`; the open hwcomposer, EGL wrapper, `pvrsrvinit` and camera HAL built; and no
  Google file: no file listed in the device tree's `proprietary-files.txt` (the files only
  XE24's image has) is in the image, apart from `vendor/firmware/fw_bcmdhd.bin`, which AOSP's
  `hardware/broadcom/wlan` ships, and no APK or jar is named like a Google or stock Glass package.

## Build on the free runner

Not yet run; see the pull request.

## Next

- Plan Task 2 (graphics): the static symbol check of `libEGL_POWERVR` against the owner's
  `libIMGegl_SGX540_120.so` (`readelf --dyn-syms`, owner's machine), and the `NEEDED`/undefined
  symbol scan of every extracted blob against this build.
- glass-rom `extract_vendor.py` for 6.0: the generic-name modules (`libsrv_init`, `libsrv_um`,
  `libIMGegl` and the other symlinks hardware/ti/omap4 expects) next to the `_SGX540_120` files,
  and `egl.cfg`/loader naming for `libEGL_POWERVR_SGX54X`. Until then `build-kitkat.sh --android
  6.0` builds only with `--stubs`.
- Plan Task 3 (lean system, compiler and dex2oat settings), Tasks 4-6.

## Device checks for this choice

Not run (no hardware), `fastboot boot` only:
- SurfaceFlinger starts with GLES 2 through `libEGL_POWERVR_SGX54X`; no
  `PVRSRV_ERROR_BUILD_MISMATCH` in `logcat`.
- hwcomposer composes with XE24's gralloc: `dumpsys SurfaceFlinger` lists HWC layers and the
  screen shows no corruption; no `hwc` errors about handle sizes or `DSSCIOC_SETUP_DISPC`.
- `screencap` works (the glReadPixels path).
- The camera preview and video decode work (TI colour format, OMX buffers).
