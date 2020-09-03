#!/bin/bash
#
# Command-line script to execute ripping using the Singularity container.

if [ "$#" -ne 2 ]; then
    echo "Requires two arguments: location of singularity file, and location containing RAWDATA and FileList files"
    exit -1
fi

singularity run --bind=${2}:/data ${1}
