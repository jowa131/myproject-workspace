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

Before the first command, add:

```text
Change class:
Observed change surface:
Risk boundary:
Expected decision value:
Estimated cost: <test count / repositories or builds / agents / output>
Escalation trigger:
```

## Decision Order

1. Determine whether any relevant source, generated data, rendered artifact,
   configuration, deployment, security, or real-order boundary changed.
2. Select the first matching row in the matrix below.
3. Apply project-specific required gates only to that changed surface.
4. Run the smallest command that can decide the stated risk.
5. Escalate only after recording a concrete remaining risk or when the user
   explicitly requests review/PR handoff coverage.

An available check is not an applicable check. A later broad gate does not
override an earlier no-change short circuit.

## Change-aware Matrix

| Class | Entry condition | Required evidence | Prohibited by default | Escalation trigger |
| --- | --- | --- | --- | --- |
| 0. No change | No relevant source/artifact changed; for a heartbeat, no current source, latest is valid, and mirror hashes match | Date/state/source-presence check and hashes only; then stop | Regeneration, tests, builds, browser QA, subagents | A mismatch, invalid/stale latest artifact, or newly available source |
| 1. Generated data only | Data values changed without generator, template, or UI code changes | Parse/schema check, key business values, and required mirror hash equality | Full code suite, site-wide build, visual QA | Schema drift, invalid value, or render contract affected |
| 2. HTML only | Existing generator recreated target HTML with no generator/template/shared-layout change | Target-file assertions and one affected-route desktop/mobile smoke QA | Full site build and unrelated route QA | Shared layout/integration changed or smoke failure |
| 3. Local code | A bounded module or behavior changed | Closest focused tests plus static/diff checks for changed files | Full suite, cross-repo build, multiple reviewers | Focused failure suggests wider coupling or dependency graph crosses boundary |
| 4. Shared logic | Shared library, generator, schema, or cross-feature contract changed | Related tests across known consumers; full suite only with a written residual risk | Automatic full suite after focused tests pass | Consumer uncertainty, migration risk, or broad regression evidence |
| 5. High-risk boundary | Deployment, security/auth, secrets handling, destructive migration, or real-order boundary changed | Full applicable verification, rollback/safety checks, and only the independent review needed for the risk | Skipping a hard safety gate | None; hard gates for the affected boundary apply |
| 6. Review handoff | User explicitly requests review, release, or PR handoff | Broad tests and multiple reviewers may be used when scope is recorded | Unbounded exploration or duplicate reviewers without distinct roles | New findings that expand the reviewed surface |

### Heartbeat short circuit

The no-change heartbeat decision must occur before generator, test, build,
browser, or subagent steps:

```text
current source exists?
  yes -> classify the resulting change and continue in the matrix
  no  -> existing latest valid AND required mirror hashes equal?
           yes -> record date/state/hashes and STOP
           no  -> repair only the invalid or mismatched surface, then classify it
```

Regression case: an Auto Trading 16:00 heartbeat had no same-day mock source
and unchanged `public`/`dist` artifacts, but still ran 326 tests, a 371-page
site build, Playwright QA, and two independent reviewers. This is a prohibited
Class 0 path. None of those checks may run unless the precondition changes or
a separate written risk justifies reclassification.

## Cost and output guards

- Running 100 or more tests, a cross-repository/site-wide build, or more than
  one subagent/reviewer requires a written risk or explicit review-handoff
  reason before the command or spawn.
- A previous thread's unfinished, advisory, or blocked validation does not
  become required in the current task without a matching current change.
- Capture long output in an evidence file. Report only exit status, pass/fail
  counts, failing test/check names, and decision-relevant excerpts.
- Token and elapsed-time efficiency are acceptance criteria alongside defect
  detection. More checks are not higher quality when they do not change the
  completion decision.

## Common Required Gates

- Code change: focused unit tests or the closest project check for the changed
  behavior; a full suite needs a Class 4-6 reason.
- UI change: desktop and mobile render check for the affected route only.
- Content change: the closest content verifier; build only when source,
  routing, shared layout, or integration risk makes it decision-relevant.
- Security-sensitive change: secret scan of changed files and explicit
  authentication/authorization check.
- Deployment change: service restart or dry-run, public/local health check, and
  rollback note.

Generated-data-only and no-change work must use the matrix rather than these
broader defaults.

Do not claim a broad gate is green from a narrow command. If the command does
not cover the risk, mark the uncovered part as advisory, blocked, or missing.
