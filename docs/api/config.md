# Module: `config`

Single source of truth for WonderDash settings.

## Contents
- `WonderConfig`: Dataclass capturing profile, region, distribution ID, refresh settings, theme, cache TTL, and placeholders for future dashboards.
- `DEFAULT_CONFIG`: Baseline configuration used when no user file exists.
- `config_path()`: Resolves the config file location (defaults to `~/.wonderdash/config.json`).
- `load_config()`: Reads the JSON file, merges with defaults, returns `WonderConfig`.
- `save_config(config)`: Serializes the dataclass back to disk.

## Usage Tips
- Always call `load_config()` instead of importing globals directly.
- Use `WonderConfig.to_dict()` to serialize for debugging or API calls.
- Keep new config fields optional with sensible defaults to avoid breaking existing files.
