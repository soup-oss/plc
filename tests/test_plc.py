#!/usr/bin/env python3
"""
Test suite for plc - Path Line Commit validator.

Creates a temporary git repo with source files, commits them to get real SHAs,
then runs the validator against doc fixtures that reference those commits.
"""

import os
import sys
import shutil
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plc


def run(cmd, cwd=None):
    subprocess.run(cmd, shell=True, capture_output=True, cwd=cwd, check=True)


def setup_test_repo():
    repo = tempfile.mkdtemp(prefix="plc-test-")
    run("git init", cwd=repo)
    run("git config user.email 'test@test.com'", cwd=repo)
    run("git config user.name 'Test'", cwd=repo)

    dirs = ["src/services", "src/lib", "src/app/actions", "src/config", "src/types"]
    for d in dirs:
        os.makedirs(os.path.join(repo, d), exist_ok=True)

    files = {
        "src/services/auth.ts": "export function auth() {}\n" * 100,
        "src/services/handler.ts": "export function handler() {}\n" * 50,
        "src/lib/utils.ts": "export function utils() {}\n" * 30,
        "src/lib/parser.ts": "export function parse() {}\n" * 30,
        "src/app/page.tsx": "export default function Page() {}\n",
        "src/app/actions/foo.ts": "export function foo() {}\n",
        "src/config/app.ts": "export const config = {};\n",
        "src/types/models.ts": "export interface Model {}\n",
    }

    for path, content in files.items():
        with open(os.path.join(repo, path), "w") as f:
            f.write(content)

    run("git add .", cwd=repo)
    run("git commit -m 'initial'", cwd=repo)

    sha_map = {}
    for path in files:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", path],
            capture_output=True, text=True, cwd=repo
        )
        sha_map[path] = result.stdout.strip()

    return repo, sha_map


def cleanup(repo):
    shutil.rmtree(repo, ignore_errors=True)


class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            print(f"  PASS: {name}")
        else:
            self.failed += 1
            msg = f"  FAIL: {name}"
            if detail:
                msg += f" -- {detail}"
            self.errors.append(msg)
            print(msg)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print("\nFailures:")
            for e in self.errors:
                print(f"  {e}")
        print(f"{'='*60}")
        return 0 if self.failed == 0 else 1


def test_valid_tagged(sha_map, results):
    print("\n[test] Valid tagged references")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "valid-tagged.md")
    with open(fixture, "r") as f:
        content = f.read()
    content = content.replace("abc1234", sha_map["src/services/auth.ts"])
    tmp = os.path.join("tests", "fixtures", "_valid_tagged_tmp.md")
    with open(tmp, "w") as f:
        f.write(content)

    result = plc.validate_file(tmp, source_files)
    os.remove(tmp)

    results.check("no errors", len(result["errors"]) == 0, str(result["errors"]))
    results.check("no untagged", len(result["untagged"]) == 0, str(result["untagged"]))
    results.check("no bare_dead", len(result["bare_dead"]) == 0, str(result["bare_dead"]))


def test_untagged_refs(results):
    print("\n[test] Untagged references")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "untagged-refs.md")
    result = plc.validate_file(fixture, source_files)

    results.check("has untagged", len(result["untagged"]) > 0, f"got {len(result['untagged'])}")
    results.check("correct count (6 — each link matches in text + target)", len(result["untagged"]) == 6, f"got {len(result['untagged'])}")


def test_invalid_sha(results):
    print("\n[test] Invalid SHA references")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "invalid-sha.md")
    result = plc.validate_file(fixture, source_files)

    results.check("has errors", len(result["errors"]) > 0, f"got {len(result['errors'])}")
    results.check("correct count (2)", len(result["errors"]) == 2, f"got {len(result['errors'])}")


def test_dead_refs(results):
    print("\n[test] Dead file references")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "dead-refs.md")
    result = plc.validate_file(fixture, source_files)

    results.check("has bare_dead", len(result["bare_dead"]) > 0, f"got {len(result['bare_dead'])}")


