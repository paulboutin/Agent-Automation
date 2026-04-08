# Phigure Mapping

Phigure is the first consumer example for this factory model.

## Core In This Repository

- contracts under `contracts/`
- templates under `templates/`
- scripts under `scripts/`
- docs under `docs/`

## Phigure Example Profile

- `examples/phigure.repo-profile.json`

It captures:

- `development -> stage -> main`
- lane inventory
- role pricing defaults
- queue labels
- concurrent workstream metadata
- promotion gates
- runtime smoke environment names

## Portability Standard

Phigure-specific paths, labels, or naming should stay in the profile or consumer hooks. Shared process behavior belongs here in the upstream factory.
