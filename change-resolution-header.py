#!/usr/bin/env python3
"""
Change NIfTI header voxel size (via affine) without resampling data.

- By default, keeps the original data dtype (no integer forcing).
- Use --force-int to snap values to nearest integer and save as int32 (useful for label maps).
- Always clears NIfTI scaling (scl_slope=1, scl_inter=0) to avoid hidden rescaling.

Examples
--------
# Keep float dtype (default)
python change_resolution_header.py -i in.nii.gz -o out.nii.gz -s 1.5

# Force integers (for label maps)
python change_resolution_header.py -i aparc.nii.gz -o aparc_hdr_scaled.nii.gz -s 1.0 --force-int
"""
import argparse
import numpy as np
import nibabel as nb

def change_resolution_header(input_path, output_path, scale_factor, force_int=False):
    if force_int:
        # Load image (lazy)
        img = nb.load(input_path)

        # Read UNscaled voxel data (raw stored values; avoids scl_slope/intercept effects)
        data = np.asanyarray(img.dataobj)
    
        # Optionally coerce to integers (for parcellations/labels)
        if not np.issubdtype(data.dtype, np.integer):
            data = np.rint(data).astype(np.int32)
        else:
            data = data.astype(np.int32)

        # Update only voxel size via affine scaling (no resampling)
        affine = img.affine.copy()
        affine[:3, :3] = affine[:3, :3] * scale_factor

        # Clean header: remove scaling and set dtype appropriately
        hdr = img.header.copy()
        hdr.set_slope_inter(1.0, 0.0)
        hdr.set_data_dtype(np.int32)
        
        out_img = nb.Nifti1Image(data, affine, hdr)
    
    else:
        img = nb.load(input_path)
        data = img.get_fdata()
        affine = img.affine.copy()
        # Scale the voxel dimensions in the affine matrix only
        affine[:3, :3] = affine[:3, :3] * scale_factor
        # Create new image with same data but different header resolution
    
        out_img = nb.Nifti1Image(data, affine, img.header)
    
    nb.save(out_img, output_path)
    return output_path


#def change_resolution_header(input_path, output_path, scale_factor, force_int=False):
#    # Load image (lazy)
#    img = nb.load(input_path)
#
#    # Read UNscaled voxel data (raw stored values; avoids scl_slope/intercept effects)
#    data = np.asanyarray(img.dataobj)
#
#    # Optionally coerce to integers (for parcellations/labels)
#    if force_int:
#        if not np.issubdtype(data.dtype, np.integer):
#            data = np.rint(data).astype(np.int32)
#        else:
#            data = data.astype(np.int32)
#
#    # Update only voxel size via affine scaling (no resampling)
#    affine = img.affine.copy()
#    affine[:3, :3] = affine[:3, :3] * scale_factor
#
#    # Clean header: remove scaling and set dtype appropriately
#    hdr = img.header.copy()
#    hdr.set_slope_inter(1.0, 0.0)
#    if force_int:
#        hdr.set_data_dtype(np.int32)
#    else:
#        # Keep original stored dtype if possible; if it's weird, fall back to float32
#        try:
#            hdr.set_data_dtype(data.dtype)
#        except Exception:
#            hdr.set_data_dtype(np.float32)
#            data = data.astype(np.float32)
#
#    out = nb.Nifti1Image(data, affine, hdr)
#    nb.save(out, output_path)
#    return output_path



#def change_resolution_header(input_path, output_path, scale_factor, force_int=False):
#
#    # Load image (lazy)
#    img = nb.load(input_path)
#
#    # Read UNscaled voxel data (raw stored values; avoids scl_slope/intercept effects)
#    data = np.asanyarray(img.dataobj)
#
#    # Optionally coerce to integers (for parcellations/labels)
#    if force_int:
#        if not np.issubdtype(data.dtype, np.integer):
#            data = np.rint(data).astype(np.int32)
#        else:
#            data = data.astype(np.int32)
#
#    # Update only voxel size via affine scaling (no resampling)
#    affine = img.affine.copy()
#    affine[:3, :3] = affine[:3, :3] * scale_factor
#
#    # Clean header: remove scaling and set dtype appropriately
#    hdr = img.header.copy()
##    hdr.set_slope_inter(1.0, 0.0)
#    if force_int:
#        hdr.set_slope_inter(1.0, 0.0)
#        hdr.set_data_dtype(np.int32)
    #else:
    #    # Keep original stored dtype if possible; if it's weird, fall back to float32
    #    try:
    #        hdr.set_data_dtype(data.dtype)
    #    except Exception:
    #        hdr.set_data_dtype(np.float32)
    #        data = data.astype(np.float32)
#
#    out = nb.Nifti1Image(data, affine, hdr)
#    nb.save(out, output_path)
#    return output_path

def main():
    ap = argparse.ArgumentParser(description="Change NIfTI header voxel size without resampling data")
    ap.add_argument("-i", "--input", required=True, help="Input NIfTI")
    ap.add_argument("-o", "--output", required=True, help="Output NIfTI")
    ap.add_argument("-s", "--scale", type=float, required=True,
                    help="Multiply voxel sizes by this factor (e.g., 1.5)")
    ap.add_argument("--force-int", action="store_true",
                    help="Snap data to nearest integer and save as int32 (for label maps)")
    args = ap.parse_args()

    change_resolution_header(args.input, args.output, args.scale, force_int=args.force_int)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

