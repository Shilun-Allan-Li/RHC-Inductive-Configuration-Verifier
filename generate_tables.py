"""Entry point: classify every predicate in ``predicates.TABLES`` and write
LaTeX tables to disk.

Typical usage:

    python generate_tables.py                          # default: write to ./tables
    python generate_tables.py --out-dir ./out          # custom output
    python generate_tables.py --no-summary             # skip console summary

By default tables are written to ``./tables`` (relative to the current working
directory). The paper's ``main.tex`` ``\\input{}``-s tables from a top-level
``tables/`` directory; running this script from the same directory as
``main.tex`` regenerates them in place.
"""

from __future__ import annotations

import argparse

from tables import emit_all_tables, print_classification_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify all predicates and emit LaTeX tables for the paper."
    )
    parser.add_argument(
        "--out-dir",
        default="./tables",
        help="Directory to write per-table LaTeX files into. Default: ./tables",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip the console classification summary.",
    )
    args = parser.parse_args()

    if not args.no_summary:
        print_classification_summary()

    emit_all_tables(args.out_dir)
    print(f"\nLaTeX tables written to {args.out_dir}")


if __name__ == "__main__":
    main()
