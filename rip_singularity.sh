#!/bin/bash
#
# Command-line script to execute ripping using the Singularity container.

if [ "$#" -ne 3 ]; then
    echo "Requires three arguments: name of the Singularity image, location containing RAWDATA and FileList files, and results location"
    exit -1
fi

singularity run --bind=${2}:/data --bind=${3}:/data ${1}
