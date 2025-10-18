"""Configuration helpers for WonderDash."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_FILENAME = "config.json"
ENV_CONFIG_PATH = "WONDER_DASH_CONFIG"


def _default_config_dir() -> Path:
    """Return the default configuration directory."""
    override = os.getenv(ENV_CONFIG_PATH)
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "WonderDash"

    # POSIX default
    base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "wonder_dash"


def config_path() -> Path:
    """Full path to the config file."""
    return _default_config_dir() / CONFIG_FILENAME


@dataclass
class WonderConfig:
    """Configuration values persisted for WonderDash."""

    aws_profile: Optional[str] = None
    distribution_id: Optional[str] = None
    region: str = "us-east-1"
    period_seconds: int = 300
    window_minutes: int = 60
    poll_seconds: int = 30

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WonderConfig":
        kwargs = {
            "aws_profile": data.get("aws_profile"),
            "distribution_id": data.get("distribution_id"),
            "region": data.get("region", "us-east-1"),
            "period_seconds": int(data.get("period_seconds", 300)),
            "window_minutes": int(data.get("window_minutes", 60)),
            "poll_seconds": int(data.get("poll_seconds", 30)),
        }
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def ensure_valid(self) -> None:
        if self.period_seconds <= 0:
            raise ValueError("period_seconds must be positive")
        if self.window_minutes <= 0:
            raise ValueError("window_minutes must be positive")
        if self.poll_seconds <= 0:
            raise ValueError("poll_seconds must be positive")

        # CloudFront metrics require 60-second multiples for period.
        if self.period_seconds < 60:
            self.period_seconds = 60
        if self.period_seconds % 60 != 0:
            remainder = self.period_seconds % 60
            self.period_seconds += 60 - remainder

        if self.distribution_id is not None:
            cleaned = "".join(ch for ch in self.distribution_id.strip() if 32 <= ord(ch) <= 126)
            if cleaned != self.distribution_id:
                self.distribution_id = cleaned
            if self.distribution_id and not self.distribution_id.isascii():
                # Ascii guard (strip already handled non-printable)
                self.distribution_id = self.distribution_id.encode("ascii", "ignore").decode()
            if self.distribution_id == "":
                self.distribution_id = None


def load_config() -> WonderConfig:
    """Load config from disk or return defaults."""
    path = config_path()
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            config = WonderConfig.from_dict(data)
            config.ensure_valid()
            if config.to_dict() != data:
                # Persist normalization (period rounding, etc.) back to disk.
                save_config(config)
            return config
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            raise RuntimeError(f"Failed to load WonderDash config: {exc}") from exc
    return WonderConfig()


def save_config(config: WonderConfig) -> Path:
    """Persist config to disk, creating parent directory as required."""
    config.ensure_valid()
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(config.to_dict(), fp, indent=2, sort_keys=True)
    return path
