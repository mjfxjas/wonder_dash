"""Interactive setup wizard for WonderDash."""

from __future__ import annotations

import sys
from typing import List, Optional

from .config import WonderConfig, save_config

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound
except ModuleNotFoundError as exc:  # pragma: no cover - informative guard
    print(
        "WonderDash requires boto3 for setup. Install it with `pip install boto3`.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def _prompt(message: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    return input(f"{message}{suffix}: ").strip() or (default or "")


def _clean_ascii(value: str) -> str:
    return "".join(ch for ch in value if 32 <= ord(ch) <= 126)


def _prompt_int(message: str, default: int, *, min_value: int = 1) -> int:
    while True:
        raw = _prompt(message, str(default))
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value < min_value:
            print(f"Value must be at least {min_value}.")
            continue
        return value


def _confirm(message: str, default: bool = True) -> bool:
    prompt = "Y/n" if default else "y/N"
    value = input(f"{message} ({prompt}): ").strip().lower()
    if not value:
        return default
    return value.startswith("y")


def _probe_identity(session: boto3.Session) -> str:
    sts = session.client("sts")
    response = sts.get_caller_identity()
    account = response.get("Account")
    arn = response.get("Arn")
    return f"{arn} (account {account})"


def _list_distributions(session: boto3.Session) -> List[str]:
    client = session.client("cloudfront")
    paginator = client.get_paginator("list_distributions")
    distribution_ids: List[str] = []
    for page in paginator.paginate():
        items = page.get("DistributionList", {}).get("Items", [])
        for dist in items or []:
            distribution_ids.append(dist["Id"])
    return distribution_ids


def run_setup(existing: Optional[WonderConfig] = None) -> WonderConfig:
    """Prompt for configuration values and persist them."""
    print("=== WonderDash Setup ===")
    config = existing or WonderConfig()

    profile = _prompt("AWS profile to use (leave blank for default)", config.aws_profile)
    session_kwargs = {}
    if profile:
        session_kwargs["profile_name"] = profile
    try:
        session = boto3.Session(**session_kwargs)
        identity = _probe_identity(session)
        print(f"AWS identity: {identity}")
    except (NoCredentialsError, ProfileNotFound):
        print("Unable to locate credentials. Ensure `aws configure` has been run.")
        raise
    except (BotoCoreError, ClientError) as exc:
        print(f"Error validating credentials: {exc}")
        raise

    try:
        distribution_ids = _list_distributions(session)
    except (BotoCoreError, ClientError) as exc:
        print(f"Unable to list CloudFront distributions: {exc}")
        distribution_ids = []

    distribution_id = config.distribution_id or ""
    if distribution_ids:
        print("\nAvailable CloudFront distributions:")
        for idx, dist_id in enumerate(distribution_ids, start=1):
            marker = "*" if dist_id == distribution_id else " "
            print(f"  {idx:>2}. {dist_id} {marker}")

        if _confirm("Select distribution from list?", True):
            while True:
                choice = _prompt("Enter number", "")
                try:
                    index = int(choice)
                    if 1 <= index <= len(distribution_ids):
                        distribution_id = distribution_ids[index - 1]
                        break
                except ValueError:
                    pass
                print("Invalid selection. Try again.")

    while True:
        distribution_id = _prompt("CloudFront distribution ID", distribution_id or "")
        distribution_id = _clean_ascii(distribution_id)
        if distribution_id:
            break
        print("Distribution ID is required and must contain printable ASCII characters.")

    region = _prompt("CloudWatch region", config.region)
    period_seconds = _prompt_int("Metric period seconds (multiple of 60)", config.period_seconds, min_value=60)
    if period_seconds % 60 != 0:
        rounded = ((period_seconds + 59) // 60) * 60
        print(f"CloudFront requires 60-second increments; rounding to {rounded}.")
        period_seconds = rounded

    window_minutes = _prompt_int("Window minutes", config.window_minutes, min_value=1)
    poll_seconds = _prompt_int("Polling interval seconds", config.poll_seconds, min_value=1)

    config.aws_profile = profile or None
    config.distribution_id = distribution_id
    config.region = region
    config.period_seconds = period_seconds
    config.window_minutes = window_minutes
    config.poll_seconds = poll_seconds
    config.ensure_valid()

    path = save_config(config)
    print(f"\nConfiguration saved to {path}")
    return config
