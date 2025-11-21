# WonderDash Developer Guide

This guide explains how to extend WonderDash safely.

## Project Layout

```
src/
  wonder_dash/
    cli.py           # CLI entrypoint and argparse wiring
    hub.py           # Menu router and export helpers
    dashboard.py     # Live dashboard renderer
    hub_utils.py     # Shared Rich layouts and exporters
    config.py        # Config dataclass + helpers
    wizard.py        # Interactive setup workflow
```

## Local Environment

1. Install dependencies:
   ```bash
   pip install -e .
   pip install boto3 rich textual
   ```
2. Ensure `aws configure` has been run or environment variables are set.
3. Optional: `pre-commit install` if hooks are added later.

## Coding Standards

- Use type hints (`from __future__ import annotations` already enabled).
- Keep Rich/Textual imports optional. Wrap them in helpful error messages if missing.
- Prefer small helper functions in `hub_utils.py` for shared layouts.
- Any new module should include a top-level docstring explaining its role.

## Adding a Dashboard Panel

1. Place rendering logic in `dashboard.py`.
2. Use `hub_utils.build_loading_layout` to keep spinner styles consistent.
3. Fetch data through boto3 sessions created in `hub_utils` so profile handling stays centralized.
4. Update the cached model if the panel exposes new resource groups.
5. Register the panel in the hub menu if it needs a direct entry point.

## Extending Configuration

1. Add a field to `WonderConfig` in `config.py`.
2. Update `load_config()` to read the new field with a default.
3. Update `docs/config.md` and `docs/usage.md` with the new setting.
4. Expose the option in `wizard.py` if it is user-facing.

## Testing Changes

- Run unit coverage (if available) and try the CLI commands: `dashboard`, `hub`, `show-config`.
- Validate with both configured and missing credentials to confirm error messages stay helpful.

## Release Checklist

- Update version in `pyproject.toml`.
- Regenerate docs if diagrams or layers changed.
- Tag and push.
