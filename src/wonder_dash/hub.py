"""Menu router and interactive export hub for WonderDash."""

from __future__ import annotations

import csv
import io
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# imports config file
try:  # allow running as module or script
    from .config import load_config
except ImportError:  # pragma: no cover - direct script execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent))
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
from .ascii_art import get_wonder_dash_logo, get_compact_logo, get_welcome_message

console = Console()

LIGHT_STYLE: Dict[str, str] = {
    "header_border": "cyan",
    "accent": "magenta",
    "accent_alt": "bright_cyan",
    "s3": "blue",
    "ec2": "green",
    "lambda": "magenta",
    "success": "green",
    "warning": "yellow",
    "error": "red",
}

DARK_STYLE: Dict[str, str] = {
    "header_border": "bright_black",
    "accent": "white",
    "accent_alt": "bright_white",
    "s3": "bright_black",
    "ec2": "bright_black",
    "lambda": "white",
    "success": "white",
    "warning": "yellow",
    "error": "bright_red",
}

USE_DARK_THEME = False


def _style(key: str) -> str:
    palette = DARK_STYLE if USE_DARK_THEME else LIGHT_STYLE
    return palette.get(key, "magenta")


TAGLINES = (
    "Telemetry tuned to the neon hum.",
    "Dashboards for the analog dreamer.",
    "Signals, stories, and synthwave static.",
    "Glow-stick ops for your cloud fleet.",
    "Metrics brewed with phosphor and jazz.",
)

MenuHandler = Callable[[], None]


@dataclass
class ExportBundle:
    title: str
    headers: List[str]
    rows: List[List[str]]


LAST_EXPORT: Optional[ExportBundle] = None


def _record_export(title: str, headers: List[str], rows: List[List[str]]) -> None:
    global LAST_EXPORT
    LAST_EXPORT = ExportBundle(title=title, headers=headers, rows=rows)


def _who_am_i() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("STS Identity", _style("accent"))
        live.update(layout)
        try:
            session = _aws_session()
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            headers = ["Field", "Value"]
            rows = [
                ["Account", identity.get("Account", "?")],
                ["ARN", identity.get("Arn", "?")],
                ["User ID", identity.get("UserId", "?")],
            ]
            table = simple_table(headers, header_style=_style("accent_alt"))
            for field, value in rows:
                table.add_row(field, value)
            layout["body"].update(table)
            _record_export("STS Identity", headers, rows)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
        live.refresh()
    input("Press Enter to return.")


def _export_menu() -> None:
    if not LAST_EXPORT:
        console.print(Panel("No exportable data yet.", border_style=_style("warning")))
        input("Press Enter to return.")
        return

    while True:
        console.clear()
        _print_header("Export Data")
        bundle = LAST_EXPORT
        summary = Table.grid(padding=(0, 1))
        summary.add_column(style=_style("accent"))
        summary.add_column()
        summary.add_row("Title", bundle.title)
        summary.add_row("Rows", str(len(bundle.rows)))
        summary.add_row("Columns", str(len(bundle.headers)))
        console.print(Panel(summary, border_style=_style("accent")))

        options = Table.grid(padding=(0, 1))
        options.add_column(justify="left", style=_style("accent"))
        options.add_column(justify="left", style=_style("accent_alt"))
        options.add_row("[1]", "Save as CSV")
        options.add_row("[2]", "Copy table to clipboard")
        options.add_row("[0]", "Back")
        console.print(Panel(options, border_style=_style("accent")))

        choice = IntPrompt.ask("Select", default=0)
        if choice == 0:
            return
        if choice == 1:
            _export_to_csv(bundle)
        elif choice == 2:
            _export_to_clipboard(bundle)
        else:
            console.print("Invalid choice.", style=_style("warning"))
            input("Press Enter to continue.")


def _export_to_csv(bundle: ExportBundle) -> None:
    default_name = f"{bundle.title.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    console.print(f"Default file: {default_name}")
    path_input = input("Save as (leave blank for default): ").strip()
    path = Path(path_input or default_name).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(bundle.headers)
            writer.writerows(bundle.rows)
        console.print(f"Saved to {path}", style=_style("success"))
    except OSError as error:
        console.print(f"Failed to save: {error}", style=_style("error"))
    input("Press Enter to continue.")


def _export_to_clipboard(bundle: ExportBundle) -> None:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(bundle.headers)
    writer.writerows(bundle.rows)
    payload = stream.getvalue()
    try:
        subprocess.run(["pbcopy"], input=payload, text=True, check=True)
        console.print("Copied table to clipboard (CSV format).", style=_style("success"))
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        console.print(f"Clipboard copy failed: {error}", style=_style("error"))
    input("Press Enter to continue.")


