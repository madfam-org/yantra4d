---
name: Yantra4D
description: The incumbent visual system of the Yantra4D Studio and landing, recorded as it is on main (91b3ffc9).
colors:
  ink: "hsl(240 10% 3.9%)"
  paper: "hsl(0 0% 100%)"
  graphite-action: "hsl(240 5.9% 10%)"
  signal-blue: "hsl(221 83% 53%)"
  signal-blue-readable-light: "hsl(221 83% 42%)"
  signal-blue-readable-dark: "hsl(221 83% 68%)"
  zinc-wash: "hsl(240 4.8% 95.9%)"
  zinc-wash-dark: "hsl(240 3.7% 15.9%)"
  zinc-quiet-text: "hsl(240 3.8% 40%)"
  zinc-quiet-text-dark: "hsl(240 5% 64.9%)"
  zinc-rule: "hsl(240 5.9% 87%)"
  zinc-field: "hsl(240 5.9% 90%)"
  alarm-red: "hsl(0 84.2% 60.2%)"
  alarm-red-dark: "hsl(0 62.8% 30.6%)"
  near-white: "hsl(0 0% 98%)"
typography:
  title:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.43
  label:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.33
  value:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.33
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  full: "9999px"
spacing:
  hair: "4px"
  tight: "6px"
  base: "8px"
  roomy: "16px"
  panel: "24px"
  target: "44px"
components:
  button-primary:
    backgroundColor: "{colors.graphite-action}"
    textColor: "{colors.near-white}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    height: "40px"
  button-primary-dark:
    backgroundColor: "{colors.signal-blue}"
    textColor: "{colors.near-white}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    height: "40px"
  button-generate:
    backgroundColor: "{colors.graphite-action}"
    textColor: "{colors.near-white}"
    rounded: "{rounded.md}"
    height: "44px"
    width: "100%"
  button-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    height: "40px"
  button-ghost:
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    size: "40px"
  input-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    height: "40px"
  tab-trigger:
    backgroundColor: "{colors.zinc-wash}"
    textColor: "{colors.zinc-quiet-text}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
  card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "24px"
---

# Design System: Yantra4D

<!-- Recorded 2026-11-20 through impeccable `document` (scan mode) for RFC 0067 phase P0.
This file describes the system as it IS. Owner ruling (2026-11-20): document the incumbent
now; run the Studio world workshop BEFORE family goldens are approved in RFC 0067 P2, since a
look change after that re-baselines every golden. The North Star and named rules below were
inferred from the code, not chosen in a workshop; treat them as provisional until then.
Source of truth for token values: packages/tokens/colors.css (shared by Studio and landing),
apps/studio/tailwind.config.js, apps/landing/tailwind.config.mjs. -->

## Overview

**Creative North Star: "The Neutral Workbench" (provisional)**

The Studio is a workbench: a dense instrument panel beside a large 3D viewport, in which the
object being configured is the only thing with colour and depth. The chrome is a stock
shadcn/ui kit on a zinc neutral scale, a system font, and one accent that changes with the
theme (graphite in light, signal blue in dark). Density is high: most chrome text is 12 px
(`text-xs` is the single most-used size in the Studio) and controls sit 4–8 px apart.

The world is coherent but not authored: nothing in the tokens says "hyperobject", "Commons" or
"4D", and most of it would read the same on any shadcn app. That is the gap the pre-P2 world
workshop exists to close. Until then, new surfaces inherit this system exactly and introduce
no new colours, fonts or radii.

**Key Characteristics:**

- One shared token file (`packages/tokens/colors.css`) for the Studio and the landing, HSL
  triplets consumed as `hsl(var(--token))`.
- Light, dark and system themes; the user cycles them in the header.
- System UI font for all chrome; monospace for numeric values, paths and code.
- Tonal layering and translucent blurred panels over the viewport; shadows are rare.
- Touch targets of 44 px on primary controls; safe-area utilities for notched phones.

## Colors

A restrained zinc neutral scale with a single accent that is graphite in light mode and signal
blue in dark mode; status colours are not yet tokens.

### Primary

- **Graphite Action** (`--primary`, light): the primary button, the Generate action, selected
  toggles. Nearly the same value as the ink, so in light mode the primary action is
  distinguished by fill, not hue.
- **Signal Blue** (`--primary`, dark): the same roles in dark mode. A surface and large-text
  accent only: it measures 3.83:1 on the dark background.
- **Signal Blue Readable** (`--primary-readable`, light 42 % / dark 68 % lightness): accent
  text under 24 px (or under 18.66 px bold). Clears 4.5:1 on every surface the landing paints.

### Neutral

- **Ink** (`--foreground`, and `--background` in dark): body text in light mode; the page in
  dark mode.
- **Paper** (`--background`, `--card`, `--popover`, light): the page, cards and popovers.
- **Zinc Wash** (`--secondary`, `--muted`, `--accent`): hover fills, tab rails, quiet panels,
  secondary buttons. One value serves three roles.
- **Zinc Quiet Text** (`--muted-foreground`): help text, units, captions, inactive tabs.
- **Zinc Rule** (`--border`) and **Zinc Field** (`--input`): hairlines and field strokes.

### Tertiary

- **Alarm Red** (`--destructive`): destructive buttons and error fills, usually at 10–15 %
  opacity behind red text.
- **Chart 1–5**: five chart hues per theme, used by the analysis overlays.

### Named Rules

**The Readable Accent Rule.** Accent-coloured text below 24 px uses `primary-readable`, never
`primary`. The landing enforces it; the Studio must too.

