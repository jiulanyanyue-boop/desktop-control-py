# Contributing

Thanks for helping improve `desktop-control-py`.

## Development setup

1. Install Python 3.11 or newer.
2. Install `uv`.
3. From the repository root, run:

```powershell
uv sync --extra dev
uv run --extra dev python -m pytest -q
```

## Validation

CI-safe checks:

```powershell
uv run --extra dev python -m pytest -q
uv run --extra dev python -m build
uv run --extra dev ruff check .
```

Real-machine validation is intentionally manual because it moves the mouse,
types into Notepad, reads the clipboard, and captures browser screenshots:

```powershell
desktop-control-py check-env
desktop-control-py smoke-test
desktop-control-py serve --transport stdio
```

## Contribution rules

- Keep MCP tool names stable unless a breaking-change discussion is opened first.
- Keep browser automation screenshot-first. Do not add DOM scraping, page-text capture, clipboard-based browser extraction, or CAPTCHA bypass flows.
- Keep Windows-only assumptions explicit.
- Add or update tests for behavior changes.
- Do not commit runtime logs, local virtual environments, build output, or machine-specific paths.
