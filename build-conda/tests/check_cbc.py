#!/usr/bin/env python3
"""
Extract and assert on the conda_build_config.yaml embedded inside a built
.conda package.

conda-build writes the resolved variant config into
  info/recipe/conda_build_config.yaml
inside the package.  This script extracts that file and optionally asserts
that specific keys hold expected values, letting CI verify that a CBC
actually propagated through the build rather than just trusting that
conda-build accepted the flag.

Exit codes:
  0  all checks passed (or no checks requested)
  1  assertion failed or package not found
  2  no embedded CBC (only for compiled packages; noarch packages skip silently)

Usage examples:

  # Print the embedded CBC
  python tests/check_cbc.py --package "./build/**/*.conda" --print

  # Assert that numpy pin contains "1.26"
  python tests/check_cbc.py --package "./build/**/*.conda" \\
      --assert-key numpy --contains 1.26

  # Assert numpy present; also print the full CBC for debugging
  python tests/check_cbc.py --package "./build/**/*.conda" \\
      --assert-key numpy --print
"""

from __future__ import annotations

import argparse
import glob
import io
import sys
import tarfile
import zipfile
from pathlib import Path

import yaml


def find_package(pattern: str) -> Path:
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        print(f"::error::No packages found matching: {pattern}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        print(f"Found {len(matches)} packages; inspecting the first: {matches[0]}")
    return Path(matches[0])


def extract_embedded_cbc(pkg: Path) -> dict | None:
    """
    Extract info/recipe/conda_build_config.yaml from a .conda file.
    Returns None if the file is not present (normal for noarch packages).
    """
    with zipfile.ZipFile(pkg) as z:
        info_members = [n for n in z.namelist() if n.startswith("info-")]
        if not info_members:
            return None
        with z.open(info_members[0]) as f:
            info_data = f.read()

    with tarfile.open(fileobj=io.BytesIO(info_data), mode="r:zst") as t:
        try:
            member = t.getmember("info/recipe/conda_build_config.yaml")
            return yaml.safe_load(t.extractfile(member).read().decode())
        except KeyError:
            return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assert on the CBC embedded inside a built .conda package."
    )
    parser.add_argument(
        "--package",
        required=True,
        metavar="GLOB",
        help="Path or glob pattern to a .conda file",
    )
    parser.add_argument(
        "--print",
        dest="print_cbc",
        action="store_true",
        help="Print the full embedded CBC",
    )
    parser.add_argument(
        "--assert-key",
        metavar="KEY",
        help="CBC key whose value must be present",
    )
    parser.add_argument(
        "--contains",
        metavar="VALUE",
        help="String that must appear in the key's value (requires --assert-key)",
    )
    parser.add_argument(
        "--noarch-ok",
        action="store_true",
        default=True,
        help="Exit 0 (not 2) when no embedded CBC is found (default: true)",
    )
    args = parser.parse_args()

    pkg = find_package(args.package)
    print(f"Inspecting: {pkg}")

    cbc = extract_embedded_cbc(pkg)

    if cbc is None:
        msg = "No embedded conda_build_config.yaml found."
        if args.noarch_ok:
            print(f"{msg}  (noarch package — skipping CBC checks)")
            return 0
        else:
            print(f"::error::{msg}", file=sys.stderr)
            return 2

    if args.print_cbc:
        print("=== Embedded conda_build_config.yaml ===")
        print(yaml.dump(cbc, default_flow_style=False))

    if args.assert_key:
        value = cbc.get(args.assert_key)
        if value is None:
            print(
                f"::error::Key '{args.assert_key}' not found in embedded CBC.\n"
                f"Available keys: {sorted(cbc.keys())}",
                file=sys.stderr,
            )
            return 1

        print(f"  {args.assert_key}: {value}")

        if args.contains and args.contains not in str(value):
            print(
                f"::error::Expected '{args.assert_key}' to contain '{args.contains}', "
                f"got: {value}",
                file=sys.stderr,
            )
            return 1

        qualifier = f" (contains '{args.contains}')" if args.contains else ""
        print(f"  ✓ {args.assert_key} = {value}{qualifier}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
