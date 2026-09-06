# plc — Path Line Commit

Every line-pinned code reference in your docs should be verifiable. `plc` makes that enforceable. It's a governance primitive for agentic workflows — a drop-in, model-agnostic rule that keeps every other agent primitive (tools, actors, orchestration) working against references that are actually true.

## What it is

A rule file and two GitHub Actions workflows that ensure every code reference in `docs/` carries a commit tag:

```
path:line:commit
```

- **New code** (introduced in the same PR) uses `{GIT_COMMIT_ID}` — CI stamps it with the merge commit SHA on merge.
- **Pre-existing code** uses the actual blame SHA — the reference is true the moment it's written.

## What it catches

- References to files that no longer exist at that commit.
- Hallucinated paths and line numbers.
- Untagged references that have no anchor to any commit.

## Files

| File | Purpose |
|------|---------|
| `RULES.md` | The rule file defining the `path:line:commit` format |
| `.github/workflows/validate-doc-tags.yml` | CI validation — blocks PRs with untagged or broken references |
| `.github/workflows/update-doc-tags.yml` | Merge stamping — replaces `{GIT_COMMIT_ID}` with the merge commit SHA |

## Adoption

1. Copy `RULES.md` into your repo root (rename to `CODING.md` or keep as-is).
2. Copy both workflow files into `.github/workflows/`.
3. Set the `PLC_TARGET_BRANCH` repository variable to your target branch (defaults to `development`).
4. Update the `branches:` trigger in each workflow file to match your target branch.
5. Start tagging your doc-to-code references.

See the full writeup — [Part 1: The Essay](https://heysoup.co/notes-hygiene-in-agentic-workflows) and [Part 2: A Practical Guide](https://heysoup.co/notes-hygiene-in-agentic-workflows-a-practical-guide) — for the reasoning behind this system.

## License

MIT