def _toggle_dark_mode() -> None:
    global USE_DARK_THEME
    USE_DARK_THEME = not USE_DARK_THEME
    mode = "Dark" if USE_DARK_THEME else "Light"
    console.print(f"Switched to {mode} theme.", style=_style("accent"))
    input("Press Enter to continue.")
def _aws_session():
    config = load_config()
    kwargs = {}
    if config.aws_profile:
        kwargs["profile_name"] = config.aws_profile
    return boto3.Session(**kwargs)


def _tagline() -> str:
    today = datetime.utcnow().timetuple().tm_yday
    return TAGLINES[today % len(TAGLINES)]


def _print_header(title: str, show_logo: bool = False) -> None:
    if show_logo:
        # Show full ASCII art logo for main menu
        try:
            logo = get_wonder_dash_logo()
            console.print(logo)
            console.print()
            welcome = get_welcome_message()
            console.print(welcome, justify="center")
            console.print()
        except Exception:
            # Fallback to compact logo if full logo fails
            logo = get_compact_logo()
            console.print(logo)
            console.print()
    else:
        # Original compact header for submenus
        banner = Text()
        banner.append("╔═╡ ", style=_style("accent_alt"))
        banner.append("WonderDash", style=f"bold {_style('accent')}")
        banner.append(" ╞═╗", style=_style("accent_alt"))
        subtitle = Text(_tagline(), style="dim white")
        console.print(
            Panel.fit(
                Text.assemble(banner, Text("\n"), subtitle),
                border_style=_style("header_border"),
                title=title,
                title_align="left",
            )
        )


def _submenu_loop(title: str, color: str, options: Dict[int, Tuple[str, MenuHandler]]) -> None:
    while True:
        console.clear()
        _print_header(title)

        menu_table = Table.grid(padding=(0, 1))
        menu_table.add_column(justify="left", style=color)
        menu_table.add_column(justify="left", style=_style("accent_alt"))
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
    console.print(Panel(f"{feature} is not implemented yet.", border_style=_style("warning")))
    input("Press Enter to return.")


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024.0 or unit == "PB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{int(size)} B"


def _clean_message(message: str, max_len: int = 120) -> str:
    cleaned = " ".join(message.split())
    if len(cleaned) > max_len:
        return f"{cleaned[: max_len - 3]}..."
    return cleaned


def _format_timestamp(epoch_ms: Optional[int]) -> str:
    if epoch_ms is None:
        return "?"
    from datetime import timezone
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _menu(actions: Dict[int, Tuple[str, MenuHandler]]) -> None:
    console.clear()
    _print_header("Hub Console", show_logo=True)

    accent = _style("accent")
    accent_alt = _style("accent_alt")
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left", style=accent)
    table.add_column(justify="left", style=accent_alt)
    for key, (label, _) in sorted(actions.items()):
        table.add_row(Text(f"[{key}]", style=f"bold {accent}"), Text(label))
    table.add_row(Text("[0]", style=f"bold {accent_alt}"), Text("Exit"))
    console.print(Panel(table, border_style=accent))


def _s3_menu() -> None:
    _submenu_loop(
        title="S3 Toolkit",
        color=_style("s3"),
        options={
            1: ("List buckets", _s3_list_buckets),
            2: ("Bucket analytics", _s3_bucket_analytics),
        },
    )


def _ec2_menu() -> None:
    _submenu_loop(
        title="EC2 Toolkit",
        color=_style("ec2"),
        options={
            1: ("List instances", _ec2_list_instances),
            2: ("Instance actions", _ec2_instance_actions),
        },
    )


def _ec2_instance_actions() -> None:
    _submenu_loop(
        title="EC2 Instance Actions",
        color=_style("ec2"),
        options={
            1: ("Start instance", lambda: _ec2_action("start")),
            2: ("Stop instance", lambda: _ec2_action("stop")),
            3: ("Reboot instance", lambda: _ec2_action("reboot")),
        },
    )


def _ec2_action(action: str) -> None:
    console.print(f"Enter instance ID for {action}:")
    instance_id = input().strip()
    if not instance_id:
        console.print("No instance ID provided.", style=_style("warning"))
        input("Press Enter to return.")
        return
    
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout(f"EC2 {action.title()}", _style("ec2"))
        live.update(layout)
        try:
            session = _aws_session()
            ec2 = session.client("ec2")
            
            if action == "start":
                ec2.start_instances(InstanceIds=[instance_id])
            elif action == "stop":
                ec2.stop_instances(InstanceIds=[instance_id])
            elif action == "reboot":
                ec2.reboot_instances(InstanceIds=[instance_id])
            
            layout["body"].update(Panel(f"Instance {instance_id} {action} initiated.", border_style=_style("success")))
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
        live.refresh()
    input("Press Enter to return.")


