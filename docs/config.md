# WonderDash Configuration

WonderDash reads configuration from two locations:

1. Defaults baked into `config.py`
2. User overrides stored in `~/.wonderdash/config.json`

The `WonderConfig` dataclass exposes these fields:

| Field | Type | Description |
| --- | --- | --- |
| `aws_profile` | `str | None` | Named profile for boto3 sessions. If `None`, the default AWS profile/environment variables are used. |
| `region` | `str | None` | Target AWS region. When missing, boto3 resolves it from environment or config. |
| `distribution_id` | `str | None` | CloudFront distribution used by the dashboard. Controls which distribution appears in summaries. |
| `refresh_interval_seconds` | `int` | Delay between dashboard refreshes. Prevents API throttling. |
| `theme` | `Literal["light", "dark"]` | Hub theme preference. Toggles palette maps in `hub.py`. |
| `cache_ttl_seconds` | `int` | TTL for cached resource discovery results. |
| `extra_dashboards` | `list[str]` | Future use. Allows third-party dashboards to register with the hub. |

## Config File Location

The helper `config_path()` returns the resolved path. By default it is `~/.wonderdash/config.json`. WonderDash will create the directory if needed.

## Environment Variables

WonderDash honors standard AWS environment variables (`AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`). There are no WonderDash-specific environment variables yet; all settings live in the JSON file.

## Editing the Config

1. Run `wonder-dash show-config` to display current values.
2. Edit `~/.wonderdash/config.json` manually or rerun `wonder-dash setup` to regenerate it.
3. Restart any running hub or dashboard instances to load the new settings.

## Validation

`load_config()` performs minimal validation and raises `RuntimeError` if the file cannot be parsed. Commands that rely on AWS calls wrap this error and exit with a helpful message.
