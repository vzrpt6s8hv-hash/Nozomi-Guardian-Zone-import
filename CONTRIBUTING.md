# Contributing

Thanks for considering a contribution to the Nozomi Guardian Zone Import
Tool! This is a small, independent community project (not affiliated with
Nozomi Networks) — contributions of any size are welcome.

## Getting set up

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/nozomi-guardian-zone-import-tool.git
cd nozomi-guardian-zone-import-tool
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

## Guidelines

- Keep `src/nozomi_zone_import_tool/core.py` free of GUI (Tkinter) imports
  so the test suite can run headless / in CI without Tk installed. GUI-only
  code belongs in `gui.py`.
- Add or update tests in `tests/test_core.py` for any change to mapping,
  generation, parsing, or asset-suggestion logic.
- Do not add real/sensitive network data (IP ranges, VLANs, zone names
  from an actual deployment) to `sample_data/` or test fixtures — use
  fictitious values only, since this repository may be public.
- Run `pytest -v` before opening a pull request.

## Reporting issues

Please include: your OS and Python version, the command/menu action you
used, the input file type (CSV/XLSX/DOCX), and, if possible, a minimal
example input (with any sensitive values replaced by fake data) that
reproduces the problem.