def _lambda_menu() -> None:
    _submenu_loop(
        title="Lambda Toolkit",
        color=_style("lambda"),
        options={
            1: ("List functions", _lambda_list_functions),
            2: ("Invocation stats", _lambda_invocation_stats),
        },
    )


def _logs_snapshot() -> None:
    prefix = input("Log group prefix (leave blank for all): ").strip()
    max_groups = max(1, IntPrompt.ask("Max groups to list", default=20))
    config = load_config()
    logs = _aws_session().client("logs", region_name=config.region)
    groups: List[Dict[str, object]] = []

    error_message: Optional[str] = None
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("CloudWatch Logs", _style("accent"))
        live.update(layout)
        try:
            paginator = logs.get_paginator("describe_log_groups")
            kwargs: Dict[str, object] = {"PaginationConfig": {"MaxItems": max_groups}}
            if prefix:
                kwargs["logGroupNamePrefix"] = prefix
            for page in paginator.paginate(**kwargs):
                groups.extend(page.get("logGroups", []))
            groups = groups[:max_groups]
            if not groups:
                layout["body"].update(Panel("No log groups found.", border_style=_style("warning")))
            else:
                table = simple_table(
                    ["Index", "Log Group", "Retention", "Stored"],
                    header_style=_style("accent_alt"),
                )
                for idx, group in enumerate(groups, start=1):
                    name = group.get("logGroupName", "?")
                    retention = group.get("retentionInDays")
                    retention_label = f"{retention}d" if retention else "Never"
                    stored = _format_bytes(int(group.get("storedBytes") or 0))
                    table.add_row(str(idx), str(name), retention_label, stored)
                layout["body"].update(table)
        except (ClientError, BotoCoreError) as error:
            error_message = str(error)
            layout["body"].update(Panel(error_message, border_style=_style("error")))
        live.refresh()

    if error_message:
        input("Press Enter to return.")
        return

    if not groups:
        input("Press Enter to return.")
        return

    while True:
        choice = IntPrompt.ask("Select log group (0 to cancel)", default=1)
        if choice == 0:
            return
        if 1 <= choice <= len(groups):
            break
        console.print("Invalid choice.", style=_style("warning"))

    group_name = str(groups[choice - 1].get("logGroupName", "?"))
    lookback_minutes = max(1, IntPrompt.ask("Look back minutes", default=15))
    max_events = max(1, IntPrompt.ask("Max events", default=25))

    snapshot_error: Optional[str] = None
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout(f"Logs Snapshot: {group_name}", _style("accent"))
        live.update(layout)
        try:
            end = datetime.now()
            from datetime import timezone
            end = end.replace(tzinfo=timezone.utc)
            start = end - timedelta(minutes=lookback_minutes)
            response = logs.filter_log_events(
                logGroupName=group_name,
                startTime=int(start.timestamp() * 1000),
                endTime=int(end.timestamp() * 1000),
                limit=max_events,
                interleaved=True,
            )
            events = response.get("events", [])
            headers = ["Time (UTC)", "Stream", "Message"]
            rows: List[List[str]] = []
            table = simple_table(headers, header_style=_style("accent_alt"))
            if events:
                for event in events:
                    timestamp = _format_timestamp(event.get("timestamp"))
                    stream = str(event.get("logStreamName", "?"))
                    message = _clean_message(str(event.get("message", "")))
                    table.add_row(timestamp, stream, message)
                    rows.append([timestamp, stream, message])
            else:
                table.add_row("No events found", "", "")
                rows.append(["No events found", "", ""])
            layout["body"].update(table)
            _record_export(f"Logs Snapshot: {group_name}", headers, rows)
        except (ClientError, BotoCoreError) as error:
            snapshot_error = str(error)
            layout["body"].update(Panel(snapshot_error, border_style=_style("error")))
        live.refresh()
    if snapshot_error:
        input("Press Enter to return.")
        return
    input("Press Enter to return.")


