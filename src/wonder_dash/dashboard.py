"""Terminal dashboard for CloudFront metrics."""

from __future__ import annotations

import os
import select
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import fmean
from typing import Dict, List, Optional

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


@dataclass(frozen=True)
class ScalarMetric:
    label: str
    unit: str
    values: List[float]
    timestamps: List[datetime]

    @property
    def latest(self) -> float:
        return self.values[-1] if self.values else 0.0

    @property
    def total(self) -> float:
        return sum(self.values)


@dataclass(frozen=True)
class HealthStatus:
    label: str
    detail: str
    style: str
    badge: str


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
    *,
    scalars: Optional[Dict[str, ScalarMetric]] = None,
) -> MetricWindow:
    end = datetime.now(timezone.utc) - timedelta(seconds=period_seconds)
    start = end - timedelta(minutes=window_minutes)

    metric_specs = {
        "requests": {"metric": "Requests", "stat": "Sum", "unit": "Count", "label": "Requests"},
        "bytes_downloaded": {
            "metric": "BytesDownloaded",
            "stat": "Sum",
            "unit": "Bytes",
            "label": "Bytes Downloaded",
        },
        "bytes_uploaded": {
            "metric": "BytesUploaded",
            "stat": "Sum",
            "unit": "Bytes",
            "label": "Bytes Uploaded",
        },
        "errors_4xx": {
            "metric": "4xxErrorRate",
            "stat": "Average",
            "unit": "Percent",
            "label": "4xx Error Rate",
        },
        "errors_5xx": {
            "metric": "5xxErrorRate",
            "stat": "Average",
            "unit": "Percent",
            "label": "5xx Error Rate",
        },
        "total_errors": {
            "metric": "TotalErrorRate",
            "stat": "Average",
            "unit": "Percent",
            "label": "Total Error Rate",
        },
        "origin_latency": {
            "metric": "OriginLatency",
            "stat": "Average",
            "unit": "Milliseconds",
            "label": "Origin Latency",
        },
        "availability": {
            "metric": "Availability",
            "stat": "Average",
            "unit": "Percent",
            "label": "Availability",
        },
        "cache_hit": {
            "metric": "CacheHitRate",
            "stat": "Average",
            "unit": "Percent",
            "label": "Cache Hit Rate",
        },
    }

    queries = []
    for key, spec in metric_specs.items():
        queries.append(
            {
                "Id": key,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/CloudFront",
                        "MetricName": spec["metric"],
                        "Dimensions": [
                            {"Name": "DistributionId", "Value": distribution_id},
                            {"Name": "Region", "Value": "Global"},
                        ],
                    },
                    "Period": period_seconds,
                    "Stat": spec["stat"],
                },
                "ReturnData": True,
            }
        )

    response = client.get_metric_data(
        MetricDataQueries=queries,
        StartTime=start,
        EndTime=end,
        ScanBy="TimestampAscending",
        MaxDatapoints=1000,
    )

    results = response.get("MetricDataResults", [])
    if not results:
        if scalars is not None:
            scalars.clear()
        return MetricWindow(samples=[], status="NoData", messages=[])

    samples: List[MetricSample] = []
    scalar_store: Dict[str, ScalarMetric] = {}
    status = "Unknown"
    messages: List[str] = []

    for result in results:
        metric_id = result.get("Id", "")
        timestamps = [
            datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
            for ts in result.get("Timestamps", [])
        ]
        values = [float(v) for v in result.get("Values", [])]
        status = result.get("StatusCode", status)

        for entry in result.get("Messages") or []:
            if isinstance(entry, dict):
                code = entry.get("Code") or "Message"
                value = entry.get("Value") or ""
                messages.append(f"{code}: {value}".strip())
            else:
                messages.append(str(entry))

        if metric_id == "requests":
            samples.extend(MetricSample(timestamp=ts, value=val) for ts, val in zip(timestamps, values))
        else:
            spec = metric_specs.get(metric_id)
            if spec:
                scalar_store[metric_id] = ScalarMetric(
                    label=spec.get("label", metric_id.replace("_", " ").title()),
                    unit=spec["unit"],
                    values=values,
                    timestamps=timestamps,
                )

    samples.sort(key=lambda sample: sample.timestamp)
    if scalars is not None:
        scalars.clear()
        scalars.update(scalar_store)
    return MetricWindow(samples=samples, status=status, messages=messages)


