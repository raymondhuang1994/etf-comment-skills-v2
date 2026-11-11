#!/usr/bin/env python3
"""Check installability, self-contained references, and public-source hygiene."""
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("etf-comment-drafts-v2",)
BLOCKED_DIRS = {"private", "local", "inputs", "outputs", ".venv", "__pycache__"}
BLOCKED_SUFFIXES = {".xlsx", ".xls", ".xlsm", ".xlsb", ".csv", ".tsv", ".jsonl", ".docx", ".jpg", ".jpeg", ".png", ".webp", ".pdf", ".log", ".pyc"}
SECRET_PATTERNS = (
    r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{40,}",
    r"sk-(?:proj-)?[A-Za-z0-9_-]{30,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"/Users/[A-Za-z0-9._-]+/",
    r"/tmp/codex-remote-attachments/[0-9a-f-]{36}/",
)


def main():
    errors = []
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for relative in filter(None, tracked):
        path = ROOT / relative
        if BLOCKED_DIRS.intersection(path.relative_to(ROOT).parts) or path.suffix.lower() in BLOCKED_SUFFIXES:
            errors.append("Private or generated artifact is tracked: " + relative)
        if path.name.startswith(".env") and path.name != ".env.example":
            errors.append("Environment file is tracked: " + relative)
        if path.is_symlink():
            errors.append("Public source must not contain a symlink: " + relative)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            errors.append("Unexpected binary or missing tracked file: " + relative)
            continue
        if any(re.search(pattern, text) for pattern in SECRET_PATTERNS):
            errors.append("Possible secret or machine-local path: " + relative)
        if path.suffix in {".yaml", ".yml"}:
            try:
                yaml.safe_load(text)
            except yaml.YAMLError:
                errors.append("Invalid YAML: " + relative)

    for name in SKILLS:
        folder = ROOT / "skills" / name
        entry = folder / "SKILL.md"
        try:
            text = entry.read_text(encoding="utf-8")
            match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
            front = yaml.safe_load(match.group(1)) if match else {}
            if front.get("name") != name or not isinstance(front.get("description"), str):
                errors.append("Invalid skill frontmatter: " + name)
            ui = yaml.safe_load((folder / "agents" / "openai.yaml").read_text())
            interface = ui["interface"]
            if not 25 <= len(interface["short_description"]) <= 64:
                errors.append("UI short_description length must be 25–64: " + name)
            if "$" + name not in interface["default_prompt"]:
                errors.append("UI prompt must invoke its own skill: " + name)
            for doc in folder.rglob("*.md"):
                for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", doc.read_text()):
                    target = link.split("#", 1)[0]
                    if not target or "://" in target or target.startswith("mailto:"):
                        continue
                    resolved = (doc.parent / target).resolve()
                    if folder.resolve() not in resolved.parents or not resolved.exists():
                        errors.append("Broken or external skill reference: " + str(doc.relative_to(ROOT)) + " -> " + link)
        except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
            errors.append("Invalid skill " + name + ": " + str(exc))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Validated the self-contained skill, YAML, links, and tracked-file hygiene.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
