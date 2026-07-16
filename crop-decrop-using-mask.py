#!/usr/bin/env python3
# This script provides a cropping and decropping function
# The cropping function allows the user to an image and crop it using a mask, and optionally, an additional boundary around the mask
# Examplary usage:
# CROP
# python crop-decrop-using-mask.py crop \
#  --in_file "sub-001_ses-001_T1w.nii.gz" \
#  --mask_file "sub-001_ses-001_desc-brainmask_T1w.nii.gz" \
#  --out_file "sub-001_ses-001_desc-cropped_T1w.nii.gz" \
#  --pad_mm 25
#
# DECROP
# python crop-decrop-using-mask.py decrop \
#  --cropped_file "sub-001_ses-001_desc-cropped_T1w.nii.gz" \
#  --ref_full_file "sub-001_ses-001_T1w.nii.gz" \
#  --out_file "sub-001_ses-001_desc-decropped_T1w.nii.gz"

import argparse
import os
import numpy as np
import ants

parser = argparse.ArgumentParser(description="ANTs crop / decrop using mm padding.")
sub = parser.add_subparsers(dest="mode", required=True)

# ---- crop ----
p_crop = sub.add_parser("crop")
p_crop.add_argument("--in_file", required=True)
p_crop.add_argument("--mask_file", required=True)
p_crop.add_argument("--out_file", required=True)
p_crop.add_argument("--pad_mm", type=float, default=25.0)

# ---- decrop ----
p_decrop = sub.add_parser("decrop")
p_decrop.add_argument("--cropped_file", required=True)
p_decrop.add_argument("--ref_full_file", required=True)
p_decrop.add_argument("--out_file", required=True)

args = parser.parse_args()

if args.mode == "crop":
    img  = ants.image_read(args.in_file)
    mask = ants.image_read(args.mask_file)

    m = mask.numpy() > 0
    coords = np.array(np.nonzero(m))
    if coords.size == 0:
        raise RuntimeError("Mask is empty (no voxels > 0); cannot crop.")

    xmin, ymin, zmin = coords.min(axis=1)
    xmax, ymax, zmax = coords.max(axis=1)

    sx, sy, sz = img.spacing  # mm
    px = int(round(args.pad_mm / sx)) if args.pad_mm > 0 else 0
    py = int(round(args.pad_mm / sy)) if args.pad_mm > 0 else 0
    pz = int(round(args.pad_mm / sz)) if args.pad_mm > 0 else 0

    # expand bbox + clamp
    xmin = max(int(xmin) - px, 0)
    ymin = max(int(ymin) - py, 0)
    zmin = max(int(zmin) - pz, 0)

    xmax = min(int(xmax) + px, img.shape[0] - 1)
    ymax = min(int(ymax) + py, img.shape[1] - 1)
    zmax = min(int(zmax) + pz, img.shape[2] - 1)

    lower = (xmin, ymin, zmin)
    upper = (xmax, ymax, zmax)

    print(f"Padding: {args.pad_mm} mm")
    print(f"Spacing: {img.spacing}")
    print(f"Pad vox:  {(px, py, pz)}")
    print(f"BBox:     lower={lower} upper={upper}")

    cropped = ants.crop_indices(img, lowerind=lower, upperind=upper)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_file)), exist_ok=True)
    ants.image_write(cropped, args.out_file)

    print("Cropped:", args.out_file)
    print("Original size:", img.shape)
    print("Cropped size:", cropped.shape)

elif args.mode == "decrop":
    cropped = ants.image_read(args.cropped_file)
    ref     = ants.image_read(args.ref_full_file)

    decropped = ants.decrop_image(cropped, ref)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_file)), exist_ok=True)
    ants.image_write(decropped, args.out_file)

    print("Decropped:", args.out_file)
    print("Full size:", ref.shape)



