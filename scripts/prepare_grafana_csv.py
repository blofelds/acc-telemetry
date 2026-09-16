#!/usr/bin/env python3
"""
Prepare ACC telemetry CSV for Grafana's CSV data source.

For each dashboard, writes an **archive** (pinned to this extract) and a
**stable** filename the dashboard points at by default (a regular copy, not
a symlink — Grafana’s process user needs ACL-friendly readable files):

Session dashboard (video elapsed time)
  - archive: ``grafana_telemetry_<YYYYMMDD_HHMMSS>.csv``
  - stable:  ``telemetry_current.csv``

Lap comparison (track position overlay)
  - archive: ``grafana_laps_by_position_<YYYYMMDD_HHMMSS>.csv``
  - stable:  ``telemetry_laps_by_position.csv``

Timestamps:

- Session file: ``1970-01-01`` + video ``time`` seconds.
- Lap file: ``1970-01-01`` + track position seconds (so ``00:00:45`` ≈ 45%
  around the lap). Set the dashboard range to cover 0–100 seconds.

By default, files go to ``/var/lib/grafana/csv``. Override with ``-o`` or
``GRAFANA_CSV_DIR``.

Example:
    python scripts/prepare_grafana_csv.py data/output/telemetry_20260916_010941.csv
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd


def _grant_grafana_read(path: Path) -> None:
    """Allow the Grafana service user to read a file we just wrote."""
    for user in ("grafana", "nobody"):
        try:
            subprocess.run(
                ["setfacl", "-m", f"u:{user}:r", str(path)],
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            return


# Fixed epoch so Grafana's time axis maps to elapsed / position seconds.
EPOCH = pd.Timestamp("1970-01-01T00:00:00Z")

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("GRAFANA_CSV_DIR", "/var/lib/grafana/csv")
)
SESSION_STABLE_NAME = "telemetry_current.csv"
LAPS_STABLE_NAME = "telemetry_laps_by_position.csv"

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


def _format_timestamp(series: pd.Series) -> pd.Series:
    """Format timedeltas-from-epoch as ISO-8601 UTC for the CSV plugin."""
    ts = EPOCH + pd.to_timedelta(series.astype(float), unit="s")
    return ts.dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z"


def prepare_session(df: pd.DataFrame) -> pd.DataFrame:
    """Add a Grafana-friendly ``timestamp`` column from video-relative ``time``."""
    if "time" not in df.columns:
        raise ValueError("CSV must include a 'time' column (seconds from video start)")

    out = df.copy()
    out["timestamp"] = _format_timestamp(out["time"])

    preferred = ["timestamp", "time", "frame"]
    preferred += [c for c in NUMERIC_COLUMNS if c in out.columns]
    preferred += [c for c in out.columns if c not in preferred]
    return out[preferred]


def _nearest_sample(targets: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Sample y at targets using nearest x (keeps binary flags as 0/1)."""
    idx = np.searchsorted(x, targets, side="left")
    idx = np.clip(idx, 0, len(x) - 1)
    left = np.clip(idx - 1, 0, len(x) - 1)
    use_left = (idx > 0) & (np.abs(x[left] - targets) <= np.abs(x[idx] - targets))
    chosen = np.where(use_left, left, idx)
    return y[chosen]


def _resample_lap_by_position(
    lap_df: pd.DataFrame, position_step: float = 0.5
) -> pd.DataFrame:
    """Interpolate one lap onto a fixed track-position grid (0–100%)."""
    valid = lap_df[lap_df["track_position"].notna()].copy()
    if valid.empty:
        return pd.DataFrame()

    valid = valid.sort_values("track_position")
    valid = valid[valid["track_position"].diff().fillna(0) >= 0]
    if len(valid) < 2:
        return pd.DataFrame()

    targets = np.arange(0.0, 100.0 + position_step, position_step)
    x = valid["track_position"].to_numpy(dtype=float)

    data = {
        "track_position": targets,
        "throttle": np.interp(targets, x, valid["throttle"].to_numpy(dtype=float)),
        "brake": np.interp(targets, x, valid["brake"].to_numpy(dtype=float)),
        "steering": np.interp(targets, x, valid["steering"].to_numpy(dtype=float)),
        "time": np.interp(targets, x, valid["time"].to_numpy(dtype=float)),
    }
    if "speed" in valid.columns and valid["speed"].notna().any():
        mask = valid["speed"].notna()
        if int(mask.sum()) >= 2:
            data["speed"] = np.interp(
                targets,
                valid.loc[mask, "track_position"].to_numpy(dtype=float),
                valid.loc[mask, "speed"].to_numpy(dtype=float),
            )

    for flag in ("tc_active", "abs_active"):
        if flag not in valid.columns:
            continue
        mask = valid[flag].notna()
        if int(mask.sum()) < 1:
            continue
        data[flag] = _nearest_sample(
            targets,
            valid.loc[mask, "track_position"].to_numpy(dtype=float),
            valid.loc[mask, flag].to_numpy(dtype=float),
        )

    return pd.DataFrame(data)


