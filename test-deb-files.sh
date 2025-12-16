#!/bin/bash
# test-deb-files.sh - Test if actual .deb files exist in Nexus

echo "Testing actual .deb files in Nexus..."
echo "======================================"

BASE="https://srvnexus1.dst.dk/repository/jammy/pool"

# All packages needed for Docker build
debs=(
  # binutils (the problematic ones)
  "main/b/binutils/binutils_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/binutils-common_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/binutils-x86-64-linux-gnu_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/libbinutils_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/libctf0_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/libctf-nobfd0_2.38-4ubuntu2.11_amd64.deb"
  # gcc
  "main/g/gcc-11/gcc-11_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-11/gcc-11-base_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-11/libgcc-11-dev_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-11/libasan6_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-11/libtsan0_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-defaults/gcc_4%3a11.2.0-1ubuntu1_amd64.deb"
  # g++
  "main/g/gcc-11/g++-11_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-11/libstdc++-11-dev_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-defaults/g++_4%3a11.2.0-1ubuntu1_amd64.deb"
  # cpp
  "main/g/gcc-11/cpp-11_11.4.0-1ubuntu1~22.04.2_amd64.deb"
  "main/g/gcc-defaults/cpp_4%3a11.2.0-1ubuntu1_amd64.deb"
  # build-essential
  "main/b/build-essential/build-essential_12.9ubuntu3_amd64.deb"
  # make
  "main/m/make-dfsg/make_4.3-4.1build1_amd64.deb"
  # git
  "main/g/git/git_1%3a2.34.1-1ubuntu1.15_amd64.deb"
  # libc
  "main/g/glibc/libc6-dev_2.35-0ubuntu3.11_amd64.deb"
  "main/g/glibc/libc-dev-bin_2.35-0ubuntu3.11_amd64.deb"
  "main/l/linux/linux-libc-dev_5.15.0-161.171_amd64.deb"
  # llvm
  "main/l/llvm-toolchain-14/libllvm14_14.0.0-1ubuntu1.1_amd64.deb"
  "main/l/llvm-toolchain-14/llvm-14_14.0.0-1ubuntu1.1_amd64.deb"
  "universe/l/llvm-defaults/llvm_14.0-55~exp2_amd64.deb"
  # ssl/zlib
  "main/o/openssl/libssl-dev_3.0.2-0ubuntu1.20_amd64.deb"
  "main/z/zlib/zlib1g-dev_1.2.11.dfsg-2ubuntu9.2_amd64.deb"
  # tini
  "universe/t/tini/tini_0.19.0-1_amd64.deb"
)

PASS=0
FAIL=0

for deb in "${debs[@]}"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/$deb")
  NAME=$(basename "$deb")
  if [ "$STATUS" == "200" ]; then
    echo "✓ OK:   $NAME"
    ((PASS++))
  else
    echo "✗ FAIL ($STATUS): $NAME"
    ((FAIL++))
  fi
done

echo ""
echo "======================================"
echo "Results: $PASS OK, $FAIL FAILED"
if [ $FAIL -eq 0 ]; then
  echo "All .deb files exist! Docker build should work."
else
  echo "Missing $FAIL files - send list to IT"
fi

