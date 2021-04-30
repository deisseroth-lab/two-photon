#!/bin/bash
#
# Command-line script to execute ripping using the Docker container.
#
# Many flags are required for the internal /usr/bin/entrypoint script to setup permissions and turn
# off rendering of the app's windows.
#
# TODO: For the common case of batch running, investigate eliminating entrypoint script 
# and many of these variables.

set -e

if [ "$#" -ne 2 ]; then
    echo "Requires two arguments: name of the Docker image, and path to acquisition top-level directory"
    exit -1
fi

if [ ! -d "${2}" ]; then
    echo "Directory missing: ${2}"
    exit -2
fi

# Flags determined by examining docker-wine with:
# --as-me
# --workdir
# --xvfb
# --name 
# https://github.com/scottyhardy/docker-wine/blob/master/docker-wine
docker run \
       -it \
       --rm \
       --volume=${2}:/data \
       --env=USER_NAME=${USER} \
       --env=USER_UID=$(id -u ${USER}) \
       --env=USER_GID=$(id -g ${USER}) \
       --env=USER_HOME=${HOME} \
       --workdir=/home/${USER} \
       --env=USE_XVFB=yes \
       --env=XVFB_SERVER=:95 \
       --env=XVFB_SCREEN=0 \
       --env=XVFB_RESOLUTION=320x240x8 \
       --env=DISPLAY=:95 \
       --hostname=bruker-ripper \
       --name=bruker-ripper \
       --shm-size=1g \
       --env=TZ=America/Los_Angeles \
       ${1}
