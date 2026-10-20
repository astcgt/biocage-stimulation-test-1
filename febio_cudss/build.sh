#!/bin/bash
# Build the FEBio cuDSS plugin against third_party/FEBio (v4.13) and the vendored cuDSS / CUDA runtime.
set -e
D="$(cd "$(dirname "$0")" && pwd)"; T="$D/../third_party"
g++ -O3 -fPIC -shared -std=gnu++17 -DLINUX -w \
  -I"$T/FEBio" -I"$T/cuda/include" "$D/CuDSSSolver.cpp" -o "$D/libfebio_cudss.so" \
  -L"$T/FEBio/cbuild/lib" -lfecore -L"$T/cuda/lib" -lcudss -lcudart \
  -Wl,-rpath,"$T/cuda/lib" -Wl,-rpath,"$T/FEBio/cbuild/lib"
echo built "$D/libfebio_cudss.so"
