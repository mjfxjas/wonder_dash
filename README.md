# WonderDash

[![CI](https://github.com/mjfxjas/wonder_dash/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mjfxjas/wonder_dash/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/wonder-dash.svg)](https://pypi.org/project/wonder-dash/)

WonderDash is a neon-styled terminal console for AWS CloudFront and core services.  
It runs entirely in your shell and uses Rich for live, animated dashboards.

## Features
- **CloudFront dashboard** – live requests, bytes, cache hit rate, error rates, latency, health badge, and trend sparkline.
- **S3 toolkit** – bucket listing and analytics with object counts, storage sizes, and regions.
- **EC2 toolkit** – instance listing and management actions (start, stop, reboot).
- **Lambda toolkit** – function listing and invocation statistics with error rates and duration metrics.
- **Logs snapshot** – CloudWatch logs browser with filtering and event viewing.
- **Error watch** – real-time monitoring of ERROR patterns across log groups.
- **Settings & config viewer** – see the active WonderDash configuration right inside the hub.
- **Identity & exports** – check the active AWS caller identity and export the latest table to CSV or clipboard.
- **Theme toggle** – swap between "Night Drive" and "Terminal Green" palettes without leaving the terminal.
- Designed for AWS CLI users: drop into the hub and drive everything with keypresses.

## Prerequisites
- Python 3.9+
- AWS credentials (CLI profile or environment vars) with permission to call CloudFront, S3, EC2, Lambda, and CloudWatch.

## Install & Run
```bash
git clone https://github.com/mjfxjas/wonder_dash.git
cd wonder_dash

python3 -m venv .venv
source .venv/bin/activate

pip install .
wonder-dash hub
```

That launches the hub menu; choose `1` for the CloudFront dashboard or explore the AWS toolkits.  
Prefer running directly? Use `python -m wonder_dash.hub`.

## Smoke Test
Quick verification that install and CLI wiring are healthy:

```bash
python3 -m pip install --upgrade wonder-dash
wonder-dash --help
python3 -c "import wonder_dash; print(wonder_dash.__version__)"
```

## Security Checks
- CI runs Bandit static security analysis on `src/wonder_dash` (Python 3.11 job).
- Failing threshold is set to medium-or-higher severity/confidence.

```bash
bandit -r src/wonder_dash --severity-level medium --confidence-level medium
```

## Development Notes
- The package follows a `src/` layout; after editing run `pip install -e .` to reload changes.
- Requires `rich` and `boto3` (pulled in automatically by `pip install .`).
- WonderDash reads `~/.aws/credentials` by default; set `CF_DISTRIBUTION_ID`, `CF_PERIOD_SECONDS`, etc., for overrides.

## Changelog
See `CHANGELOG.md` for versioned release notes.

## License
MIT. See `LICENSE`.
