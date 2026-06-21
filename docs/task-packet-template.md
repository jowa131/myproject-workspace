# Task Packet Template

Use this for non-trivial feature work, fixes, investigations, deployment work,
and handoffs under `C:\MyProject`.

```text
Task:
Owner project:
Goal:
Non-goals:
User-visible behavior:
Files allowed:
Files excluded:
Required context:
Acceptance criteria:
Verification commands:
Verification gates:
Security/privacy notes:
Generated artifacts:
Git dirty-state note:
Handoff location:
```

## Rules

- Keep the packet small enough that one thread can finish or hand off cleanly.
- Prefer exact file paths over broad directories for `Files allowed`.
- List secrets, credentials, personal data, raw photos, tokens, and generated
  output in `Files excluded` when relevant.
- Verification gates must use the levels from `verification-gates.md`.
- Handoff must include changed files, commands run, results, unresolved risk,
  and the next task packet when work remains.

