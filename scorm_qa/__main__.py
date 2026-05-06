"""CLI: python -m scorm_qa validate <package.zip>"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import validate_package
from .report import write_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scorm_qa", description="SCORM package QA validator")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate")
    p.add_argument("zip", type=Path)
    p.add_argument("--out", type=Path, default=Path("reports"))
    args = parser.parse_args(argv)

    if args.cmd == "validate":
        defects, _ = validate_package(str(args.zip))
        md, _ = write_reports(args.out, str(args.zip), defects)
        critical = any(d["severity"] in ("CRITICAL", "HIGH") for d in defects)
        verdict = "FAIL" if critical else "PASS"
        print(f"{verdict}  {args.zip.name}  defects={len(defects)}  -> {md}")
        return 0 if not critical else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
