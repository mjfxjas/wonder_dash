# WonderDash Usage Guide

WonderDash ships as a Python CLI (`wonder-dash`). The entry point lives in `cli.py`, so every command eventually flows through that module.

## Installation

```bash
pip install -e .
# or build via hatch/uv according to pyproject.toml
```

Ensure `boto3`, `rich`, and AWS credentials are configured (`aws configure`).

## First Run

```bash
wonder-dash setup
```

The setup wizard (`wizard.py`) walks through:

1. Selecting or creating an AWS profile
2. Choosing a CloudFront distribution ID
3. Setting refresh intervals and UI theme

A JSON config is written to `~/.wonderdash/config.json`.

## Launching the Dashboard

```bash
wonder-dash dashboard
```

- Loads config via `config.load_config()`
- Builds a boto3 session
- Streams CloudFront, S3, Lambda, EC2, DynamoDB, and identity data into the Rich dashboard.

## Using the Hub Menu

```bash
wonder-dash hub
```

The hub (`hub.py`) offers menu-driven access to:

- Identity probe (STS `GetCallerIdentity`)
- S3 bucket summary
- CloudFront distribution stats
- Export and clipboard helpers
- Theme toggle

Use arrow keys or number keys to navigate. Press `q` to exit.

## Quick Commands

- `wonder-dash show-config` prints the resolved config and path.
- `wonder-dash list-distributions` lists CloudFront distributions for the configured profile and highlights the current selection.

## Troubleshooting

- Missing `boto3`: install with `pip install boto3`.
- Missing AWS credentials: run `aws configure` or export `AWS_PROFILE`/`AWS_ACCESS_KEY_ID`.
- Config read errors: delete `~/.wonderdash/config.json` and rerun `wonder-dash setup`.
