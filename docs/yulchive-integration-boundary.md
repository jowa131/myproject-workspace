# Yulchive Integration Boundary

`C:\MyProject\yulchive-astro` is the public static blog and route integration
point. Feature projects own their own source, tests, requirements, operating
notes, and reusable automation.

## Feature Owners

- `C:\MyProject\yulchive-stock`: stock dashboard feature source and tests
- `C:\MyProject\yulchive-photo-publisher`: Google Photos to Yulchive draft and
  publish harness
- `C:\MyProject\yulchive-youtube-tracker`: YouTube transcript and review draft
  workflow

## Astro Integration Receives

- generated preview routes
- final MDX posts
- optimized public images
- minimal route/layout glue
- service scripts only when the public blog runtime owns the serving boundary

## Rules

- Keep feature planning and task packets in the feature project.
- Keep final public rendering checks in `yulchive-astro`.
- Do not move secrets, raw private media, provider tokens, or private evidence
  into `yulchive-astro`.
- When a feature project writes into `yulchive-astro`, the handoff must list
  every target file and the required Astro verification gates.
- If a file is mirrored in both places, document which copy is authoritative.

