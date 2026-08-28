#!/bin/bash
# Build the pinned x86_64-elf binutils/GCC toolchain used by this project.
set -euo pipefail

umask 077

INSTALL_PREFIX="${1:-${HOME}/.local/cross}"
TARGET="x86_64-elf"
GCC_VER="13.2.0"
# Computed from the tarballs after validating their detached signatures with
# ftp.gnu.org/gnu/gnu-keyring.gpg.
GCC_SHA256="e275e76442a6067341a27f04c5c6b83d8613144004c0413528863dc6b5c743da"
BINUTILS_VER="2.42"
BINUTILS_SHA256="f6e4d41fd5fc778b06b7891457b3620da5ecea1006c6a4a41ae998109f85a800"
NPROC="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '1')"
MAKE_JOBS="${MAKE_JOBS:-${NPROC}}"

ESC='\033'; CR="${ESC}[0m"; CB="${ESC}[1m"
CG="${ESC}[38;5;83m"; CRD="${ESC}[38;5;203m"; CGY="${ESC}[38;5;240m"
CWH="${ESC}[38;5;255m"; G_OK='✓'; G_NO='✗'; G_DOT='•'

step() { printf "  ${CGY}${G_DOT}${CR} %s\n" "$1"; }
ok() { printf "  ${CG}${G_OK}${CR} ${CGY}%s${CR}\n" "$1"; }
fail() { printf "  ${CRD}${G_NO}${CR} ${CRD}%s${CR}\n" "$1" >&2; exit 1; }

installed_toolchain_usable() {
    local tool
    local prefix="${INSTALL_PREFIX}/bin/${TARGET}-"
    for tool in gcc as ld objcopy objdump nm; do
        [ -x "${prefix}${tool}" ] || return 1
    done
    [ "$("${prefix}gcc" -dumpmachine 2>/dev/null)" = "${TARGET}" ] || return 1
    [ "$("${prefix}gcc" -dumpfullversion -dumpversion 2>/dev/null)" = "${GCC_VER}" ] || return 1
    printf 'void f(void) {}\n' \
        | "${prefix}gcc" -m32 -ffreestanding -fleading-underscore \
            -x c -c -o /dev/null - >/dev/null 2>&1
}

if installed_toolchain_usable; then
    ver="$("${INSTALL_PREFIX}/bin/${TARGET}-gcc" --version 2>/dev/null)"
    ver="${ver%%$'\n'*}"
    ok "Verified pinned cross-compiler at ${INSTALL_PREFIX}/bin (${ver})"
    exit 0
fi
if [ -e "${INSTALL_PREFIX}/bin/${TARGET}-gcc" ]; then
    fail "Existing compiler at ${INSTALL_PREFIX}/bin is incomplete or not GCC ${GCC_VER}; choose an empty prefix"
fi

required_tools=(mktemp make gcc g++ bison flex makeinfo patch tar xz sha256sum)
missing_tools=()
for tool in "${required_tools[@]}"; do
    command -v "${tool}" >/dev/null 2>&1 || missing_tools+=("${tool}")
done
if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    missing_tools+=("curl-or-wget")
fi
if [ "${#missing_tools[@]}" -ne 0 ]; then
    fail "Missing cross-toolchain prerequisites: ${missing_tools[*]}"
fi

BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/linux001-cross.XXXXXXXX")"
cleanup() {
    rm -rf -- "${BUILD_DIR}"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

mkdir -p -- "${INSTALL_PREFIX}/bin" "${BUILD_DIR}/src" \
    "${BUILD_DIR}/build-binutils" "${BUILD_DIR}/build-gcc"

# Fail before lengthy downloads if required development headers or libraries
# are unavailable to GCC's configure checks.
if ! printf '%s\n' \
    '#include <gmp.h>' \
    '#include <mpfr.h>' \
    '#include <mpc.h>' \
    '#include <zlib.h>' \
    'int main(void) { mpz_t z; mpfr_t r; mpc_t c; z_stream s = {0}; mpz_init(z); mpfr_init2(r, 32); mpc_init2(c, 32); deflateEnd(&s); mpc_clear(c); mpfr_clear(r); mpz_clear(z); return 0; }' \
    | gcc -x c - -o "${BUILD_DIR}/prereq-check" -lgmp -lmpfr -lmpc -lz; then
    fail "Missing GMP, MPFR, MPC, or zlib development headers/libraries"
fi

download() {
    local url="$1"
    local output="$2"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --proto '=https' --tlsv1.2 \
            --retry 3 --output "${output}.part" "${url}"
    else
        wget --https-only --secure-protocol=TLSv1_2 --tries=3 \
            --output-document="${output}.part" "${url}"
    fi
    mv -- "${output}.part" "${output}"
}

verify_sha256() {
    local expected="$1"
    local file="$2"
    printf '%s  %s\n' "${expected}" "${file}" | sha256sum --check --status - \
        || fail "SHA-256 verification failed for ${file}"
}

BINUTILS_ARCHIVE="${BUILD_DIR}/src/binutils-${BINUTILS_VER}.tar.xz"
GCC_ARCHIVE="${BUILD_DIR}/src/gcc-${GCC_VER}.tar.xz"

printf "\n  ${CB}${CWH}Building x86_64-elf cross-compiler${CR}\n"
printf "  ${CGY}Target: %s   Prefix: %s${CR}\n" "${TARGET}" "${INSTALL_PREFIX}"
printf "  ${CGY}GCC: %s   Binutils: %s   Jobs: %s${CR}\n\n" \
    "${GCC_VER}" "${BINUTILS_VER}" "${MAKE_JOBS}"
step "Private build directory: ${BUILD_DIR}"

step "Downloading and verifying binutils-${BINUTILS_VER}..."
download "https://ftp.gnu.org/gnu/binutils/binutils-${BINUTILS_VER}.tar.xz" \
    "${BINUTILS_ARCHIVE}"
verify_sha256 "${BINUTILS_SHA256}" "${BINUTILS_ARCHIVE}"

step "Downloading and verifying gcc-${GCC_VER}..."
download "https://ftp.gnu.org/gnu/gcc/gcc-${GCC_VER}/gcc-${GCC_VER}.tar.xz" \
    "${GCC_ARCHIVE}"
verify_sha256 "${GCC_SHA256}" "${GCC_ARCHIVE}"
ok "Pinned source archives verified"

step "Extracting source archives..."
tar --extract --file="${BINUTILS_ARCHIVE}" --directory="${BUILD_DIR}/src"
tar --extract --file="${GCC_ARCHIVE}" --directory="${BUILD_DIR}/src"

step "Building binutils (stage 1/2)..."
cd "${BUILD_DIR}/build-binutils"
"${BUILD_DIR}/src/binutils-${BINUTILS_VER}/configure" \
    --prefix="${INSTALL_PREFIX}" \
    --target="${TARGET}" \
    --disable-nls \
    --disable-werror \
    --with-sysroot \
    2>&1 | tail -n 3
make -j"${MAKE_JOBS}" 2>&1 | tail -n 5
make install 2>&1 | tail -n 3
ok "binutils installed to ${INSTALL_PREFIX}/bin"

export PATH="${INSTALL_PREFIX}/bin:${PATH}"
step "Building GCC and required target libgcc (stage 2/2)..."
cd "${BUILD_DIR}/build-gcc"
"${BUILD_DIR}/src/gcc-${GCC_VER}/configure" \
    --prefix="${INSTALL_PREFIX}" \
    --target="${TARGET}" \
    --enable-languages=c \
    --disable-libssp \
    --disable-libstdcxx-pch \
    --disable-shared \
    --disable-nls \
    --disable-werror \
    --without-headers \
    --with-newlib \
    --without-included-gettext \
    --with-sysroot \
    2>&1 | tail -n 3
make -j"${MAKE_JOBS}" all-gcc 2>&1 | tail -n 5
make install-gcc 2>&1 | tail -n 3
make -j"${MAKE_JOBS}" all-target-libgcc 2>&1 | tail -n 5
make install-target-libgcc 2>&1 | tail -n 3

if [ ! -x "${INSTALL_PREFIX}/bin/${TARGET}-gcc" ]; then
    fail "Cross-compiler build failed: ${TARGET}-gcc not found"
fi
if ! printf 'void f(void) {}\n' \
    | "${INSTALL_PREFIX}/bin/${TARGET}-gcc" -m32 -ffreestanding \
        -fleading-underscore -x c -c -o "${BUILD_DIR}/target-check.o" -; then
    fail "Installed compiler cannot produce required freestanding i386 objects"
fi

ver="$("${INSTALL_PREFIX}/bin/${TARGET}-gcc" --version 2>/dev/null)"
ver="${ver%%$'\n'*}"
ok "Cross-compiler build successful: ${ver}"
ok "Installed at ${INSTALL_PREFIX}/bin; private build directory will be removed"
