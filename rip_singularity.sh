#!/bin/bash
#
# Command-line script to execute ripping using the Singularity container.

if [ "$#" -ne 1 ]; then
    echo "Require one argument: directory to rip, which should contain RAWDATA and FileList files"
    exit -1
fi

singularity run --bind=${1}:/data two-photon.sif
