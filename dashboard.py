"""Terminal dashboard for CloudFront metrics."""

from __future__ import annotations

import os
import select
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .config import WonderConfig

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound
except ModuleNotFoundError as exc:  # pragma: no cover - informative guard
    print(
        "WonderDash dashboard requires boto3. Install it with `pip install boto3`.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.spinner import Spinner
    from rich.table import Table
    from rich.text import Text
except ModuleNotFoundError as exc:  # pragma: no cover - informative guard
    print(
        "WonderDash dashboard requires the 'rich' package. Install it with `pip install rich`.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

try:  # pragma: no cover - UNIX-only
    import termios
    import tty
except ModuleNotFoundError:  # pragma: no cover - non-UNIX
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]

try:  # pragma: no cover - Windows-only
    import msvcrt  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - non-Windows
    msvcrt = None  # type: ignore[assignment]

console = Console()


@dataclass(frozen=True)
class MetricSample:
    timestamp: datetime
    value: float


@dataclass(frozen=True)
class MetricWindow:
    samples: List[MetricSample]
    status: str
    messages: List[str]


def _session_from_config(config: WonderConfig) -> boto3.Session:
    kwargs = {}
    if config.aws_profile:
        kwargs["profile_name"] = config.aws_profile
    return boto3.Session(**kwargs)


def _cloudwatch_client(config: WonderConfig):
    session = _session_from_config(config)
    return session.client("cloudwatch", region_name=config.region)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    with suppress(ValueError):
        return max(1, int(raw))
    return default


def _inject_overrides(config: WonderConfig) -> WonderConfig:
    overrides = {
        "distribution_id": os.getenv("CF_DISTRIBUTION_ID"),
        "period_seconds": _env_int("CF_PERIOD_SECONDS", config.period_seconds),
        "window_minutes": _env_int("CF_WINDOW_MINUTES", config.window_minutes),
        "poll_seconds": _env_int("CF_POLL_SECONDS", config.poll_seconds),
        "region": os.getenv("CF_CW_REGION") or config.region,
    }
    copy = WonderConfig(
        aws_profile=os.getenv("CF_AWS_PROFILE") or config.aws_profile,
        distribution_id=overrides["distribution_id"] or config.distribution_id,
        region=overrides["region"],
        period_seconds=overrides["period_seconds"],
        window_minutes=overrides["window_minutes"],
        poll_seconds=overrides["poll_seconds"],
    )
    return copy


def fetch_request_series(
    client,
    distribution_id: str,
    period_seconds: int,
    window_minutes: int,
) -> MetricWindow:
    end = datetime.now(timezone.utc) - timedelta(seconds=period_seconds)
    start = end - timedelta(minutes=window_minutes)

    response = client.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "requests",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/CloudFront",
                        "MetricName": "Requests",
                        "Dimensions": [
                            {"Name": "DistributionId", "Value": distribution_id},
                            {"Name": "Region", "Value": "Global"},
                        ],
                    },
                    "Period": period_seconds,
                    "Stat": "Sum",
                },
                "ReturnData": True,
            }
        ],
        StartTime=start,
        EndTime=end,
        ScanBy="TimestampAscending",
        MaxDatapoints=1000,
    )

    results = response.get("MetricDataResults", [])
    if not results:
        return MetricWindow(samples=[], status="NoData", messages=[])

    result = results[0]
    timestamps = result.get("Timestamps", [])
    values = result.get("Values", [])
    status = result.get("StatusCode", "Unknown")

    raw_messages = result.get("Messages") or []
    messages: List[str] = []
    for entry in raw_messages:
        if isinstance(entry, dict):
            code = entry.get("Code") or "Message"
            value = entry.get("Value") or ""
            messages.append(f"{code}: {value}".strip())
        else:
            messages.append(str(entry))

    samples: List[MetricSample] = []
    for ts, value in zip(timestamps, values):
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        samples.append(MetricSample(timestamp=ts, value=float(value)))
    samples.sort(key=lambda sample: sample.timestamp)
    return MetricWindow(samples=samples, status=status, messages=messages)


