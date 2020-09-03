# two-photon

First, install the code. You can use [GitHub desktop](https://desktop.github.com/), or use git on the command line:

```bash
git clone https://github.com/deisseroth-lab/two-photon.git
```

Next, install the environment. You will need to install [conda](https://docs.conda.io/en/latest/) first. Then
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

Run the ripper using the following command, using a directory containin the *RAWDATA* and *FileList.txt files.

```bash
./docker_rip.sh /media/hdd0/two-photon/sample/overview-023
```

## Singularity for ripping only

### 1. Build from Docker

To build the Singularity container, build the Docker container first:

```bash
docker build -t dlab/two-photon:latest .
```

and then build the [Singularity recipe](singularity/Singularity) that has a custom entrypoint. 
Note that this script assumes the context to be the root of the repository.

```bash
sudo singularity build two-photon.sif singularity/Singularity
```

### 2. Run interactively 

If you don't bind a data directory, then the runscript (entrypoint) will give you an interactive bash
shell to issue commands. For example, if we don't
have data and want to interact with wine in the container:

```bash
# create profiles directory to save profiles
mkdir -p profiles

# Run the container! Note that you can also build the container with any Windows
# applications already added (instead of bound)
singularity run --bind ${PWD}/profiles:/PROFILES two-photon.sif
```

This is going to set up wine, and then start a bash shell for you to work with. For example,
I could use wine to open up the .exe file:

```bash
wine /APPS/Prairie\ View/Utilities/Image-Block\ Ripping\ Utility.exe
```

and this is the Image Block Ripping Utility:

![singularity/img/ripping-utility.png](singularity/img/ripping-utility.png)

If you want to run the ripper script, we can prepare to run the script by first
looking at its usage:

```bash
$ /usr/bin/python3 /app/rip.py --help
usage: rip.py [-h] --directory DIRECTORY [--ripper RIPPER]

Preprocess 2-photon raw data into individual tiffs

optional arguments:
  -h, --help            show this help message and exit
  --directory DIRECTORY
                        Directory containing RAWDATA and Filelist.txt files for ripping
  --ripper RIPPER       Location of Bruker Image Block Ripping Utility.
```

You would need to have bound the data to some folder in the container other than
/data (binding to data will run the script automatically). For example:

```bash
singularity run \
    --bind ${PWD}/profiles:/PROFILES \
    --bind ${PWD}/overview-23:/ripper-data \
    two-photon.sif
```

So we would then run:

```bash
$ /usr/bin/python3 /app/rip.py --directory /ripper-data
2020-08-30 13:26:17.533 rip:50 INFO Ripping from:
 /data/Cycle00001_Filelist.txt
 /data/CYCLE_000001_RAWDATA_000025
2020-08-30 13:26:17.536 rip:96 INFO Waiting for ripper to finish: 3600 seconds remaining
0032:fixme:ntdll:EtwEventRegister ({5eec90ab-c022-44b2-a5dd-fd716a222a15}, 0xd4c1000, 0xd4d2030, 0xd4d2050) stub.
0032:fixme:ntdll:EtwEventSetInformation (deadbeef, 2, 0xd4cfd70, 43) stub
0032:fixme:nls:GetThreadPreferredUILanguages 00000038, 0xdb0cdb4, 0xdb0cdd0 0xdb0cdb0
0032:fixme:nls:get_dummy_preferred_ui_language (0x38 0xdb0cdb4 0xdb0cdd0 0xdb0cdb0) returning a dummy value (current locale)
2020-08-30 13:26:27.546 rip:107 INFO   Found filelist files: None
2020-08-30 13:26:27.546 rip:108 INFO   Found rawdata files: None
2020-08-30 13:26:27.546 rip:109 INFO   Found this many tiff files: 1
2020-08-30 13:26:27.546 rip:96 INFO Waiting for ripper to finish: 3590 seconds remaining
2020-08-30 13:26:37.557 rip:107 INFO   Found filelist files: None
2020-08-30 13:26:37.558 rip:108 INFO   Found rawdata files: None
2020-08-30 13:26:37.558 rip:109 INFO   Found this many tiff files: 1
2020-08-30 13:26:37.558 rip:112 INFO Detected ripping is complete
2020-08-30 13:26:47.565 rip:114 INFO Killing ripper
2020-08-30 13:26:47.566 rip:116 INFO Ripper has been killed
2020-08-30 13:26:48.567 rip:88 INFO cleaned up!
```

### 3. Run headlessly

If you want to run the same command but headlessly, you can bind your data folder to /data in the container,
and be sure to export environment variables for xvfb-run (a virtual display).

```bash
# create profiles directory to save profiles
mkdir -p profiles

singularity run \
    --env=XVFB_SERVER=:95 \
    --env=XVFB_SCREEN=0 \
    --env=XVFB_RESOLUTION=320x240x8 \
    --env=DISPLAY=:95 \
    --bind ${PWD}/profiles:/PROFILES \
    --bind ${PWD}/overview-23:/data \
    two-photon.sif
```

The command above should work headlessly, and exit the container when all is
finished. Again, if you want to work headlessly without having it automated, just bind
the data to another location. Also please be careful about specifying /usr/bin/python3
directly, as likely a python from a host environment could also be found.
