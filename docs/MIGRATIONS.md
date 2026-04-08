# Migrations

## Rule

Behavior changes should land in this order:

1. update contract, profile shape, or pack boundary
2. update factory core
3. update render and validation coverage
4. then update consumer repos

## v2 Migration Notes

This repository is a clean-break `repo-profile.v2` release.

Key changes:

- generic worker branches use `agent/...`
- generic workflow names use `agent-*`
- hosts and packs are first-class profile concepts
- workflows and hooks render into consumer repos instead of staying as placeholders

## Consumer Upgrade Flow

1. vendor the new factory version
2. replace the old profile with `repo-profile.v2`
3. choose the default host and enabled packs
4. rerender assets
5. rerun validation and smoke checks

## Backward Compatibility

There is no compatibility shim for `repo-profile.v1`.
