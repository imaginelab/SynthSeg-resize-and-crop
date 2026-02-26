##!/bin/bash

set -euo pipefail

# -------------------- usage/help --------------------
usage() {
  cat <<'EOF'
Usage:
  reconall-clinical-resampling.sh [options]

Required arguments:
  --subid SUBID                    e.g. sub-001
  --age_days AGE                   integer days
  --input_file PATH                path to input NIfTI (.nii.gz)
  --modality MOD                   T1w | T2w | FLAIR | ...
  --scale SCALE                    e.g. 0.5
  --outdir PATH                    output directory
  --fs_singularity PATH            path to FreeSurfer Singularity (.sif)
  --fs_license PATH                FreeSurfer license.txt
  --toolpath PATH                  path to tool folder

Optional:
  -h, --help                       show this help and exit

Example:
  reconall-clinical-resampling.sh \
    --subid sub-123456 \
    --age_days 180 \
    --input_file /data/sub-123456/..._T2w.nii.gz \
    --modality T2w \
    --scale 0.5 \
    --outdir /out/sub-123456/ses-1 \
    --fs_singularity /tools/freesurfer/freesurfer_7.4.1.sif \
    --fs_license /tools/freesurfer/license.txt \
    --toolpath /tools/reconall-clinical-resampling \
EOF
}

die() { echo "ERROR: $*" >&2; exit 2; }

# -------------------- defaults --------------------
SUBID=""; AGE_DAYS=""; INPUT_FILE=""; MODALITY=""
SCALE=""; OUTDIR=""; FS_SINGULARITY=""
FS_LICENSE=""; TOOLPATH=""

# -------------------- parse arguments --------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;

    --subid)           SUBID="${2:?}"; shift 2 ;;
    --subid=*)         SUBID="${1#*=}"; shift ;;

    --age_days)        AGE_DAYS="${2:?}"; shift 2 ;;
    --age_days=*)      AGE_DAYS="${1#*=}"; shift ;;

    --input_file)      INPUT_FILE="${2:?}"; shift 2 ;;
    --input_file=*)    INPUT_FILE="${1#*=}"; shift ;;

    --modality)        MODALITY="${2:?}"; shift 2 ;;
    --modality=*)      MODALITY="${1#*=}"; shift ;;

    --scale)           SCALE="${2:?}"; shift 2 ;;
    --scale=*)         SCALE="${1#*=}"; shift ;;

    --outdir)          OUTDIR="${2:?}"; shift 2 ;;
    --outdir=*)        OUTDIR="${1#*=}"; shift ;;

    --fs_singularity)  FS_SINGULARITY="${2:?}"; shift 2 ;;
    --fs_singularity=*)FS_SINGULARITY="${1#*=}"; shift ;;

    --fs_license)      FS_LICENSE="${2:?}"; shift 2 ;;
    --fs_license=*)    FS_LICENSE="${1#*=}"; shift ;;

    --toolpath)        TOOLPATH="${2:?}"; shift 2 ;;
    --toolpath=*)      TOOLPATH="${1#*=}"; shift ;;

    -*) die "Unknown option: $1 (see --help)" ;;
    *)  break ;;
  esac
done

# -------------------- validate required --------------------
[[ -n "$SUBID"          ]] || die "--subid is required"
[[ -n "$AGE_DAYS"       ]] || die "--age_days is required"
[[ -n "$INPUT_FILE"     ]] || die "--input_file is required"
[[ -n "$MODALITY"       ]] || die "--modality is required"
[[ -n "$SCALE"          ]] || die "--scale is required"
[[ -n "$OUTDIR"         ]] || die "--outdir is required"
[[ -n "$FS_SINGULARITY" ]] || die "--fs_singularity is required"
[[ -n "$FS_LICENSE"     ]] || die "--fs_license is required"
[[ -n "$TOOLPATH"       ]] || die "--toolpath is required"

# sanity checks
[[ -f "$INPUT_FILE"     ]] || die "input_file not found: $INPUT_FILE"
[[ -f "$FS_SINGULARITY" ]] || die "fs_singularity not found: $FS_SINGULARITY"
[[ -f "$FS_LICENSE"     ]] || die "fs_license not found: $FS_LICENSE"
[[ -d "$TOOLPATH"       ]] || die "toolpath not found: $TOOLPATH"


now=$(date +"%T")
echo "Start time : $now"

#############################################################
# STEP 1: GET SCALING FACTOR
#############################################################

