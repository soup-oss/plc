# Mixed Scenarios

This file has a mix of valid, invalid, and special cases.

Valid reference: [src/services/auth.ts:88-96](src/services/auth.ts:88-96:abc1234).

Untagged reference (bad tag): [src/lib/parser.ts:10-20:notatag](src/lib/parser.ts:10-20:notatag).

Dead reference: [src/nonexistent/module.ts:5:abc1234](src/nonexistent/module.ts:5:abc1234).

Code block (should skip):

```python
# This references src/dead/code.py but it's in a code block
import src.dead.code
```

Ignored line: `src/also-ignored.ts` <!-- plc:ignore -->.

Whole-file valid: [src/app/page.tsx:0](src/app/page.tsx:0:abc1234).