def _lambda_invocation_stats() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("Lambda Invocation Stats", _style("lambda"))
        live.update(layout)
        try:
            session = _aws_session()
            cloudwatch = session.client("cloudwatch")
            aws_lambda = session.client("lambda")
            
            # Get functions first
            functions_response = aws_lambda.list_functions(MaxItems=10)
            functions = functions_response.get("Functions", [])
            
            headers = ["Function", "Invocations", "Errors", "Duration (ms)"]
            rows: List[List[str]] = []
            table = simple_table(headers, header_style=_style("accent_alt"))
            
            from datetime import datetime, timedelta
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            for function in functions:
                name = function.get("FunctionName")
                try:
                    # Get invocation count
                    inv_response = cloudwatch.get_metric_statistics(
                        Namespace="AWS/Lambda",
                        MetricName="Invocations",
                        Dimensions=[{"Name": "FunctionName", "Value": name}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,
                        Statistics=["Sum"]
                    )
                    invocations = int(inv_response["Datapoints"][0]["Sum"]) if inv_response["Datapoints"] else 0
                    
                    # Get error count
                    err_response = cloudwatch.get_metric_statistics(
                        Namespace="AWS/Lambda",
                        MetricName="Errors",
                        Dimensions=[{"Name": "FunctionName", "Value": name}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,
                        Statistics=["Sum"]
                    )
                    errors = int(err_response["Datapoints"][0]["Sum"]) if err_response["Datapoints"] else 0
                    
                    # Get average duration
                    dur_response = cloudwatch.get_metric_statistics(
                        Namespace="AWS/Lambda",
                        MetricName="Duration",
                        Dimensions=[{"Name": "FunctionName", "Value": name}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,
                        Statistics=["Average"]
                    )
                    duration = int(dur_response["Datapoints"][0]["Average"]) if dur_response["Datapoints"] else 0
                    
                    table.add_row(name, str(invocations), str(errors), str(duration))
                    rows.append([name, str(invocations), str(errors), str(duration)])
                except Exception:
                    table.add_row(name, "N/A", "N/A", "N/A")
                    rows.append([name, "N/A", "N/A", "N/A"])
            
            if not functions:
                table.add_row("No functions found", "0", "0", "0")
                rows.append(["No functions found", "0", "0", "0"])
            
            layout["body"].update(table)
            _record_export("Lambda Invocation Stats", headers, rows)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
        live.refresh()
    input("Press Enter to return.")


def _s3_bucket_analytics() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("S3 Bucket Analytics", _style("s3"))
        live.update(layout)
        try:
            session = _aws_session()
            s3 = session.client("s3")
            
            response = s3.list_buckets()
            buckets = response.get("Buckets", [])
            
            headers = ["Bucket", "Objects", "Size (MB)", "Region"]
            rows: List[List[str]] = []
            table = simple_table(headers, header_style=_style("accent_alt"))
            
            for bucket in buckets[:10]:  # Limit to 10 buckets
                name = bucket.get("Name", "")
                try:
                    # Get bucket location
                    location = s3.get_bucket_location(Bucket=name)
                    region = location.get("LocationConstraint") or "us-east-1"
                    
                    # Get object count and size
                    objects_response = s3.list_objects_v2(Bucket=name, MaxKeys=1000)
                    objects = objects_response.get("KeyCount", 0)
                    
                    # Calculate total size
                    total_size = 0
                    if "Contents" in objects_response:
                        total_size = sum(obj.get("Size", 0) for obj in objects_response["Contents"])
                    
                    size_mb = round(total_size / 1024 / 1024, 2)
                    
                    table.add_row(name, str(objects), str(size_mb), region)
                    rows.append([name, str(objects), str(size_mb), region])
                except Exception as e:
                    table.add_row(name, "Access denied", "N/A", "N/A")
                    rows.append([name, "Access denied", "N/A", "N/A"])
            
            if not buckets:
                table.add_row("No buckets found", "0", "0", "N/A")
                rows.append(["No buckets found", "0", "0", "N/A"])
            
            layout["body"].update(table)
            _record_export("S3 Bucket Analytics", headers, rows)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
        live.refresh()
    input("Press Enter to return.")


def _s3_list_buckets() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("S3 Buckets", _style("s3"))
        live.update(layout)
        try:
            session = _aws_session()
            s3 = session.client("s3")
            response = s3.list_buckets()
            buckets = response.get("Buckets", [])
            headers = ["Bucket", "Created"]
            rows: List[List[str]] = []
            table = simple_table(headers, header_style=_style("accent_alt"))
            for bucket in buckets:
                name = bucket.get("Name", "?")
                created = bucket.get("CreationDate")
                when = created.strftime("%Y-%m-%d %H:%M") if created else "?"
                table.add_row(name, when)
                rows.append([name, when])
            if not buckets:
                table.add_row("No buckets found", "")
                rows.append(["No buckets found", ""])
            layout["body"].update(table)
            _record_export("S3 Buckets", headers, rows)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
        live.refresh()
    input("Press Enter to return.")


def _ec2_list_instances() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("EC2 Instances", _style("ec2"))
        live.update(layout)
        try:
            session = _aws_session()
            ec2 = session.client("ec2")
            response = ec2.describe_instances()
            reservations = response.get("Reservations", [])
            headers = ["Instance", "State", "Name", "Launched"]
            rows: List[List[str]] = []
            table = simple_table(headers, header_style=_style("accent_alt"))
            for reservation in reservations:
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId")
                    state = instance.get("State", {}).get("Name", "?")
                    launched = instance.get("LaunchTime")
                    launch_str = launched.strftime("%Y-%m-%d %H:%M") if launched else "?"
                    name_tag = next((tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"), "-")
                    table.add_row(instance_id, state, name_tag, launch_str)
                    rows.append([instance_id, state, name_tag, launch_str])
            if not table.rows:
                table.add_row("No instances", "", "", "")
                rows.append(["No instances", "", "", ""])
            layout["body"].update(table)
            _record_export("EC2 Instances", headers, rows)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
        live.refresh()
    input("Press Enter to return.")


def _lambda_list_functions() -> None:
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        layout = build_loading_layout("Lambda Functions", _style("lambda"))
        live.update(layout)
        try:
            session = _aws_session()
            aws_lambda = session.client("lambda")
            paginator = aws_lambda.get_paginator("list_functions")
            headers = ["Function", "Runtime", "Updated"]
            rows: List[List[str]] = []
            table = simple_table(headers, header_style=_style("accent_alt"))
            for page in paginator.paginate():
                for function in page.get("Functions", []):
                    name = function.get("FunctionName")
                    runtime = function.get("Runtime", "?")
                    updated = function.get("LastModified", "?")
                    table.add_row(name, runtime, updated)
                    rows.append([name, runtime, updated])
            if not table.rows:
                table.add_row("No functions found", "", "")
                rows.append(["No functions found", "", ""])
            layout["body"].update(table)
            _record_export("Lambda Functions", headers, rows)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
        live.refresh()
    input("Press Enter to return.")


def _error_watch() -> None:
    with Live(console=console, refresh_per_second=2, screen=False) as live:
        layout = build_loading_layout("Error Watch", _style("error"))
        live.update(layout)
        try:
            session = _aws_session()
            logs = session.client("logs")
            
            # Get recent log groups
            response = logs.describe_log_groups(limit=10)
            log_groups = response.get("logGroups", [])
            
            headers = ["Log Group", "Error Count", "Latest Error"]
            rows: List[List[str]] = []
            table = simple_table(headers, header_style=_style("accent_alt"))
            
            from datetime import datetime, timedelta
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            for log_group in log_groups[:5]:  # Check top 5 groups
                group_name = log_group.get("logGroupName", "")
                try:
                    # Search for ERROR patterns
                    search_response = logs.filter_log_events(
                        logGroupName=group_name,
                        startTime=int(start_time.timestamp() * 1000),
                        endTime=int(end_time.timestamp() * 1000),
                        filterPattern="ERROR",
                        limit=10
                    )
                    events = search_response.get("events", [])
                    error_count = len(events)
                    latest_error = events[0].get("message", "")[:50] + "..." if events else "None"
                    
                    style = _style("error") if error_count > 0 else _style("success")
                    table.add_row(
                        Text(group_name, style=style),
                        Text(str(error_count), style=style),
                        Text(latest_error, style="dim white")
                    )
                    rows.append([group_name, str(error_count), latest_error])
                except Exception:
                    table.add_row(group_name, "Access denied", "")
                    rows.append([group_name, "Access denied", ""])
            
            if not log_groups:
                table.add_row("No log groups found", "0", "")
                rows.append(["No log groups found", "0", ""])
            
            layout["body"].update(table)
            _record_export("Error Watch", headers, rows)
        except (ClientError, BotoCoreError) as error:
            layout["body"].update(Panel(str(error), border_style=_style("error")))
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
        5: ("Logs Snapshot", _logs_snapshot),
        6: ("Error Watch", _error_watch),
        7: ("Settings", _settings),
        8: ("Who am I", _who_am_i),
        9: ("Export last table", _export_menu),
        10: ("Toggle dark theme", _toggle_dark_mode),
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
