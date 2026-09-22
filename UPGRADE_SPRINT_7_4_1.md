# Sprint 7.4.1 — Mobile Hero Spacing Hotfix

Scope intentionally limited to the Home hero on mobile.

## Change
- Removes the oversized empty vertical band between the mobile header and the hero headline.
- The hero copy now starts from a controlled top offset instead of being anchored to the bottom of the hero.
- Mobile hero minimum height reduced slightly to keep the first screen tighter.
- Portrait, desktop layout, content, search, CTAs, animations and all sections below remain unchanged.

## Breakpoints
- <= 760px: hero min-height 690px; copy starts at `clamp(190px, 27vh, 220px)`.
- <= 430px: hero min-height 650px; copy starts at `clamp(170px, 24vh, 195px)`.

No migration required.
