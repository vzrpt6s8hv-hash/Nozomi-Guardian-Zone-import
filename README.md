# Nozomi Guardian Zone Import Tool

[![CI]([https://github.com/vzrpt6s8hv-hash/Nozomi-Guardian-Zone-Converter/nozomi-guardian-zone-import-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR-GITHUB-USERNAME/nozomi-guardian-zone-import-tool/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Disclaimer:** This is an independent, community-built tool put together
> by a tech enthusiast. It is **not developed, endorsed, certified, or
> supported by Nozomi Networks** in any way. "Nozomi" and "Guardian" are
> trademarks of their respective owner, used here only to describe
> compatibility. Use at your own risk, review all generated output before
> applying it to a production system, and always keep a backup of your
> existing zone configuration.

A simple, cross-platform (Windows / macOS / Linux) GUI application that:

1. Imports zone data from a **CSV, Excel (.xls/.xlsx) or Word (.docx table)** file.
2. Automatically maps the source columns onto Nozomi Guardian's zone fields
   — with a **manual mapping screen** you can always adjust if auto-mapping
   gets something wrong or misses a column.
3. Shows the mapped zones in an editable, spreadsheet-like grid where you
   can edit individual cells **or bulk-edit a field across many zones at
   once** (e.g. set `security_profile` for every selected zone in one go).
4. Can also **derive candidate zones from a raw Guardian Asset Export**
   (grouping assets by segment/subnet and VLAN) — see "Suggest Zones from
   Asset Export" below.
5. Exports a ready-to-run Guardian zone configuration file using the same
   `vi zones add / vi zones set...` CLI command format used by Guardian's
   own "Zone configurations" export/import.

It was built and validated against a real exported Guardian zone
configuration file: every zone, network, VLAN, level and flag round-trips
correctly (see `tests/test_core.py`).

## Quick start

You do **not** need to manually install Python packages — the launcher
scripts create an isolated virtual environment and install everything
needed (pandas, openpyxl, xlrd, python-docx) automatically the first time
you run them.

- **Windows:** double-click `install_and_run.bat`
- **macOS / Linux:**
  ```bash
  git clone https://github.com/YOUR-GITHUB-USERNAME/nozomi-guardian-zone-import-tool.git
  cd nozomi-guardian-zone-import-tool
  chmod +x install_and_run.sh
  ./install_and_run.sh
  ```

Requirement: Python 3.8+ must already be installed on your machine
(the installers from https://python.org for Windows/macOS include it; most
Linux distributions already ship `python3`). On some minimal Linux
installs you may also need the OS-level Tk package for the GUI to display:
- Debian/Ubuntu: `sudo apt-get install python3-tk python3-venv`
- Fedora: `sudo dnf install python3-tkinter`
- Arch: `sudo pacman -S tk`

### Installing as a regular Python package

If you'd rather manage the environment yourself:
```bash
pip install .           # or: pip install -e .   for an editable/dev install
nozomi-zone-import-tool  # launches the GUI
```

## Using the tool

### 1. Import your zone data
`File > Import CSV / Excel / Word File...` and pick your spreadsheet or
document. The tool reads the header row and tries to automatically match
each column to a Guardian zone field (Zone Name, Networks, Level, Security
Profile, VLAN fields, etc.) using both exact and fuzzy name matching.

A **mapping screen** then appears showing what it found. Any field it
couldn't confidently auto-detect is labeled in red/amber with
`<-- select manually (not auto-detected)` — just pick the correct column
from that field's dropdown yourself before clicking **Apply**. Zone Name
and Networks are the only two required fields; everything else can be
left unmapped/blank. **Manual mapping is always available as a fallback**,
whether or not auto-mapping found anything.

### 2. Review and bulk-edit
The grid shows one row per zone. Double-click any cell to edit it in
place. To change a field across many zones at once:
- Select the rows (click, or Ctrl/Cmd-click, or Shift-click for a range)
- Click **Bulk Edit Field...** (toolbar or Edit menu)
- Pick the field, type the new value, choose "Selected rows" or "All
  rows", optionally restrict to rows where the field is currently empty,
  and click Apply.

You can also **Add Row** / **Delete Selected Row(s)** from the Edit menu.

### 3. Suggest zones from an Asset Export
`File > Suggest Zones from Asset Export...` lets you point the tool at a
raw Guardian **Asset export** (CSV/Excel with one row per discovered
device) instead of a zone list. Map its IP Address / VLAN / Segment
columns, and the tool will:

- Group assets into candidate zones (one per Segment/Subnet column value
  if present, otherwise one per VLAN with the IP addresses automatically
  summarized into the smallest set of covering CIDR blocks).
- Decide between the two VLAN fields per the same rule Guardian itself
  follows:
  - **`assigned_vlan_id`** is used in the normal case, where a zone's
    network range is unique — the VLAN is simply assigned/tagged to that
    zone (and `force_assigned_vlan_id` is set to `true`).
  - **`matching_vlan_id`** is used only when the *same* network/CIDR is
    reused across more than one VLAN or segment (e.g. two sites that both
    use `10.10.1.0/24` privately, on different VLANs). In that case the
    IP range alone is ambiguous, so Guardian needs the VLAN as an extra
    matching criterion, and `matching_vlan_id` is populated instead of
    `assigned_vlan_id`.
- Show a review dialog explaining every assumption it made (which zones
  got `matching_vlan_id` and why, zones with mixed VLANs that might need
  splitting, zones where no network could be derived, etc.).

The suggested zones land in the same editable grid as a normal import, so
you can rename, merge, bulk-edit or delete them before exporting — this
feature is meant to save time, not to be the final word; always review
its output.

### 4. Export
`File > Export Guardian Zone Config...` (or the toolbar button) writes a
`.cfg` file containing the `vi zones ...` commands, ready to paste into
Guardian's CLI or import via Guardian's own config-import mechanism.
Use **Preview Output** first if you want to check the generated text
before saving.

**Output mode** (toolbar dropdown, default `full`):
- `full` — every field is written for every zone (blank if you didn't
  give it a value). This matches the majority pattern seen in real
  Guardian zone exports.
- `compact` — only fields that actually have a value are written. Useful
  for lightweight zones that only need a level/VLAN.

You can override the mode per individual zone by filling in its
`output_mode` cell with `full` or `compact` — that takes priority over the
toolbar default for that row.

### 5. Re-opening an existing config
`File > Open Existing Guardian Config (.cfg)...` parses an already
exported Guardian zone file back into the editable grid, so you can tweak
an existing configuration (including bulk-editing across its zones) and
re-export it.

### 6. Save a template
`File > Save Mapped Data as CSV Template...` writes out the current grid
as a CSV using the tool's own column names — handy as a starting template
for future imports, or to hand to a colleague to fill in.

## Guardian zone fields reference

| Field | CLI command | Notes |
|---|---|---|
| Zone Name | `vi zones add <networks> <name>` | Required |
| Networks / CIDR | (same, comma separated) | Required |
| Level | `setlevel` | |
| Security Profile | `setsecurity_profile` | |
| Force Assigned VLAN ID | `setforce_assigned_vlan_id` | `true`/`false` |
| MAC Matching Fallback | `setmac_matching_fallback` | `true`/`false` |
| Extended Network Statistic Enabled | `setextended_network_statistic_enabled` | `true`/`false` |
| Use Label As Node Device ID | `setuse_label_as_node_device_id` | `true`/`false` |
| Matching VLAN ID | `setmatching_vlan_id` | see VLAN rule above |
| Assigned VLAN ID | `setassigned_vlan_id` | see VLAN rule above |
| Adaptive Learning | `setadaptive_learning` | `true`/`false` |
| Learning | `setlearning` | `true`/`false` |
| Is Public | `setis_public` | `true`/`false` |
| Merging Zone | `setmerging_zone` | only written when given a value |
| Merging | `setmerging` | `true`/`false` |
| Isolated | `setisolated` | `true`/`false` |

## Command-line / scripted use

For automation or testing you can skip the GUI entirely:
```bash
nozomi-zone-import-tool --input zones.csv --output zones.cfg --mode full
```
`--map field=Column` can be used to force a specific mapping, e.g.
`--map zone_name=Zone --map networks=Subnets` (repeatable).

## Development

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/nozomi-guardian-zone-import-tool.git
cd nozomi-guardian-zone-import-tool
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

The test suite (`tests/test_core.py`) exercises the field mapping,
generation/parsing, and asset-to-zone suggestion logic against the sample
files in `sample_data/` — including a round-trip check that regenerating a
config from a parsed export reproduces every command line. GUI code
(`src/nozomi_zone_import_tool/gui.py`) is kept separate from the core logic
so tests can run without Tkinter installed, and CI (`.github/workflows/ci.yml`)
runs the suite on Ubuntu, Windows and macOS across Python 3.9–3.12.

Sample/demo data in `sample_data/` uses entirely fictitious zone names and
IP ranges — no real network information is included in this repository.

## Project layout

```
.
├── src/nozomi_zone_import_tool/
│   ├── core.py     # field schema, file loading, mapping, config gen/parse, asset->zone suggestion
│   ├── gui.py       # Tkinter GUI (imports core, no GUI code in core.py)
│   ├── cli.py       # argparse entry point (GUI by default, headless with --input/--output)
│   └── __main__.py  # enables `python -m nozomi_zone_import_tool`
├── tests/test_core.py
├── sample_data/      # fictitious example CSV/cfg files used by the tests and as templates
├── install_and_run.sh / .bat
└── pyproject.toml
```

## Contributing

Issues and pull requests are welcome. Please run `pytest -v` before
submitting a PR, and avoid including any real/sensitive network data in
sample files or test fixtures.

## License

[MIT](LICENSE)
