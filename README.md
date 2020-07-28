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

## Docker

To build the docker container and tag it as `two-photon:latest`, use:

```bash
docker build -t two-photon .
```

Run the ripper using the command like the following (remove `--xvfb` to launch the GUI).  Substitute your own
data directory in both the --volume flag and the `-AddRawFileWithSubFolders`/`-SetOutputDirectory` flags.  

Note that the exectuable will not stop on its own, and needs to be killed with `docker container stop wine` once
the data is processed.

```bash
./docker-wine/docker-wine \
    --xvfb \
    --volume=/media/hdd0:/media/hdd0 \
    --home-volume=${HOME} \
    --local=two-photon \
    wine '/Prairie View/Utilities/Image-Block Ripping Utility.exe' \
    -IncludeSubFolders \
    -AddRawFileWithSubFolders \
    /media/hdd0/two-photon/sample/overview-023 \
    -SetOutputDirectory \
    /media/hdd0/two-photon/sample/overview-023 \
    -Convert 
```

## Singularity

The following singularity commands are adapted from the equivalent docker commands that 
`docker-wine` runs.

To build the Singularity container, build the Docker container first and then convert:

```bash
docker build -t two-photon .
singularity build two-photon.sif docker-daemon://two-photon:latest
```

With X11 forwarding (needs Xkey, which is automatically created when using `docker-wine` above):

```bash
singularity exec \
    --env=USER_NAME=${USER} \
    --env=USER_UID=1001 \
    --env=USER_GID=1001 \
    --env=USER_HOME=${HOME} \
    --bind=${HOME}/.docker-wine.Xkey:/root/.Xkey:ro \
    --bind=/tmp/pulse-socket:/tmp/pulse-socket \
    --bind=/tmp/.X11-unix:/tmp/.X11-unix:ro \
    --hostname="$(hostname)" \
    --bind=${HOME}:${HOME} \
    --workdir=${HOME} \
    --env=TZ=America/Los_Angeles \
    two-photon.sif \
    wine '/Prairie View/Utilities/Image-Block Ripping Utility.exe'
```

With no GUI is work-in-progress.  The following fails with 

```
002a:err:winediag:nodrv_CreateWindow Application tried to create a window, but no driver could be loaded.
002a:err:winediag:nodrv_CreateWindow Make sure that your X server is running and that $DISPLAY is set correctly.
```

```bash
singularity exec \
    --env=USER_NAME=${USER} \
    --env=USER_UID=1001 \
    --env=USER_GID=1001 \
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
    wine '/Prairie View/Utilities/Image-Block Ripping Utility.exe'
```
