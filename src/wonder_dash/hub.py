from __future__ import annotations

import sys
from datetime import datetime
from typing import Callable, Dict, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

try:  # allow running as module or script
    from .config import load_config
except ImportError:  # pragma: no cover - direct script execution fallback
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from config import load_config  # type: ignore

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.prompt import IntPrompt
    from rich.table import Table
    from rich.text import Text
except ModuleNotFoundError as exc:  # pragma: no cover
    print("WonderDash needs the 'rich' package. Install it with `pip install rich`.", file=sys.stderr)
    raise SystemExit(1) from exc

from .hub_utils import build_loading_layout, simple_table

console = Console()

TAGLINES = (
    "Telemetry tuned to the neon hum.",
    "Dashboards for the analog dreamer.",
    "Signals, stories, and synthwave static.",
    "Glow-stick ops for your cloud fleet.",
    "Metrics brewed with phosphor and jazz.",
)

MenuHandler = Callable[[], None]


def _aws_session():
    config = load_config()
    kwargs = {}
    if config.aws_profile:
        kwargs["profile_name"] = config.aws_profile
    return boto3.Session(**kwargs)


def _tagline() -> str:
    today = datetime.utcnow().timetuple().tm_yday
    return TAGLINES[today % len(TAGLINES)]


def _print_header(title: str) -> None:
    banner = Text()
    banner.append("╔═╡ ", style="cyan")
    banner.append("WonderDash", style="bold magenta")
    banner.append(" ╞═╗", style="cyan")
    subtitle = Text(_tagline(), style="dim white")
    console.print(Panel.fit(Text.assemble(banner, Text("\n"), subtitle), border_style="cyan", title=title, title_align="left"))


def _submenu_loop(title: str, color: str, options: Dict[int, Tuple[str, MenuHandler]]) -> None:
    while True:
        console.clear()
        _print_header(title)

        menu_table = Table.grid(padding=(0, 1))
        menu_table.add_column(justify="left", style=color)
        menu_table.add_column(justify="left")
        for key, (label, _) in sorted(options.items()):
            menu_table.add_row(Text(f"[{key}]", style=f"bold {color}"), Text(label))
        menu_table.add_row(Text("[0]", style=f"bold {color}"), Text("Back"))
        console.print(Panel(menu_table, border_style=color))

        choice = IntPrompt.ask("Select", default=0)
        if choice == 0:
            return
        entry = options.get(choice)
        if not entry:
            console.print("Invalid choice.", style="red")
            input("Press Enter to continue.")
            continue
        _, handler = entry
        handler()


def _stub(feature: str) -> None:
    console.print(Panel(f"{feature} is not implemented yet.", border_style="yellow"))
    input("Press Enter to return.")


def _menu(actions: Dict[int, Tuple[str, MenuHandler]]) -> None:
    console.clear()
    _print_header("Hub Console")

    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left", style="magenta")
    table.add_column(justify="left")
    for key, (label, _) in sorted(actions.items()):
        style = "magenta" if key else "cyan"
        table.add_row(Text(f"[{key}]", style=f"bold {style}"), Text(label))
    console.print(Panel(table, border_style="magenta"))


def _s3_menu() -> None:
    _submenu_loop(
        title="S3 Toolkit",
        color="blue",
        options={
            1: ("List buckets", _s3_list_buckets),
            2: ("Bucket analytics (coming soon)", lambda: _stub("Bucket analytics")),
        },
    )


def _ec2_menu() -> None:
    _submenu_loop(
        title="EC2 Toolkit",
        color="green",
        options={
            1: ("List instances", _ec2_list_instances),
            2: ("Instance actions (coming soon)", lambda: _stub("Instance actions")),
        },
    )


def _lambda_menu() -> None:
    _submenu_loop(
        title="Lambda Toolkit",
        color="magenta",
        options={
            1: ("List functions", _lambda_list_functions),
            2: ("Invocation stats (coming soon)", lambda: _stub("Invocation stats")),
        },
    )


def _s3_list_buckets() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("S3 Buckets", "blue")
        live.update(layout)
        try:
            session = _aws_session()
            s3 = session.client("s3")
            response = s3.list_buckets()
            buckets = response.get("Buckets", [])
            table = simple_table(["Bucket", "Created"])
            for bucket in buckets:
                name = bucket.get("Name", "?")
                created = bucket.get("CreationDate")
                when = created.strftime("%Y-%m-%d %H:%M") if created else "?"
                table.add_row(name, when)
            if not buckets:
                table.add_row("No buckets found", "")
            layout["body"].update(table)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style="red"))
        live.refresh()
    input("Press Enter to return.")


def _ec2_list_instances() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("EC2 Instances", "green")
        live.update(layout)
        try:
            session = _aws_session()
            ec2 = session.client("ec2")
            response = ec2.describe_instances()
            reservations = response.get("Reservations", [])
            table = simple_table(["Instance", "State", "Name", "Launched"])
            for reservation in reservations:
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId")
                    state = instance.get("State", {}).get("Name", "?")
                    launched = instance.get("LaunchTime")
                    launch_str = launched.strftime("%Y-%m-%d %H:%M") if launched else "?"
                    name_tag = next((tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"), "-")
                    table.add_row(instance_id, state, name_tag, launch_str)
            if not table.rows:
                table.add_row("No instances", "", "", "")
            layout["body"].update(table)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style="red"))
        live.refresh()
    input("Press Enter to return.")


def _lambda_list_functions() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("Lambda Functions", "magenta")
        live.update(layout)
        try:
            session = _aws_session()
            aws_lambda = session.client("lambda")
            paginator = aws_lambda.get_paginator("list_functions")
            table = simple_table(["Function", "Runtime", "Updated"])
            for page in paginator.paginate():
                for function in page.get("Functions", []):
                    name = function.get("FunctionName")
                    runtime = function.get("Runtime", "?")
                    updated = function.get("LastModified", "?")
                    table.add_row(name, runtime, updated)
            if not table.rows:
                table.add_row("No functions found", "", "")
            layout["body"].update(table)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style="red"))
        live.refresh()
    input("Press Enter to return.")


def _settings() -> None:
    config = load_config()
    console.print("Current configuration:")
    for key, value in config.to_dict().items():
        console.print(f"  {key}: {value}")
    input("Press Enter to return.")


def _launch_cloudfront() -> None:
    from .dashboard import run_dashboard

    config = load_config()
    run_dashboard(config)


def launch_hub() -> None:
    if not sys.stdin.isatty():
        print("WonderDash hub needs an interactive terminal. Run this from a shell.")
        return

    actions: Dict[int, Tuple[str, MenuHandler]] = {
        1: ("CloudFront Traffic", _launch_cloudfront),
        2: ("S3 Buckets", _s3_menu),
        3: ("EC2 Instances", _ec2_menu),
        4: ("Lambda Functions", _lambda_menu),
        5: ("Logs Snapshot (coming soon)", lambda: _stub("Logs snapshot")),
        6: ("Error Watch (coming soon)", lambda: _stub("Error watch")),
        7: ("Settings", _settings),
    }

    while True:
        _menu(actions)

        try:
            choice = IntPrompt.ask("Select an option", default=1)
        except EOFError:
            console.print("Interactive input is unavailable.", style="red")
            return

        if choice == 0:
            console.print("Goodbye.")
            return

        entry = actions.get(choice)
        if not entry:
            console.print("Invalid choice, try again.", style="red")
            input("Press Enter to continue.")
            continue
        _, handler = entry
        handler()


def main() -> None:
    launch_hub()


if __name__ == "__main__":  # pragma: no cover
    main()
