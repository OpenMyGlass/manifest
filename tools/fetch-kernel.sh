#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Build the Track A kernel and SGX module with glass-kernel at the commit pinned in
# tools/kernel.env, and copy them where the device tree expects them:
#   tools/fetch-kernel.sh <aosp-tree> [<work-dir>]
# Writes <aosp-tree>/vendor/glass/kernel/{zImage,pvrsrvkm_sgx540_120.ko,config,SHA256SUMS}.
# Needs git and docker (or podman); glass-kernel's scripts/build-in-container.sh does the build.
set -eu

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "usage: $0 <aosp-tree> [<work-dir>]" >&2
    exit 2
fi
tree=$1
here=$(cd "$(dirname "$0")" && pwd)
work=${2:-$tree/../glass-kernel}
# shellcheck disable=SC1091
. "$here/kernel.env"

[ -d "$tree/device/glass/glass-1" ] || {
    echo "error: $tree has no device/glass/glass-1; run repo sync first" >&2
    exit 1
}
if [ ! -d "$work/.git" ]; then
    git clone -q "$GLASS_KERNEL_REPO" "$work"
fi
git -C "$work" fetch -q origin "$GLASS_KERNEL_COMMIT"
git -C "$work" checkout -q --detach "$GLASS_KERNEL_COMMIT"
test "$(git -C "$work" rev-parse HEAD)" = "$GLASS_KERNEL_COMMIT"

(cd "$work" && VARIANT=$GLASS_KERNEL_VARIANT scripts/build-in-container.sh)

dest=$tree/vendor/glass/kernel
mkdir -p "$dest"
for f in zImage pvrsrvkm_sgx540_120.ko config SHA256SUMS; do
    cp "$work/out/$f" "$dest/$f"
done
(cd "$dest" && sha256sum -c --quiet SHA256SUMS)
printf '%s %s %s\n' "$GLASS_KERNEL_REPO" "$GLASS_KERNEL_COMMIT" "$GLASS_KERNEL_VARIANT" > "$dest/SOURCE"
echo "kernel: $dest (glass-kernel $GLASS_KERNEL_COMMIT, $GLASS_KERNEL_VARIANT)"