def build_layout(
    window: MetricWindow,
    period_seconds: int,
    last_refresh: Optional[datetime],
    poll_seconds: int,
    remaining_seconds: Optional[float] = None,
) -> Layout:
    samples = list(window.samples)
    overview_panel = _overview_panel(samples, period_seconds)
    history_panel = _history_panel(samples)
    status_lines = [f"Metric status: {window.status or 'Unknown'}"]
    if not samples and window.status not in {"CloudWatchError", "CredentialsMissing"}:
        status_lines.append(
            "No datapoints in window. CloudFront metrics can lag by ~5 minutes—"
            "generate traffic or widen the window."
        )
    if window.messages:
        status_lines.extend(window.messages)

    if remaining_seconds is None:
        if last_refresh is not None:
            elapsed = (datetime.now(timezone.utc) - last_refresh).total_seconds()
            remaining_seconds = max(0.0, poll_seconds - elapsed)
        else:
            remaining_seconds = float(poll_seconds)

    status_panel = _status_panel(
        "\n".join(filter(None, status_lines)),
        remaining_seconds=remaining_seconds,
        poll_seconds=poll_seconds,
    )

    layout = Layout(name="root")
    layout.split_column(
        Layout(overview_panel, name="summary", size=12),
        Layout(history_panel, name="history"),
        Layout(status_panel, name="status", size=7),
    )
    return layout


