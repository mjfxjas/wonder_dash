# WonderDash

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
cd wonder_dash_repo

python3 -m venv .venv
source .venv/bin/activate

pip install .
wonder-dash hub
```

That launches the hub menu; choose `1` for the CloudFront dashboard or explore the AWS toolkits.  
Prefer running directly? Use `python -m wonder_dash.hub`.

## Development Notes
- The package follows a `src/` layout; after editing run `pip install -e .` to reload changes.
- Requires `rich` and `boto3` (pulled in automatically by `pip install .`).
- WonderDash reads `~/.aws/credentials` by default; set `CF_DISTRIBUTION_ID`, `CF_PERIOD_SECONDS`, etc., for overrides.

## License
MIT License © 2025 Jonathan Schimpf