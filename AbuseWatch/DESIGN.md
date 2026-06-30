# AbuseWatch Design System

## 1. Atmosphere & Identity

AbuseWatch is a quiet evidence desk for local, human-reviewed reporting work. It should feel restrained, procedural, and careful rather than punitive. The signature is a calm queue-to-evidence workspace: dense enough for review, but with clear separation between candidate URLs, captures, audit records, and report packages.

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | --surface-primary | #F7F8FA | #111315 | App background |
| Surface/secondary | --surface-secondary | #FFFFFF | #171A1D | Panels |
| Surface/elevated | --surface-elevated | #F0F3F5 | #20252A | Tool strips, table heads |
| Text/primary | --text-primary | #172026 | #F4F7F8 | Headings, primary body |
| Text/secondary | --text-secondary | #51606B | #B3BEC7 | Secondary body |
| Text/tertiary | --text-tertiary | #7B8790 | #77838C | Metadata |
| Border/default | --border-default | #D9E0E5 | #30373D | Panel borders |
| Border/subtle | --border-subtle | #E8EDF1 | #242A30 | Dividers |
| Accent/primary | --accent-primary | #0F766E | #2DD4BF | Primary actions, focus |
| Accent/hover | --accent-hover | #115E59 | #5EEAD4 | Hover state |
| Status/success | --status-success | #15803D | #4ADE80 | Confirmed evidence |
| Status/warning | --status-warning | #B45309 | #FBBF24 | Needs review |
| Status/error | --status-error | #B91C1C | #F87171 | Validation errors |
| Status/info | --status-info | #2563EB | #60A5FA | Informational states |

### Rules

- Accent is reserved for interaction, focus, and selected review state.
- Status colors describe review state only. They must never label a person.
- No public blacklist or accusation styling is allowed.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| Display | 32px | 700 | 1.15 | 0 | Workspace title |
| H1 | 28px | 700 | 1.2 | 0 | Page header |
| H2 | 22px | 650 | 1.3 | 0 | Panel group headers |
| H3 | 18px | 650 | 1.4 | 0 | Panel titles |
| Body/lg | 17px | 400 | 1.55 | 0 | Lead text |
| Body | 15px | 400 | 1.55 | 0 | Default UI text |
| Body/sm | 14px | 400 | 1.45 | 0 | Table and metadata |
| Caption | 12px | 600 | 1.35 | 0 | Labels |
| Mono | 13px | 500 | 1.45 | 0 | Hashes, IDs, URLs |

### Font Stack

- Primary: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
- Mono: "Cascadia Mono", "SFMono-Regular", Consolas, monospace

### Rules

- Body text stays at 14px or larger.
- Long URLs use the mono stack and wrap safely.

## 4. Spacing & Layout

### Base Unit

All spacing derives from 4px.

| Token | Value | Usage |
|-------|-------|-------|
| --space-1 | 4px | Tight inline gaps |
| --space-2 | 8px | Compact controls |
| --space-3 | 12px | Field padding |
| --space-4 | 16px | Panel inner padding |
| --space-5 | 20px | Panel group spacing |
| --space-6 | 24px | Page sections |
| --space-8 | 32px | Major workspace columns |

### Grid

- Max content width: 1320px.
- Layout: responsive operational grid, one column on mobile, two columns above 980px.
- Breakpoints: sm 640px, md 768px, lg 1024px, xl 1280px.

### Rules

- Use CSS variables for spacing in product CSS.
- Dense data views use dividers before nested cards.

## 5. Components

### Workspace Panel

- Structure: section with heading, optional action row, and list or table body.
- Variants: neutral, warning, success.
- Spacing: --space-4 internal, --space-5 between panels.
- States: empty, loading, error, selected, focus.
- Accessibility: headings are semantic, controls are keyboard focusable.
- Motion: opacity and transform only, 120ms hover transitions.

### Status Badge

- Structure: inline span with text only.
- Variants: queued, captured, duplicate, needs-review, approved.
- Spacing: --space-1 vertical, --space-2 horizontal.
- Accessibility: color is never the sole meaning.

## 6. Motion & Interaction

### Timing

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 120ms | ease-out | Hover, focus |
| Standard | 180ms | ease-in-out | Panel state changes |

### Rules

- Animate only opacity and transform.
- Respect `prefers-reduced-motion`.
- Focus outlines use --accent-primary and must remain visible.

## 7. Depth & Surface

### Strategy

Use borders-only.

| Type | Value | Usage |
|------|-------|-------|
| Default | 1px solid var(--border-default) | Panels, inputs, tables |
| Subtle | 1px solid var(--border-subtle) | Internal row dividers |

No box shadows are used in the MVP shell.