def _overview_panel(samples: List[MetricSample], period_seconds: int) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="right")

    datapoints = len(samples)
    total_requests = sum(sample.value for sample in samples)
    latest = samples[-1].value if samples else 0.0

    window_minutes = max(datapoints, 1) * (period_seconds / 60)
    per_minute = total_requests / window_minutes if window_minutes else 0.0
    per_hour = per_minute * 60

    table.add_row("Window datapoints", f"{datapoints}")
    table.add_row("Total requests", f"{total_requests:,.0f}")
    table.add_row("Most recent period", f"{latest:,.0f}")
    table.add_row("Requests / minute", f"{per_minute:,.2f}")
    table.add_row("Requests / hour", f"{per_hour:,.0f}")

    if samples:
        first_ts = samples[0].timestamp.astimezone(timezone.utc)
        last_ts = samples[-1].timestamp.astimezone(timezone.utc)
        table.add_row("Window start (UTC)", first_ts.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Window end (UTC)", last_ts.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        table.add_row("Window start (UTC)", "—")
        table.add_row("Window end (UTC)", "—")

    return Panel(table, title="CloudFront Requests", border_style="cyan")


def _history_panel(samples: List[MetricSample]) -> Panel:
    chart = Table(show_header=False, box=None, expand=True, padding=(0, 1))
    chart.add_column("Time", justify="left", no_wrap=True)
    chart.add_column("Requests", justify="right")
    chart.add_column("Spark", justify="left")

    tail = samples[-30:]
    blocks = "▁▂▃▄▅▆▇█"

    if tail:
        max_val = max(sample.value for sample in tail) or 1.0
        for sample in tail:
            block_index = min(int((sample.value / max_val) * (len(blocks) - 1)), len(blocks) - 1)
            chart.add_row(
                sample.timestamp.strftime("%H:%M"),
                f"{sample.value:,.0f}",
                blocks[block_index],
            )
    else:
        return Panel(
            "Waiting for datapoints… CloudFront metrics trail by a few minutes.",
            title="Recent Periods",
            border_style="magenta",
        )

    return Panel(chart, title="Recent Periods", border_style="magenta")


def _status_panel(
    message: str,
    *,
    remaining_seconds: float,
    poll_seconds: int,
) -> Panel:
    grid = Table.grid(expand=True)
    remaining_display = max(0.0, remaining_seconds)
    if remaining_display == poll_seconds:
        spinner_text = f"Polling CloudWatch… interval {poll_seconds}s"
    else:
        spinner_text = f"Polling CloudWatch… next refresh in {remaining_display:0.1f}s"
    grid.add_row(Spinner("dots", text=spinner_text))

    message = message.strip()
    if message:
        grid.add_row(Text(message))

    grid.add_row(Text("Press Q to exit • Ctrl+C to abort", style="dim"))
    return Panel(grid, title="Status", border_style="yellow")


EXIT_KEYS = {"q", "Q"}


def _read_single_key(timeout: float) -> Optional[str]:
    if timeout <= 0:
        timeout = 0

    if msvcrt:  # pragma: no cover - Windows
        end_time = time.monotonic() + timeout
        while time.monotonic() < end_time:
            if msvcrt.kbhit():
                return msvcrt.getwch()
            time.sleep(0.05)
        return None

    if termios is None or tty is None or not sys.stdin.isatty():  # pragma: no cover
        time.sleep(timeout)
        return None

    fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(fd)
    except termios.error:  # pragma: no cover
        time.sleep(timeout)
        return None

    try:
        tty.setcbreak(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            return sys.stdin.read(1)
    except (OSError, termios.error):  # pragma: no cover
        return None
    finally:
        with suppress(termios.error):
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None


def _wait_for_next_poll(
    live: Live,
    window: MetricWindow,
    period_seconds: int,
    last_refresh: Optional[datetime],
    poll_seconds: int,
) -> bool:
    deadline = time.monotonic() + poll_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False

        key = _read_single_key(min(0.5, max(0.05, remaining)))
        if key and key in EXIT_KEYS:
            return True

        live.update(
            build_layout(
                window,
                period_seconds,
                last_refresh,
                poll_seconds,
                remaining_seconds=remaining,
            ),
            refresh=True,
        )


def run_dashboard(config: WonderConfig) -> None:
    if not config.distribution_id:
        console.print(
            "[red]No CloudFront distribution configured.[/red] "
            "Run `wonder-dash setup` first to capture settings."
        )
        raise SystemExit(1)

    config = _inject_overrides(config)
    client = _cloudwatch_client(config)
    refresh_hz = max(1, min(10, 60 // max(1, config.poll_seconds // 2)))

    window = MetricWindow(
        samples=[],
        status="Init",
        messages=[f"Watching distribution {config.distribution_id}"],
    )
    last_refresh: Optional[datetime] = None

    with Live(console=console, refresh_per_second=refresh_hz, screen=False) as live:
        live.update(
            build_layout(
                window,
                config.period_seconds,
                last_refresh,
                config.poll_seconds,
            ),
            refresh=True,
        )

        try:
            while True:
                try:
                    window = fetch_request_series(
                        client,
                        distribution_id=config.distribution_id,
                        period_seconds=config.period_seconds,
                        window_minutes=config.window_minutes,
                    )
                    last_refresh = datetime.now(timezone.utc)
                except ProfileNotFound as error:
                    window = MetricWindow(
                        samples=[],
                        status="CredentialsMissing",
                        messages=[f"AWS profile not found: {error}"],
                    )
                    last_refresh = datetime.now(timezone.utc)
                    console.log(f"Profile error: {error}")
                except NoCredentialsError as error:
                    window = MetricWindow(
                        samples=[],
                        status="CredentialsMissing",
                        messages=[
                            "AWS credentials not found.",
                            "Run `aws configure` or export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.",
                            str(error),
                        ],
                    )
                    last_refresh = datetime.now(timezone.utc)
                    console.log(f"Credentials error: {error}")
                except (ClientError, BotoCoreError) as error:
                    window = MetricWindow(
                        samples=[],
                        status="CloudWatchError",
                        messages=[str(error)],
                    )
                    last_refresh = datetime.now(timezone.utc)
                    console.log(f"CloudWatch error: {error}")

                live.update(
                    build_layout(
                        window,
                        config.period_seconds,
                        last_refresh,
                        config.poll_seconds,
                    ),
                    refresh=True,
                )

                if _wait_for_next_poll(
                    live,
                    window,
                    config.period_seconds,
                    last_refresh,
                    config.poll_seconds,
                ):
                    console.print("\n[cyan]Exit requested (q).[/cyan]")
                    break
        except KeyboardInterrupt:
            console.print("\n[cyan]Shutting down WonderDash…[/cyan]")
