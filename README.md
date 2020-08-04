# two-photon

First, install the code.  You can use [GitHub desktop](https://desktop.github.com/), or use git on the command line:

```bash
git clone https://github.com/deisseroth-lab/two-photon.git
```

Next, install the environment.  You will need to install [conda](https://docs.conda.io/en/latest/) first.  Then
use the following command from within the directory where you installed the repo above.

```bash
conda env create -f environment.yml -n two-photon
```

To run the processing script, the environment needs to be activated:
```
conda activate two-photon
```

See the comments at the top of the [preprocess script](https://github.com/deisseroth-lab/two-photon/blob/master/process.py)
for examples of how to run the processing.

## Docker for ripping only

To build the docker container and tag it as `two-photon:latest`, use:

```bash
docker build -t two-photon .
```

Run the ripper using the command like the following (remove `--xvfb` to launch the GUI).  Substitute your own
data information in both the `--volume` flag (for mounting), the `--input_dir` flag, and the `--recording` flag.  

```bash
./docker-wine/docker-wine \
    --xvfb \
    --volume=/media/hdd0:/media/hdd0 \
    --home-volume=${HOME} \
    --local=two-photon \
    python \
    /app/process.py \
    --ripper='/Prairie View/Utilities/Image-Block Ripping Utility.exe' \
    --input_dir=/media/hdd0/two-photon \
    --output_dir=/media/hdd0/two-photon-output \
    --recording=sample:overview-023 \
    --rip
```

To use X11 forwarding, remove the `--xvfb` flag.

## Singularity for ripping only

The following singularity commands are adapted from the equivalent docker commands that 
`docker-wine` runs.

To build the Singularity container, build the Docker container first and then convert:

```bash
docker build -t two-photon .
singularity build two-photon.sif docker-daemon://two-photon:latest
```

Similar to docker, tweak the 1st `--bind` flag, the `--input_dir` flag, and the `--recording` flag.  

```bash
singularity exec \
    --bind=/media/hdd0:/media/hdd0 \
    --env=USER_NAME=${USER} \
    --env=USER_UID=$(id -u) \
    --env=USER_GID=$(id -g) \
    --env=USER_HOME=${HOME} \
    --env=USE_XVFB=yes \
    --env=XVFB_SERVER=:95 \
    --env=XVFB_SCREEN=0 \
    --env=XVFB_RESOLUTION=320x240x8 \
    --env=DISPLAY=:95 \
    --hostname="$(hostname)" \
    --bind=${HOME}:${HOME} \
    --workdir=${HOME} \
    --env=TZ=America/Los_Angeles \
    two-photon.sif \
    xvfb-run \
    python \
    /app/process.py \
    --ripper='/Prairie View/Utilities/Image-Block Ripping Utility.exe' \
    --input_dir=/media/hdd0/two-photon \
    --output_dir=/media/hdd0/two-photon-output \
    --recording=sample:overview-023 \
    --rip
```

To use X11 forwarding, the incantation is a bit different.  First, an Xkey file is needed:

```bash
xauth list "${DISPLAY}" | head -n1 | awk '{print $3}' > ~/.docker-wine.Xkey
chmod 600 ~/.docker-wine.Xkey
```

Then run the following:

```bash
singularity exec \
    --bind=/media/hdd0:/media/hdd0 \
    --env=USER_NAME=${USER} \
    --env=USER_UID=$(id -u) \
    --env=USER_GID=$(id -g) \
    --env=USER_HOME=${HOME} \ 
    --volume=${HOME}/.docker-wine.Xkey:/root/.Xkey:ro \
    --volume=/tmp/pulse-socket:/tmp/pulse-socket \
    --env=DISPLAY=${DISPLAY} \
    --volume=/tmp/.X11-unix:/tmp/.X11-unix:ro \
    --hostname=hoosierdaddy \
    --volume=${HOME}:${HOME} \
    --workdir=${HOME} \
    --env=TZ=America/Los_Angeles two-photon:latest \
    two-photon.sif \ 
    python \
    /app/process.py \
    --ripper='/Prairie View/Utilities/Image-Block Ripping Utility.exe' \
    --input_dir=/media/hdd0/two-photon \
    --output_dir=/media/hdd0/two-photon-output \
    --recording=sample:overview-023 \
    --rip
```