def test_bare_existing(results):
    print("\n[test] Bare existing file references")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "bare-existing.md")
    result = plc.validate_file(fixture, source_files)

    results.check("has bare_existing", len(result["bare_existing"]) > 0, f"got {len(result['bare_existing'])}")
    results.check("no errors", len(result["errors"]) == 0, str(result["errors"]))
    results.check("no bare_dead", len(result["bare_dead"]) == 0, str(result["bare_dead"]))


def test_code_blocks(results):
    print("\n[test] Code block skipping")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "code-blocks.md")
    result = plc.validate_file(fixture, source_files)

    results.check("code block refs skipped (no untagged)", len(result["untagged"]) == 0, f"untagged: {result['untagged']}")
    results.check("code block dead refs skipped (no bare_dead)", len(result["bare_dead"]) == 0, f"bare_dead: {result['bare_dead']}")


def test_plc_ignore(results):
    print("\n[test] plc:ignore directive")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "plc-ignore.md")
    result = plc.validate_file(fixture, source_files)

    results.check("ignored lines have no bare_existing", len(result["bare_existing"]) <= 1,
                  f"bare_existing: {result['bare_existing']}")


def test_mixed(sha_map, results):
    print("\n[test] Mixed scenarios")
    source_files = plc.find_source_files(".")
    fixture = os.path.join("tests", "fixtures", "mixed.md")
    with open(fixture, "r") as f:
        content = f.read()
    content = content.replace("abc1234", sha_map["src/services/auth.ts"])
    tmp = os.path.join("tests", "fixtures", "_mixed_tmp.md")
    with open(tmp, "w") as f:
        f.write(content)

    result = plc.validate_file(tmp, source_files)
    os.remove(tmp)

    results.check("untagged found", len(result["untagged"]) > 0, f"got {len(result['untagged'])}")
    results.check("no code block refs leaked", not any("dead/code.py" in e for e in result["bare_dead"]),
                  f"bare_dead: {result['bare_dead']}")


def test_stamp(tmp_path):
    print("\n[test] Stamping {GIT_COMMIT_ID}")
    test_file = os.path.join(str(tmp_path), "test.md")
    with open(test_file, "w") as f:
        f.write("Ref: src/foo.ts:10:{GIT_COMMIT_ID}\nAnother: src/bar.ts:20:{GIT_COMMIT_ID}\n")

    count = plc.stamp_file(test_file, "abc1234")
    with open(test_file, "r") as f:
        content = f.read()

    results = Results()
    results.check("stamp count is 2", count == 2, f"got {count}")
    results.check("SHA replaced", "abc1234" in content and "{GIT_COMMIT_ID}" not in content, content)
    return results


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(os.path.join(".."))

    print("Setting up test git repo...")
    repo, sha_map = setup_test_repo()

    # Override source_files to come from test repo
    old_cwd = os.getcwd()
    os.chdir(repo)

    results = Results()

    try:
        # Copy fixtures into test repo
        fixtures_src = os.path.join(old_cwd, "tests", "fixtures")
        fixtures_dst = os.path.join(repo, "tests", "fixtures")
        os.makedirs(fixtures_dst, exist_ok=True)
        for f in os.listdir(fixtures_src):
            if f.endswith(".md") and not f.startswith("_"):
                shutil.copy2(os.path.join(fixtures_src, f), os.path.join(fixtures_dst, f))

        test_valid_tagged(sha_map, results)
        test_untagged_refs(results)
        test_invalid_sha(results)
        test_dead_refs(results)
        test_bare_existing(results)
        test_code_blocks(results)
        test_plc_ignore(results)
        test_mixed(sha_map, results)

        os.chdir(old_cwd)
        stamp_results = test_stamp(tempfile.mkdtemp())
        results.passed += stamp_results.passed
        results.failed += stamp_results.failed
        results.errors.extend(stamp_results.errors)

    finally:
        os.chdir(old_cwd)
        cleanup(repo)

    return results.summary()


if __name__ == "__main__":
    sys.exit(main())
