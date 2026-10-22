#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Static checks of a Track B build (Android 6.0.1). glass-rom plan 2026-10-21-android-lean-6.md,
# first milestone: images built, ART present, no Google files.
#   tools/check-build-6.0.sh <aosp-tree> <product-out> [<extracted-vendor-dir>]
# <product-out> is out/target/product/glass-1. <extracted-vendor-dir> is the owner's
# vendor/glass/glass-1/proprietary; CI has none, and then no file that the device tree's
# proprietary-files.txt lists (the files only the owner's XE24 image has) may be in the image,
# apart from the known ones that AOSP or hardware/ti/omap4 build or ship themselves.
# Prints one line per check and exits 1 if any fails.
set -u

if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    echo "usage: $0 <aosp-tree> <product-out> [<extracted-vendor-dir>]" >&2
    exit 2
fi
tree=$1 out=$2 vendor=${3:-}
sys=$out/system
fail=0
ok() { echo "ok:   $*"; }
bad() { echo "FAIL: $*"; fail=1; }
need() { if [ -e "$sys/$1" ]; then ok "$1 present"; else bad "$1 missing"; fi; }
absent() { if [ -e "$sys/$1" ]; then bad "$1 present"; else ok "$1 absent"; fi; }

[ -d "$sys" ] || { echo "error: no $sys" >&2; exit 2; }

# Images. boot and recovery need the glass-kernel zImage (tools/fetch-kernel.sh).
for img in system.img boot.img recovery.img; do
    if [ -s "$out/$img" ]; then ok "$img built ($(wc -c < "$out/$img") bytes)"; else bad "$img missing or empty"; fi
done
[ -s "$out/kernel" ] && echo "info: kernel $(wc -c < "$out/kernel") bytes"
need lib/modules/pvrsrvkm_sgx540_120.ko

# ART, the only runtime on 6.0, and its boot image (WITH_DEXPREOPT in BoardConfig.mk).
need lib/libart.so
need lib/libart-compiler.so
need bin/dex2oat
need bin/dalvikvm
need framework/core-libart.jar
need framework/arm/boot.art
need framework/arm/boot.oat
absent lib/libdvm.so
absent bin/dexopt
odex=$(find "$sys" -name '*.odex' | wc -l)
echo "info: $odex .odex files (dexpreopt)"

# build.prop.
prop() {
    # The last assignment wins for properties that are not ro.
    v=$(grep "^$1=" "$sys/build.prop" | tail -n 1 | cut -d= -f2-)
    if [ "$v" = "$2" ]; then ok "build.prop $1=$2"; else bad "build.prop $1='$v', want '$2'"; fi
}
prop ro.build.version.release 6.0.1
prop ro.build.version.sdk 23
prop persist.sys.dalvik.vm.lib.2 libart.so
prop dalvik.vm.isa.arm.variant cortex-a9
prop ro.board.platform omap4
echo "info: $(grep '^ro.build.version.security_patch=' "$sys/build.prop")"
echo "info: $(grep '^ro.build.fingerprint=' "$sys/build.prop")"
echo "info: $(grep '^dalvik.vm.isa.arm.features=' "$sys/build.prop")"

# The open OMAP4 parts that replace XE24 binaries.
need vendor/lib/hw/hwcomposer.omap4.so
need vendor/lib/egl/libEGL_POWERVR_SGX54X.so
need bin/pvrsrvinit
need lib/hw/camera.omap4.so

# No Google files. Without the owner's vendor directory, no file of proprietary-files.txt may be
# in the image, except these, which come from AOSP or hardware/ti/omap4 sources:
#   vendor/firmware/fw_bcmdhd.bin: AOSP's hardware/broadcom/wlan bcm4330 firmware (device.mk
#     inherits its device-bcm.mk), Broadcom's redistributable file, not XE24's copy.
known_open='vendor/firmware/fw_bcmdhd.bin'
list=$tree/device/glass/glass-1/proprietary-files.txt
if [ -n "$vendor" ]; then
    echo "info: owner build with $vendor; proprietary-files.txt check skipped"
elif [ ! -f "$list" ]; then
    bad "no $list"
else
    hits=$(mktemp)
    grep -v -e '^#' -e '^$' "$list" | while read -r f; do
        if [ -e "$sys/$f" ] || [ -L "$sys/$f" ]; then
            case " $known_open " in
                *" $f "*) echo "info: $f present (known: built from open source)" ;;
                *) echo "$f" >> "$hits" ;;
            esac
        fi
    done
    if [ -s "$hits" ]; then
        bad "files of proprietary-files.txt in the image:"; sed 's/^/      /' "$hits"
    else
        ok "no file of proprietary-files.txt in the image, apart from the known open ones"
    fi
    rm -f "$hits"
fi
names=$(find "$sys/app" "$sys/priv-app" "$sys/framework" \( -name '*.apk' -o -name '*.jar' \) 2>/dev/null \
    | grep -i -E '/(google|gms|gsf|phonesky|velvet|glass)[^/]*$' || true)
if [ -n "$names" ]; then
    bad "APKs or jars named like Google or stock Glass packages:"; echo "$names" | sed 's/^/      /'
else
    ok "no APK or jar named like a Google or stock Glass package"
fi
if [ -f "$sys/build.prop" ] && grep -q '^ro.glass.blob_stubs=true' "$sys/build.prop"; then
    for f in vendor/lib/libsrv_init.so vendor/lib/libsrv_um.so vendor/lib/libIMGegl.so; do
        if [ -e "$sys/$f" ]; then echo "info: $f is a CI stub"; fi
    done
    echo "info: CI blob stubs: this image must never be booted"
fi

# Sizes.
for img in system.img boot.img recovery.img userdata.img; do
    [ -f "$out/$img" ] && echo "info: $img $(wc -c < "$out/$img") bytes"
done
echo "info: system/ $(du -sk "$sys" | cut -f1) KiB"
for d in app priv-app framework lib bin vendor; do
    [ -d "$sys/$d" ] && echo "info: system/$d $(du -sk "$sys/$d" | cut -f1) KiB"
done
exit $fail
