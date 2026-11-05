#!/usr/bin/env python3
"""Build reproducible ZIPs from Git-tracked skill files only."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("etf-comment-drafts-v2",)


def build(destination):
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "skills/"], cwd=ROOT
    ).decode().split("\0")
    destination.mkdir(parents=True, exist_ok=True)
    sums = []
    for name in NAMES:
        prefix = "skills/" + name + "/"
        files = sorted(p for p in tracked if p.startswith(prefix))
        if prefix + "SKILL.md" not in files:
            raise ValueError("Stage or commit the complete skill before packaging: " + name)
        path = destination / (name + ".zip")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in files:
                source = ROOT / relative
                if source.is_symlink():
                    raise ValueError("Do not package symlinks: " + relative)
                info = zipfile.ZipInfo(relative.removeprefix("skills/"), (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, source.read_bytes())
            license_info = zipfile.ZipInfo(name + "/LICENSE", (2026, 1, 1, 0, 0, 0))
            license_info.compress_type = zipfile.ZIP_DEFLATED
            license_info.external_attr = 0o100644 << 16
            archive.writestr(license_info, (ROOT / "LICENSE").read_bytes())
        sums.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name)
        print(str(path))
    (destination / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=ROOT / "dist")
    build(parser.parse_args().dest.resolve())
