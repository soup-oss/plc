# References Inside Code Blocks

These should be skipped entirely.

```typescript
// This is just an example, not a real claim
const auth = require('src/services/auth.ts:42');
```

```markdown
Reference to [src/lib/utils.ts:10-20](src/lib/utils.ts:10-20:abc1234) in a code block.
```

The real reference is below:

The handler lives at [src/services/handler.ts:42](src/services/handler.ts:42:abc1234).
