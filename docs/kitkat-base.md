<!-- SPDX-License-Identifier: Apache-2.0 -->
# KitKat base

Track A of the glass-rom roadmap: Android 4.4.4 for Glass Explorer Edition, ART only. Plan:
[`2026-10-21-android-lean-kitkat-art.md`](https://github.com/OpenMyGlass/glass-rom/blob/main/docs/plans/2026-10-21-android-lean-kitkat-art.md),
Task 1. This page records which OMAP4 hardware projects the build uses, and why.

## The choice

| Project | From | Pinned |
|---|---|---|
| AOSP | `android-4.4.4_r2.0.1` (`aosp.xml`, unchanged except the remote URL) | tag |
| `hardware/ti/omap4` | [omap4-aosp/android_hardware_ti_omap4](https://github.com/omap4-aosp/android_hardware_ti_omap4) `aosp-4.4` | `a99c69f` |
| `build` | our fork of [omap4-aosp/android_build](https://github.com/omap4-aosp/android_build) `aosp-4.4` (`ba41986`), plus Cortex-A9 code generation | fork |
| `frameworks/native` | our fork of android-security's `aosp-4.4`, plus omap4-aosp's three OMAP4 screenshot commits and our installd change | fork |
| `libnativehelper` | our fork of AOSP `android-4.4.4_r2.0.1`, with the JNI fallback set to ART | fork |
| `art` | our fork of android-security's `aosp-4.4` (`479fe13`), plus ART fixes backported from later AOSP (glass-rom `docs/plans/2026-10-22-kitkat-art-fixes.md`) | fork |
| 62 other AOSP projects | unmodified forks of [android-security](https://github.com/android-security)'s `aosp-4.4` (`OpenMyGlass/android_<path>`, with `/` as `_`): Google's KitKat security fixes backported. Every android-security repository with an `aosp-4.4` branch for a project of AOSP 4.4.4 (bionic, frameworks/base and av, system/core, media, vold and netd, hardware/libhardware, sepolicy, webview, openssl and others), except `hardware/qcom/*` | each pinned |
| `device/glass/glass-1` | [OpenMyGlass/android_device_glass_glass-1](https://github.com/OpenMyGlass/android_device_glass_glass-1) `android-4.4.4` | commit |

omap4-aosp is the organisation that later became Unlegacy-Android. Its `aosp-4.4` manifest
([omap4-aosp/android](https://github.com/omap4-aosp/android) `aosp-4.4`) is AOSP
`android-4.4.4_r2.0.1` plus:
- its `build` and `frameworks/native`;
- `hardware/ti/omap4`;
- 32 android-security projects.

This manifest takes every android-security repository with an `aosp-4.4` branch instead (63
projects; `art` now comes from our fork, which keeps android-security's commit): their later fixes need each other. The first CI build stopped in `frameworks/av`
because its Visualizer fix needs `MEASUREMENT_COUNT` from android-security's `system/media`; the
second, with android-security's own 42-project manifest, because `EffectBundle.cpp` needs
`EFFECT_PARAM_SIZE_MAX` from its `hardware/libhardware`, which that manifest lacks.

Its manifest builds KitKat for the Galaxy Nexus (tuna) and the Galaxy Tab 2 (espresso). This
manifest follows it, without those devices and their vendor repositories.

## Candidates for the OMAP4 hardware projects

Compared at:
- AOSP `platform/hardware/ti/omap4xxx` at `android-4.4.4_r2.0.1` (`0fbe7ec`, 2013-12);
- CyanogenMod `android_hardware_ti_omap4` `cm-11.0` (`a3195fe`, 2016-01), carried forward on LineageOS's `cm-11.0` (`5c3dd65`, 2018-02) with Nougat and Oreo changes. The header and file comparisons below used LineageOS's head;
- omap4-aosp `android_hardware_ti_omap4` `aosp-4.4` (`a99c69f`, 2016-06).

Unlegacy-Android's own `android_hardware_ti_omap4` has only a `stable` branch (7.x and later);
its KitKat work is the omap4-aosp `aosp-4.4` branch.

The Glass side of each comparison:
- the kernel headers of [kernel-omap](https://github.com/OpenMyGlass/kernel-omap)
  `glass-omap-xrx13b-stable-3.4.113` (the tuned-stable source);
- XE24's file names in `glass-rom/docs/xe24-blobs.md`.

Struct sizes and ioctl numbers were computed for ARM EABI with `clang -target
armv7a-none-linux-gnueabi` from each header.

| | AOSP omap4xxx (4.4) | CM / LineageOS cm-11.0 | omap4-aosp aosp-4.4 |
|---|---|---|---|
| Built for | tuna, which AOSP 4.4 does not ship (no `device/samsung/tuna` in the 4.4.4 manifest) | CM 11's OMAP4 devices, with CM's build system | tuna, espresso, on plain AOSP 4.4.4 |
| hwcomposer vs Glass `dsscomp` | no `video/dsscomp.h` in the tree; tuna's came from its device tree | header in `kernel-headers/`; every struct size and ioctl number equal to Glass's | same header as cm-11.0 |
| `libion_ti` vs Glass `omap_ion.h` | `omap_ion_tiler_alloc_data` lacks `out_align` and `token`, so the TILER ioctl size differs | equal | equal |
| domx, camera vs Glass `rpmsg_omx.h` | no header in the tree | the user-visible ioctls are equal; Glass adds `OMX_GET_TIMER` and kernel-internal types | same as cm-11.0 |
| `libtiutils`, camera HAL (OMX/Ducati) | present (tuna) | present (`TI_CAMERAHAL_INTERFACE`) | present (`TI_CAMERAHAL_INTERFACE`) |
| bltsville (XE24 has `libbltsville_*`) | none | `bltsville/` | `bltsville/`, opt-in (`TI_OMAP_USE_BLTSVILLE`) |
| PowerVR file names | tuna layout (`gralloc.omap4.so`, no core suffix) | `_SGX540_120` suffix, `gralloc.omap4430.so`, as XE24 | same as cm-11.0 |
| PVR DDK it was paired with | tuna's 1.8 (`1.8.GOOGLENEXUS.ED945322@2198402`, tuna kernel `jb-mr2`) | 1.9@2291151 (`pvr-source`) | 1.9@2291151 (`pvr-source`) |
| Gralloc handle (`hwc/hal_public.h`) | `IMG_native_handle_t` | same struct; adds `BGRX_8888` and `TI_NV12*` formats | same as cm-11.0, plus `GRALLOC_USAGE_SYSTEM_HEAP` and `_PHYS_CONTIG` |
| Licence | `MODULE_LICENSE_BSD_APL2`, Apache-2.0 headers | same, plus a TI binary (`bltsville/ticpu`) under TI's licence | same as cm-11.0 |

### DDK `1.9@2166536`

No candidate was built against XE24's DDK `1.9@2166536`, so none matches it exactly. What
matters is where the DDK build meets the code built here:
- **The kernel module.** We do not use any candidate's `pvr-source` (`1.9@2291151`, which XE24's
  libraries would reject). glass-kernel builds `pvrsrvkm` from `1.9@2166536`.
- **The gralloc handle.** The hwcomposer reads the handle that XE24's `gralloc.omap4430.so`
  allocates. `IMG_native_handle_t` is the same in all three candidates, from DDK 1.8 to
  1.9@2291151. That it is also the layout of `1.9@2166536` is likely but not verified; see the
  device check below.
- **pvrsrvinit.** omap4-aosp's open `pvrsrvinit` calls `SrvInit()` from
  `libsrv_init_SGX540_120.so`, the name XE24 uses.

### Why omap4-aosp `aosp-4.4`

1. Its kernel interfaces (dsscomp, ION, rpmsg-omx) match the Glass kernel, as do cm-11.0's. AOSP
   omap4xxx's ION TILER struct does not, and it has no dsscomp header.
2. It was built and shipped on plain AOSP `android-4.4.4_r2.0.1`, which is the plan's base. Its
   manifest says which build fork and security projects it used. cm-11.0 was built with CM 11's
   build system, and the LineageOS head carries later Android versions' changes.
3. Its PowerVR file layout is XE24's (`_SGX540_120`, `gralloc.omap4430.so`, bltsville).
4. Its licence is clear: Apache-2.0 and BSD sources. The one binary, TI's
   `libbltsville_ticpu.2.1.0.0.so`, has the same SHA-256 as XE24's copy (`3d02c453…7279`), and so
   has its licence file. The device tree therefore no longer extracts those files from the
   owner's image.

`hardware/ti/omap4` is used unmodified. The Glass headers fit it as they are: Glass's two extra
`dss2_ovl_cfg` fields (`force_1d`, `mflag_en`) sit in what was padding, and the hwcomposer clears
the whole struct (`memset` in `hwc.c`) before it fills it.

## Our forks

Each fork has a branch `glass-4.4`, and each change to it is a pull request with its own CI:
- [android_frameworks_native](https://github.com/OpenMyGlass/android_frameworks_native) (plan Tasks 2 and 3):
  - android-security's `aosp-4.4`;
  - omap4-aosp's three OMAP4 screenshot commits (`17653353`, `2a58e489`, `54e8a773`, cherry-picked
    with `-x`), which `FORCE_SCREENSHOT_CPU_PATH` in `hardware/ti/omap4` relies on;
  - installd: ART only, with dex2oat compiler filters.
- [android_libnativehelper](https://github.com/OpenMyGlass/android_libnativehelper) (plan Task 2): AOSP
  `android-4.4.4_r2.0.1`, with the device's JNI fallback runtime set to `libart.so`.
- [android_build](https://github.com/OpenMyGlass/android_build) (plan Task 4): omap4-aosp's `aosp-4.4`,
  with `-mcpu=cortex-a9` and `--no-fix-cortex-a8` for the A9.
- [android_art](https://github.com/OpenMyGlass/android_art) (plan Task 5, rank 5): android-security's
  `aosp-4.4`, plus fixes cherry-picked from AOSP `platform/art` of 2013-2014 (crashes, JNI
  behaviour that differed from Dalvik, dex2oat failures), each with `-x` and the upstream author.

Not patched, because nothing needs a patch (both come from our plain mirrors):
- `frameworks/base`: SystemServer writes back `VMRuntime.vmLibrary()`, which is always
  `libart.so` now.
- `packages/apps/Settings`: the runtime picker removes itself when only one runtime library
  exists.

## Trimming

`repo init -g default,-device,-darwin,-mips,-x86` leaves out:
- the darwin, MIPS and x86 prebuilts;
- the `device` group;
- everything in `notdefault`.

`default.xml` also removes:
- the other devices (asus, lge, samsung, google accessory);
- `hardware/qcom/*`, `hardware/samsung_slsi/exynos5`, `hardware/ti/omap3`, and AOSP's
  `hardware/ti/omap4xxx` (replaced);
- `cts`: `build/core/config.mk` only `-include`s it;
- `developers/*`;
- `external/eclipse-basebuilder` and `external/eclipse-windowbuilder`.

`sdk` and `development` stay: `build/core/main.mk` includes `sdk/build/windows_sdk_whitelist.mk`
unconditionally.

Checkout size: 11-12 GB after `repo sync -c --depth=1` with these groups (89 s on a standard
runner).

## Build on the free runner

The free standard GitHub runner fits a full build (CI `build`, run 39700241850, 2026-10-22,
without blobs):

| | |
|---|---|
| Runner | ubuntu-24.04, 4 vCPU, 15 GB RAM, 145 GB disk (122 GB free after removing preinstalled tools) |
| Time | `repo sync` 89 s, glass-kernel build 242 s, AOSP build 5192 s, job about 95 minutes |
| Disk | source 12 GB, output 23 GB, 87 GB still free at the end |
| Images | `system.img` 196,495,936 bytes, `boot.img` 5,181,440, `recovery.img` 5,744,640 |
| Checks | `tools/check-build.sh`: no libdvm, dexopt, core.jar or .odex; libart, dex2oat and core-libart.jar present; runtime and dex2oat properties set; no ELF needs libdvm.so |

Earlier attempts failed in `frameworks/av` (see above) and led to the 63-project security set.
The only remaining build error is ignored by the 4.4 build itself: `recovery.img` tries to copy
`init.recovery.*.rc`, which this device does not have.

`art/Android.mk` names libdvm only in its phony `use-art`/`use-dalvik` developer targets
(`adb shell setprop`), which build and link nothing; `check-build.sh` lists it as known.

Not yet measured: the size of an odexed (Dalvik) build for comparison (plan Task 2, step 5).


## Checks

- CI `check`: `tools/check_manifest.py` compares `aosp.xml` with AOSP's manifest at the tag. It
  also checks that:
  - every removed project exists;
  - every project from GitHub is pinned to a commit and comes from an expected organisation;
  - the forks and the device tree are the expected repositories.
- CI `build` (run by hand) builds the whole tree without blobs and runs `tools/check-build.sh`.

## Device check for this choice

Not run (no hardware), `fastboot boot` only:
- hwcomposer composes with XE24's gralloc: `dumpsys SurfaceFlinger` lists HWC layers ("OVERLAY"),
  and the screen shows no corruption or tearing.
- `logcat` has no `hwc` errors about handle sizes or `DSSCIOC_SETUP_DISPC` failures.