def prepare_laps_by_position(
    df: pd.DataFrame,
    position_step: float = 0.5,
    min_points: int = 200,
    min_position_span: float = 80.0,
    include_lap_zero: bool = False,
) -> tuple[pd.DataFrame, List[str]]:
    """
    Build a multi-lap CSV aligned on track position for overlay charts.

    Each lap is resampled onto the same 0–100% grid. ``timestamp`` is position
    expressed as seconds from the epoch so Grafana time-series panels can
    overlay every lap without a two-lap selector.
    """
    required = {"lap_number", "track_position", "throttle", "brake", "steering", "time"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Lap comparison CSV needs columns {sorted(required)}; missing {sorted(missing)}"
        )

    work = df.copy()
    work["lap_number"] = pd.to_numeric(work["lap_number"], errors="coerce")
    work["track_position"] = pd.to_numeric(work["track_position"], errors="coerce")
    work = work[work["lap_number"].notna() & work["track_position"].notna()]
    if not include_lap_zero:
        work = work[work["lap_number"] >= 1]

    if work.empty:
        raise ValueError("No rows with both lap_number and track_position")

    pieces: List[pd.DataFrame] = []
    skipped: List[str] = []

    for lap_num, lap_df in work.groupby("lap_number", sort=True):
        lap_int = int(lap_num)
        pos = lap_df["track_position"]
        span = float(pos.max() - pos.min()) if len(pos) else 0.0
        if len(lap_df) < min_points or span < min_position_span:
            skipped.append(
                f"lap {lap_int} (n={len(lap_df)}, span={span:.1f}%)"
            )
            continue

        resampled = _resample_lap_by_position(lap_df, position_step=position_step)
        if resampled.empty:
            skipped.append(f"lap {lap_int} (resample failed)")
            continue

        resampled["lap_number"] = lap_int
        resampled["lap_label"] = f"Lap {lap_int}"
        resampled["timestamp"] = _format_timestamp(resampled["track_position"])
        t0 = float(resampled["time"].iloc[0])
        resampled["lap_elapsed"] = resampled["time"] - t0
        pieces.append(resampled)

    if not pieces:
        raise ValueError(
            "No complete laps to export. "
            f"Skipped: {', '.join(skipped) if skipped else 'none'}"
        )

    out = pd.concat(pieces, ignore_index=True)
    cols = [
        "timestamp",
        "track_position",
        "lap_number",
        "lap_label",
        "throttle",
        "brake",
        "steering",
        "speed",
        "tc_active",
        "abs_active",
        "lap_elapsed",
        "time",
    ]
    cols = [c for c in cols if c in out.columns]
    return out[cols], skipped


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)
    _grant_grafana_read(path)
    print(f"Wrote {path} ({len(df)} rows)")


def _publish_pair(
    df: pd.DataFrame,
    archive_path: Path,
    stable_path: Path,
    *,
    update_stable: bool,
) -> None:
    """Write archive CSV, then optionally copy it to the stable dashboard name."""
    _write_csv(df, archive_path)
    if update_stable:
        shutil.copy2(archive_path, stable_path)
        _grant_grafana_read(stable_path)
        print(f"Updated {stable_path}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert ACC telemetry CSV for Grafana CSV data source"
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to telemetry_*.csv from main.py (under data/output/)",
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
        "--no-stable",
        action="store_true",
        help=(
            "Do not update stable dashboard pointers "
            f"({SESSION_STABLE_NAME}, {LAPS_STABLE_NAME})"
        ),
    )
    parser.add_argument(
        "--no-current",
        action="store_true",
        help="Alias for --no-stable (kept for older scripts)",
    )
    parser.add_argument(
        "--no-laps",
        action="store_true",
        help="Skip the position-aligned multi-lap CSV pair",
    )
    parser.add_argument(
        "--position-step",
        type=float,
        default=0.5,
        help="Track position sample step in percent (default: 0.5)",
    )
    parser.add_argument(
        "--include-lap-zero",
        action="store_true",
        help="Include lap_number 0 in the position overlay (often an out-lap)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    update_stable = not (args.no_stable or args.no_current)

    if not args.csv_path.is_file():
        print(f"Error: file not found: {args.csv_path}", file=sys.stderr)
        return 1

    df = pd.read_csv(args.csv_path)
    stem = args.csv_path.stem
    # data/output/telemetry_YYYYMMDD_HHMMSS.csv → YYYYMMDD_HHMMSS in archive names
    archive_id = (
        stem.removeprefix("telemetry_")
        if stem.startswith("telemetry_")
        else stem
    )

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

    session = prepare_session(df)
    session_archive = args.output_dir / f"grafana_telemetry_{archive_id}.csv"
    try:
        _publish_pair(
            session,
            session_archive,
            args.output_dir / SESSION_STABLE_NAME,
            update_stable=update_stable,
        )
    except PermissionError:
        print(
            f"Error: cannot write under {args.output_dir}\n"
            f"  sudo setfacl -m u:$USER:rwx {args.output_dir}\n"
            f"  sudo setfacl -d -m u:$USER:rwx {args.output_dir}",
            file=sys.stderr,
        )
        return 1

    if not args.no_laps:
        try:
            laps_df, skipped = prepare_laps_by_position(
                df,
                position_step=args.position_step,
                include_lap_zero=args.include_lap_zero,
            )
        except ValueError as exc:
            print(f"Warning: skipped lap overlay CSV ({exc})", file=sys.stderr)
        else:
            laps_archive = (
                args.output_dir / f"grafana_laps_by_position_{archive_id}.csv"
            )
            _publish_pair(
                laps_df,
                laps_archive,
                args.output_dir / LAPS_STABLE_NAME,
                update_stable=update_stable,
            )
            n_laps = laps_df["lap_number"].nunique()
            print(f"Lap overlay: {n_laps} laps at {args.position_step}% steps")
            if skipped:
                print(f"  Skipped incomplete: {', '.join(skipped)}")
            print(
                "\nLap comparison dashboard time range:\n"
                "  From: 1970-01-01 00:00:00\n"
                "  To:   1970-01-01 00:01:40\n"
                "  (X-axis seconds ≈ track position %)"
            )

    duration = float(df["time"].max()) if len(df) else 0.0
    end = EPOCH + pd.Timedelta(seconds=duration)
    print(
        f"\nSession dashboard time range:\n"
        f"  From: 1970-01-01 00:00:00\n"
        f"  To:   {end.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"(time axis = video elapsed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
