#/bin/bash
#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Require one argument: directory to rip, which should contain RAWDATA and FileList files"
fi

# Possibly would need xvfb-run
#
# Docker arguments that do not translate to singularity.
#       -it \
#       --rm \
#       --name=wine \
#       --shm-size=1g \

# create profiles directory to save profiles
mkdir -p profiles

# Run the container! Note that you can also build the container with any Windows
# applications already added (instead of bound)
singularity run \
    --bind "${PWD}/Prairie View":"/APPS/Prairie View/" \
    --bind ${PWD}/profiles:/PROFILES \
    --bind=${1}:/data \
    two-photon.sif
