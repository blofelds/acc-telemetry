# Grafana dashboards for ACC Telemetry Extractor

Mirrors the interactive HTML from `main.py` (throttle, brake, steering,
speed, gear, TC, ABS, lap) using the **CSV data source** plugin you already
have (`marcusolsson-csv-datasource`).

## Prerequisites

- Grafana running (you have 13.x)
- Plugin: **CSV** (`marcusolsson-csv-datasource`) — already present on your install
- A telemetry CSV from `python main.py`

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

Keep CSVs under Grafana’s own tree. Your process already has
`/var/lib/grafana/csv` (owned by the Grafana runtime user). Grant **only
your account** write access with an ACL — do **not** `chmod a+rx` on `$HOME`:

```bash
# You can write; Grafana can read. Still no world access on $HOME.
sudo setfacl -m u:$USER:rwx /var/lib/grafana/csv
sudo setfacl -m u:grafana:rx /var/lib/grafana/csv
sudo setfacl -d -m u:$USER:rwx /var/lib/grafana/csv
sudo setfacl -d -m u:grafana:r /var/lib/grafana/csv
```

`prepare_grafana_csv.py` also runs `setfacl -m u:grafana:r` on each file it
writes (as file owner, no sudo).

Check:

```bash
getfacl /var/lib/grafana/csv
touch /var/lib/grafana/csv/.write_test && rm /var/lib/grafana/csv/.write_test
```

Optional alternative (same idea, group instead of ACL): make a dedicated dir
owned by you with group readable by Grafana’s group, mode `2750` — still no
“other” permissions.

### 3. Provision data source + dashboard (recommended)

Copy provisioning configs and the dashboard JSON into places Grafana already
owns (again: no `$HOME` permissions required):

```bash
sudo cp grafana/provisioning/datasources/acc-telemetry-csv.yaml \
  /etc/grafana/provisioning/datasources/

sudo cp grafana/provisioning/dashboards/acc-telemetry.yaml \
  /etc/grafana/provisioning/dashboards/

sudo mkdir -p /var/lib/grafana/dashboards/acc-telemetry
sudo cp grafana/dashboards/*.json /var/lib/grafana/dashboards/acc-telemetry/
sudo chown -R nobody:nogroup /var/lib/grafana/dashboards/acc-telemetry

sudo systemctl restart grafana-server
```

Or **manual UI** (simplest):

1. **Connections → Data sources → Add** → search **CSV**
2. Storage: **Local**
3. Path / URL: `/var/lib/grafana/csv`
4. Save & test
5. **Dashboards → New → Import** → upload `grafana/dashboards/acc-telemetry.json`
6. Pick the CSV data source when prompted (or set UID `acc-telemetry-csv` to match)

## Load a session into Grafana

After extraction:

```bash
source venv/bin/activate
python scripts/prepare_grafana_csv.py data/output/telemetry_YYYYMMDD_HHMMSS.csv
```

Writes into `/var/lib/grafana/csv` by default:

- `grafana_telemetry_….csv` — archived copy for this run
- `telemetry_current.csv` — what the dashboard reads by default

Override location with `-o` or `GRAFANA_CSV_DIR` if needed.

Open **ACC Telemetry Analysis** in Grafana.

### Time range

Timestamps are mapped onto **1970-01-01 UTC** so the axis equals video
elapsed time. Default dashboard range is 5 minutes from midnight UTC.

- Short clips: zoom or set **To** earlier (e.g. `1970-01-01 00:01:30`)
- Longer sessions: extend **To** past your max `time` column

Shared crosshair is on (`graphTooltip: 1`) so all panels track together,
similar to the HTML unified hover.

### Switch files

Use the **CSV file** text box at the top of the dashboard (relative to
`/var/lib/grafana/csv`), e.g. `grafana_telemetry_20250101_120000.csv`.

## Panel map (HTML ↔ Grafana)

| HTML subplot | Grafana panel | Colour |
|---|---|---|
| Throttle | Throttle Input | Green |
| Brake | Brake Input | Red |
| Steering | Steering Input | Dodger blue |
| Speed | Speed | Dark orange |
| Gear | Gear (step) | Purple |
| TC | Traction Control | Orange |
| ABS | ABS | Dark orange |
| (lap markers) | Lap Number | Slate |

## Note on the CSV plugin

Grafana Labs marks `marcusolsson-csv-datasource` as deprecated (EOL Feb 2027)
and suggests **Infinity**. This setup uses CSV because it is already installed
and running on your machine. Migrating later is mostly a data-source swap.
