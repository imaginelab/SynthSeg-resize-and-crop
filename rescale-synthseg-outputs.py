import pandas as pd


def rescale_synthseg_volumes(volumes_csv: str,
                             qc_csv: str,
                             scaling_factor: float,
                             out_csv: str) -> None:
    """
    Rescale SynthSeg volumes by dividing all volume columns
    (everything except 'subject') by scaling_factor^3
    and save adjusted volumes + QC columns to out_csv.

    Requirements:
        - scaling_factor must be provided and non-zero
        - volumes and QC files must have same number of rows
        - row order must match
    """

    # Enforce scaling factor
    if scaling_factor is None:
        raise ValueError("No scaling_factor supplied.")
    try:
        sf = float(scaling_factor)
    except Exception as e:
        raise ValueError(f"Invalid scaling_factor={scaling_factor!r}. Must be numeric.") from e
    if sf == 0:
        raise ValueError("scaling_factor must be non-zero.")

    denom = sf ** 3

    # Read files
    vol = pd.read_csv(volumes_csv)
    qc = pd.read_csv(qc_csv)

    if "subject" not in vol.columns:
        raise ValueError("Expected column 'subject' in volumes file.")

    print('Adjusting volumes by scaling factor')
    # Eescale all volume columns except 'subject'
    volume_cols = [c for c in vol.columns if c != "subject"]

    vol[volume_cols] = vol[volume_cols].apply(
        lambda s: pd.to_numeric(s, errors="coerce") / denom
    )

    # Commbine volume and qc file and save
    out = pd.concat([vol, qc], axis=1)
    out.to_csv(out_csv, index=False)


if __name__ == "__main__":
    import sys
    volumes_csv = sys.argv[1]
    qc_csv = sys.argv[2]
    scaling_factor = float(sys.argv[3])
    out_csv = sys.argv[4]
    rescale_synthseg_volumes(volumes_csv, qc_csv, scaling_factor, out_csv)
