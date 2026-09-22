#!/usr/bin/env python3
"""Show CachyOS's reboot recommendation until the next boot, without root/hooks."""

import fnmatch
from pathlib import Path
import re
import sys


def reboot_reasons(root: Path = Path("/")) -> list[str]:
    """Read boot and package state; root also allows isolated fixture checks."""
    for marker in ("run/reboot-required", "var/run/reboot-required"):
        if (root / marker).exists():
            return ["system reboot-required flag"]

    try:
        boot = int(re.search(r"^btime (\d+)$", (root / "proc/stat").read_text(), re.M)[1])
        hook = (root / "usr/share/libalpm/hooks/cachyos-reboot-required.hook").read_text()
        version = (root / "proc/version").read_text()
        mounts = (root / "proc/mounts").read_text()
    except (OSError, ValueError, TypeError):
        return []  # No CachyOS detector on this host (e.g. macOS).

    targets = re.findall(r"^Target\s*=\s*(\S+)", hook, re.M)
    kernel_match = re.search(r"\(([^()@]+)@[^()]+\)", version)
    kernel = kernel_match[1] if kernel_match else ""
    filesystems = {line.split()[2] for line in mounts.splitlines() if len(line.split()) >= 3}
    fs_packages = {"btrfs-progs": "btrfs", "xfsprogs": "xfs", "e2fsprogs": "ext4"}
    reasons = set()

    # The local database survives log rotation. INSTALLDATE changes on upgrades
    # and reinstalls too; a core-package install after boot is conservatively
    # treated as a recommendation, just like an upgrade.
    for desc in (root / "var/lib/pacman/local").glob("*/desc"):
        # Most packages cannot match the hook; avoid reading their metadata.
        if not any(fnmatch.fnmatchcase(desc.parent.name, target + "-*") for target in targets):
            continue
        try:
            fields = desc.read_text().split("\n\n")
            metadata = dict(field.split("\n", 1) for field in fields if "\n" in field)
            package = metadata["%NAME%"].strip()
            installed = int(metadata["%INSTALLDATE%"])
        except (OSError, KeyError, ValueError):
            continue
        if installed <= boot or not any(fnmatch.fnmatchcase(package, target) for target in targets):
            continue
        if package in fs_packages and fs_packages[package] not in filesystems:
            continue
        if package.startswith("linux-cachyos") and "-nvidia" in package:
            if not kernel.startswith("linux-cachyos"):
                continue
        elif package == "linux" or (package.startswith("linux-") and not package.startswith("linux-firmware")):
            # Ignore alternate kernels and headers, even though the hook has
            # broad linux-cachyos* triggers. The running kernel is what matters.
            if package != kernel:
                continue
        if package == "nvidia" and kernel != "linux":
            continue
        if package == "nvidia-lts" and kernel != "linux-lts":
            continue
        reasons.add(package)

    return sorted(reasons)


if __name__ == "__main__":
    reasons = reboot_reasons()
    if "--explain" in sys.argv:
        print("Reboot recommended: " + ", ".join(reasons) if reasons else "No reboot recommendation.")
    elif reasons:
        # Push/pop style keeps the surrounding One Dark status segments intact.
        print("#[push-default,fg=#e5c07b,bold] REBOOT #[pop-default]", end="")
