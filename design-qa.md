# Design QA - research dashboard

final result: passed

## Scope and visual references

This is a scoped redesign, not a pixel-for-pixel clone. The user's two screenshots
and written requests define the intended changes: replace radio navigation, use the
research subject as the title, move explanations to a dedicated page, remove repeated
labels/footer, and add chart-detail dialogs. Preserve data, filters and downloads.

Source visual truth:
- C:/Users/hoang/AppData/Local/Temp/codex-clipboard-fed42c3f-18ed-4834-bd41-d64942b6535c.png (296 x 929, cropped sidebar)
- C:/Users/hoang/AppData/Local/Temp/codex-clipboard-638ea75f-6b7b-4b09-802b-c8efa59d7295.png (1447 x 863, cropped overview, Oct-Nov)

Evidence directory:
C:/Users/hoang/.codex/visualizations/2026/11/09/01a1c073-ebb7-7eb1-bc4c-e0d678851205/

Implementation screenshots:
- dashboard-final.png: overview, both seasons, 1366 x 900 CSS viewport.
- dashboard-desktop-v2.png: Oct-Nov overview, 1747 x 900 CSS viewport.
- dashboard-laptop-final.png: overview, both seasons, 1280 x 800 CSS viewport.
- dashboard-methods.png: methodology route, 1366 x 900 CSS viewport.
- dashboard-detail.png: PM2.5 dialog, both seasons, 1366 x 900 CSS viewport.

Original screenshots are cropped and their full browser viewport/density is unknown.
Implementation captures use the requested CSS viewport sizes without manual resampling.
The original overview and Oct-Nov implementation were viewed together in one comparison
input. Full desktop capture resolves surrounding layout; source sidebar and the live
sidebar were reviewed as focused regions. Do not interpret different crop positions
or intentional content reorganization as fidelity defects.

## Findings and comparison history

1. P2, navigation alignment: initial button contents were centered, making labels
   unevenly aligned. Scoped button-content CSS now aligns icons and labels left.
   Verified in dashboard-methods.png and dashboard-final.png.
2. P2, retained scroll position: changing content with a session-state-only menu could
   retain an old scroll offset and hide the new heading. Changed to native Streamlit
   pages and switch_page, while retaining the custom menu. Verified /methods opens
   at the top with its heading visible (dashboard-methods.png).
3. P2, KPI labels at 1280 px: long labels were ellipsized. Allowed label wrapping and
   reserved a uniform 40 px label height. Re-captured dashboard-laptop-final.png;
   all five labels are visible and values remain aligned. DOM measurements confirm
   label height is 40 px for every KPI.

No remaining actionable P0/P1/P2 findings in the reviewed states.

## Required surfaces

- Typography: retained native Vietnamese-compatible sans-serif. Reduced header weight,
  removed uppercase English eyebrow text, retained clear heading/body hierarchy.
  KPI labels wrap; long menu labels fit the sidebar. No decorative font dependency.
- Layout: light section header replaces oversized dark hero; charts move above the fold
  after relocating the pipeline explanation. Native responsive columns remain. At 1280 px,
  document scrollWidth equals viewport width; no horizontal page overflow.
- Tokens: navy text, muted teal selected navigation and PM2.5, orange VIIRS, pale background.
  Selection has a visible filled background and border; keyboard focus outline retained.
- Assets: native Material icons and real data charts/maps. No generated image assets or
  invented observational data. Browser evidence has capture softness; no rasterized UI
  or image-text assets were introduced.
- Copy: research title replaces exercise number, no old breadcrumb/footer, no sidebar
  disclaimer. Definitions and interpretation limits live in the methods page; relevant
  AOD/correlation context remains beside results and in dialogs.

## Interaction checks

- AppTest: six navigation items, three season choices, chart dialogs on all five analysis
  pages passed. Native page navigation rechecked after switching implementation.
- Browser: overview and methods routes, active menu style, methods sub-tabs, season selector,
  popup opening/closing, popup scope (Oct-Nov), and CSV download tested.
- Downloaded PM2.5 popup CSV matches the corresponding original daily dataset columns.
- Browser console error query returned no entries.
- Syntax/import compilation passed. Existing output and pipeline files were not edited.

## Follow-up polish / limits

- Desktop/laptop widths reviewed: 1747, 1366, 1280 px. Phone-specific layout was not part
  of this pass. No claim of exhaustive assistive-technology testing.
- Methodology PDF buttons use existing files; CSV was downloaded and checked in-browser.

## Implementation checklist

- [x] Research title and concise header
- [x] Six-item menu with active state and native routes
- [x] Dedicated methods/glossary/report page
- [x] Chart dialogs with explanation, source, data and CSV
- [x] Preserve science, filters and real data
- [x] Fix visual issues, re-capture and verify

## Section borders and page introductions — 2026-11-09

## Conclusions page — follow-up

- Added Conclusions before Methods, with seasonal findings, robustness, AOD limitations,
  practical interpretation and next research steps grounded in final exported CSV/JSON.
- Clearly distinguished fixed two-season synthesis from the season-filtered evidence table.
- Direct page AppTest passed all three season filters (8/4/4 evidence rows). Sidebar
  navigation to Conclusions and Methods tested separately; AppTest does not preserve
  the selected native route across subsequent filter reruns in this harness.
- Browser confirmed /conclusions and rendered bordered interpretation sections.
- Moved switch_page out of the button callback into the main render flow.
- Screenshot: dashboard-conclusions.png in the existing visualization evidence folder.
- Python compilation and whitespace checks passed; no pipeline or scientific output edits.

Result: passed for the reviewed desktop states.

- Added white bordered panels around charts, the map, QA groups and methodology tabs.
- Every page now includes a concise purpose statement in its bordered introduction.
- Moved chart detail actions into panel headers, beside the title; scope stays below.
- Fixed a discovered header-wrap issue: the longer Cropland title displaced its action
  and misaligned the adjacent charts. Non-wrapping header rows and a shared minimum
  height keep both panels aligned in the final 1366 × 1000 capture.
- Reference: codex-clipboard-4694e0b9-a987-4d17-925e-f2c51a9093e6.png.
- Evidence: C:/Users/hoang/.codex/visualizations/2026/11/09/01a1c073-ebb7-7eb1-bc4c-e0d678851205/dashboard-panels-final.png.
- Rechecked all six pages with all three season selections in AppTest, plus a chart
  dialog on each analytical page. Browser confirmed the repositioned button opens
  the populated dialog and closes correctly; no console errors were recorded.
- Final Python compilation and git diff whitespace checks passed. Scientific outputs
  and processing pipelines remain unchanged. Mobile layout was not reviewed.