if [[ "$AGE_DAYS" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  AGE_DAYS_ROUNDED=$(printf "%.0f" "$AGE_DAYS")
  # Check if rounding changed the value
  if (( $(echo "$AGE_DAYS != $AGE_DAYS_ROUNDED" | bc -l) )); then
    echo "Warning: age_days ($AGE_DAYS) was rounded to nearest full day ($AGE_DAYS_ROUNDED)" >&2
    AGE_DAYS=${AGE_DAYS_ROUNDED}
  fi
else
  echo "ERROR: AGE_DAYS is not a valid number: '$AGE_DAYS'" >&2
  exit 1
fi


# ensure SCALE is numeric and 0 < SCALE < 1
if ! awk -v s="${SCALE}" 'BEGIN{exit !(s ~ /^0?\.[0-9]+$/ || s=="0" || s=="1")}'; then
  echo "ERROR: --scale must be a number between 0 and 1 (e.g., 0.5, 0.975)" >&2
  exit 1
fi
# reject 0 and 1 explicitly
if awk -v s="${SCALE}" 'BEGIN{exit !(s>0 && s<1)}'; then :; else
  echo "ERROR: --scale must be strictly between 0 and 1 (0 < scale < 1)" >&2
  exit 1
fi

echo "Get scaling factor by age"

# --- Convert SCALE (e.g., 0.975 -> 975; 0.5 -> 500) ---
# Multiply by 1000 and round to nearest integer
csv_file="${TOOLPATH%/}/scaling-factor.csv"

scale_suffix="$(awk -v s="$SCALE" 'BEGIN{if(!(s>0&&s<1)) exit 1; printf "%.0f", s*1000}')"
col="scalefactor_adj_perc${scale_suffix}"

scale_factor="$(
  awk -v age="$AGE_DAYS" -v col="$col" -F',' '
    NR==1{
      for(i=1;i<=NF;i++){ gsub(/^"|"$/,"",$i); if($i=="age_days") A=i; if($i==col) C=i }
      next
    }
    {
      # strip quotes on the fields we care about (robust if some rows are quoted)
      if (A) { tmp=$A; gsub(/^"|"$/,"",tmp); $A=tmp }
      if (C) { tmp=$C; gsub(/^"|"$/,"",tmp); $C=tmp }
    }
    $A==age { print $C; exit }
  ' "$csv_file"
)"


# If awk exited with error, pipeline would have already exited (set -e)
# Otherwise, we have the value in SCALE_FACTOR
if [ -z "${scale_factor}" ]; then
  echo "ERROR: Scaling factor empty for ${col} at age_days=${AGE_DAYS}." >&2
  exit 4
fi

echo "Selected column: ${col}"
echo "Scaling factor for age_days=${AGE_DAYS}: ${scale_factor}"


#############################################################
# STEP 2: RESCALE SCAN
#############################################################

echo "Rescale data"
# Extract the filename (without extension)
filename=$(basename "$INPUT_FILE" .nii.gz)
# If the filename ends with "_${MODALITY}", strip it
if [[ "$filename" == *_${MODALITY} ]]; then
    scan_identifier="${filename%_${MODALITY}}"
else
    scan_identifier="$filename"
fi

resampled_scan=${scan_identifier}_res-${scale_factor}_${MODALITY}
output_file=${OUTDIR}/${resampled_scan}/${resampled_scan}.nii.gz

mkdir -p ${OUTDIR}/${resampled_scan}/
python ${TOOLPATH}/change-resolution-header.py -i ${INPUT_FILE} -o ${output_file} -s ${scale_factor}

now=$(date +"%T")
echo "Resized image;  Current time : $now"

#############################################################
# STEP 3: SYNTHSTRIP CROPPING
#############################################################

echo "Crop data"

resized_cropped_scan=${scan_identifier}_res-${scale_factor}_desc-cropped_${MODALITY}
brainmask=${scan_identifier}_res-${scale_factor}_desc-brainmask_${MODALITY}
skullstripped_scan=${scan_identifier}_res-${scale_factor}_desc-skullstripped_${MODALITY}

singularity run --cleanenv \
  --env FS_LICENSE=${FS_LICENSE} \
  --env SUBJECTS_DIR=${OUTDIR}/${resampled_scan}/ \
  -B ${FS_LICENSE}:/opt/freesurfer/license.txt \
  -B ${OUTDIR}/${resampled_scan}/:/derivatives \
  ${FS_SINGULARITY} \
  mri_synthstrip \
  -i /derivatives/${resampled_scan}.nii.gz \
  -o /derivatives/${skullstripped_scan}.nii.gz \
  -m /derivatives/${brainmask}.nii.gz

python ${TOOLPATH}/crop-decrop-using-mask.py crop \
  --in_file ${OUTDIR}/${resampled_scan}/${resampled_scan}.nii.gz \
  --mask_file ${OUTDIR}/${resampled_scan}/${brainmask}.nii.gz \
  --out_file ${OUTDIR}/${resampled_scan}/${resized_cropped_scan}.nii.gz \
  --pad_mm 25

now=$(date +"%T")
echo "Cropped image;  Current time : $now"

#############################################################
# STEP 5: RUN SYNTHSEG
#############################################################

echo "Running SynthSeg"

preprocessed_identifier=${resized_cropped_scan}
outcsv=${OUTDIR}/${resampled_scan}/${preprocessed_identifier}_volumes.csv
outqc=${OUTDIR}/${resampled_scan}/${preprocessed_identifier}_qc.csv
outseg=${OUTDIR}/${resampled_scan}/${preprocessed_identifier}_seg.nii.gz

# If this file exists, run synthseg
if [[ -f ${OUTDIR}/${resampled_scan}/${preprocessed_identifier}.nii.gz ]]; then
        python ${synthsegpath}/scripts/commands/SynthSeg_predict.py --i ${OUTDIR}/${resampled_scan}/${preprocessed_identifier}.nii.gz --o ${outseg} --parc --robust --vol ${outcsv} --qc ${outqc}
        echo "Ran SynthSeg;  Current time : $now"
fi


#############################################################
# STEP 6: GET RESIZED PARCELLATION INTO NATIVE SPACE 
#############################################################

# Inverse scaling factor
inv_resolution=$(printf '%s / %s\n' "1" "$scale_factor" | bc -l)

echo "Resampled segementation file to input file space"

segmentation_inverse=${preprocessed_identifier}_desc-inverse_seg.nii.gz
segmentation_native=${preprocessed_identifier}_desc-native_seg.nii.gz

singularity run --cleanenv \
  --env FS_LICENSE=${FS_LICENSE} \
  --env SUBJECTS_DIR="${OUTDIR}/${resampled_scan}/" \
  -B ${FS_LICENSE}:/opt/freesurfer/license.txt \
  -B ${OUTDIR}:/derivatives \
  ${FS_SINGULARITY} \
  mri_vol2vol \
    --mov /derivatives/${resampled_scan}/${preprocessed_identifier}_seg.nii.gz \
    --targ /derivatives/${resampled_scan}/${resampled_scan}.nii.gz \
    --regheader \
    --interp nearest \
    --o /derivatives/${resampled_scan}/${segmentation_inverse}

echo "Resampled SynthSeg segmentation to input resized space"

python change-resolution-header.py \
        -i ${OUTDIR}/${resampled_scan}/${segmentation_inverse} \
        -o ${OUTDIR}/${resampled_scan}/${segmentation_native} \
        -s ${inv_resolution} \
        --force-int

echo "Header change resampled SynthSeg segmentation"


#############################################################
# STEP 7: ESTIMATE VOLUMES IN NATIVE SPACE
#############################################################

echo "Estimating regional volumes from segmentation in native space"

segstats=${preprocessed_identifier}_desc-native_volumes.csv

singularity run --cleanenv \
  --env FS_LICENSE=${FS_LICENSE} \
  --env SUBJECTS_DIR="${OUTDIR}/${resampled_scan}/" \
  -B ${FS_LICENSE}:/opt/freesurfer/license.txt \
  -B ${OUTDIR}:/derivatives \
  ${FS_SINGULARITY} \
  mri_segstats \
  --seg /derivatives/${resampled_scan}/${segmentation_native} \
  --sum /derivatives/${resampled_scan}/${segstats} \
  --ctab ${TOOLPATH}/FreeSurferColorLUT.txt

echo "Aggregating outputs to csv"
python ${TOOLPATH}/write-segstats-and-qc-output.py \
        ${OUTDIR}/${resampled_scan}/${segmentation_native} \
        ${OUTDIR}/${resampled_scan}/${segstats} \
        ${outqc} \
        ${OUTDIR}/${resampled_scan}/${preprocessed_identifier}_volumes-and-qc.csv
echo "All done! Congrats!"

conda deactivate

now=$(date +"%T")

