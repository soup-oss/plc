# PLC Ignore Directive

These lines have `<!-- plc:ignore -->` and should be exempt from bare-ref checks.

Mention of `src/nonexistent/file.ts` <!-- plc:ignore -->.

Another one: see `src/also-nonexistent.ts` <!-- plc:ignore -->.

But this one is NOT ignored and will warn: `src/config/app.ts`.
