#/bin/bash
#
# Example:
# ./docker_run.sh /media/ssd/data

set -e  # Exit immediately on error
set -x  # Display command when running it

# --user and --group-add options are to allow read/write to data and notebook directories
# from within container.
docker run \
       --user $(id -u $USER) \
       --group-add users \
       --rm \
       --volume "${data_dir}":/data \
       dlab/two-photon:latest \
       "$@"
