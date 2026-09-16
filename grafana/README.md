# Grafana dashboards for ACC Telemetry Extractor

Uses the **CSV data source** plugin (`marcusolsson-csv-datasource`) to mirror
the Plotly HTML outputs from `main.py`.

| Dashboard | JSON | What it shows |
|---|---|---|
| **ACC Telemetry Analysis** | `dashboards/acc-telemetry.json` | Full session vs video time (throttle, brake, steering, speed, gear, TC, ABS, lap) |
| **ACC Lap Comparison (all laps)** | `dashboards/acc-lap-comparison.json` | Every complete lap overlaid on **track position** (throttle, brake, steering, speed, TC, ABS) |

## Prerequisites

- Grafana running (you have 13.x)
- Plugin: **CSV** (`marcusolsson-csv-datasource`)
- A telemetry CSV from `python main.py` that includes `lap_number` and
  `track_position` for the lap overlay dashboard

## One-time Grafana setup

### 1. Allow the CSV plugin to read local files

Edit `/etc/grafana/grafana.ini` (needs sudo) and add:

```ini
[plugin.marcusolsson-csv-datasource]
allow_local_mode = true
```

Restart Grafana:

```bash
sudo systemctl restart grafana-server
# or however you start it if not using systemd
```

### 2. CSV directory (no world-readable home)

Keep CSVs under Grafana’s own tree (`/var/lib/grafana/csv`). Grant **only
your account** write access with an ACL — do **not** `chmod a+rx` on `$HOME`:

```bash
sudo setfacl -m u:$USER:rwx /var/lib/grafana/csv
sudo setfacl -m u:grafana:rx /var/lib/grafana/csv
sudo setfacl -d -m u:$USER:rwx /var/lib/grafana/csv
sudo setfacl -d -m u:grafana:r /var/lib/grafana/csv
```

`prepare_grafana_csv.py` also runs `setfacl -m u:grafana:r` on each file it
writes (as file owner, no sudo).

### 3. Data source + import dashboards

**Manual UI (simplest):**

1. **Connections → Data sources → Add** → **CSV**
2. Storage: **Local**, path: `/var/lib/grafana/csv`
3. Save & test
4. **Dashboards → Import** each of:
   - `grafana/dashboards/acc-telemetry.json`
   - `grafana/dashboards/acc-lap-comparison.json`
5. Pick your CSV data source from the dashboard **Data source** dropdown

Or copy the provisioning files under `grafana/provisioning/` plus both JSON
dashboards into Grafana’s provisioned paths (see comments in those YAML files).

## Load a session into Grafana

```bash
source venv/bin/activate
python scripts/prepare_grafana_csv.py data/output/telemetry_YYYYMMDD_HHMMSS.csv
```

Writes into `/var/lib/grafana/csv` by default:

| File | Used by |
|---|---|
| `telemetry_current.csv` | Session dashboard |
| `telemetry_laps_by_position.csv` | Lap comparison (all laps, position-aligned) |
| `grafana_telemetry_….csv` | Archived session copy |

Incomplete laps (short span / few frames) and lap `0` are skipped for the
overlay. Use `--include-lap-zero` if you want lap 0 included.

### Session dashboard time range

Timestamps = video elapsed on **1970-01-01 UTC**.

- **From:** `1970-01-01 00:00:00`
- **To:** past your session length (e.g. `00:12:30`)

### Lap comparison time range

Timestamps = **track position %** mapped to seconds (`00:00:45` ≈ 45% around
the lap). Default dashboard window is 0–100 seconds:

- **From:** `1970-01-01 00:00:00`
- **To:** `1970-01-01 00:01:40`

All complete laps appear as separate series on each panel. Use the **Laps**
multi-select at the top to show or hide the same laps on every panel at once
(legend clicks only affect one panel).

Shared crosshair is on for both dashboards.

## Panel map — session dashboard

| HTML subplot | Grafana panel |
|---|---|
| Throttle | Throttle Input |
| Brake | Brake Input |
| Steering | Steering Input |
| Speed | Speed |
| Gear | Gear |
| TC | Traction Control |
| ABS | ABS |
| (lap markers) | Lap Number |

## Panel map — lap comparison

| HTML (`plot_position_based_comparison`) | Grafana |
|---|---|
| Throttle overlay (2 laps) | Throttle vs Track Position (**all** laps) |
| Brake overlay | Brake vs Track Position |
| Steering overlay | Steering vs Track Position |
| Speed overlay | Speed vs Track Position |
| *(not in HTML lap compare)* | TC / ABS vs Track Position |
| Time delta (pairwise) | Not yet (needs a chosen baseline lap) |

## Note on the CSV plugin

Grafana Labs marks `marcusolsson-csv-datasource` as deprecated (EOL Feb 2027)
and suggests **Infinity**. This setup uses CSV because it is already installed
and running on your machine. Migrating later is mostly a data-source swap.
