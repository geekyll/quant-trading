# Agent Guidelines

All code must use **English only** for Comments, Print and log messages.

## Git

- `commit` after each task — do **not** `push` unless the user explicitly requests it.

### Commit Message Format

```
<prefix>: <short description>

[optional body]
```

### Prefix Definitions

| Prefix | When to use | Example |
|--------|-------------|---------|
| `feat` | New feature or capability | `feat: add SMA200 backtest engine` |
| `fix` | Bug fix | `fix: correct lookahead bias in signal shift` |
| `docs` | Documentation only (README, TODO, AGENTS) | `docs: update TODO with Phase 3 items` |
| `style` | Formatting, no logic change (Ruff, whitespace) | `style: replace Korean strings with English` |
| `refactor` | Code restructure without feature change | `refactor: extract metrics into separate module` |
| `chore` | Build, deps, config, tooling | `chore: add Ruff and EditorConfig` |
| `data` | Data pipeline changes (collector, universe) | `data: add SOXL and BTC-USD to universe` |

### Rules

- Subject line: imperative mood, no period, max 72 chars
- Always run `ruff check --fix` and `ruff format` before committing
- Always update `TODO.md` checkboxes in the same commit as the feature
