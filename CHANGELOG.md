# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-08-19

### Added
- Initial release.
- Import zone data from CSV, Excel (.xls/.xlsx) or Word (.docx table) files
  with automatic column-to-field mapping (with a manual override screen).
- Editable, spreadsheet-like grid with per-cell editing and bulk-edit
  across selected/all rows.
- "Suggest Zones from Asset Export" — derive candidate zones from a raw
  Guardian asset export, automatically choosing between `assigned_vlan_id`
  and `matching_vlan_id` based on whether a network/CIDR is unique or
  reused across VLANs/segments.
- Export to Guardian's `vi zones add / vi zones set...` CLI config format,
  with `full` and `compact` output modes (globally or per-zone).
- Open an existing Guardian zone config back into the editable grid.
- Cross-platform installer scripts (`install_and_run.sh` / `.bat`) that set
  up a virtual environment and install dependencies automatically.
- Headless CLI mode (`--input` / `--output`) for scripting.
- Test suite validated against a real Guardian zone export for round-trip
  fidelity.