def build_layout(
    window: MetricWindow,
    period_seconds: int,
    last_refresh: Optional[datetime],
    poll_seconds: int,
    remaining_seconds: Optional[float] = None,
    *,
    header: Panel,
    scalars: Optional[Dict[str, ScalarMetric]] = None,
) -> Layout:
    samples = list(window.samples)
    overview_panel = _overview_panel(samples, period_seconds)
    history_panel = _history_panel(samples)
    metrics_panel = _metrics_panel(scalars or {})
    recent_panel = _recent_panel(samples)
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
        Layout(header, name="header", size=5),
        Layout(overview_panel, name="summary", size=10),
        Layout(recent_panel, name="recent", size=7),
        Layout(history_panel, name="history"),
        Layout(metrics_panel, name="metrics", size=9),
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


def _format_bytes(value: float) -> str:
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:,.2f} {unit}"
        value /= 1024
    return f"{value:,.2f} Bytes"


def _metrics_panel(metrics: Dict[str, ScalarMetric]) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="right")

    if not metrics:
        table.add_row("No supporting metrics yet.", "")
        return Panel(table, title="Additional Metrics", border_style="blue")

    def add_row(label: str, value: str) -> None:
        table.add_row(label, value)

    groups = [
        ("Throughput", ["bytes_downloaded", "bytes_uploaded"]),
        ("Reliability", ["availability", "total_errors", "errors_4xx", "errors_5xx"]),
        ("Latency", ["origin_latency"]),
        ("Cache", ["cache_hit"]),
    ]

    for group, keys in groups:
        items = [metrics.get(key) for key in keys if metrics.get(key)]
        if not items:
            continue
        add_row(Text(group, style="bold cyan"), "")
        for metric in items:
            bullet = "› "
            if metric.unit == "Bytes":
                add_row(f"{bullet}{metric.label} (latest)", _format_bytes(metric.latest))
                add_row("  Window total", _format_bytes(metric.total))
            elif metric.unit == "Milliseconds":
                avg = fmean(metric.values) if metric.values else 0.0
                add_row(f"{bullet}{metric.label}", f"{metric.latest:,.0f} ms")
                add_row("  Window avg", f"{avg:,.0f} ms")
            elif metric.unit == "Percent":
                avg = fmean(metric.values) if metric.values else 0.0
                add_row(f"{bullet}{metric.label}", f"{metric.latest:,.2f}%")
                add_row("  Window avg", f"{avg:,.2f}%")
            else:
                add_row(f"{bullet}{metric.label}", f"{metric.latest:,.2f}")
                add_row("  Window total", f"{metric.total:,.2f}")
        add_row("", "")

    return Panel(table, title="Additional Metrics", border_style="blue")


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


def _recent_panel(samples: List[MetricSample]) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="right")

    if not samples:
        table.add_row("Latest", "—")
        table.add_row("Change", "—")
        table.add_row("Window avg", "—")
        return Panel(table, title="Request Snapshots", border_style="green")

    latest = samples[-1].value
    prev = samples[-2].value if len(samples) > 1 else 0.0
    change = latest - prev
    avg = sum(s.value for s in samples) / len(samples)

    if change > 0:
        change_symbol = "+"
        change_style = "green"
    elif change < 0:
        change_symbol = "-"
        change_style = "red"
    else:
        change_symbol = "="
        change_style = "yellow"
    table.add_row("Latest requests", f"{latest:,.0f}")
    table.add_row("Change", Text(f"{change_symbol}{abs(change):,.0f}", style=change_style))
    table.add_row("Window avg", f"{avg:,.0f}")

    return Panel(table, title="Request Snapshots", border_style="green")


