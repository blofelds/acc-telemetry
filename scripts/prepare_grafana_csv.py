#!/usr/bin/env python3
"""
Prepare ACC telemetry CSV for Grafana's CSV data source.

Grafana time-series panels need absolute timestamps. Our extractor stores
video-relative seconds in the ``time`` column. This script maps those onto
1970-01-01 UTC so the clock reads as elapsed lap/session time (mm:ss).

By default, files go to Grafana's own CSV directory
(``/var/lib/grafana/csv``) so the Grafana process can read them without
opening up your home directory. Override with ``-o`` or ``GRAFANA_CSV_DIR``.

Example:
    python scripts/prepare_grafana_csv.py data/output/telemetry_20250101_120000.csv
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd


def _grant_grafana_read(path: Path) -> None:
    """Allow the Grafana service user to read a file we just wrote.

    CSVs land in /var/lib/grafana/csv with the invoking user as owner. Without
    an ACL, the grafana process cannot open them (directory is not world-
    readable). File owners can setfacl without sudo.
    """
    for user in ("grafana", "nobody"):
        try:
            subprocess.run(
                ["setfacl", "-m", f"u:{user}:r", str(path)],
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            return

# Fixed epoch so Grafana's time axis == video elapsed seconds.
EPOCH = pd.Timestamp("1970-01-01T00:00:00Z")

# Prefer Grafana's data dir so local mode does not need home-directory access.
DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("GRAFANA_CSV_DIR", "/var/lib/grafana/csv")
)
CURRENT_NAME = "telemetry_current.csv"

# Columns the HTML graphs plot (optional ones kept when present).
NUMERIC_COLUMNS = (
    "throttle",
    "brake",
    "steering",
    "speed",
    "gear",
    "tc_active",
    "abs_active",
    "lap_number",
    "track_position",
)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Add a Grafana-friendly ``timestamp`` column from video-relative ``time``."""
    if "time" not in df.columns:
        raise ValueError("CSV must include a 'time' column (seconds from video start)")

    out = df.copy()
    out["timestamp"] = EPOCH + pd.to_timedelta(out["time"].astype(float), unit="s")
    # ISO-8601 with Z — CSV plugin parses this reliably as Time.
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z"

    preferred = ["timestamp", "time", "frame"]
    preferred += [c for c in NUMERIC_COLUMNS if c in out.columns]
    preferred += [c for c in out.columns if c not in preferred]
    return out[preferred]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert ACC telemetry CSV for Grafana CSV data source"
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to telemetry_*.csv from main.py",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            f"Directory for Grafana-ready CSVs "
            f"(default: {DEFAULT_OUTPUT_DIR}; override with GRAFANA_CSV_DIR)"
        ),
    )
    parser.add_argument(
        "--no-current",
        action="store_true",
        help="Do not update telemetry_current.csv copy",
    )
    args = parser.parse_args(argv)

    if not args.csv_path.is_file():
        print(f"Error: file not found: {args.csv_path}", file=sys.stderr)
        return 1

    df = pd.read_csv(args.csv_path)
    prepared = prepare(df)

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(
            f"Error: cannot write to {args.output_dir}\n"
            f"Grant your user access once (no world-readable home needed):\n"
            f"  sudo setfacl -m u:$USER:rwx {args.output_dir}\n"
            f"  sudo setfacl -d -m u:$USER:rwx {args.output_dir}\n"
            f"Or write elsewhere:  -o /path/you/own\n"
            f"See grafana/README.md.",
            file=sys.stderr,
        )
        return 1

    out_name = f"grafana_{args.csv_path.stem}.csv"
    out_path = args.output_dir / out_name
    try:
        prepared.to_csv(out_path, index=False)
    except PermissionError:
        print(
            f"Error: cannot write {out_path}\n"
            f"  sudo setfacl -m u:$USER:rwx {args.output_dir}\n"
            f"  sudo setfacl -d -m u:$USER:rwx {args.output_dir}",
            file=sys.stderr,
        )
        return 1
    print(f"Wrote {out_path} ({len(prepared)} rows)")
    _grant_grafana_read(out_path)

    if not args.no_current:
        current = args.output_dir / CURRENT_NAME
        # Copy (not symlink) so Grafana local mode works across users.
        shutil.copy2(out_path, current)
        _grant_grafana_read(current)
        print(f"Updated {current}")

    duration = float(df["time"].max()) if len(df) else 0.0
    end = EPOCH + pd.Timedelta(seconds=duration)
    print(
        f"\nIn Grafana, set absolute time range to:\n"
        f"  From: 1970-01-01 00:00:00\n"
        f"  To:   {end.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"(or zoom after load — time axis = video elapsed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
