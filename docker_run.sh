#/bin/bash

# Example:
# ./docker_run.sh 8888 ${PWD}/notebooks /media/ssd/data

set -e  # Exit immediately on error

usage() { echo "Usage: $0 [jupyter_port] [notebook_dir] [data_dir]"; exit 1; }
[ $# == 3 ] || usage
port="${1}"
notebook_dir="${2}"
data_dir="${3}"

set -x  # Display command when running it

# --user and --group-add options are to allow read/write to data and notebook directories
# from within container.
docker run \
       --user $(id -u $USER) \
       --group-add users \
       --rm \
       --publish ${port}:8888 \
       --env JUPYTER_ENABLE_LAB=yes \
       --volume "${notebook_dir}":/home/jovyan/work \
       --volume "${data_dir}":/data \
       dlab/two-photon-jupyter:latest \
       start-notebook.sh --NotebookApp.password='sha1:44a74847f86a:0f42fd0ccf3710917712856a47edaa2252105d80'