def _compute_health(metrics: Dict[str, ScalarMetric], samples: List[MetricSample]) -> HealthStatus:
    if not metrics and not samples:
        return HealthStatus("Monitoring", "Waiting for metrics", "yellow", badge="? Monitoring")

    severity = 0
    notes: List[str] = []

    availability = metrics.get("availability")
    if availability and availability.values:
        latest = availability.latest
        if latest < 98.0:
            severity = max(severity, 2)
            notes.append(f"Availability {latest:,.2f}%")
        elif latest < 99.5:
            severity = max(severity, 1)
            notes.append(f"Availability {latest:,.2f}%")

    errors = metrics.get("total_errors")
    if errors and errors.values:
        latest = errors.latest
        if latest > 5:
            severity = max(severity, 2)
            notes.append(f"Errors {latest:,.2f}%")
        elif latest > 1:
            severity = max(severity, 1)
            notes.append(f"Errors {latest:,.2f}%")

    latency = metrics.get("origin_latency")
    if latency and latency.values:
        latest = latency.latest
        if latest > 400:
            severity = max(severity, 2)
            notes.append(f"Latency {latest:,.0f}ms")
        elif latest > 250:
            severity = max(severity, 1)
            notes.append(f"Latency {latest:,.0f}ms")

    if severity == 0:
        label = "Healthy"
        style = "green"
        detail = ", ".join(notes) if notes else "All metrics nominal"
        badge = "[OK]"
    elif severity == 1:
        label = "Watch"
        style = "yellow"
        detail = ", ".join(notes)
        badge = "[WARN]"
    else:
        label = "Degraded"
        style = "red"
        detail = ", ".join(notes) if notes else "Investigate metrics"
        badge = "[CRIT]"

    return HealthStatus(label, detail, style, badge)


def _header_panel(config: WonderConfig, health: HealthStatus, window: MetricWindow) -> Panel:
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1, justify="right")

    grid.add_row(Text(f"{health.badge} {health.label}", style=f"bold {health.style}"), Text(health.detail or ""))
    grid.add_row(
        f"Distribution: {config.distribution_id or '—'}",
        f"Region: {config.region}",
    )
    grid.add_row(
        f"Period: {config.period_seconds}s",
        f"Window: {config.window_minutes}m",
    )
    if window.samples:
        grid.add_row(
            f"Last datapoint: {window.samples[-1].timestamp.astimezone(timezone.utc).strftime('%H:%M:%S UTC')}",
            f"Points: {len(window.samples)}",
        )

    return Panel(grid, border_style=health.style, title="WonderDash")


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
    *,
    header: Panel,
    scalars: Optional[Dict[str, ScalarMetric]] = None,
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
                header=header,
                scalars=scalars,
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
    scalars: Dict[str, ScalarMetric] = {}

    health = _compute_health(scalars, window.samples)
    header = _header_panel(config, health, window)

    with Live(console=console, refresh_per_second=refresh_hz, screen=False) as live:
        live.update(
            build_layout(
                window,
                config.period_seconds,
                last_refresh,
                config.poll_seconds,
                header=header,
                scalars=scalars,
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
                        scalars=scalars,
                    )
                    last_refresh = datetime.now(timezone.utc)
                except ProfileNotFound as error:
                    scalars.clear()
                    window = MetricWindow(
                        samples=[],
                        status="CredentialsMissing",
                        messages=[f"AWS profile not found: {error}"],
                    )
                    last_refresh = datetime.now(timezone.utc)
                    console.log(f"Profile error: {error}")
                except NoCredentialsError as error:
                    scalars.clear()
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
                    scalars.clear()
                    window = MetricWindow(
                        samples=[],
                        status="CloudWatchError",
                        messages=[str(error)],
                    )
                    last_refresh = datetime.now(timezone.utc)
                    console.log(f"CloudWatch error: {error}")

                health = _compute_health(scalars, window.samples)
                header = _header_panel(config, health, window)

                live.update(
                    build_layout(
                        window,
                        config.period_seconds,
                        last_refresh,
                        config.poll_seconds,
                        header=header,
                        scalars=scalars,
                    ),
                    refresh=True,
                )

                if _wait_for_next_poll(
                    live,
                    window,
                    config.period_seconds,
                    last_refresh,
                    config.poll_seconds,
                    header=header,
                    scalars=scalars,
                ):
                    console.print("\n[cyan]Exit requested (q).[/cyan]")
                    break
        except KeyboardInterrupt:
            console.print("\n[cyan]Shutting down WonderDash…[/cyan]")
