## What does this change?

<!-- One or two sentences. -->

## Why?

<!-- Link an issue if there is one. -->

## Component(s) touched

- [ ] SDK (`voidremote/api/`, or anything it depends on)
- [ ] CLI (`voidremote/cli/`)
- [ ] GUI (`voidremote/ui/`)
- [ ] Packaging (`pyproject.toml`, `scripts/`)
- [ ] Documentation
- [ ] CI / workflows

## Checklist

- [ ] `black voidremote tests` — no changes needed
- [ ] `ruff check voidremote tests` — passes
- [ ] `mypy voidremote` — passes
- [ ] `pytest` — passes (unit, integration, cli, packaging)
- [ ] `QT_QPA_PLATFORM=offscreen pytest -m gui` — passes, if `voidremote/ui/` was touched
- [ ] Added/updated tests for the change
- [ ] Updated `CHANGELOG.md`
- [ ] If this touches `voidremote/api/`: confirmed it's backward-compatible, or this is
      flagged as a breaking change for the next major version

## Notes for reviewers

<!-- Anything that needs context: design tradeoffs, things you're unsure about. -->
