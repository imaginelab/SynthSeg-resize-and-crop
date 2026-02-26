#!/usr/bin/env python3

import argparse
import os
import sys

import pandas as pd


def read_stats(stats_path: str) -> pd.DataFrame:
    """
    Read a FreeSurfer mri_segstats-style aseg+aparc stats file and return
    a *wide* DataFrame with one row and one column per StructName
    containing Volume_mm3.

    Assumes standard format with 5 columns:
      Index, SegId, NVoxels, Volume_mm3, StructName
    and all header info in commented lines (# ...).
    """
    try:
        df = pd.read_csv(
            stats_path,
            delim_whitespace=True,
            comment="#",
            header=None,
            names=["Index", "SegId", "NVoxels", "Volume_mm3", "StructName"],
        )
    except Exception as e:
        raise RuntimeError(f"Failed to read stats file '{stats_path}': {e}")

    required_cols = {"StructName", "Volume_mm3"}
    missing = required_cols - set(df.columns)
    if missing:
        raise RuntimeError(
            f"Stats file '{stats_path}' is missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    # Long: StructName, Volume_mm3
    long_df = df[["StructName", "Volume_mm3"]].copy()

    # Just in case there are duplicate StructName entries, sum them
    grouped = (
        long_df.groupby("StructName", as_index=False)["Volume_mm3"]
        .sum()
    )

    # Wide: one row, columns = StructName, values = Volume_mm3
    wide_df = grouped.set_index("StructName")["Volume_mm3"].to_frame().T
    wide_df.reset_index(drop=True, inplace=True)

    return wide_df


def read_qc(qc_path: str) -> pd.DataFrame:
    """
    Read a SynthSeg QC file:
      subject,general white matter,general grey matter,...
      native.mgz,0.7477,0.7076,...

    Returns a 1-row DataFrame with:
      - 'subject' column dropped
      - all other columns renamed to have no spaces
        and start with 'qc_'
        e.g. 'general white matter' -> 'qc_general_white_matter'
    """
    ext = os.path.splitext(qc_path)[1].lower()

    try:
        if ext in [".tsv", ".txt"]:
            qc_df = pd.read_csv(qc_path, sep="\t")
        else:
            qc_df = pd.read_csv(qc_path)  # default: CSV
    except Exception as e:
        raise RuntimeError(f"Failed to read QC file '{qc_path}': {e}")

    if qc_df.shape[0] != 1:
        raise RuntimeError(
            f"Expected QC file '{qc_path}' to have exactly 1 row, "
            f"but found {qc_df.shape[0]}."
        )

    # Drop 'subject' column if present
    if "subject" in qc_df.columns:
        qc_df = qc_df.drop(columns=["subject"])

    # Rename remaining columns: strip spaces, replace spaces with '_', prefix with 'qc_'
    new_cols = {}
    for col in qc_df.columns:
        safe = col.strip().replace(" ", "_")
        new_cols[col] = f"qc_{safe}"

    qc_df = qc_df.rename(columns=new_cols)

    return qc_df


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Combine a FreeSurfer aparc/aseg stats file with a SynthSeg QC file "
            "for a single subject. Stats are reshaped wide (one row, one column "
            "per StructName). QC columns are renamed to 'qc_*', and both are "
            "combined into a single row with the NIfTI file as the first column."
        )
    )
    parser.add_argument(
        "nii_file",
        help="Path to the NIfTI file the stats are based on (will be first column in output).",
    )
    parser.add_argument(
        "stats_path",
        help="Path to aseg+aparc-native.stats file.",
    )
    parser.add_argument(
        "qc_path",
        help="Path to SynthSeg QC CSV/TSV file.",
    )
    parser.add_argument(
        "out_csv",
        help="Output CSV file name.",
    )

    args = parser.parse_args()

    try:
        stats_wide = read_stats(args.stats_path)
        qc_df = read_qc(args.qc_path)

        # One row with 'file' column
        base_df = pd.DataFrame({"file": [args.nii_file]})

        # All three should be 1-row dataframes; concatenate horizontally
        combined = pd.concat([base_df, stats_wide, qc_df], axis=1)

        combined.to_csv(args.out_csv, index=False)
        print(f"Wrote combined CSV to: {args.out_csv}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


