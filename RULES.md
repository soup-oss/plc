# Path Line Commit (plc)

Documentation code references must be verifiable. Every line-pinned code reference in `docs/` carries a commit tag that traces it to its origin.

## Format

```
path:line:<tag>
```

Where:

- **path** — repo-root-relative path (e.g. `src/app/actions/foo.ts`, not `../../src/app/actions/foo.ts`)
- **line** — line number (`N`), range (`A-B`), comma-list (`A,B-C`), or `0` for whole-file references
- **tag** — one of:
  - `{GIT_COMMIT_ID}` — new code introduced in the same PR. CI replaces this with the merge commit SHA on merge.
  - `<sha>` — pre-existing code. Use the actual blame SHA (short hex, 7-40 chars). Look it up via:
    ```bash
    git log -L <start>,<end>:<path> --format='%h' -1 -s
    ```

## Examples

New code (introduced in this PR):
```
src/services/auth.ts:88-96:{GIT_COMMIT_ID}
```

Pre-existing code:
```
src/services/auth.ts:88-96:abc1234
```

Whole-file reference:
```
src/app/actions/foo.ts:0:{GIT_COMMIT_ID}
```

## Rules

1. Full repo-root-relative path — required so `git cat-file -e <sha>:<path>` works.
2. Bracket paths (e.g. `[externalOrderId]`) and Next.js route groups (e.g. `(dashboard)`) are allowed in the path.
3. Line spec: `N`, range `A-B`, or comma-list `A,B-C` (no spaces). Tag appended directly after.
4. Whole-file references use line spec `0` and **do** carry a tag.
5. When editing an existing tagged reference, re-derive the tag: `{GIT_COMMIT_ID}` if the code is new to this PR, or a fresh blame SHA if pre-existing.
6. References inside code blocks (``` fenced) are skipped — they are examples, not claims.
7. Lines containing `<!-- plc:ignore -->` are exempt from bare-ref checks.

## Bare references

Beyond line-pinned triples, the validator also checks for bare source file mentions — paths to files in `src/`, `prisma/`, `tests/`, `infra/` that appear without a `line:tag`.

- If the file **exists** in the repo → **warning**. The mention is untagged. Add a `path:line:{GIT_COMMIT_ID}` to make it verifiable.
- If the file **does not exist** → **error**. The reference is dead. Fix or remove it.

Bare-ref checks only apply outside code blocks and on lines without `<!-- plc:ignore -->`.

## Validation

PRs fail validation if:

- A line-pinned code reference in `docs/` (including `:0:` whole-file refs) is missing its tag.
- Any hex SHA does not resolve (`git cat-file -e <sha>:<path>` fails — catches hallucinations and typos).
- A bare reference points to a file that does not exist in the repo.

The validator only checks doc files changed in the PR (diff-based), not the entire `docs/` tree.

See `.github/workflows/validate-doc-tags.yml`.

## Stamping

On PR merge, `.github/workflows/update-doc-tags.yml` replaces all `{GIT_COMMIT_ID}` placeholders in `docs/` with the merge commit SHA. Only `docs/` is rewritten — this rule file documents the literal format and must never be rewritten.

After stamping, the workflow re-validates the changed docs to ensure the SHA replacement itself didn't introduce problems.

## Local validation

To validate locally before pushing, run the validator from `validate-doc-tags.yml` against `docs/` in the repo root. The Python script checks every line-pinned reference for a tag and verifies that all hex SHAs resolve.

## Configuration

The target branch defaults to `development`. To change it, set the `PLC_TARGET_BRANCH` repository variable in GitHub (Settings → Secrets and variables → Actions → Variables) and update the `branches:` trigger in both workflow files to match.

The `branches:` trigger in GitHub Actions does not support variable expressions, so it must be updated manually when changing the target branch.