**The Token-Only Rule.** New UI colours come from the token file. The Studio today hard-codes
yellow, green, amber, purple and blue utility colours for warnings, success and tier badges
(about 40 uses) and raw hex in the viewer overlays; that is recorded drift, not precedent.
Warning, success and info need tokens before the generated configurator ships (see
`docs/architecture/graph-generated-surfaces.md`).

**The Error Text Rule.** Error and constraint text must clear 4.5:1. `--destructive` used as
text measures 3.76:1 on the light background and 1.99:1 on the dark one, so it is a fill, not
a text colour, until a readable error token exists (the same pattern as `primary-readable`).
`apps/studio/src/test/tokenContrast.test.ts` holds the measured pairs.

## Typography

**Display Font:** none (the Studio has no display face)
**Body Font:** system-ui (with -apple-system, Segoe UI, Roboto, sans-serif)
**Label/Mono Font:** ui-monospace (with SFMono-Regular, Menlo, Consolas, monospace)
**3D label font:** Roboto Regular (Latin subset, served from `/fonts/roboto-regular.woff`) for
text drawn inside the viewport only; the CSP forbids runtime font fetches
(`apps/studio/src/lib/studioFonts.ts`).

**Character:** a utilitarian pairing: the platform's own UI face for words and a monospace for
numbers, so values line up and read as measurements.

### Hierarchy

- **Title** (600, 18 px, 1.4): panel and dialog titles.
- **Body** (400, 14 px, 1.43): descriptions, dialog copy, list rows.
- **Label** (500, 12 px, 1.33): control labels, tab triggers, buttons inside panels; the
  workhorse size of the Studio.
- **Value** (mono 400, 12 px): parameter values, units, coordinates, file names.

### Named Rules

**The Measurement Rule.** A number the visitor can act on (a parameter value, a measured
distance, a quota) is set in the mono face, with its unit, in Zinc Quiet Text when it is not
the focus.

**The 16 px Field Rule.** On viewports under 768 px, inputs, selects and textareas are 16 px so
mobile browsers do not zoom on focus (`index.css`).

## Layout

The Studio is a two-region workbench: a resizable sidebar of controls and a viewport that
takes the rest. A sticky action dock closes the sidebar (Compare, render placement, Generate,
Verify, Reset). On phones the sidebar becomes a sheet and the viewport fills the screen; a
`phone-landscape` screen (landscape and under 1024 px) exists for the cramped case, and `xs`
(360 px) is the smallest designed width. Spacing runs on a 4 px base, mostly 4, 6 and 8 px
inside panels and 16–24 px between them. A golden-ratio pair (`--phi`, `--phi-inv`) is
declared for proportions.

## Elevation & Depth

Flat by default, with depth by tonal layering and translucency rather than shadow: panels over
the viewport use 70–90 % background with `backdrop-blur`, and the action dock carries one soft
upward shadow (`0 -4px 24px` at 5 % black, 20 % in dark). Small shadows (`shadow-sm`) mark
raised buttons and cards; large shadows only on popovers and dialogs. The 3D object is the
only element with real depth.

### Named Rules

**The Object Has The Depth Rule.** Chrome stays flat and translucent so the configured object
is the deepest, most lit thing on screen.

## Shapes

Gently rounded rectangles: 8 px on cards and panels (`--radius`), 6 px on buttons and fields,
4 px on tab triggers and chips, full pills for badges and toggles. Hairline 1 px borders in Zinc
Rule separate regions; there are no decorative shapes in the Studio chrome.

## Components

### Buttons

- **Shape:** gently rounded (6 px).
- **Primary:** Graphite Action fill (Signal Blue in dark), near-white text, 40 px high, 16 px
  side padding; hover drops to 90 % opacity.
- **Generate:** the primary button at full sidebar width and 44 px, with a spinner and "working"
  label while rendering; disabled while a constraint is violated.
- **Outline / Ghost / Secondary:** outline on Paper with a Zinc Field stroke; ghost with a Zinc
  Wash hover; secondary on Zinc Wash.
- **Focus:** a 2 px ring in `--ring` with a 2 px offset (3 px / 4 px on coarse pointers).

### Inputs / Fields

- **Style:** 1 px Zinc Field stroke, Paper fill, 6 px radius, 40 px high.
- **Focus:** the shared 2 px ring.
- **Error / Disabled:** disabled at 50 % opacity; errors are carried by text, not field colour.

### Navigation

- **Tabs** (sidebar sections, compare): a Zinc Wash rail with the active trigger lifted to Paper
  with `shadow-sm`; 12 px medium labels.
- **Header:** project name, theme cycle, language toggle, unit toggle, account.

### Sliders (signature control)

The parameter slider is the Studio's most common control (4,028 of 4,509 Commons parameters):
label and live mono value on one line, the Radix slider below, the unit in Zinc Quiet Text.
The filled range is `--primary` on a `--secondary` track: 16.13:1 in light, but 2.86:1 in dark,
under the 3:1 non-text floor (recorded debt in `apps/studio/src/test/tokenContrast.test.ts`).

## Do's and Don'ts

### Do:

- **Do** take every colour from `packages/tokens/colors.css` through `hsl(var(--token))`.
- **Do** use `primary-readable` for accent text under 24 px.
- **Do** set acted-on numbers in the mono face with their unit.
- **Do** keep 44 px targets on primary controls and the 16 px field size on phones.
- **Do** honour `prefers-reduced-motion`: the token file already stops animations and
  transitions globally.

### Don't:

- **Don't** add new hard-coded Tailwind palette colours (`text-yellow-600`, `bg-green-500`) or
  raw hex in chrome; add a token.
- **Don't** give chrome real shadows or depth that competes with the 3D object.
- **Don't** introduce a new font, radius or accent before the pre-P2 world workshop decides the
  Studio's world.
