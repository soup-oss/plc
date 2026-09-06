"""
plc — Path Line Commit validator.

Core validation logic for doc-to-code reference checking.
Used by both the GitHub Actions workflow and the test suite.
"""

import re
import subprocess
import os


def find_source_files(repo_root=".", exclude=None):
    """Collect every source file in the repo."""
    if exclude is None:
        exclude = {"node_modules", ".next", ".git", "dist"}
    source_files = set()
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in exclude]
        for f in files:
            if f.endswith((".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".prisma", ".sql")):
                rel = os.path.relpath(os.path.join(root, f), repo_root)
                source_files.add(rel)
    return source_files


def validate_file(filepath, source_files):
    """
    Validate a single markdown file for plc reference integrity.

    Returns a dict with:
      - errors: list of error strings (PR-blocking)
      - untagged: list of untagged line-pinned refs
      - bare_dead: list of dead bare file references
      - bare_existing: list of bare mentions of existing files (warnings)
    """
    pinned = re.compile(
        r"([\w./\-\(\)\[\]]+\.(?:json|css|prisma|sql|tsx?|jsx?)):(\d+(?:[,-]\d+)*):([^\s\)]+)"
    )
    any_source_path = re.compile(
        r"(?:`|\()((?:src|prisma|tests|infra)/[\w./\-\(\)\[\]]+\.(?:json|css|prisma|sql|tsx?|jsx?))(?:`|\))"
    )
    existing_bare = re.compile(
        "(" + "|".join(re.escape(p) for p in sorted(source_files)) + r")(?![\w:]*:)"
    )

    errors, untagged = [], []
    bare_existing, bare_dead = [], []

    if not os.path.isfile(filepath):
        return {"errors": errors, "untagged": untagged, "bare_dead": bare_dead, "bare_existing": bare_existing}

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    in_code_block = False
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        ignore_line = "<!-- plc:ignore -->" in line

        # Pass 1: line-pinned refs
        for c, chunk in enumerate(line.split("](")):
            if c > 0 and ")" in chunk:
                chunk = chunk.rsplit(")", 1)[0]
            for match in pinned.finditer(chunk):
                path, linenum, tag = match.groups()
                path = path.lstrip("([")
                tag = tag.rstrip("`")
                if "{GIT_COMMIT_ID}" in tag:
                    continue
                if tag == "plc:ignore":
                    continue
                sha_match = re.search(r"\b[0-9a-f]{7,40}\b", tag)
                if sha_match:
                    sha = sha_match.group(0)
                    res = subprocess.run(
                        ["git", "cat-file", "-e", f"{sha}:{path}"],
                        capture_output=True,
                    )
                    if res.returncode != 0:
                        errors.append(f"{filepath}:{line_num}: {path} → {sha} (file does not exist at this commit)")
                else:
                    untagged.append(f"{filepath}:{line_num}: {path}:{linenum} (tag: {tag})")

        # Pass 2b: dead refs (file does not exist at all)
        if not ignore_line:
            for match in any_source_path.finditer(line):
                raw = match.group(1)
                if raw not in source_files:
                    bare_dead.append(f"{filepath}:{line_num}: {raw} (file does not exist)")

        # Pass 2a: bare mentions of existing files (need tags)
        if not ignore_line:
            for match in existing_bare.finditer(line):
                bare_existing.append(
                    f"{filepath}:{line_num}: {match.group(1)} (no line:tag — add path:line:{{GIT_COMMIT_ID}})"
                )

    return {
        "errors": errors,
        "untagged": untagged,
        "bare_dead": bare_dead,
        "bare_existing": bare_existing,
    }


def validate_files(filepaths, source_files):
    """
    Validate multiple markdown files.

    Returns a dict with aggregated results and an exit code.
    """
    all_errors, all_untagged = [], []
    all_bare_dead, all_bare_existing = [], []

    for filepath in filepaths:
        result = validate_file(filepath, source_files)
        all_errors.extend(result["errors"])
        all_untagged.extend(result["untagged"])
        all_bare_dead.extend(result["bare_dead"])
        all_bare_existing.extend(result["bare_existing"])

    return {
        "errors": all_errors,
        "untagged": all_untagged,
        "bare_dead": all_bare_dead,
        "bare_existing": all_bare_existing,
        "exit_code": 1 if (all_untagged or all_errors or all_bare_dead) else 0,
        "file_count": len(filepaths),
    }


def stamp_file(filepath, commit_sha):
    """
    Replace {GIT_COMMIT_ID} placeholders with the given commit SHA.
    Only stamps line-pinned references, skips code blocks and <!-- plc:ignore --> lines.
    Returns the number of replacements made.
    """
    pinned = re.compile(
        r"([\w./\-\(\)\[\]]+\.(?:json|css|prisma|sql|tsx?|jsx?)):"
        r"(\d+(?:[,-]\d+)*):\{GIT_COMMIT_ID\}"
    )

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    in_code_block = False
    hits = 0
    out = []
    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            out.append(line)
            continue
        if not in_code_block and "<!-- plc:ignore -->" not in line:
            new_line, n = pinned.subn(
                lambda m: f"{m.group(1)}:{m.group(2)}:{commit_sha}",
                line,
            )
            hits += n
            out.append(new_line)
        else:
            out.append(line)

    if hits:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(out)

    return hits
