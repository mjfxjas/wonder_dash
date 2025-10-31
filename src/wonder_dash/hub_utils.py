from __future__ import annotations

from typing import Iterable

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table


def build_loading_layout(title: str, color: str = "blue") -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(Panel.fit(title, border_style=color, title="AWS"), name="header", size=3),
        Layout(Panel("Working…", border_style=color), name="body"),
    )
    return layout


def simple_table(headers: Iterable[str], header_style: str = "bold cyan") -> Table:
    table = Table(expand=True, row_styles=("", "dim"))
    for header in headers:
        table.add_column(header, header_style=header_style, overflow="fold")
    return table
