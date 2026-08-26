#!/bin/bash
# Verify host prerequisites and install/discover the project toolchain.
set -euo pipefail

umask 077

CROSS_PREFIX="${1:-${HOME}/.local/cross}"
TARGET="x86_64-elf"
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
UNAME_S="$(uname -s)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/linux001-setup.XXXXXXXX")"

cleanup() {
    rm -rf -- "${WORK_DIR}"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

ESC='\033'; CR="${ESC}[0m"; CB="${ESC}[1m"
CG="${ESC}[38;5;83m"; CY="${ESC}[38;5;221m"; CRD="${ESC}[38;5;203m"
CGY="${ESC}[38;5;240m"; CWH="${ESC}[38;5;255m"
G_OK='✓'; G_NO='✗'; G_ARR='▶'; G_INF='◢'; G_DOT='•'

step() { printf "  ${CGY}${G_DOT}${CR} %s\n" "$1"; }
ok() { printf "  ${CG}${G_OK}${CR} ${CGY}%s${CR}\n" "$1"; }
warn() { printf "  ${CY}${G_INF}${CR} %s\n" "$1"; }
fail() { printf "  ${CRD}${G_NO}${CR} ${CRD}%s${CR}\n" "$1" >&2; exit 1; }

if [ "${UNAME_S}" != "Linux" ]; then
    fail "bEMU requires Linux KVM; this setup supports Linux hosts only"
fi

cross_toolchain_usable() {
    local prefix="$1/bin/${TARGET}-"
    local tool
    for tool in gcc as ld objcopy objdump nm; do
        [ -x "${prefix}${tool}" ] || return 1
    done
    [ "$("${prefix}gcc" -dumpmachine 2>/dev/null)" = "${TARGET}" ] || return 1
    printf 'void f(void) {}\n' \
        | "${prefix}gcc" -m32 -ffreestanding -fleading-underscore \
            -x c -c -o "${WORK_DIR}/cross-i386.o" - >/dev/null 2>&1
}

if [ "${EUID}" -eq 0 ]; then
    SUDO=()
elif command -v sudo >/dev/null 2>&1; then
    SUDO=(sudo)
else
    SUDO=()
fi

host_libraries_available() {
    printf '%s\n' \
        '#include <gmp.h>' \
        '#include <mpfr.h>' \
        '#include <mpc.h>' \
        '#include <zlib.h>' \
        'int main(void) { mpz_t z; mpfr_t r; mpc_t c; z_stream s = {0}; mpz_init(z); mpfr_init2(r, 32); mpc_init2(c, 32); deflateEnd(&s); mpc_clear(c); mpfr_clear(r); mpz_clear(z); return 0; }' \
        | gcc -x c - -o "${WORK_DIR}/host-libraries" -lgmp -lmpfr -lmpc -lz \
            >/dev/null 2>&1
}

printf "\n  ${CB}${CWH}linux-0.01-still-runs toolchain setup${CR}\n\n"
step "Step 1/3: Checking host prerequisites for ${UNAME_S}..."

required_host_tools=(nasm python3 git make gcc g++ as ld objcopy objdump nm patch tar xz)
if [ "${UNAME_S}" != "Darwin" ]; then
    required_host_tools+=(bison flex makeinfo sha256sum fsck.minix)
fi
missing_host_tools=()
for tool in "${required_host_tools[@]}"; do
    if command -v "${tool}" >/dev/null 2>&1; then
        printf "  ${CG}${G_OK}${CR} %-22s\n" "${tool}"
    else
        printf "  ${CRD}${G_NO}${CR} %-22s ${CRD}MISSING${CR}\n" "${tool}"
        missing_host_tools+=("${tool}")
    fi
done

need_packages=0
if [ "${#missing_host_tools[@]}" -ne 0 ]; then
    need_packages=1
fi
if [ "${UNAME_S}" != "Darwin" ] && ! host_libraries_available; then
    warn "GMP, MPFR, MPC, or zlib development files are missing"
    need_packages=1
fi

if [ "${need_packages}" -eq 1 ]; then
    if [ "${UNAME_S}" != "Darwin" ] && [ "${EUID}" -ne 0 ] && [ "${#SUDO[@]}" -eq 0 ]; then
        fail "Package installation requires root or sudo"
    fi
    if [ "${UNAME_S}" = "Darwin" ]; then
        command -v brew >/dev/null 2>&1 || fail "Homebrew not found: https://brew.sh"
        step "Installing macOS prerequisites with Homebrew..."
        brew install x86_64-elf-gcc nasm xz git
        CROSS_PREFIX="$(brew --prefix x86_64-elf-gcc)"
    elif command -v apt-get >/dev/null 2>&1; then
        step "Installing Debian-family prerequisites..."
        "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get update
        "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            build-essential bison flex libgmp-dev libmpfr-dev libmpc-dev \
            texinfo zlib1g-dev wget git nasm python3 mtools xz-utils ca-certificates \
            util-linux
    elif command -v pacman >/dev/null 2>&1; then
        step "Installing Arch Linux prerequisites..."
        "${SUDO[@]}" pacman -Sy --noconfirm base-devel bison flex gmp mpfr mpc \
            texinfo zlib wget git nasm python3 mtools xz ca-certificates util-linux
    elif command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1; then
        step "Installing Fedora-family prerequisites..."
        if command -v dnf >/dev/null 2>&1; then
            package_manager="$(command -v dnf)"
        else
            package_manager="$(command -v yum)"
        fi
        "${SUDO[@]}" "${package_manager}" install -y gcc gcc-c++ make bison flex \
            gmp-devel mpfr-devel libmpc-devel texinfo zlib-devel wget git nasm \
            python3 mtools xz ca-certificates util-linux
    else
        fail "Unsupported package manager; install: ${missing_host_tools[*]} GMP MPFR MPC zlib development files"
    fi
fi

for tool in "${required_host_tools[@]}"; do
    command -v "${tool}" >/dev/null 2>&1 || fail "Required host tool still missing: ${tool}"
done
if [ "${UNAME_S}" != "Darwin" ]; then
    host_libraries_available || fail "Required GMP, MPFR, MPC, or zlib development files are unavailable"
fi
ok "Host prerequisites verified"

step "Step 2/3: Checking for ${TARGET} cross-compiler..."
FOUND_CROSS=0
NATIVE_TOOLCHAIN=0
for search_prefix in "${CROSS_PREFIX}" "${HOME}/.local/cross" /usr/local/cross /opt/cross; do
    if cross_toolchain_usable "${search_prefix}"; then
        CROSS_PREFIX="${search_prefix}"
        FOUND_CROSS=1
        break
    fi
done
if [ "${FOUND_CROSS}" -eq 0 ] && command -v "${TARGET}-gcc" >/dev/null 2>&1; then
    gcc_path="$(command -v "${TARGET}-gcc")"
    candidate_prefix="$(dirname "$(dirname "${gcc_path}")")"
    if cross_toolchain_usable "${candidate_prefix}"; then
        CROSS_PREFIX="${candidate_prefix}"
        FOUND_CROSS=1
    fi
fi

if [ "${FOUND_CROSS}" -eq 1 ]; then
    ver="$("${CROSS_PREFIX}/bin/${TARGET}-gcc" --version 2>/dev/null)"
    ver="${ver%%$'\n'*}"
    ok "${TARGET}-gcc found: ${ver} (prefix: ${CROSS_PREFIX})"
elif [ "${UNAME_S}" = "Linux" ] && \
    printf 'void f(void) {}\n' | gcc -m32 -ffreestanding -fleading-underscore \
        -x c -c -o "${WORK_DIR}/native-i386.o" - >/dev/null 2>&1; then
    NATIVE_TOOLCHAIN=1
    ok "Native GCC supports the required freestanding i386 target"
else
    step "Cross-compiler not found; building pinned sources into ${CROSS_PREFIX}..."
    bash "${PROJ_DIR}/tools/build-cross-compiler.sh" "${CROSS_PREFIX}"
    [ -x "${CROSS_PREFIX}/bin/${TARGET}-gcc" ] || fail "Cross-compiler build failed"
fi

step "Step 3/3: Verifying toolchain binaries..."
if [ "${NATIVE_TOOLCHAIN}" -eq 0 ]; then
    export PATH="${CROSS_PREFIX}/bin:${PATH}"
    toolchain_tools=("${TARGET}-gcc" "${TARGET}-as" "${TARGET}-ld" \
        "${TARGET}-objcopy" "${TARGET}-objdump" "${TARGET}-nm")
else
    toolchain_tools=(gcc as ld objcopy objdump nm)
fi
for tool in "${toolchain_tools[@]}" nasm python3; do
    command -v "${tool}" >/dev/null 2>&1 || fail "Required tool missing: ${tool}"
    ver="$("${tool}" --version 2>/dev/null)"
    ver="${ver%%$'\n'*}"
    ver="${ver:0:60}"
    printf "  ${CG}${G_OK}${CR} %-22s ${CGY}%s${CR}\n" "${tool}" "${ver}"
done

if [ "${UNAME_S}" = "Linux" ] && [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    ok "/dev/kvm is available"
else
    warn "/dev/kvm unavailable; builds work, but bEMU runtime tests cannot run"
fi

mkdir -p -- "${PROJ_DIR}/build"
if [ "${NATIVE_TOOLCHAIN}" -eq 1 ]; then
    rm -f -- "${PROJ_DIR}/build/.cross_prefix"
else
    printf '%s\n' "${CROSS_PREFIX}" > "${PROJ_DIR}/build/.cross_prefix"
fi

printf "\n  ${CB}${CG}${G_OK}${CR} ${CGY}Toolchain setup complete${CR}\n\n"
if [ "${UNAME_S}" != "Darwin" ] && [ "${NATIVE_TOOLCHAIN}" -eq 0 ]; then
    case ":${PATH}:" in
        *":${CROSS_PREFIX}/bin:"*) ;;
        *)
            printf "  ${CY}${G_ARR}${CR} Add to PATH: ${CWH}export PATH=\"%s/bin:\$PATH\"${CR}\n\n" \
                "${CROSS_PREFIX}"
            ;;
    esac
fi
printf "  ${CGY}Next: ${CB}make all${CR} or ${CB}make boom${CR}\n\n"
