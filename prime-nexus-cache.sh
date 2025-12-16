#!/bin/bash
# prime-nexus-cache.sh - Try to trigger Nexus to cache missing packages

BASE="https://srvnexus1.dst.dk/repository/jammy/pool"

files=(
  "main/b/binutils/binutils_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/binutils-common_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/binutils-x86-64-linux-gnu_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/libbinutils_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/libctf0_2.38-4ubuntu2.11_amd64.deb"
  "main/b/binutils/libctf-nobfd0_2.38-4ubuntu2.11_amd64.deb"
  "main/g/gcc-defaults/gcc_4%3a11.2.0-1ubuntu1_amd64.deb"
  "main/g/gcc-defaults/g++_4%3a11.2.0-1ubuntu1_amd64.deb"
  "main/g/gcc-defaults/cpp_4%3a11.2.0-1ubuntu1_amd64.deb"
  "main/g/git/git_1%3a2.34.1-1ubuntu1.15_amd64.deb"
  "main/l/llvm-toolchain-14/llvm-14_14.0.0-1ubuntu1.1_amd64.deb"
)

for f in "${files[@]}"; do
  echo "Requesting: $f"
  curl -s -o /dev/null -w "Status: %{http_code}\n" "$BASE/$f"
  sleep 1
done

echo ""
echo "Done. Now run test-deb-files.sh to check if they're cached."

