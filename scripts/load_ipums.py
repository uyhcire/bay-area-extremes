#!/usr/bin/env python3
#
# Load an IPUMS microdata extract (the .dat.gz fixed-width file + its .xml DDI
# codebook produced by scripts/download_ipums.sh) into a pandas DataFrame.
#
# Requires the official client:  pip install ipumspy
#
# Usage:
#   scripts/load_ipums.py [EXTRACT]
#
#   EXTRACT   Path to either the .dat.gz data file or the .xml DDI, OR a
#             directory containing exactly one extract. Defaults to the
#             newest extract under data/raw/ipums_usa/.
#
# Options:
#   --ca           Filter to California person records (STATEFIP == 6).
#   --counties     Comma-separated county FIPS to filter to via PUMA-overlap is
#                  NOT done here (PUMS bottoms out at PUMA); use --ca then map
#                  PUMAs yourself. Kept out on purpose to avoid a false join.
#   --head N       Print the first N rows (default 5).
#   --describe     Print row/column counts and per-column IPUMS descriptions.
#
# Examples:
#   scripts/load_ipums.py --describe
#   scripts/load_ipums.py data/raw/ipums_usa/usa_00001.xml --ca --head 10
#
# This is a thin, well-documented wrapper around ipumspy.readers so analysis
# notebooks don't each re-implement the .dat.gz/.xml pairing logic.
import argparse
import glob
import os
import sys


def find_extract(arg: str | None) -> tuple[str, str]:
    """Resolve (ddi_xml_path, data_dat_path) from a file, directory, or default."""
    search_dir = "data/raw/ipums_usa"
    candidate = arg

    if candidate is None:
        if not os.path.isdir(search_dir):
            sys.exit(
                f"No extract given and {search_dir}/ not found. "
                "Run scripts/download_ipums.sh first."
            )
        candidate = search_dir

    if os.path.isdir(candidate):
        xmls = sorted(glob.glob(os.path.join(candidate, "*.xml")))
        if not xmls:
            sys.exit(f"No .xml DDI codebook found in {candidate}/.")
        ddi_path = xmls[-1]  # newest by name (usa_00001, usa_00002, ...)
    elif candidate.endswith(".xml"):
        ddi_path = candidate
    elif candidate.endswith(".dat.gz") or candidate.endswith(".dat"):
        ddi_path = candidate.replace(".dat.gz", ".xml").replace(".dat", ".xml")
    else:
        sys.exit(f"Don't know how to load '{candidate}' (expected .xml, .dat.gz, or a dir).")

    if not os.path.exists(ddi_path):
        sys.exit(f"DDI codebook not found: {ddi_path}")
    return ddi_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load an IPUMS extract into pandas.")
    parser.add_argument("extract", nargs="?", default=None,
                        help="Path to .dat.gz / .xml, or a directory (default: data/raw/ipums_usa).")
    parser.add_argument("--ca", action="store_true",
                        help="Filter to California (STATEFIP == 6).")
    parser.add_argument("--head", type=int, default=5, help="Rows to print (default 5).")
    parser.add_argument("--describe", action="store_true",
                        help="Print shape and per-column IPUMS descriptions.")
    args = parser.parse_args()

    try:
        from ipumspy import readers
    except ImportError:
        sys.exit("The 'ipumspy' package is required: pip install ipumspy")

    ddi_path = find_extract(args.extract)
    data_path = ddi_path.replace(".xml", ".dat.gz")
    if not os.path.exists(data_path):
        # fall back to uncompressed
        alt = ddi_path.replace(".xml", ".dat")
        data_path = alt if os.path.exists(alt) else data_path

    ddi = readers.read_ipums_ddi(ddi_path)
    df = readers.read_microdata(ddi, data_path)

    if args.ca:
        if "STATEFIP" not in df.columns:
            sys.exit("--ca requested but STATEFIP is not in this extract's variables.")
        df = df[df["STATEFIP"] == 6]

    if args.describe:
        print(f"Extract:  {ddi_path}")
        print(f"Rows:     {len(df):,}")
        print(f"Columns:  {df.shape[1]}")
        print()
        for var in ddi.data_description:
            print(f"  {var.name:<10} {var.label}")
    else:
        print(f"Loaded {len(df):,} rows x {df.shape[1]} columns from {os.path.basename(data_path)}")
        print(df.head(args.head).to_string())


if __name__ == "__main__":
    main()
