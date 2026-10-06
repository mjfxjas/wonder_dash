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

Install from the shared [Homebrew tap](https://github.com/mjfxjas/homebrew-tap):

```bash
brew install mjfxjas/tap/wonder-dash
wonder-dash setup
wonder-dash hub
```

Homebrew manages Python and all dependencies, including AWS CRT. No virtual
environment activation is needed. AWS credentials and the appropriate IAM
permissions are still required.

For a Python CLI installation, pipx also manages the environment:

```bash
pipx install wonder-dash
wonder-dash hub
```

Version 0.1.4+ includes support for credentials created by `aws login`.
Upgrade with `brew upgrade mjfxjas/tap/wonder-dash` or `pipx upgrade wonder-dash`.

For development from source:

```bash
git clone https://github.com/mjfxjas/wonder_dash.git
cd wonder_dash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
wonder-dash hub
```

Choose `1` in the hub for the CloudFront dashboard. The hub also runs with
`python -m wonder_dash.hub`.

## Smoke Test
Quick verification that install and CLI wiring are healthy:

```bash
wonder-dash --help
wonder-dash --version
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
- CloudWatch metric queries consume every response page and retain scalar history across pages.
- Run offline regression tests after installing the package: `python -m unittest discover -s tests -v`.

## Changelog
See `CHANGELOG.md` for versioned release notes.

## License
MIT. See `LICENSE`.
