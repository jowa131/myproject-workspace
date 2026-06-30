# IBS Care Android Design System

## 1. Atmosphere

IBS Care Android follows the existing web app's quiet clinical command-center direction. The mobile screen is a compact recording surface, not a marketing page. Korean labels stay direct and respectful, and the app never claims diagnosis, treatment, cure, certainty, or automatic bowel confirmation.

## 2. Color Tokens

| Role | Android resource | Value | Usage |
| --- | --- | --- | --- |
| Surface primary | `@color/surface_primary` | `#F7FAF8` | App background |
| Surface secondary | `@color/surface_secondary` | `#FFFFFF` | Form panels |
| Surface elevated | `@color/surface_elevated` | `#EEF5F1` | Likely-session proposal panel |
| Surface field | `@color/surface_field` | `#FDFEFE` | Field-like quiet surfaces |
| Text primary | `@color/text_primary` | `#17211D` | Titles and important text |
| Text secondary | `@color/text_secondary` | `#52615B` | Body and helper text |
| Border default | `@color/border_default` | `#D8E4DE` | Panel outlines |
| Accent primary | `@color/accent_primary` | `#197A68` | Primary actions and focus |
| Accent soft | `@color/accent_soft` | `#DDF2EC` | Selected calm backgrounds |
| Status warning | `@color/status_warning` | `#A0641F` | Safety caution only |

## 3. Typography

- Main title: 28sp, bold, line height close to 1.25.
- Section title: 22sp, bold.
- Card title: 18sp, bold.
- Korean body text: 15sp or larger.
- Helper and safety text: 14sp or larger.
- Letter spacing remains 0 for Korean readability.

## 4. Spacing

- Base unit: 4dp.
- Screen gutter: 20dp.
- Panel padding: 16dp.
- Panel gap: 12dp.
- Compact internal gap: 8dp.
- Top content must reserve status-bar height plus 20dp so Korean text never overlaps system UI.

## 5. Components

- Proposal panel: elevated surface, one-pixel clinical border, direct score/status heading, no certainty language.
- Primary button: accent primary background, white text, 8dp radius, full-width where repeated action matters.
- Log panel: visible section heading, time field, Bristol type selector, expected checkboxes, explicit `기록 저장` action.
- Safety panel: plain clinical caution copy; no alarmist visual treatment.

## 6. Motion And Safety

- No decorative animation is required for the native MVP.
- Sensor scoring may prefill only after the user taps `배변 기록 확인하기` or opens a pending background candidate.
- Durable storage changes only after the user taps `기록 저장`.
- The app processes motion signals locally. It uses location only as a short candidate-time movement gate, and still has no network, Bluetooth, microphone, or Accessibility dependency.
