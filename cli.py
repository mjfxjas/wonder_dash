"""Command-line interface for WonderDash."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from .config import WonderConfig, config_path, load_config, save_config


def _require_boto3():
    try:
        import boto3  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover
        print("This command requires boto3. Install it with `pip install boto3`.", file=sys.stderr)
        raise SystemExit(1) from exc


def cmd_setup(args: argparse.Namespace) -> None:
    from .wizard import run_setup

    existing = None
    try:
        existing = load_config()
    except RuntimeError:
        existing = None
    run_setup(existing)


def cmd_dashboard(args: argparse.Namespace) -> None:
    from .dashboard import run_dashboard

    config = load_config()
    run_dashboard(config)


def cmd_show_config(args: argparse.Namespace) -> None:
    try:
        config = load_config()
    except RuntimeError as exc:
        print(f"Failed to read config: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    path = config_path()
    data = config.to_dict()
    print(f"Config path: {path}")
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_list_distributions(args: argparse.Namespace) -> None:
    _require_boto3()
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound

    config = load_config()
    session_kwargs = {}
    if config.aws_profile:
        session_kwargs["profile_name"] = config.aws_profile

    try:
        session = boto3.Session(**session_kwargs)
        cf = session.client("cloudfront")
        paginator = cf.get_paginator("list_distributions")
        found = False
        for page in paginator.paginate():
            for dist in page.get("DistributionList", {}).get("Items", []) or []:
                found = True
                marker = "*" if dist["Id"] == config.distribution_id else " "
                aliases = dist.get("Aliases", {}).get("Items", [])
                alias_str = ", ".join(aliases) if aliases else "-"
                print(f"{dist['Id']} {marker}  Origins: {dist['Origins']['Quantity']}  Aliases: {alias_str}")
        if not found:
            print("No distributions returned for this account.")
    except (ProfileNotFound, NoCredentialsError):
        print("Unable to locate AWS credentials/profile. Run `aws configure`.", file=sys.stderr)
        raise SystemExit(1)
    except (BotoCoreError, ClientError) as exc:
        print(f"Error listing distributions: {exc}", file=sys.stderr)
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wonder-dash",
        description="WonderDash – CloudFront request dashboard and setup assistant.",
    )
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser("setup", help="Run the interactive setup wizard.")
    setup_parser.set_defaults(func=cmd_setup)

    dash_parser = subparsers.add_parser("dashboard", help="Launch the terminal dashboard.")
    dash_parser.set_defaults(func=cmd_dashboard)

    show_parser = subparsers.add_parser("show-config", help="Display current configuration.")
    show_parser.set_defaults(func=cmd_show_config)

    list_parser = subparsers.add_parser("list-distributions", help="List CloudFront distributions for the configured profile.")
    list_parser.set_defaults(func=cmd_list_distributions)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not hasattr(args, "func") or args.func is None:
        parser.print_help()
        return 1

    args.func(args)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
