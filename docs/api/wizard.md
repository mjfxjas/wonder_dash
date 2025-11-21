# Module: `wizard`

Interactive setup workflow for WonderDash.

## Responsibilities
- Prompt the user for AWS profile, region, and CloudFront distribution ID.
- Allow editing of refresh intervals and theme preferences.
- Persist answers via `config.save_config()`.

## Flow
1. Load existing config if present to prefill answers.
2. Prompt for AWS profile (`default`, `prod`, etc.).
3. Prompt for distribution ID (optionally listing existing CloudFront distributions).
4. Prompt for refresh interval and theme.
5. Write updated `WonderConfig` to the config path.

## Extension Points
- Add new questions near the end of the wizard to keep essential steps first.
- Keep prompts resilient (default values, validation loops) so headless shells behave predictably.
