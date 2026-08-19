"""Command-line entry point for the Nozomi Guardian Zone Import Tool.

Running with no arguments launches the GUI. Passing --input/--output runs
a headless conversion, useful for scripting and CI.
"""

import argparse
import sys

from .core import auto_map_columns, apply_mapping, generate_config_text, load_table_file


def run_headless(args):
    df = load_table_file(args.input)
    mapping = auto_map_columns(list(df.columns))
    if args.map:
        for pair in args.map:
            k, _, v = pair.partition("=")
            if k in mapping:
                mapping[k] = v
            else:
                print(f"Warning: '{k}' is not a known field, ignoring --map {pair}", file=sys.stderr)
    rows = apply_mapping(df, mapping)
    text = generate_config_text(rows, default_mode=args.mode)
    with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"Wrote {len(rows)} zone(s) to {args.output}")
    print("Column mapping used:")
    for k, v in mapping.items():
        if v:
            print(f"  {k:38s} <- {v}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="nozomi-zone-import-tool",
        description="Nozomi Guardian Zone Import Tool - import zone data from "
                     "CSV/Excel/Word and generate a Guardian 'vi zones' config. "
                     "Run with no arguments to launch the GUI.",
    )
    parser.add_argument("--input", help="CSV/XLS/XLSX/DOCX file to convert (headless mode)")
    parser.add_argument("--output", help="Output .cfg file path (headless mode)")
    parser.add_argument("--mode", choices=["full", "compact"], default="full",
                         help="Default output mode when a row has no 'output_mode' override")
    parser.add_argument("--map", action="append",
                         help="Override auto-mapping, e.g. --map zone_name=Zone "
                              "(can be repeated)")
    parser.add_argument("--version", action="store_true", help="Print the version and exit")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from . import __version__
        print(__version__)
        return 0

    if args.input and args.output:
        run_headless(args)
        return 0

    if args.input or args.output:
        parser.error("--input and --output must be given together for headless mode")

    try:
        from .gui import launch_gui
    except ImportError as e:
        print(
            "Could not start the GUI (Tkinter not available in this Python "
            "installation).\n"
            "- Debian/Ubuntu: sudo apt-get install python3-tk\n"
            "- Fedora: sudo dnf install python3-tkinter\n"
            "- Arch: sudo pacman -S tk\n"
            "- Windows/macOS: reinstall Python from python.org with Tcl/Tk enabled\n\n"
            "Alternatively, use headless mode: "
            "nozomi-zone-import-tool --input FILE --output FILE.cfg",
            file=sys.stderr,
        )
        raise SystemExit(1) from e
    launch_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
