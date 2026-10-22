# SPDX-License-Identifier: Apache-2.0
# Build environment for AOSP 4.4: Ubuntu 14.04 (the same pinned image as glass-kernel), GNU make
# 3.81, OpenJDK 6 (4.4's build/core/main.mk requires java and javac 1.6) and Python 2.7.
# Packages: AOSP's 4.4-era host requirements plus the 32-bit libraries its prebuilt host
# toolchain (i686-linux-glibc2.7) needs.
FROM ubuntu:14.04@sha256:64483f3496c1373bfd55348e88694d1c4d0c9b660dee6bfef5e12f43b9933b30
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      openjdk-6-jdk python2.7 python make bison flex gperf zip unzip curl ca-certificates git \
      build-essential gcc-multilib g++-multilib libc6-dev-i386 lib32z1-dev lib32ncurses5-dev \
      zlib1g-dev libncurses5-dev libxml2-utils xsltproc bc rsync file \
 && rm -rf /var/lib/apt/lists/*
# 4.4's build calls /bin/sh scripts that expect bash.
RUN ln -sf bash /bin/sh
ENV USE_CCACHE=0 LC_ALL=C
WORKDIR /aosp
