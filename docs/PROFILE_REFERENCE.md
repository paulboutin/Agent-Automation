# Profile Reference

The factory uses `repo-profile.v2`.

## Top-Level Sections

- `version`
  Must be `repo-profile.v2`.
- `repo`
  Consumer repo identity.
- `platform`
  Git provider selection. V1 requires `github`.
- `branches`
  Development, promotion, and worker branch settings.
- `labels`
  Queue and lane labels.
- `roles`
  Role inventory and default cost profiles.
- `lanes`
  Lane inventory and default cost profiles.
- `execution`
  Default host, enabled hosts, hosted enablement, automation root, and cost profiles.
- `hosts`
  Host-specific CLI and install-root data.
- `packs`
  Enabled pack flags.
- `protocols`
  Contract versions for worker status and PR wake payloads.
- `requiredDocs`
  Consumer docs that must exist.
- `templates`
  Issue and PR template content.
- `promotion`
  Promotion transitions and gates.
- `concurrency`
  Base-branch and scope field naming plus helper script path.
- `operatorProof`
  Operator-proof lane selection.

## Execution

`execution` is the main v2 addition.

Key fields:

- `defaultHost`
  The host used by local worker resolution and any hosted path.
- `enabledHosts`
  Host names enabled for the consumer repo.
- `hostedEnabled`
  Allows hosted GitHub worker flows when the default host supports them.
- `automationRoot`
  Where rendered hooks and packs live in the consumer repo.
- `costProfiles`
  Cost tier to reasoning-effort mapping plus per-host model env vars.

Example shape:

```json
{
  "execution": {
    "defaultHost": "codex",
    "enabledHosts": ["codex", "claude", "opencode"],
    "hostedEnabled": true,
    "automationRoot": ".agent-automation",
    "costProfiles": {
      "standard": {
        "reasoningEffort": "medium",
        "hosts": {
          "codex": {
            "localModelEnvVar": "AGENT_AUTOMATION_CODEX_MODEL_STANDARD",
            "hostedModelEnvVar": "AGENT_AUTOMATION_CODEX_MODEL_STANDARD"
          },
          "claude": {
            "localModelEnvVar": "AGENT_AUTOMATION_CLAUDE_MODEL_STANDARD"
          },
          "opencode": {
            "localModelEnvVar": "AGENT_AUTOMATION_OPENCODE_MODEL_STANDARD",
            "variant": "medium"
          }
        }
      }
    }
  }
}
```

## Hosts

Each enabled host declares:

- `displayName`
- `cliCommand`
- `cliAliases`
- `homeRoot`
- `repoRoot`

Generic core uses these to resolve runtime behavior without hardcoding one host.

## Packs

Each pack is a boolean flag:

- `automation`
- `governance`
- `review`
- `qa`

Disabling a pack stops its consumer outputs from rendering.

## Branches And Labels

Generic defaults:

- worker branch format: `agent/issue-{issue_number}-{lane}`
- ready label: `ready`
- active label: `active`
- blocker label: `needs-decision`
- proposal label: `decision-proposed`
- failed label: `agent-failed`
- PR conflict label: `merge-conflict`

These can be changed in the profile as long as the consumer repo remains internally consistent.
