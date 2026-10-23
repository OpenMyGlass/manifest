# SPDX-License-Identifier: Apache-2.0
# Build environment for AOSP 6.0.1 (Track B): Ubuntu 14.04 (the same pinned image as Track A and
# glass-kernel), GNU make 3.81, OpenJDK 7 (6.0's build/core/main.mk requires java and javac 1.7,
# OpenJDK on Linux) and Python 2.7. Packages: AOSP's 6.0-era host requirements plus the 32-bit
# libraries some of its prebuilt host tools need.
FROM ubuntu:14.04@sha256:64483f3496c1373bfd55348e88694d1c4d0c9b660dee6bfef5e12f43b9933b30
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      openjdk-7-jdk python2.7 python make bison flex gperf zip unzip curl ca-certificates git \
      build-essential gcc-multilib g++-multilib libc6-dev-i386 lib32z1-dev lib32ncurses5-dev \
      zlib1g-dev libncurses5-dev libxml2-utils xsltproc bc rsync file \
 && rm -rf /var/lib/apt/lists/*
# AOSP's build calls /bin/sh scripts that expect bash.
RUN ln -sf bash /bin/sh
ENV USE_CCACHE=0 LC_ALL=C
WORKDIR /aosp
