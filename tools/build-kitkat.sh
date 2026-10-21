#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Check out and build Track A (Android 4.4.4, ART only) for Glass on a Linux PC.
# Guide: docs/build-on-pc.md. Nothing here talks to a device; boot the result with
# `fastboot boot` only, never flash bootloader, xloader or fpga.
#
#   tools/build-kitkat.sh --tree DIR --system-raw FILE [options]
#   tools/build-kitkat.sh --tree DIR --stubs [options]       (no blobs: build check only)
#
# Options:
#   --tree DIR           checkout directory (created; about 11 GB of source). DIR/.work holds
#                        the glass-kernel and glass-rom checkouts; glass-kernel also uses the
#                        docker volume glass-kernel-src (about 2 GB)
#   --out DIR            build output directory (default DIR/out; about 30-40 GB)
#   --system-raw FILE    the owner's raw XE24 system image (glass-rom: fetch-factory.sh, sparse.py)
#   --stubs              build without blobs (tools/ci-blob-stubs.sh); the image must not be booted
#   --manifest-url URL   default https://github.com/OpenMyGlass/manifest
#   --manifest-rev REV   branch of the manifest repository, default main
#   --jobs N             make -j (default: number of CPUs)
#   --skip-sync          reuse the existing checkout
#   --skip-kernel        reuse DIR/vendor/glass/kernel
#   --keep-going         make -k: build as much as possible and list every failure
# Writes a summary with timings and sizes to DIR/build-numbers.txt.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
tree='' out='' system_raw='' stubs=no jobs='' skip_sync=no skip_kernel=no keep_going=''
manifest_url=https://github.com/OpenMyGlass/manifest
manifest_rev=main
lunch_combo=aosp_glass_1-userdebug
image=openmyglass-aosp44

die() { echo "error: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
    case $1 in
        --tree) tree=$2; shift 2 ;;
        --out) out=$2; shift 2 ;;
        --system-raw) system_raw=$2; shift 2 ;;
        --stubs) stubs=yes; shift ;;
        --manifest-url) manifest_url=$2; shift 2 ;;
        --manifest-rev) manifest_rev=$2; shift 2 ;;
        --jobs) jobs=$2; shift 2 ;;
        --skip-sync) skip_sync=yes; shift ;;
        --skip-kernel) skip_kernel=yes; shift ;;
        --keep-going) keep_going=-k; shift ;;
        -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
        *) die "unknown option $1 (see --help)" ;;
    esac
done
[ -n "$tree" ] || die "--tree is required"
if [ "$stubs" = yes ] && [ -n "$system_raw" ]; then die "--stubs and --system-raw exclude each other"; fi
if [ "$stubs" = no ] && [ -z "$system_raw" ]; then die "--system-raw FILE (or --stubs) is required"; fi
[ -z "$system_raw" ] || [ -f "$system_raw" ] || die "no file $system_raw"

# Preflight.
[ "$(uname -s)" = Linux ] || die "Linux only (AOSP 4.4 needs a case-sensitive file system)"
[ "$(uname -m)" = x86_64 ] || die "x86_64 only (AOSP 4.4's prebuilt host tools)"
for t in git python3 curl docker readelf unzip sha256sum; do
    command -v "$t" >/dev/null || die "$t not found"
done
if [ "$stubs" = no ] && ! command -v debugfs >/dev/null && [ ! -x /sbin/debugfs ]; then
    die "debugfs not found (e2fsprogs); extract_vendor.py needs it"
fi
git_minor=$(git --version | awk '{split($3, v, "."); print v[1] * 100 + v[2]}')
[ "$git_minor" -ge 225 ] || die "git 2.25 or newer is needed (glass-kernel's fetch-pvr.sh)"
docker info >/dev/null 2>&1 || die "docker is installed but not usable by $(id -un) (add the user to the docker group)"
# Rootless docker maps the host user to root in the container: run as root there.
user_opt="-u $(id -u):$(id -g)"
if docker info -f '{{.SecurityOptions}}' 2>/dev/null | grep -q rootless; then user_opt=''; fi
mkdir -p "$tree"
tree=$(cd "$tree" && pwd)
out=${out:-$tree/out}
mkdir -p "$out"
out=$(cd "$out" && pwd)
jobs=${jobs:-$(nproc)}
numbers=$tree/build-numbers.txt
avail_gb() { df -Pk "$1" | awk 'NR==2 {printf "%d", $4 / 1048576}'; }
free_tree=$(avail_gb "$tree") free_out=$(avail_gb "$out")
echo "free space: $free_tree GB at $tree, $free_out GB at $out"
if [ "$(df -P "$tree" | awk 'NR==2 {print $1}')" = "$(df -P "$out" | awk 'NR==2 {print $1}')" ]; then
    [ "$free_tree" -ge 70 ] || die "need about 70 GB free for source and output, $free_tree GB free"
else
    [ "$free_tree" -ge 30 ] || die "need about 30 GB free for the source, $free_tree GB free"
    [ "$free_out" -ge 40 ] || die "need about 40 GB free for the output, $free_out GB free"
