#/bin/bash
#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Require one argument: directory to rip, which should contain RAWDATA and FileList files"
fi

docker run \
       -it \
       --volume=${1}:/data \
       --env=RUN_AS_ROOT=yes \
       --env=USE_XVFB=yes \
       --env=XVFB_SERVER=:95 \
       --env=XVFB_SCREEN=0 \
       --env=XVFB_RESOLUTION=320x240x8 \
       --env=DISPLAY=:95 \
       --rm \
       --hostname="$(hostname)" \
       --name=wine \
       --shm-size=1g \
       --workdir=/ \
       --env=TZ=America/Los_Angeles \
       two-photon:latest \
       python /app/rip.py --directory=/data
