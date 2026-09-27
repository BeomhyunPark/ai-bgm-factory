"""Run acceptance checks with kernel network denial on Linux, inherited by FFmpeg.

Usage: python scripts/offline_check.py --basetemp /absolute/new/test-directory
macOS: ordinary pytest still denies Python sockets; kernel isolation is Linux-only.
"""

import ctypes
import ctypes.util
import errno
import json
import socket
import subprocess
import sys


def deny_network():
    if sys.platform != "linux":
        raise RuntimeError("Kernel-isolated acceptance runner requires Linux + libseccomp")
    library = ctypes.util.find_library("seccomp")
    if not library:
        raise RuntimeError("libseccomp is required")
    lib = ctypes.CDLL(library)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7FFF0000)  # ALLOW except socket operations below.
    if not context:
        raise RuntimeError("seccomp initialization failed")
    try:
        for name in (b"socket", b"connect", b"sendto"):
            syscall = lib.seccomp_syscall_resolve_name(name)
            if syscall < 0 or lib.seccomp_rule_add(context, 0x00050000 | errno.EPERM, syscall, 0):
                raise RuntimeError("seccomp rule installation failed")
        if lib.seccomp_load(context):
            raise RuntimeError("seccomp activation failed")
    finally:
        lib.seccomp_release(context)
    try:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        return
    raise RuntimeError("Network isolation was not effective")


if __name__ == "__main__":
    deny_network()
    print(json.dumps({"schema_version": "1.0.0", "kernel_network_denied": True}), flush=True)
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", *sys.argv[1:]])
    )
