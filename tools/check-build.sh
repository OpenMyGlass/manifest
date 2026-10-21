#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Static checks of a Track A build (ART only). Plan Task 2, steps 1, 3 and 4.
#   tools/check-build.sh <aosp-tree> <product-out> [<extracted-vendor-dir>]
# <product-out> is out/target/product/glass-1. <extracted-vendor-dir> is the owner's
# vendor/glass/glass-1/proprietary; CI has none. Prints one line per check and exits 1 if any fails.
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
for t in readelf unzip od; do
    command -v "$t" >/dev/null || { echo "error: $t not found" >&2; exit 2; }
done

# Runtime files.
need lib/libart.so
need lib/libart-compiler.so
need bin/dex2oat
need framework/core-libart.jar
absent lib/libdvm.so
absent bin/dexopt
absent framework/core.jar

# build.prop.
prop() {
    v=$(grep -m1 "^$1=" "$sys/build.prop" | cut -d= -f2-)
    if [ "$v" = "$2" ]; then ok "build.prop $1=$2"; else bad "build.prop $1='$v', want '$2'"; fi
}
prop persist.sys.dalvik.vm.lib libart.so
prop persist.glass.d2o.sys speed
prop persist.glass.d2o.usr space

# No pre-optimisation: no .odex, and code stays in the APKs and jars.
odex=$(find "$sys" -name '*.odex' | wc -l)
if [ "$odex" -eq 0 ]; then ok "no .odex files"; else bad "$odex .odex files"; fi
archives=$(mktemp)
find "$sys/framework" "$sys/app" "$sys/priv-app" \( -name '*.jar' -o -name '*.apk' \) \
    2>/dev/null | sort > "$archives"
nodex=0
while read -r f; do
    if ! unzip -l "$f" classes.dex >/dev/null 2>&1; then
        nodex=$((nodex + 1))
        echo "info: no classes.dex in ${f#"$sys"/} (resource-only, or code stripped)"
    fi
done < "$archives"
echo "info: $(wc -l < "$archives") APKs and jars, $nodex without classes.dex"
rm -f "$archives"

# Nothing links libdvm.so: build output and, on the owner's machine, the extracted binaries.
elf_hits=$(mktemp)
for d in "$sys" ${vendor:+"$vendor"}; do
    find "$d" -type f | while read -r f; do
        if [ "$(head -c 4 "$f" | od -An -c | tr -d ' ')" = '177ELF' ]; then
            if readelf -d "$f" 2>/dev/null | grep -q 'NEEDED.*\[libdvm\.so\]'; then
                echo "$f" >> "$elf_hits"
            fi
        fi
    done
done
if [ -s "$elf_hits" ]; then
    bad "ELF files that need libdvm.so:"; sed 's/^/      /' "$elf_hits"
else
    ok "no ELF file needs libdvm.so${vendor:+ (including $vendor)}"
fi
rm -f "$elf_hits"

# No makefile outside dalvik/ names libdvm.
mk_hits=$(cd "$tree" && grep -rl --include=Android.mk -w libdvm . 2>/dev/null \
    | grep -v '^\./dalvik/' | grep -v '^\./out/' | sort)
if [ -n "$mk_hits" ]; then
    bad "Android.mk files outside dalvik/ that name libdvm:"; echo "$mk_hits" | sed 's/^/      /'
else
    ok "no Android.mk outside dalvik/ names libdvm"
fi

# Sizes.
for img in system.img boot.img recovery.img; do
    [ -f "$out/$img" ] && echo "info: $img $(wc -c < "$out/$img") bytes"
done
echo "info: system/ $(du -sk "$sys" | cut -f1) KiB"
[ -f "$sys/build.prop" ] && grep -m1 '^ro.glass.blob_stubs=' "$sys/build.prop" \
    && echo "info: CI blob stubs: this image must never be booted"
exit $fail
