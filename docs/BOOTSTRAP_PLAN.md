# Bootstrap Plan

## Objective

Turn `Agent-Automation` into a reusable upstream factory for GitHub-first repository automation that can run with multiple AI hosts.

## v2 Targets

- host-agnostic `repo-profile.v2`
- real rendered workflow and hook packs
- host configs for Codex, Claude, and OpenCode
- reusable review and QA packs
- no legacy repo-specific artifacts in the shipped package

## Current Factory Definition

The factory is considered healthy when:

- a clean consumer repo can install it and validate successfully
- issue, PR, workflow, and hook assets all render from the profile
- the default host can be swapped without changing generic core files
- review and QA packs can be enabled by profile
- upstream validation catches legacy naming or forbidden strings before release

## Implementation Order

1. lock the v2 profile contract
2. resolve hosts and packs from one loader path
3. render consumer outputs from that model
4. validate both package integrity and consumer installs
5. keep GitHub-specific orchestration separate from host-specific runtime choices
