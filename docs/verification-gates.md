# Verification Gates

Use these levels when reporting verification under `C:\MyProject`.

## Levels

- `required`: Must pass before the task can be called complete.
- `advisory`: Useful signal, but not required for this task's scope.
- `blocked-by-external`: Cannot run because an external dependency is missing
  or intentionally unavailable, such as credentials, network access, provider
  quota, or hardware.
- `not-applicable`: Does not apply to this task.

## Report Format

```text
Gate:
Level:
Command or check:
Result:
Evidence:
Notes:
```

## Common Required Gates

- Code change: unit tests or the closest project check command.
- UI change: desktop and mobile render check for the affected route.
- Content change: content verifier plus build when the project provides both.
- Security-sensitive change: secret scan of changed files and explicit
  authentication/authorization check.
- Deployment change: service restart or dry-run, public/local health check, and
  rollback note.

Do not claim a broad gate is green from a narrow command. If the command does
not cover the risk, mark the uncovered part as advisory, blocked, or missing.

