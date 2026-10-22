<!-- SPDX-License-Identifier: Apache-2.0 -->
# Building Track A on your own Linux PC

This builds Android 4.4.4 for Glass (ART only) with the PowerVR and other binaries from **your
own** XE24 factory image. CI builds the same tree, but without those binaries
(`tools/ci-blob-stubs.sh`). Its images are a build check and must never be booted.

Everything runs on your PC. No account, credential or remote access is needed beyond anonymous
downloads from GitHub (our repositories and mirrors, omap4-aosp, and KFire-Android for the
GPU kernel module source), android.googlesource.com (AOSP), storage.googleapis.com
(the `repo` tool), Docker Hub (`ubuntu:14.04`) and the Ubuntu archive (the build containers).

## What you need

- Linux on x86_64. AOSP 4.4 needs a case-sensitive file system: ext4 is fine, NTFS or exFAT is
  not.
- Disk: the script stops below 70 GB free. One build used 36 GB on the CI runner; a 200 GB SSD is
  enough.
  - Source: 11-12 GB after `repo sync`.
  - Output: 23 GB.
  - The glass-kernel build: a few GB, in `~/glass-kk/.work/` and the docker volume
    `glass-kernel-src`.
  - Containers: about 1 GB.
- RAM: 16 GB, or 8 GB plus 8 GB of swap.
- Packages: `git` 2.25 or newer, `python3`, `curl`, `binutils` (readelf), `unzip`, `coreutils` (sha256sum), `e2fsprogs` (debugfs, for `extract_vendor.py`), and Docker. Your user must
  be able to run `docker` (the `docker` group; rootless Docker is detected). The build itself runs in an
  Ubuntu 14.04 container with OpenJDK 6 and make 3.81 (`tools/docker/Dockerfile`), so nothing
  else needs installing on the PC.
- Your XE24 raw system image. With [glass-rom](https://github.com/OpenMyGlass/glass-rom), as in
  its README:

      tools/fetch-factory.sh factory/
      tools/sparse.py factory/system.img factory/system.raw

Measured on a free GitHub runner (4 vCPU, 16 GB RAM, `--stubs`, run 39700241850, 2026-10-22):
`repo sync` 89 s, kernel 242 s, build 5192 s (87 minutes), total 92 minutes. A PC with more
cores builds faster.

## Build

    git clone https://github.com/OpenMyGlass/manifest
    manifest/tools/build-kitkat.sh --tree ~/glass-kk --system-raw /path/to/factory/system.raw

The script runs these steps:
1. **Preflight.** It checks the OS, the tools, the free disk and the memory.
2. **Source.** It downloads `repo` if it is not installed. It then runs
   `repo init -u https://github.com/OpenMyGlass/manifest -b main --depth=1 -g default,-device,-darwin,-mips,-x86`
   and `repo sync`.
3. **Kernel.** `tools/fetch-kernel.sh` clones glass-kernel at the commit in `tools/kernel.env`
   and builds variant `tuned-stable` in its own container. It copies `zImage` and
   `pvrsrvkm_sgx540_120.ko` into `vendor/glass/kernel/`.
4. **Vendor files.** It clones glass-rom at the commit in `tools/glass-rom.env`, and its
   `extract_vendor.py` copies the files in `device/glass/glass-1/proprietary-files.txt` from your
   image into `vendor/glass/glass-1/`. Nothing from your image leaves your PC.
5. **Build.** It builds `aosp_glass_1-userdebug` with `make -j<CPUs>` in the container. The log
   is `~/glass-kk/build.log`.
6. **Checks.** `tools/check-build.sh` writes `~/glass-kk/check-build.txt`:
   - no `libdvm.so`, `dexopt`, `core.jar` or `.odex` in the system;
   - `libart`, `dex2oat` and `core-libart.jar` present;
   - the runtime and dex2oat properties in `build.prop`;
   - no ELF file that needs `libdvm.so`, **including the binaries extracted from your image**.
     This is the plan's Task 2 step 3 check that CI cannot run. If a Glass binary needs
     libdvm, the check fails: stop there and report it.
7. **Summary.** Timings, sizes and free disk go to `~/glass-kk/build-numbers.txt`.

Options:
- `--out DIR` puts the output on another disk.
- `--jobs N`.
- `--skip-sync` and `--skip-kernel` reuse an earlier checkout and kernel.
- `--stubs` builds without your image, like CI does.
- `--help` lists them all.

Re-running the script updates the checkout to the manifest's current pins.

Outputs, in `~/glass-kk/out/target/product/glass-1/`: `boot.img`, `system.img`,
`recovery.img`.

## Please send back

After a run, these files contain no Google file and nothing from your image:
- `~/glass-kk/build-numbers.txt`;
- `~/glass-kk/check-build.txt`;
- the last 200 lines of `~/glass-kk/build.log` if the build failed.

Open an issue with them in OpenMyGlass/manifest, or hand them to the agent.

## On a Glass

Nothing here has been tested on a device. Rules:
- **Never** write the `bootloader`, `xloader` or `fpga` partitions.
- Test a boot image with `fastboot boot boot.img`. It runs from RAM and writes nothing.

A boot image alone is not enough to try this Android: its system lives in `system.img`, which
`fastboot boot` does not load. Writing `system.img` to the Glass's `system` partition is a
separate step. It is **your decision**, and the script does not do it. The way back is
glass-rom's factory image for that partition. The device checks are in the device tree's
`docs/kitkat.md` and `docs/device-checklist.md`. All of them are marked "not run".
