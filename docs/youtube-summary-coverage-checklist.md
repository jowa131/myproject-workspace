# YouTube Summary Coverage Checklist

Use this checklist before a YouTube meeting or briefing summary is considered
ready for user review or publication.

## Required Coverage Gates

1. Build a source coverage map before polishing prose.
   - Split the transcript into meaningful agenda/issue units.
   - Include opening remarks, president questions, minister answers, public
     comment responses, official briefing-only items, and closing/private
     agenda items when verified.
   - Do not treat "already mentioned in opening remarks" or "already in key
     issues" as coverage for the detailed agenda section.

2. Preserve every president question or instruction.
   - If the president asks, checks, orders, or requests review, map it to a
     detailed agenda bullet.
   - If an answer is present, include `질의` and `답변` in the same note group.
   - If no answer is present, do not use `질의`; use `쟁점`, `지시`, or `확인`
     according to the evidence.

3. Avoid topic compression loss.
   - A card may have a main theme, but secondary issues inside the same report
     must remain when they include a question, answer, instruction, numerical
     claim, policy option, or official follow-up.
   - Financial and economic reports often contain several independent issues;
     do not collapse them into the most prominent program name.
   - Macro-economy and inflation response briefings are recurring cabinet
     meeting coverage. Track oil prices, exchange rates, interest rates, growth
     outlook, current account or external soundness, inflation targets,
     employment, and exchange-rate or vulnerable-borrower support as their own
     coverage unit when present.
   - When a previous cabinet-meeting summary has a comparable macro-economy
     card, include a short before/after comparison in the current detailed
     agenda or coverage audit.

4. Match every verified official agenda item.
   - Compare the transcript summary with official briefing pages when available.
   - Private or closed-session items from official briefings should be included
     as official-briefing-based bullets, not as transcript claims.
   - Source-basis notes belong in `요약 기준`; do not add a `쟁점과 지시` box
     that only says where the fact came from.

5. Run a final omission audit.
   - Create or update a per-video coverage audit file under the draft evidence
     folder.
   - The audit must list each major transcript/official issue, the destination
     section/card, and one of:
     - `covered`
     - `merged intentionally`
     - `excluded with reason`
     - `needs user decision`
   - Any `excluded` or `needs user decision` item must be reported to the user.

## Required Mechanical Checks

- Forbidden filler phrases:
  - `보고 시작`
  - `보고했다`
  - `보고됐다`
  - `언급됐다`
  - `보고가 있었다`
- Forbidden clipped wording from prior regressions:
  - `대응 축`
- Avoid public-facing internal draft terms unless the page is explicitly a
  private review page:
  - `검수 초안`
  - `검수 핵심`
  - `검수 항목`
- `질의` and `답변` must be paired in the same note group.
- Repeated timestamps should not appear in visible detailed notes.
- Detail notes must add value beyond the bullet immediately above them.
- Run the tracker repetition checker for Astro temp pages or structured
  components:
  `node scripts/check-youtube-summary-repetition.mjs <astro-temp-or-component-file>`.
  The result must be 0 redundant bullet/note pairs.

## Definition Of Done

For a public or preview YouTube summary:

- Coverage audit file exists and has no unexplained `missing` item.
- Repetition checker passes with 0 redundant bullet/note pairs.
- Content verifier passes in `C:\MyProject\yulchive-astro`.
- Astro build passes in `C:\MyProject\yulchive-astro`.
- Desktop and mobile render checks pass for the affected route.
- Wiki records changed files, coverage audit result, verification commands, and
  unresolved risks.
