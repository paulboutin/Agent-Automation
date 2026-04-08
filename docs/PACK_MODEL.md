# Pack Model

## Purpose

Packs let the factory ship reusable behavior bundles without forcing every consumer to hand-wire the same assets.

## V1 Packs

- `automation`
  Task issue flow, worker dispatch, unblocker, PR wake, and local worker hooks.
- `governance`
  Merge-daemon status and launch-next hooks plus promotion helpers.
- `review`
  Review checklist and prompt pack.
- `qa`
  QA checklist and prompt pack plus operator-proof hook seam.

## Rendering Rule

Enabled packs render into consumer repos under:

- `.github/`
- `.agent-automation/`

Packs are selected by profile, not by editing upstream templates directly.
