#!/usr/bin/env python3
"""Every link in a tracked markdown file resolves. Run from the repository root.

A link to a file that is not in the tree is a closed door: the reader stops
there. This gate walks every tracked markdown file and resolves every link
target it can check.

  relative target   resolved against the file's own directory
  /root target      a page on soyrocoto.com, which is Rocoto-Labs/site and not
                    this tree — so it never resolves here and is reported.
                    Write it as a full https:// URL
  http, mailto, tel, data, bare #anchor   left alone

Misses print as "file:line -> target"; the gate exits 1 when there is one.
"""
import re
import os
import sys
from pathlib import Path

LINK = re.compile(r"\]\(\s*(<[^>]*>|[^()\s]*(?:\([^()\s]*\)[^()\s]*)*)")
SKIP = ("http://", "https://", "mailto:", "tel:", "#", "data:")


def targets(line):
    """Every link target on one line, unwrapped and stripped of its title."""
    for raw in LINK.findall(line):
        target = raw.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split(" ", 1)[0].strip()
        if target and not target.lower().startswith(SKIP):
            yield target


def resolves(source, target):
    path = target.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return True
    if path.startswith("/"):
        # An absolute target is a soyrocoto.com route, and the site left this repository on
        # 2026-09-07 (decision record 0010). Resolving it against the filesystem root would ask
        # about the machine rather than the tree, so it is a miss and the writer names the URL.
        return False
    return (source.parent / path).exists()


def main():
    files = []
    for base, directories, names in os.walk("."):
        directories[:] = [name for name in directories if name not in {".venv", "node_modules", ".git", "__pycache__", ".pytest_cache", "dist"} and not name.startswith("dist-")]
        files.extend(str(Path(base) / name) for name in names if name.endswith(".md"))
    misses = 0
    for name in files:
        source = Path(name)
        text = source.read_text(encoding="utf-8", errors="replace")
        fenced = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith((chr(96)*3, "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            for target in targets(line):
                if not resolves(source, target):
                    print(f"{name}:{number} -> {target}")
                    misses += 1
    print(f"link-gate: {misses} broken link(s) in {len(files)} markdown files")
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
