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

singularity exec \
	    --bind=${1}:/data \
	    --env=RUN_AS_ROOT=yes \
	    --env=USE_XVFB=yes \
	    --env=XVFB_SERVER=:95 \
	    --env=XVFB_SCREEN=0 \
	    --env=XVFB_RESOLUTION=320x240x8 \
	    --env=DISPLAY=:95 \
	    --hostname="$(hostname)" \
	    --workdir=/ \
	    --env=TZ=America/Los_Angeles \
	    two-photon.sif \
	    xvfb-run python /app/rip.py --directory=/data
