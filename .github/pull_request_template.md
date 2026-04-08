## Summary

- What changed?
- Why?
- How was it validated?

## Workstream

- [ ] Backend
- [ ] Frontend
- [ ] Infra / CI
- [ ] Docs / DX
- [ ] QA / Release

## Checklist

- [ ] Checklist created and used during implementation
- [ ] Contracts updated (if interface changed)
- [ ] Docs updated (if behavior changed)
- [ ] Validation/tests run and results reviewed

## Promotion Gates

- [ ] Human-tested on development (required for `development -> stage`)
- [ ] Runtime smoke gates passed on development (required for `development -> stage`)
- [ ] Release readiness checks passed on development (required for `development -> stage`)
- [ ] Human-tested on stage (required for `stage -> main`)
- [ ] Runtime smoke gates passed on stage (required for `stage -> main`)
- [ ] Rollback plan validated for stage -> main (required for `stage -> main`)
- [ ] Production operator checkpoint approved for stage -> main (required for `stage -> main`)
