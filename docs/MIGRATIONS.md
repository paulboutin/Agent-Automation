# Migrations

## Rule

Behavior changes should land in this order:

1. update contract, template, or profile shape
2. update factory core
3. add validation or smoke coverage
4. then update consumer repos

## Consumer Upgrade Flow

1. pull the new factory package version into the consumer repo
2. review docs and contract changes
3. update `agent-factory.profile.json` if needed
4. rerender templates
5. rerun validation and smoke checks

## Backward Compatibility

The profile schema is intentionally additive where possible. Breaking changes should use a new version string rather than silently changing current semantics.
