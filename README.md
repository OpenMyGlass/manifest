<!-- SPDX-License-Identifier: Apache-2.0 -->
# OpenMyGlass manifest

`repo` manifest for Android 4.4.4 (KitKat, ART only) on Google Glass Explorer Edition: Track A of
the [glass-rom roadmap](https://github.com/OpenMyGlass/glass-rom/blob/main/docs/plans/2026-10-21-open-source-roadmap.md).

- `aosp.xml`: AOSP `android-4.4.4_r2.0.1`, unchanged except for the remote URL.
- `default.xml`: what changes on top of it. Every project outside AOSP is pinned to a commit:
  - the OMAP4 projects from omap4-aosp (later Unlegacy-Android);
  - the security-patched KitKat projects from android-security;
  - our forks [android_frameworks_native](https://github.com/OpenMyGlass/android_frameworks_native),
    [android_libnativehelper](https://github.com/OpenMyGlass/android_libnativehelper) and
    [android_build](https://github.com/OpenMyGlass/android_build);
  - the device tree's [`android-4.4.4`](https://github.com/OpenMyGlass/android_device_glass_glass-1/tree/android-4.4.4)
    branch.

  It also leaves out what one ARM device does not need.
- [docs/kitkat-base.md](docs/kitkat-base.md): which OMAP4 base, and why.
- [docs/build-on-pc.md](docs/build-on-pc.md): build it on your own Linux PC with your own
  factory image (`tools/build-kitkat.sh`).

No Google file is in this repository. The PowerVR and other Glass binaries come only from the
owner's own image, extracted at build time by glass-rom's `extract_vendor.py`. CI builds without
them (`tools/ci-blob-stubs.sh`), and its images are never booted or published.

Nothing built from here has been tested on a device. Test with `fastboot boot` only, and never
write the `bootloader`, `xloader` or `fpga` partitions.

Licence: Apache-2.0 (`LICENSE`). The projects the manifest points to carry their own licences.
