# Host Model

## Purpose

Hosts define how the factory targets AI runners without hardcoding one agent across generic core logic.

## V1 Host Fields

Each host config supplies:

- display name
- CLI command and aliases
- home install root
- repo-local root
- whether the host supports GitHub-hosted worker execution

## V1 Hosts

- `codex`
  Supports local execution and GitHub-hosted worker flow.
- `claude`
  Supports local execution only.
- `opencode`
  Supports local execution only.

## Resolution Rule

The profile selects:

- one `defaultHost`
- one or more `enabledHosts`

Generic core derives behavior from those settings. Host-specific model env vars live under `execution.costProfiles`.