fi
mem_gb=$(awk '/MemTotal/ {printf "%d", $2 / 1048576}' /proc/meminfo)
swap_gb=$(awk '/SwapTotal/ {printf "%d", $2 / 1048576}' /proc/meminfo)
[ $((mem_gb + swap_gb)) -ge 12 ] || echo "warning: ${mem_gb} GB RAM + ${swap_gb} GB swap; 16 GB is recommended"

now() { date +%s; }
t0=$(now)
{
    echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "host: $(nproc) CPUs, ${mem_gb} GB RAM, ${swap_gb} GB swap, jobs $jobs"
    echo "free at start: $free_tree GB (tree), $free_out GB (out)"
    echo "manifest: $manifest_url $manifest_rev"
} > "$numbers"
step() { echo "$1: $(( $(now) - $2 )) s" >> "$numbers"; }

# 1. Source.
if [ "$skip_sync" = no ]; then
    t=$(now)
    repo=$(command -v repo || true)
    if [ -z "$repo" ]; then
        mkdir -p "$tree/.bin"
        curl -fsSL --retry 3 -o "$tree/.bin/repo" https://storage.googleapis.com/git-repo-downloads/repo
        chmod +x "$tree/.bin/repo"
        repo=$tree/.bin/repo
    fi
    (cd "$tree" && "$repo" init -q -u "$manifest_url" -b "$manifest_rev" --depth=1 \
        -g default,-device,-darwin,-mips,-x86 &&
        "$repo" sync -q -c -j8 --no-tags --no-clone-bundle --optimized-fetch --force-sync)
    step "repo sync" "$t"
    echo "source: $(du -sh --exclude=out "$tree" | cut -f1)" >> "$numbers"
fi
[ -n "${repo:-}" ] || repo=$(command -v repo || echo "$tree/.bin/repo")
(cd "$tree" && "$repo" manifest -r -o "$tree/manifest-pinned.xml" 2>/dev/null) || true

# 2. Kernel and SGX module (glass-kernel, tuned-stable).
if [ "$skip_kernel" = no ]; then
    t=$(now)
    "$here/fetch-kernel.sh" "$tree" "$tree/.work/glass-kernel"
    step "kernel" "$t"
fi

# 3. Vendor files: the owner's image, or CI stubs.
rm -rf "$tree/vendor/glass/glass-1"
if [ "$stubs" = yes ]; then
    "$here/ci-blob-stubs.sh" "$tree"
    echo "warning: --stubs: the images in $out are a build check only; never boot them"
else
    # shellcheck disable=SC1091
    . "$here/glass-rom.env"
    rom=$tree/.work/glass-rom
    [ -d "$rom/.git" ] || git clone -q "$GLASS_ROM_REPO" "$rom"
    git -C "$rom" fetch -q origin "$GLASS_ROM_COMMIT"
    git -C "$rom" checkout -q --detach "$GLASS_ROM_COMMIT"
    python3 "$rom/tools/extract_vendor.py" "$system_raw" \
        "$tree/device/glass/glass-1/proprietary-files.txt" "$tree/vendor/glass/glass-1"
fi

# 4. Build in the pinned Ubuntu 14.04 container.
t=$(now)
docker build -q -t "$image" "$here/docker" >/dev/null
# shellcheck disable=SC2086  # user_opt is empty or two words
docker run --rm $user_opt -e HOME=/tmp -e USER="$(id -un)" -e OUT_DIR=/out \
    -v "$tree:/aosp" -v "$out:/out" "$image" \
    bash -c ". build/envsetup.sh >/dev/null && lunch $lunch_combo >/dev/null && make -j$jobs -l$jobs $keep_going" \
    > "$tree/build.log" 2>&1 || {
        step "build (failed)" "$t"
        grep -n -E 'error:|Error [0-9]+|\*\*\*' "$tree/build.log" | head -n 60 || true
        tail -n 20 "$tree/build.log"
        die "build failed; full log: $tree/build.log"
    }
step "build" "$t"

# 5. Checks.
product=$out/target/product/glass-1
vendor_dir=''
[ "$stubs" = yes ] || vendor_dir=$tree/vendor/glass/glass-1/proprietary
status=0
"$here/check-build.sh" "$tree" "$product" ${vendor_dir:+"$vendor_dir"} > "$tree/check-build.txt" 2>&1 \
    || status=1
cat "$tree/check-build.txt"
{
    echo "output: $(du -sh "$out" | cut -f1)"
    echo "free at end: $(avail_gb "$tree") GB (tree), $(avail_gb "$out") GB (out)"
    echo "total: $(( $(now) - t0 )) s"
} >> "$numbers"
cat "$numbers"
echo "images: $product/{boot,system,recovery}.img"
if [ "$stubs" = no ]; then
    echo "device tests: see docs/build-on-pc.md, 'On a Glass' (fastboot boot only; writing"
    echo "system.img to the device is the owner's decision and is not done by this script)"
fi
exit $status
