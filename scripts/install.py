#!/usr/bin/env python3
"""Install the standalone skill without replacing an existing local skill."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "standalone": "etf-comment-drafts-v2",
}


def install(selection, destination):
    names = list(SKILLS.values()) if selection == "all" else [SKILLS[selection]]
    for name in names:
        source = ROOT / "skills" / name
        if not (source / "SKILL.md").is_file():
            raise ValueError("Skill not found: " + name)
        if (destination / name).exists() or (destination / name).is_symlink():
            raise ValueError("Existing skill preserved: " + str(destination / name)
                             + ". Back it up or choose another --dest before installing.")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".etf-skills-", dir=str(destination)) as tmp:
        staging = Path(tmp)
        for name in names:
            shutil.copytree(ROOT / "skills" / name, staging / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        for name in names:
            (staging / name).rename(destination / name)
            print("Installed " + str(destination / name))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variant", choices=["standalone", "all"], nargs="?", default="standalone")
    codex_base = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    parser.add_argument("--dest", type=Path, default=codex_base / "skills",
                        help="Skill directory; default: CODEX_HOME/skills or ~/.codex/skills")
    args = parser.parse_args()
    try:
        install(args.variant, args.dest.expanduser().resolve())
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
