#!/bin/bash
#
# Command-line script to execute ripping using the Docker container.
#
# Many flags are required for the internal /usr/bin/entrypoint script to setup permissions and turn
# off rendering of the app's windows.
#
# TODO: For the common case of batch running, investigate eliminating entrypoint script 
# and many of these variables.

if [ "$#" -ne 2 ]; then
    echo "Requires two arguments: name of the Docker image and the location containing RAWDATA and FileList files"
    exit -1
fi

## Support running in parallel:
# https://stackoverflow.com/questions/30332137/xvfb-run-unreliable-when-multiple-instances-invoked-in-parallel

# allow settings to be updated via environment
: "${xvfb_lockdir:=$HOME/.xvfb-locks}"
: "${xvfb_display_min:=99}"
: "${xvfb_display_max:=599}"

# assuming only one user will use this, let's put the locks in our own home directory
# avoids vulnerability to symlink attacks.
mkdir -p -- "$xvfb_lockdir" || exit

i=$xvfb_display_min     # minimum display number
while (( i < xvfb_display_max )); do
  if [ -f "/tmp/.X$i-lock" ]; then                # still avoid an obvious open display
    (( ++i )); continue
  fi
  exec 5>"$xvfb_lockdir/$i" || continue           # open a lockfile
  if flock -x -n 5; then                          # try to lock it
    # if locked, run

    # Flags determined by examining docker-wine with:
    # --as-me
    # --workdir
    # --xvfb
    # --name 
    # https://github.com/scottyhardy/docker-wine/blob/master/docker-wine
    exec docker run \
        -it \
        --rm \
        --volume=${2}:/data \
        --env=USER_NAME=${USER} \
        --env=USER_UID=$(id -u ${USER}) \
        --env=USER_GID=$(id -g ${USER}) \
        --env=USER_HOME=${HOME} \
        --workdir=/home/${USER} \
        --env=USE_XVFB=yes \
        --env=XVFB_SERVER=:$i \
        --env=XVFB_SCREEN=0 \
        --env=XVFB_RESOLUTION=320x240x8 \
        --env=DISPLAY=:$i \
        --hostname=bruker-ripper \
        --name=bruker-ripper-$i \
        --shm-size=1g \
        --env=TZ=America/Los_Angeles \
        ${1}
  fi
  (( i++ ))
done

