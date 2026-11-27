#!/bin/zsh
set -eu

root=${0:A:h:h}
revision=d0d9889514e94195ebcdbf86e23a60f4f5756189
mode=${1:-}
source="$root/.build/xcl-mac"
patch="$root/patches/mac-compat.patch"
lanes_patch="$root/patches/lanes-experiment.patch"

if [[ $# -gt 1 || ( -n $mode && $mode != --prepare && $mode != --test-title && $mode != --lanes ) ]]; then
    print -u2 'Usage: scripts/build.sh [--prepare | --test-title | --lanes]'
    exit 2
fi
if [[ $mode == --lanes ]]; then
    source="$root/.build/xcl-mac-lanes"
fi

if [[ ! -d "$source/.git" ]]; then
    git init --quiet "$source"
    git -C "$source" remote add origin https://github.com/utkarshxdev/xcl-mac.git
fi
if ! git -C "$source" rev-parse --verify HEAD >/dev/null 2>&1; then
    git -C "$source" fetch --depth 1 origin refs/tags/v0.1.0-stage6
    git -C "$source" checkout --detach "$revision"
fi
if [[ $(git -C "$source" rev-parse HEAD) != "$revision" ]]; then
    print -u2 "Unexpected XCL source revision in $source"
    exit 1
fi
apply_patch_once() {
    if git -C "$source" apply --reverse --check "$1" 2>/dev/null; then
        return
    fi
    git -C "$source" apply "$1"
}
prepare_patches() {
    if [[ $mode == --lanes ]] && git -C "$source" apply --reverse --check "$lanes_patch" 2>/dev/null; then
        return
    fi
    apply_patch_once "$patch"
    if [[ $mode == --test-title ]]; then
        apply_patch_once "$root/patches/test-title-readback.patch"
    fi
    if [[ $mode == --lanes ]]; then
        git -C "$source" apply "$lanes_patch"
    fi
}
prepare_patches

if [[ $mode != --prepare ]]; then
    : "${SCARLETT_LLVM_MINGW:?Set SCARLETT_LLVM_MINGW to the extracted LLVM-MinGW directory}"
    mingw=${SCARLETT_LLVM_MINGW:A}
    export PATH="$mingw/bin:$PATH"
    export CARGO_TARGET_X86_64_PC_WINDOWS_GNULLVM_LINKER=x86_64-w64-mingw32-clang
    cd "$source"
    packages=(-p xcl)
    if [[ $mode == --test-title ]]; then
        packages+=(-p xcl-testtitle -p testgame-mw)
    fi
    rustup run "${SCARLETT_RUST_TOOLCHAIN:-stable}" cargo build --release --locked --target x86_64-pc-windows-gnullvm "${packages[@]}"
    if [[ $mode == --test-title ]]; then
        fixture="$root/.build/test-title"
        built="$source/target/x86_64-pc-windows-gnullvm/release"
        mkdir -p "$fixture"
        cp -R tests/data/testgame/. "$fixture"
        cp "$built/xcl_testtitle.exe" "$built/testgame_mw.dll" "$mingw/x86_64-w64-mingw32/bin/libunwind.dll" "$fixture"
    fi
fi
