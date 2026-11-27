#!/bin/sh
set -eu

bundle=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
recipe=$bundle
if [ "${1-}" = --checkpoint ]; then
    recipe=$bundle/checkpoint
    shift
elif [ "${1-}" = --perf ]; then
    recipe=$bundle/perf
    shift
fi
mode=build
if [ "${1-}" = --prepare ]; then
    mode=prepare
    shift
fi
if [ "$#" -ne 1 ]; then
    printf 'Usage: %s [--checkpoint|--perf] [--prepare] NEW_SOURCE_DIR\n' "$0" >&2
    exit 2
fi

source_dir=$1
if [ -e "$source_dir" ] || [ -L "$source_dir" ]; then
    printf 'Choose a new source directory: %s\n' "$source_dir" >&2
    exit 2
fi

if [ "$mode" = build ]; then
    : "${LLVM_MINGW_ROOT:?Set LLVM_MINGW_ROOT to an extracted llvm-mingw UCRT distribution}"
    cross_tools=$(CDPATH='' cd -- "$LLVM_MINGW_ROOT/bin" && pwd)
    cross_clang=$cross_tools/x86_64-w64-mingw32-clang
    cross_ar=$cross_tools/llvm-ar
    cross_unwind=$cross_tools/../x86_64-w64-mingw32/bin/libunwind.dll
    if [ ! -x "$cross_clang" ] || [ ! -x "$cross_ar" ]; then
        printf '%s\n' 'The llvm-mingw bin directory must contain x86_64-w64-mingw32-clang and llvm-ar.' >&2
        exit 2
    fi
    if [ ! -f "$cross_unwind" ]; then
        printf '%s\n' 'The llvm-mingw toolchain must include x86_64-w64-mingw32/bin/libunwind.dll.' >&2
        exit 2
    fi
fi

{
    IFS= read -r upstream
    IFS= read -r pin
} < "$recipe/UPSTREAM"

git init -q -- "$source_dir"
git -C "$source_dir" fetch --quiet --depth=1 -- "$upstream" "$pin"
git -C "$source_dir" checkout --quiet --detach FETCH_HEAD
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$pin" ]
while IFS= read -r patch; do
    [ -n "$patch" ] || continue
    git -C "$source_dir" apply --index --check "$recipe/patches/$patch"
    git -C "$source_dir" apply --index "$recipe/patches/$patch"
done < "$recipe/patches/series"

cd -- "$source_dir"
if [ "$mode" = prepare ]; then
    printf 'Prepared %s\n' "$PWD"
    exit 0
fi

export CARGO_TARGET_X86_64_PC_WINDOWS_GNULLVM_LINKER="$cross_clang"
export CC_x86_64_pc_windows_gnullvm="$cross_clang"
export AR_x86_64_pc_windows_gnullvm="$cross_ar"
export CARGO_TARGET_DIR="$PWD/target"
target=x86_64-pc-windows-gnullvm
profile=${SCARLETTMAC_BUILD_PROFILE:-diag}
set --
if [ "$profile" = diag ]; then
    set -- --features diagnostics
fi
cargo build --locked --jobs "${SCARLETTMAC_BUILD_JOBS:-2}" --target "$target" \
    --profile "$profile" "$@" -p victory
output=$CARGO_TARGET_DIR/$target/$profile
cp -- "$cross_unwind" "$output/libunwind.dll"
printf '%s\n' "$output/victory.exe"
