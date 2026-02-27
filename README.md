# SynthSeg-resize-and-crop

Pipeline for resizing infant MRI scans to adult-like sizes, and cropping them, to run SynthSeg on them. This is a work around to make SynthSeg run smoothly on very young infants. 

## Requirements
#### 1. This repository
Clone the github repo, for example into `tools/`: 

```
mkdir -p tools/SynthSeg-resize-and-crop
cd tools/SynthSeg-resize-and-crop
git clone git@github.com:LenaDorfschmidt/SynthSeg-resize-and-crop.git
```

#### 2. FreeSurfer 7.4.1 singularity container
We can convert the official docker container into a singularity container, for example into a folder `tools/freesurfer/`

```
mkdir -p tools/freesurfer
cd tools/freesurfer
singularity pull freesurfer_7.4.1.sif docker://freesurfer/freesurfer:7.4.1
```

You will also need to obtain a FreeSurfer license file from: https://surfer.nmr.mgh.harvard.edu/fswiki/License
  
#### 3. Python
You will need a working python installation with libraries:

- python=3.10
- numpy
- pandas
- nibabel
- pip
- antspyx

Install a python environment using the `environment.yml` file. I installed it into a specific location `$ENV_PATH`: 

```
conda env create -p "$ENV_PATH" -f environment.yml
```

## Usage
Examplary usage:

```
Usage:
  SSr-resize-and-crop.sh [options]

Required arguments:
  --subid SUBID                    e.g. sub-001
  --age_days AGE                   integer days
  --input_file PATH                path to input NIfTI (.nii.gz)
  --modality MOD                   T1w | T2w | FLAIR | ...
  --scale SCALE                    e.g. 0.5
  --outdir PATH                    output directory
  --fs_singularity PATH            path to FreeSurfer Singularity (.sif)
  --fs_license PATH                FreeSurfer license.txt
  --toolpath PATH                  Path to SynthSeg resize and crop tool folder

Optional:
  -h, --help                       show this help and exit

Example:
  SynthSeg-resize-and-crop.sh \
    --subid sub-123456 \
    --age_days 180 \
    --input_file sub-12345_ses-01_..._T2w.nii.gz \
    --modality T2w \
    --scale 0.5 \
    --outdir /out/sub-123456/ses-01/ \
    --fs_singularity /tools/freesurfer/freesurfer_7.4.1.sif \
    --fs_license /tools/freesurfer/license.txt \
    --toolpath /tools/SynthSeg-resize-and-crop/

```



